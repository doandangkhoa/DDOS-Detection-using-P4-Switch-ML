import time
import csv
import os

# ==========================================================
# DATASET PATH
# ==========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

DATASET_DIR = os.path.join(
    PROJECT_ROOT,
    "control_plane",
    "ml_pipeline",
    "dataset"
)

GROUND_TRUTH_FILE = os.path.join(
    DATASET_DIR,
    "ground_truth.csv"
)

# ==========================================================
# LOGGER
# ==========================================================
def log_event(label, description, start_ts, end_ts):
    os.makedirs(DATASET_DIR, exist_ok=True)
    file_exists = os.path.isfile(GROUND_TRUTH_FILE)

    with open(GROUND_TRUTH_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "start_ts",
                "end_ts",
                "label",
                "description"
            ])
        writer.writerow([
            start_ts,
            end_ts,
            label,
            description
        ])

# ==========================================================
# CLEANUP (SAFE NAMESPACE MODE)
# ==========================================================
def restart_victim_servers(h3, h4):
    """Restart server trên h3 chuẩn mực nhất"""
    h3.cmd('pkill -9 -f "python3 -m http.server" > /dev/null 2>&1')
    h3.cmd('pkill -9 -f "iperf" > /dev/null 2>&1')
    time.sleep(0.5)

    # nohup giúp web server Python sống sót sau khi Mininet đóng shell
    h3.cmd("nohup python3 -m http.server 80 > /tmp/h3_http.log 2>&1 &")
    
    # cờ -D ép iperf tự động chạy dưới dạng tiến trình nền (Daemon)
    h3.cmd("iperf -s -p 5001 -D")
    h3.cmd("iperf -s -u -p 5002 -D")

def cleanup(h1, h2, h4):
    """
    Dọn dẹp an toàn: Chỉ gọi lệnh killall bên trong namespace của các Host Client.
    Tuyệt đối không đụng vào h3 (Victim Server) để giữ kết nối.
    """
    clients = [h1, h2, h4]
    for h in clients:
        h.cmd("pkill -9 -f bash > /dev/null 2>&1")
        h.cmd("pkill -9 -f 'while true' > /dev/null 2>&1")
        h.cmd("killall -9 ping > /dev/null 2>&1")
        h.cmd("killall -9 hping3 > /dev/null 2>&1")
        h.cmd("killall -9 curl > /dev/null 2>&1")
        h.cmd("killall -9 wget > /dev/null 2>&1")
        h.cmd("killall -9 iperf > /dev/null 2>&1")
        h.cmd("killall -9 iperf3 > /dev/null 2>&1")

# ==========================================================
# BACKGROUND TRAFFIC
# ==========================================================
def start_background_traffic(h1, h2, h4):
    # 1. Nhịp tim ICMP
    h1.cmd("ping -i 0.05 10.0.0.3 > /dev/null 2>&1 &")
    
    # 2. Ép Mininet tạo file bash script rồi chạy ngầm để né 100% lỗi Syntax
    h1.cmd("echo 'while true; do curl -s http://10.0.0.3/ > /dev/null; sleep 0.05; done' > /tmp/h1_curl.sh")
    h1.cmd("bash /tmp/h1_curl.sh > /dev/null 2>&1 &")

    h2.cmd("echo 'while true; do curl -s http://10.0.0.3/ > /dev/null; sleep 0.1; done' > /tmp/h2_curl.sh")
    h2.cmd("bash /tmp/h2_curl.sh > /dev/null 2>&1 &")

    h4.cmd("echo 'while true; do iperf -c 10.0.0.3 -p 5001 -t 10; sleep 0.5; done' > /tmp/h4_iperf.sh")
    h4.cmd("bash /tmp/h4_iperf.sh > /dev/null 2>&1 &")

# ==========================================================
# MAIN SCENARIOS RUNNER
# ==========================================================
def run_scenarios(net):
    h1 = net.get("h1")
    h2 = net.get("h2")
    h3 = net.get("h3")
    h4 = net.get("h4")

    print("\n[*] Đang khởi động các dịch vụ nền trên Victim Server (h3)...")
    restart_victim_servers(h3, h4)
    time.sleep(3)

    scenarios = [
        # ==================================================
        # 1 NORMAL WEB TRAFFIC
        # ==================================================
        (
            "Benign",
            "Normal office traffic",
            120,
            lambda: start_background_traffic(h1, h2, h4)
        ),

        # ==================================================
        # 2 HEAVY TCP BENIGN (LARGE BACKUP)
        # ==================================================
        (
            "Benign",
            "Large backup transfer (Heavy TCP)",
            120,
            lambda: (
                start_background_traffic(h1, h2, h4),
                h1.cmd("iperf -c 10.0.0.3 -p 5001 -t 120 > /dev/null 2>&1 &"),
                h2.cmd("iperf -c 10.0.0.3 -p 5001 -t 120 > /dev/null 2>&1 &")
                # h4 đã chạy iperf ở background traffic, không thêm luồng thừa
            )
        ),

        # ==================================================
        # 3 HEAVY UDP BENIGN (DNS/VIDEO STYLE)
        # ==================================================
        (
            "Benign",
            "DNS/Video style UDP traffic",
            120,
            lambda: (
                start_background_traffic(h1, h2, h4),
                h1.cmd("iperf -u -c 10.0.0.3 -p 5002 -b 15M -t 120 > /dev/null 2>&1 &"),
                h2.cmd("iperf -u -c 10.0.0.3 -p 5002 -b 10M -t 120 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 4 FLASH CROWD (TCP + UDP + CURL)
        # ==================================================
        (
            "Benign",
            "Flash crowd event with mixed protocols",
            120,
            lambda: (
                h1.cmd("iperf -c 10.0.0.3 -p 5001 -t 120 > /dev/null 2>&1 &"),
                h2.cmd("iperf -c 10.0.0.3 -p 5001 -t 120 > /dev/null 2>&1 &"),
                h4.cmd("iperf -c 10.0.0.3 -p 5001 -t 120 > /dev/null 2>&1 &"),
                h4.cmd("iperf -u -c 10.0.0.3 -p 5002 -b 5M -t 120 > /dev/null 2>&1 &"),
                h1.cmd("while true; do curl -s http://10.0.0.3 > /dev/null; sleep 0.1; done > /dev/null 2>&1 &"),
                h2.cmd("while true; do curl -s http://10.0.0.3 > /dev/null; sleep 0.1; done > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 5 LOW RATE SYN FLOOD
        # ==================================================
        (
            "Attack",
            "Low and slow SYN flood",
            120,
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd("hping3 -S -p 80 -i u5000 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 6 MEDIUM SYN FLOOD
        # ==================================================
        (
            "Attack",
            "Medium SYN flood",
            120,
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd("hping3 -S -p 80 -i u1000 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 7 HIGH RATE SYN FLOOD
        # ==================================================
        (
            "Attack",
            "High rate SYN flood",
            120,
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd("hping3 -S -p 80 --flood 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 8 MIXED TRAFFIC ATTACK
        # ==================================================
        (
            "Attack",
            "Flash crowd mixed with SYN flood",
            120,
            lambda: (
                h1.cmd("iperf -c 10.0.0.3 -p 5001 -t 120 > /dev/null 2>&1 &"),
                h4.cmd("iperf -c 10.0.0.3 -p 5001 -t 120 > /dev/null 2>&1 &"),
                h1.cmd("while true; do curl -s http://10.0.0.3 > /dev/null; sleep 0.1; done > /dev/null 2>&1 &"),
                h4.cmd("while true; do curl -s http://10.0.0.3 > /dev/null; sleep 0.1; done > /dev/null 2>&1 &"),
                h2.cmd("hping3 -S -p 80 --flood 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 9 CHANGE VICTIM
        # ==================================================
        (
            "Attack",
            "Victim switching attack (target h4)",
            120,
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd("hping3 -S -p 80 --flood 10.0.0.4 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 10 ATTACK OFF
        # ==================================================
        (
            "Benign",
            "Recovery after attack",
            120,
            lambda: start_background_traffic(h1,h2,h4)
        ),
    ]

    for label, description, duration, action in scenarios:
        print(f"\n[SCENARIO] Đang chạy: {description} ({duration}s)")
        
        start_ts = time.time()
        action()
        time.sleep(duration)
        end_ts = time.time()
        
        log_event(label, description, start_ts, end_ts)

        cleanup(h1, h2, h4)
        restart_victim_servers(h3, h4)
        print("   -> [Cooldown] Đợi 10 giây để Switch xả sạch rác trong telemetry window...")
        time.sleep(10)

    # ==========================================================
    # FINAL CLEANUP
    # ==========================================================
    cleanup(h1, h2, h4)
    print("\n[*] Đang dọn dẹp Victim Servers trên h3...")
    os.system('pkill -9 -f "python3 -m http.server" > /dev/null 2>&1')
    h3.cmd('killall -9 iperf > /dev/null 2>&1')
    h3.cmd('killall -9 iperf3 > /dev/null 2>&1')

    print("\n✅ [+] Dataset generation completed")
    print(f"✅ [+] Ground truth: {GROUND_TRUTH_FILE}")