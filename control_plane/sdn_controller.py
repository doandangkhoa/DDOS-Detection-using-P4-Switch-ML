import socket
import threading
import time
import os
import csv
from datetime import datetime
from collections import Counter
from scapy.all import sniff, IP, TCP

from scapy_headers import DDoSReport
from ml_pipeline.predict import TrafficPredictor

CONTROLLER_IP = '0.0.0.0'
CONTROLLER_PORT = 50000

# Đổi thành 'Benign' khi chạy traffic sạch. Đổi thành 'Syn' khi bật hping3.
CURRENT_SCENARIO = 'Benign' 
# Đổi thành False nếu bạn đã thu thập đủ data và chỉ muốn Controller chạy AI bảo vệ
ENABLE_LOGGING = False 

# protected state prevent to sending duplicate decision
protected_servers = set()
protected_lock = threading.Lock()

# ─── STATE CHIA SẺ: report telemetry mới nhất từ Switch ───
# Switch đã tự tính victim_ip bằng heavy-hitter sketch ngay trong data-plane,
# Controller chỉ cần đọc lại giá trị này, không cần tự sniff/DPI nữa.
latest_report_lock = threading.Lock()
latest_report = {}

predictor = TrafficPredictor(model_path='ml_pipeline/random_forest.pkl', time_window=1.0, attack_thresh=0.6)

def log_to_csv(report_dict, label):
    """Ghi trực tiếp Telemetry từ Switch ra file CSV để làm Dataset"""
    # Đảm bảo thư mục dataset tồn tại
    os.makedirs('dataset', exist_ok=True)
    filename = "dataset/Real_Mininet_Telemetry.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as f:
        writer = csv.writer(f)
        # Ghi header nếu file mới
        if not file_exists:
            writer.writerow(['tot_pck', 'tot_bytes', 'tcp_pck', 'udp_pck', 'syn_pck', 'Label'])
            
        writer.writerow([
            report_dict['tot_pck'], 
            report_dict['tot_bytes'],
            report_dict['tcp_pck'], 
            report_dict['udp_pck'], 
            report_dict['syn_pck'], 
            label
        ])

def apply_rate_limit(victim_ip):
    """Push Rate Limiting rule down to P4 Switch"""
    with protected_lock:
        if victim_ip in protected_servers:
            print(f"  [i] Máy chủ {victim_ip} đang được bảo vệ bởi Rate Limit.")
            return 
        protected_servers.add(victim_ip)

    print(f"  🛡️ BẢO VỆ MỤC TIÊU: Kích hoạt Rate Limit cho {victim_ip}")
    
    cmd_table = f"echo 'table_add table_rate_limit action_set_meter_index {victim_ip}/32 => 1' | simple_switch_CLI --thrift-port 9090 > /dev/null 2>&1"
    cmd_meter = f"echo 'meter_array_set_rates meter_syn_flood 1 1000 500' | simple_switch_CLI --thrift-port 9090 > /dev/null 2>&1"

    os.system(cmd_table)
    os.system(cmd_meter)

def window_worker():
    """Luồng chạy ngầm, gọi bộ não ML mỗi giây để hỏi kết quả"""
    while True:
        time.sleep(predictor.time_window)
        result = predictor.analyze_window()
        
        if result is None:
            continue

        now = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{now}] ── KẾT QUẢ PHÂN TÍCH ───────────────────")
        print(f"  Trạng thái   : {result['label']}")
        print(f"  Tỷ lệ độc hại: {result['attack_ratio']}% ")

        # Nếu có tấn công, ra lệnh bóp băng thông
        if result['label'] == 'Attack':
            print(f"  🚨 PHÁT HIỆN DẪU HIỆU SYN FLOOD!")

            # Đọc victim_ip mà Switch đã tự xác định bằng sketch trong data-plane
            with latest_report_lock:
                victim_ip = latest_report.get('victim_ip')

            if victim_ip and victim_ip != "0.0.0.0":
                print(f"  🎯 NẠN NHÂN (xác định bởi Switch): {victim_ip}")
                apply_rate_limit(victim_ip)
            else:
                print(f"  [!] Chưa có victim_ip hợp lệ trong telemetry, bỏ qua window này.")


def start_controller():
    # 1. Bật luồng phân tích ngầm
    t = threading.Thread(target=window_worker, daemon=True)
    t.start()

    # 2. Bật cổng lắng nghe UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((CONTROLLER_IP, CONTROLLER_PORT))

    print(f"\n{'='*55}")
    print(f"  🛡️ SDN SECURITY CONTROLLER ĐÃ KHỞI ĐỘNG")
    print(f"  Lắng nghe Telemetry tại port: {CONTROLLER_PORT}")
    status_log = f"BẬT (Ghi nhãn: {CURRENT_SCENARIO})" if ENABLE_LOGGING else "TẮT"
    print(f"  Chế độ tự sinh Dataset: {status_log}")
    print(f"{'='*55}\n")

    while True:
        try:
            # Nhận chuỗi byte từ Switch
            data, _ = sock.recvfrom(4096)
            
            try:
                # Dùng Scapy để ép kiểu chuỗi byte thành Object
                report = DDoSReport(data)
                
                # Trích xuất thành Dictionary
                report_dict = {
                    'switch_id': report.switch_id,
                    'tot_pck'  : report.tot_pck,
                    'tot_bytes': report.tot_bytes,
                    'tcp_pck'  : report.tcp_pck,
                    'udp_pck'  : report.udp_pck,
                    'syn_pck'  : report.syn_pck,
                    'victim_ip' : report.victim_ip,
                }

                # ─── LƯU LẠI REPORT MỚI NHẤT cho window_worker đọc ───
                with latest_report_lock:
                    latest_report.update(report_dict)
                    
                # ─── GHI DATASET NẾU ĐƯỢC BẬT ───
                if ENABLE_LOGGING:
                    log_to_csv(report_dict, CURRENT_SCENARIO)
                # ────────────────────────────────
                
                # đưa data sang cho AI
                predictor.add_telemetry(report_dict)
                
            except Exception:
                pass

        except KeyboardInterrupt:
            print("\n⛔ Tắt Controller.")
            break
        except Exception as e:
            print(f"[-] Lỗi Socket: {e}")

if __name__ == '__main__':
    start_controller()