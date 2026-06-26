import socket
import threading
import time
import os
import re
import subprocess
import csv
from datetime import datetime

from scapy_headers import DDoSReport
from ml_pipeline.predict import TrafficPredictor

CONTROLLER_IP = '0.0.0.0'
CONTROLLER_PORT = 50000

DATA_COLLECTION_MODE = False   # True: chỉ log + dự đoán, KHÔNG enforce rate-limit (tránh làm bẩn data)
ENABLE_LOGGING = False

BENIGN_STREAK_THRESHOLD = 5

# protected_servers: dict {victim_ip: entry_handle}
protected_servers = {}
protected_lock = threading.Lock()

latest_report_lock = threading.Lock()
latest_report = {}

predictor = TrafficPredictor(model_path='ml_pipeline/random_forest.pkl', time_window=2.0, attack_thresh=0.7)

meter_index_pool_lock = threading.Lock()
meter_index_pool = list(range(1, 32))
meter_index_in_use = {}

# ─── BỘ NHỚ ĐỆM GOM DỮ LIỆU WINDOW ───
# Bộ đệm này sẽ cộng dồn các thông số của các bản tin P4 gửi về
current_window_stats = {
    'tot_pck': 0, 
    'tot_bytes': 0, 
    'tcp_pck': 0, 
    'udp_pck': 0, 
    'syn_pck': 0,
    'victim_ip': "0.0.0.0"
}
window_stats_lock = threading.Lock()

def log_raw_telemetry(stats, ts):
    """Ghi log dữ liệu ĐÃ GOM TRONG 1 GIÂY ra file CSV."""
    os.makedirs('ml_pipeline/dataset', exist_ok=True)
    filename = "ml_pipeline/dataset/raw_telemetry.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'tot_pck', 'tot_bytes', 'tcp_pck', 'udp_pck', 'syn_pck', 'victim_ip'])
        
        writer.writerow([
            ts, # Dùng chung 1 timestamp cho cả window
            stats['tot_pck'], 
            stats['tot_bytes'],
            stats['tcp_pck'], 
            stats['udp_pck'],
            stats['syn_pck'], 
            stats['victim_ip']
        ])
def run_switch_cli(command_str):
    """Chạy 1 lệnh CLI vào simple_switch, xuyên qua namespace gốc bằng nsenter,
    không dùng echo|pipe qua nhiều lớp shell (tránh lỗi escape ký tự)."""
    result = subprocess.run(
        ["nsenter", "-t", "1", "-n", "simple_switch_CLI", "--thrift-port", "9090"],
        input=command_str,
        capture_output=True,
        text=True
    )
    return result
    
def apply_rate_limit(victim_ip):
    """Push Rate Limiting rule down to P4 Switch, lưu lại handle + idx để gỡ sau."""
    with protected_lock:
        if victim_ip in protected_servers:
            print(f"  [i] Máy chủ {victim_ip} đang được bảo vệ bởi Rate Limit.")
            return

    # Cấp index TRƯỚC, và chỉ "chiếm chỗ" trong protected_servers SAU KHI
    # chắc chắn có index hợp lệ — tránh rò trạng thái khi hết slot.
    with meter_index_pool_lock:
        if not meter_index_pool:
            print("  [!] Hết slot meter khả dụng, không thể bảo vệ thêm victim mới.")
            return
        idx = meter_index_pool.pop(0)
        meter_index_in_use[victim_ip] = idx

    print(f"  🛡️ BẢO VỆ MỤC TIÊU: Kích hoạt Rate Limit cho {victim_ip} (meter idx={idx})")

    cmd_str = f"table_add table_rate_limit action_set_meter_index {victim_ip} => {idx}\n"
    result =  run_switch_cli(cmd_str)

    if "DUPLICATE_ENTRY" in result.stdout:
        print(f"  ⚠️  Switch đã có rule cho {victim_ip} từ trước (có thể do controller "
              f"restart mất state). Dọn rule cũ rồi thử lại...")
        run_switch_cli("table_clear table_rate_limit\n")
        result = run_switch_cli(cmd_str)   # thử lại 1 lần sau khi dọn

    handle = None
    match = re.search(r"handle\s+(\d+)", result.stdout)
    if match:
        handle = int(match.group(1))

    if handle is None:
        print(f"  ❌ THẤT BẠI: Không thể áp Rate Limit cho {victim_ip} — switch không phản hồi.")
        print(f"     CLI output: {result.stdout.strip()} {result.stderr.strip()}")
        # Trả lại idx vào pool vì chưa thực sự dùng
        with meter_index_pool_lock:
            meter_index_in_use.pop(victim_ip, None)
            meter_index_pool.append(idx)
        return   # KHÔNG lưu vào protected_servers — để lần sau window_worker() gọi lại apply_rate_limit()

    meter_result = run_switch_cli(f"meter_set_rates meter_syn_flood {idx} 0.125:15000 0.25:30000\n")
    if "Error" in meter_result.stdout:
        print(f"  ⚠️  Lỗi khi set meter rate: {meter_result.stdout.strip()}")

    with protected_lock:
        protected_servers[victim_ip] = handle
    print(f"  ✅ Rate Limit đã áp dụng thành công (handle={handle}).")

def remove_rate_limit(victim_ip):
    with protected_lock:
        if victim_ip not in protected_servers:
            return
        handle = protected_servers.pop(victim_ip)

    with meter_index_pool_lock:
        idx = meter_index_in_use.pop(victim_ip, None)
        if idx is not None:
            meter_index_pool.append(idx)

    if handle is None:
        print(f"  [!] Không có handle hợp lệ cho {victim_ip}, bỏ qua bước gỡ table_delete.")
        return

    print(f"  ✅ GỠ BẢO VỆ: {victim_ip} đã sạch, gỡ Rate Limit (handle={handle}).")
    run_switch_cli(f"table_delete table_rate_limit {handle}\n")


def unprotect_all():
    with protected_lock:
        victims = list(protected_servers.keys())
    for v in victims:
        remove_rate_limit(v)


def window_worker():
    """Luồng trung tâm: Chốt sổ mỗi giây, ghi log, gọi AI dự đoán và ra quyết định."""
    global current_window_stats
    benign_streak = 0

    while True:
        # 1. Đợi đúng 1 khoảng thời gian 
        time.sleep(predictor.time_window)

        # 2. "Khóa" và copy dữ liệu hiện tại, đồng thời reset bộ đệm
        with window_stats_lock:
            stats_to_process = current_window_stats.copy()
            current_window_stats = {
                'tot_pck': 0, 'tot_bytes': 0, 'tcp_pck': 0, 'udp_pck': 0, 'syn_pck': 0, 'victim_ip': "0.0.0.0"
            }

        # Bỏ qua nếu trong x s qua không có traffic nào
        if stats_to_process['tot_pck'] == 0:
            continue

        current_ts = time.time()

        # 3. Ghi dữ liệu đã gom ra CSV (Sinh Dataset thực tế)
        if ENABLE_LOGGING:
            log_raw_telemetry(stats_to_process, current_ts)

        # 4. Đưa dữ liệu đã gom vào Pipeline AI
        result = predictor.analyze_single_window(stats_to_process) 
        
        if result is None:
            continue

        now = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{now}] ── KẾT QUẢ PHÂN TÍCH ───────────────────")
        print(f"  Trạng thái   : {result['label']}")
        print(f"  Tỷ lệ độc hại: {result['attack_ratio']}% ")

        # 5. Xử lý Mitigation
        if result['label'] == 'Attack':
            benign_streak = 0
            print(f"  🚨 PHÁT HIỆN DẤU HIỆU SYN FLOOD!")

            victim_ip = stats_to_process.get('victim_ip')

            if victim_ip and victim_ip != "0.0.0.0":
                print(f"  🎯 NẠN NHÂN (xác định bởi Switch): {victim_ip}")
                if not DATA_COLLECTION_MODE:
                    apply_rate_limit(victim_ip)
                else:
                    print("  [DATA COLLECTION] Bỏ qua enforcement để giữ traffic gốc cho dataset.")
            else:
                print(f"  [!] Chưa có victim_ip hợp lệ trong telemetry, bỏ qua window này.")
        else:
            with protected_lock:
                has_protected = len(protected_servers) > 0

            if has_protected:
                benign_streak += 1
                print(f"  [i] Traffic bình thường ({benign_streak}/{BENIGN_STREAK_THRESHOLD} window sạch liên tiếp).")
                if benign_streak >= BENIGN_STREAK_THRESHOLD:
                    unprotect_all()
                    benign_streak = 0
            else:
                benign_streak = 0


def start_controller():
    t = threading.Thread(target=window_worker, daemon=True)
    t.start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((CONTROLLER_IP, CONTROLLER_PORT))

    print(f"\n{'='*55}")
    print(f"  🛡️ SDN SECURITY CONTROLLER ĐÃ KHỞI ĐỘNG")
    print(f"  Lắng nghe Telemetry tại port: {CONTROLLER_PORT}")
    status_log = f"BẬT (log thô, gán nhãn qua ground_truth.csv)" if ENABLE_LOGGING else "TẮT"
    print(f"  Chế độ tự sinh Dataset: {status_log}")
    print(f"  Ngưỡng gỡ Rate Limit  : {BENIGN_STREAK_THRESHOLD} window sạch liên tiếp")
    print(f"{'='*55}\n")

    while True:
        try:
            data, _ = sock.recvfrom(4096)
            try:
                report = DDoSReport(data)
                # ─── CỘNG DỒN VÀO BỘ ĐỆM WINDOW ───
                with window_stats_lock:
                    current_window_stats['tot_pck'] += report.tot_pck
                    current_window_stats['tot_bytes'] += report.tot_bytes
                    current_window_stats['tcp_pck'] += report.tcp_pck
                    current_window_stats['udp_pck'] += report.udp_pck
                    current_window_stats['syn_pck'] += report.syn_pck
                    
                    # Chỉ cập nhật IP nếu Switch tìm thấy, giữ lại IP cuối cùng trong 1s
                    if report.victim_ip != "0.0.0.0":
                        current_window_stats['victim_ip'] = report.victim_ip

            except Exception:
                pass

        except KeyboardInterrupt:
            print("\n⛔ Tắt Controller.")
            break
        except Exception as e:
            print(f"[-] Lỗi Socket: {e}")


if __name__ == '__main__':
    start_controller()