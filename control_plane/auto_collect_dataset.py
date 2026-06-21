#!/usr/bin/env python3
"""
Tự động hoá toàn bộ pipeline thu thập dataset.
Chạy: sudo python3 auto_collect_dataset.py   (đứng tại control_plane/)
"""

import os
import sys
import time
import subprocess
import glob   
import shutil
from mininet.net import Mininet

# ── Xác định path tuyệt đối dựa theo vị trí thật của file này ──
CONTROL_PLANE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONTROL_PLANE_DIR)
TOPOLOGY_DIR = os.path.join(PROJECT_ROOT, "topology")
P4SRC_DIR = os.path.join(PROJECT_ROOT, "data_plane", "p4src")
DATASET_DIR = os.path.join(CONTROL_PLANE_DIR, "ml_pipeline", "dataset") 
MERGE_SCRIPT = os.path.join(CONTROL_PLANE_DIR, "merge_labels.py")

# network_topo.py, p4_mininet.py, scenario_simulator.py đều nằm ở topology/
sys.path.insert(0, TOPOLOGY_DIR)
from network_topo import EnterpriseDDoSTopo, disable_ipv6   # noqa: E402
from p4_mininet import P4Switch, P4Host                      # noqa: E402
import scenario_simulator                                     # noqa: E402


def banner(msg):
    print(f"\n{'='*65}\n{msg}\n{'='*65}")


def cleanup_old_env():
    banner("🧹 [1/6] DỌN MÔI TRƯỜNG CŨ")

    # Giết TẤT CẢ tiến trình liên quan, không chỉ pkill 1 lần
    for _ in range(3):  # lặp vài lần vì có thể có process con sinh lại
        subprocess.run("sudo pkill -9 -f run_demo.sh", shell=True, capture_output=True)
        subprocess.run("sudo pkill -9 -f 'nc -z localhost 9090'", shell=True, capture_output=True)
        subprocess.run("sudo pkill -9 -f simple_switch", shell=True, capture_output=True)
        subprocess.run("sudo pkill -9 -f simple_switch_CLI", shell=True, capture_output=True)
        time.sleep(0.5)

    result = subprocess.run("sudo mn -c", shell=True, capture_output=True, text=True)
    print(result.stdout)
    if "Cleanup complete" not in result.stdout:
        print(result.stderr)
        print("⚠️  'mn -c' báo lỗi.")

    subprocess.run("sudo fuser -k -9 9090/tcp", shell=True, capture_output=True)
    time.sleep(1)

    # ─── XÁC MINH: đảm bảo port 9090 THỰC SỰ trống trước khi tiếp tục ───
    check = subprocess.run("sudo fuser 9090/tcp", shell=True, capture_output=True, text=True)
    if check.stdout.strip():
        print(f"❌ Port 9090 vẫn còn process chiếm dụng: {check.stdout.strip()}")
        print("   Đang thử force-kill lần cuối...")
        subprocess.run(f"sudo kill -9 {check.stdout.strip()}", shell=True, capture_output=True)
        time.sleep(2)

    # Diệt sạch traffic-gen còn sót
    leftover = subprocess.run(
        "ps aux | grep -E 'ping |hping3|iperf|curl' | grep -v grep",
        shell=True, capture_output=True, text=True
    )
    if leftover.stdout.strip():
        print("⚠️  Tiến trình traffic-gen còn sót:")
        print(leftover.stdout)
        subprocess.run("sudo pkill -9 -f 'ping '", shell=True, capture_output=True)
        subprocess.run("sudo pkill -9 -f hping3", shell=True, capture_output=True)
        subprocess.run("sudo pkill -9 -f iperf", shell=True, capture_output=True)
        subprocess.run("sudo pkill -9 -f 'curl'", shell=True, capture_output=True)

    # Dọn network namespace mồ côi (nếu mn -c không dọn hết)
    subprocess.run("sudo ip -all netns delete", shell=True, capture_output=True)

    print("✅ Đã dọn xong, đã xác minh port 9090 trống.")

def compile_p4():
    banner("🚀 [2/6] COMPILE P4 SOURCE")
    json_out = os.path.join(TOPOLOGY_DIR, "p4_compiled.json")

    if os.path.exists(json_out):
        os.remove(json_out)

    # ─── XÁC MINH NGAY: in ra đúng ngưỡng t_pck đang có trong ingress.p4 ───
    ingress_path = os.path.join(P4SRC_DIR, "ingress.p4")
    grep_result = subprocess.run(
        f"grep -n 't_pck >=' {ingress_path}", shell=True, capture_output=True, text=True
    )
    print(f"[*] Ngưỡng t_pck hiện tại trong ingress.p4:\n{grep_result.stdout.strip()}")

    cmd = f"p4c-bm2-ss --p4v 16 -o {json_out} main.p4"
    result = subprocess.run(cmd, shell=True, cwd=P4SRC_DIR, capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("❌ Compile P4 thất bại — dừng pipeline.")
    print("✅ Compile thành công.")

def get_simple_switch_pids():
    result = subprocess.run(
        "pgrep -x simple_switch", shell=True, capture_output=True, text=True
    )
    pids = [p for p in result.stdout.strip().split('\n') if p]
    return pids


def wait_for_thrift_port(expected_pid=None, port=9090, timeout=20):
    print(f"[*] Đang chờ thrift port {port}...")
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(f"nc -z localhost {port}", shell=True, capture_output=True)
        if result.returncode == 0:
            # Xác minh thêm: đúng PID switch hiện tại có đang sống không,
            # và không có nhiều hơn 1 tiến trình simple_switch đang chạy
            pids = get_simple_switch_pids()
            if len(pids) == 0:
                print("⚠️  Port mở nhưng không tìm thấy tiến trình simple_switch — thử lại...")
            elif len(pids) > 1:
                raise RuntimeError(
                    f"❌ Phát hiện {len(pids)} tiến trình simple_switch cùng chạy "
                    f"(PIDs: {pids}) — môi trường chưa sạch, dừng để tránh DUPLICATE_ENTRY."
                )
            elif expected_pid and pids[0] != str(expected_pid):
                print(f"⚠️  PID đang nghe ({pids[0]}) khác PID switch mới khởi tạo ({expected_pid}).")
            else:
                print(f"✅ Switch đã sẵn sàng (PID: {pids[0]}).")
                return
        time.sleep(1)
    raise RuntimeError(f"❌ Switch không lên port {port} sau {timeout}s.")


def load_switch_rules():
    commands_file = os.path.join(TOPOLOGY_DIR, "s1-commands.txt")
    if not os.path.exists(commands_file):
        raise RuntimeError(f"❌ Không tìm thấy {commands_file}")

    cmd = f"simple_switch_CLI --thrift-port 9090 < {commands_file}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("❌ Nạp s1-commands.txt thất bại.")
    print("✅ Đã nạp xong bảng forwarding + mirroring.")


def reset_temp_datasets():
    banner("🧹 DỌN DẸP FILE DATASET TẠM TỪ LẦN TRƯỚC")
    for fname in ["raw_telemetry.csv", "ground_truth.csv", "Final_Labeled_Dataset.csv"]:
        target = os.path.join(DATASET_DIR, fname)
        if os.path.exists(target):
            os.remove(target)
            print(f"  [-] Đã xóa: {fname}")
    print("✅ Đã dọn sạch file tạm, sẵn sàng cho luồng dữ liệu mới.")

def save_versioned_dataset():
    banner("💾 LƯU PHIÊN BẢN DATASET (VERSIONING)")
    final_csv = os.path.join(DATASET_DIR, "Final_Labeled_Dataset.csv")
    
    if not os.path.exists(final_csv):
        print("⚠️ Không tìm thấy Final_Labeled_Dataset.csv để lưu.")
        return

    # Tìm các file dataset_v*.csv hiện có trong thư mục
    existing_versions = glob.glob(os.path.join(DATASET_DIR, "dataset_v*.csv"))
    max_v = 0
    
    for f in existing_versions:
        basename = os.path.basename(f)
        try:
            # Cắt bỏ chữ "dataset_v" và ".csv" để lấy ra số version
            v_num = int(basename.replace("dataset_v", "").replace(".csv", ""))
            if v_num > max_v:
                max_v = v_num
        except ValueError:
            continue

    # Tăng version lên 1
    next_v = max_v + 1
    new_filename = f"dataset_v{next_v}.csv"
    new_filepath = os.path.join(DATASET_DIR, new_filename)

    # Copy file Final ra thành bản version mới
    shutil.copy2(final_csv, new_filepath)
    print(f"🎉 Đã lưu trữ thành công bộ Dataset tại: {new_filename}")

def start_controller(h5):
    banner("🛡️ [4/6] KHỞI ĐỘNG CONTROLLER (DATA COLLECTION MODE)")
    log_file = "/tmp/sdn_controller.log"

    h5.cmd("pkill -f sdn_controller.py > /dev/null 2>&1")
    time.sleep(1)

    cmd = f"cd {CONTROL_PLANE_DIR} && nohup python3 sdn_controller.py > {log_file} 2>&1 &"
    h5.cmd(cmd)
    time.sleep(3)

    check = h5.cmd("pgrep -f sdn_controller.py")
    if not check.strip():
        print(f"❌ Controller không khởi động được. Xem log: {log_file}")
        print(h5.cmd(f"cat {log_file}"))
        raise RuntimeError("Controller start thất bại.")

    print(f"✅ Controller đang chạy trên h5 (PID: {check.strip()}).")
    print(f"   Log realtime: tail -f {log_file}")


def stop_controller(h5):
    banner("⛔ [6/6] DỪNG CONTROLLER")
    h5.cmd("pkill -f sdn_controller.py > /dev/null 2>&1")
    time.sleep(1)
    print("✅ Đã dừng Controller.")


def run_merge_labels():
    banner("🔗 MERGE NHÃN -> Final_Labeled_Dataset.csv")
    if not os.path.exists(MERGE_SCRIPT):
        print(f"⚠️  Không tìm thấy {MERGE_SCRIPT}, bỏ qua bước merge.")
        return

    result = subprocess.run(
        f"python3 {MERGE_SCRIPT}", shell=True, cwd=CONTROL_PLANE_DIR,
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        print("⚠️  Merge thất bại — kiểm tra raw_telemetry.csv / ground_truth.csv tay.")
    else:
        print("✅ Đã tạo dataset/Final_Labeled_Dataset.csv")

def check_ethtool_installed():
    result = subprocess.run("which ethtool", shell=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            "❌ Thiếu 'ethtool' — cần để tắt checksum offload (bắt buộc cho BMv2+TCP).\n"
            "   Chạy: sudo apt install -y ethtool"
        )

def main():
    check_ethtool_installed()
    cleanup_old_env()
    compile_p4()
    disable_ipv6()
    reset_temp_datasets()

    banner("🌐 [3/6] DỰNG MẠNG MININET")
    topo = EnterpriseDDoSTopo()
    net = Mininet(topo=topo, host=P4Host, switch=P4Switch, controller=None)
    net.start()

    # ─── TẮT CHECKSUM/SEGMENTATION OFFLOAD TRÊN MỌI HOST ───
    # Bắt buộc cho BMv2 + veth: kernel mặc định "giả định" có NIC thật để
    # tính checksum/segment ở tầng phần cứng, nhưng veth không có NIC thật,
    # simple_switch chỉ đọc raw bytes -> gói TCP/UDP có thể mang checksum/
    # segment sai nếu không tắt các cờ này. Đã xác nhận qua debug thực tế:
    # thiếu phần này khiến TCP timeout im lặng và UDP bị switch không
    # đếm đúng dù traffic đã tới đúng namespace.
    print("[+] Tắt checksum/segmentation offload trên mọi host...")
    for h in net.hosts:
        h.cmd(
            'ethtool -K eth0 '
            'tx off rx off tso off gso off gro off lro off '
            'tx-udp-segmentation off tx-udp_tnl-csum-segmentation off '
            'tx-udp_tnl-segmentation off '
            '2>/dev/null'
        )
    print("✅ Đã tắt offload trên toàn bộ host.")

    try:
        wait_for_thrift_port()
        load_switch_rules()

        print("[+] Cấu hình ARP tĩnh...")
        net.staticArp()
        print("✅ ARP tĩnh đã cấu hình.")

        h5 = net.get('h5')
        start_controller(h5)
        # ─── KIỂM TRA SỚM: đợi 15s rồi xem dòng đầu tiên có hợp lý không ───
        print("[*] Đợi 15s để có vài dòng telemetry đầu tiên, kiểm tra nhanh...")
        time.sleep(15)
        raw_path = os.path.join(DATASET_DIR, "raw_telemetry.csv")
        if os.path.exists(raw_path):
            check = subprocess.run(f"head -3 {raw_path}", shell=True, capture_output=True, text=True)
            print(f"[*] 3 dòng đầu của raw_telemetry.csv:\n{check.stdout}")
        else:
            print("⚠️  Chưa có file raw_telemetry.csv sau 15s — kiểm tra log controller.")

        banner("🎬 [5/6] CHẠY KỊCH BẢN TRAFFIC")
        scenario_simulator.run_scenarios(net)

        stop_controller(h5)

    finally:
        banner("🛑 DỪNG MẠNG MININET")
        net.stop()

    run_merge_labels()
    save_versioned_dataset()

    banner("🎉 HOÀN TẤT TOÀN BỘ PIPELINE THU THẬP DATASET")
    print("Kiểm tra kết quả:")
    print(f"  cat {os.path.join(DATASET_DIR, 'ground_truth.csv')}")
    print(f"  wc -l {os.path.join(DATASET_DIR, 'raw_telemetry.csv')}")
    print(f"  wc -l {os.path.join(DATASET_DIR, 'Final_Labeled_Dataset.csv')}")


if __name__ == '__main__':
    if os.geteuid() != 0:
        print("❌ Cần chạy bằng sudo (Mininet yêu cầu quyền root).")
        sys.exit(1)
    main()