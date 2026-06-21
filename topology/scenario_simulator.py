import time
import csv
import os
import random

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
    for h in [h3, h4]:
        h.cmd('pkill -9 -f "python3 -m http.server" > /dev/null 2>&1')
        h.cmd('pkill -9 -f "iperf" > /dev/null 2>&1')
    time.sleep(0.5)

    h3.cmd("mkdir -p /tmp/h3_webroot")
    h3.cmd("test -f /tmp/h3_webroot/bigfile.bin || dd if=/dev/zero of=/tmp/h3_webroot/bigfile.bin bs=1M count=100 2>/dev/null")
    h3.cmd("cd /tmp/h3_webroot && nohup python3 -m http.server 80 > /tmp/h3_http.log 2>&1 &")
    h3.cmd("iperf -s -p 5001 -D")
    h3.cmd("iperf -s -u -p 5002 -D")

def cleanup(h1, h2, h4):
    """
    Dọn dẹp an toàn: Chỉ gọi lệnh killall bên trong namespace của các Host Client.
    Tuyệt đối không đụng vào h3 (Victim Server) để giữ kết nối.
    """
    clients = [h1, h2, h4]
    for h in clients:
        h.cmd("pkill -9 -f '/tmp/.*_curl.sh' > /dev/null 2>&1")
        h.cmd("pkill -9 -f '/tmp/.*_wget.sh' > /dev/null 2>&1")
        h.cmd("killall -9 ping > /dev/null 2>&1")
        h.cmd("killall -9 hping3 > /dev/null 2>&1")
        h.cmd("killall -9 curl > /dev/null 2>&1")
        h.cmd("killall -9 wget > /dev/null 2>&1")
        h.cmd("killall -9 iperf > /dev/null 2>&1")
        h.cmd("killall -9 iperf3 > /dev/null 2>&1")


def curl_loop(h, sleep_interval, tag):
    script_path = f"/tmp/{tag}_curl.sh"
    h.cmd(f"echo 'while true; do curl -s http://10.0.0.3/ > /dev/null; sleep {sleep_interval}; done' > {script_path}")
    h.cmd(f"bash {script_path} > /dev/null 2>&1 &")

# ==========================================================
# BACKGROUND TRAFFIC
# Random hoá nhịp curl mỗi lần gọi, để các lần chạy khác nhau
# không tạo ra điểm dữ liệu giống hệt nhau (tránh model học "vẹt"
# theo đúng 1 vài cụm cố định).
# ==========================================================
def start_background_traffic(h1, h2, h4):
    h1.cmd(f"ping -i {round(random.uniform(0.05, 0.2), 2)} 10.0.0.3 > /dev/null 2>&1 &")

    curl_loop(h1, round(random.uniform(0.08, 0.15), 3), "h1_bg")
    curl_loop(h2, round(random.uniform(0.2, 0.4), 3), "h2_bg")

    h4.cmd(
        "iperf -c 10.0.0.3 -p 5001 -t 9999 > /dev/null 2>&1 &"
    )

    h4.cmd(
        f"iperf -u -c 10.0.0.3 -p 5002 -b {random.randint(1, 3)}M -t 9999 > /dev/null 2>&1 &"
    )
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

    # ─── scenarios được build LẠI mỗi lần gọi run_scenarios(),
    # nên mọi random.randint/uniform/choice bên trong các lambda chỉ
    # được tính tại đúng thời điểm action() chạy -> mỗi lần chạy script
    # (mỗi lần gọi auto_collect_dataset.py) sẽ cho ra tham số khác nhau,
    # tránh lặp lại y hệt giữa các lần -> giảm nguy cơ model học theo
    # đúng vài cụm giá trị cố định (nguyên nhân chính gây overfit trước đó).
    scenarios = [
        # ==================================================
        # 1 NORMAL WEB TRAFFIC
        # ==================================================
        (
            "Benign",
            "Normal office traffic",
            random.randint(90, 150),
            lambda: start_background_traffic(h1, h2, h4)
        ),

        # ==================================================
        # 2 HEAVY TCP BENIGN (LARGE BACKUP)
        # ==================================================
        (
            "Benign",
            "Large backup transfer (Heavy TCP)",
            random.randint(90, 150),
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
            random.randint(90, 150),
            lambda: (
                start_background_traffic(h1, h2, h4),
                h1.cmd(f"iperf -u -c 10.0.0.3 -p 5002 -b {random.randint(8, 18)}M -t 120 > /dev/null 2>&1 &"),
                h2.cmd(f"iperf -u -c 10.0.0.3 -p 5002 -b {random.randint(5, 12)}M -t 120 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 4 FLASH CROWD (TCP + UDP + CURL)
        # ==================================================
        (
            "Benign",
            "Flash crowd event with mixed protocols",
            random.randint(60, 100),
            lambda: (
                h1.cmd("iperf -c 10.0.0.3 -p 5001 -t 100 > /dev/null 2>&1 &"),
                h2.cmd("iperf -c 10.0.0.3 -p 5001 -t 100 > /dev/null 2>&1 &"),
                h4.cmd("iperf -c 10.0.0.3 -p 5001 -t 100 > /dev/null 2>&1 &"),
                h4.cmd(f"iperf -u -c 10.0.0.3 -p 5002 -b {random.randint(3, 7)}M -t 100 > /dev/null 2>&1 &"),
                curl_loop(h1, round(random.uniform(0.05, 0.15), 3), "h1_flash"),
                curl_loop(h2, round(random.uniform(0.05, 0.15), 3), "h2_flash"),
            )
        ),

        # ==================================================
        # 5 LOW RATE SYN FLOOD
        # ==================================================
        (
            "Attack",
            "Low and slow SYN flood",
            random.randint(90, 150),
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd(f"hping3 -S -p 80 -i u{random.randint(4000, 8000)} 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 6 MEDIUM SYN FLOOD
        # (đã sửa: thiếu f-string khiến hping3 nhận literal "u{...}"
        # và không gửi được gói nào — bug nghiêm trọng làm bẩn nhãn Attack)
        # ==================================================
        (
            "Attack",
            "Medium SYN flood",
            random.randint(90, 150),
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd(f"hping3 -S -p 80 -i u{random.randint(800, 3000)} 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 7 HIGH RATE SYN FLOOD
        # ==================================================
        (
            "Attack",
            "High rate SYN flood",
            random.randint(60, 100),
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
            random.randint(60, 100),
            lambda: (
                h1.cmd("iperf -c 10.0.0.3 -p 5001 -t 100 > /dev/null 2>&1 &"),
                h4.cmd("iperf -c 10.0.0.3 -p 5001 -t 100 > /dev/null 2>&1 &"),
                curl_loop(h1, round(random.uniform(0.05, 0.15), 3), "h1_flash"),
                curl_loop(h4, round(random.uniform(0.05, 0.15), 3), "h4_flash"),
                h2.cmd("hping3 -S -p 80 --flood 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 9 CHANGE VICTIM
        # ==================================================
        (
            "Attack",
            "Victim switching attack (target h4)",
            random.randint(90, 150),
            lambda: (
                start_background_traffic(h1, h2, h4),
                h4.cmd("nohup python3 -m http.server 80 > /tmp/h4_http.log 2>&1 &"),
                h2.cmd(
                    f"hping3 -S -p 80 {'--flood' if random.random() < 0.5 else f'-i u{random.randint(1000, 5000)}'} "
                    f"10.0.0.4 > /dev/null 2>&1 &"
                )
            )
        ),

        # ==================================================
        # 10 DOWNLOAD LARG FILES 
        # ==================================================
        (
            "Benign",
            "Large file download (high TCP volume, very low SYN)",
            random.randint(90, 150),
            lambda: (
                h1.cmd("echo 'while true; do wget -q http://10.0.0.3/bigfile.bin -O /dev/null; sleep 0.5; done' > /tmp/h1_wget.sh"),
                h1.cmd("bash /tmp/h1_wget.sh > /dev/null 2>&1 &"),
                h4.cmd("echo 'while true; do wget -q http://10.0.0.3/bigfile.bin -O /dev/null; sleep 0.8; done' > /tmp/h4_wget.sh"),
                h4.cmd("bash /tmp/h4_wget.sh > /dev/null 2>&1 &"),
            )
        ),

        # ==================================================
        # 11 BENIGN VỚI SYN RATIO CAO BẤT THƯỜNG (Flash crowd cực đoan)
        # Nhiều client mở RẤT NHIỀU connection ngắn liên tục -> đẩy syn_ratio benign
        # lên gần vùng "trông giống Attack", buộc model phải dựa vào pattern khác
        # (ví dụ avg_length, tcp_ratio) thay vì chỉ riêng syn_ratio.
        # ==================================================
        (
            "Benign",
            "Extreme flash crowd - many short-lived connections",
            random.randint(60, 100),
            lambda: (
                curl_loop(h1, round(random.uniform(0.015, 0.035), 3), "h1_extreme"),
                curl_loop(h2, round(random.uniform(0.015, 0.035), 3), "h2_extreme"),
                curl_loop(h4, round(random.uniform(0.02, 0.04), 3), "h4_extreme"),
            )
        ),

        # ==================================================
        # 12 ATTACK RẤT CHẬM, GẦN NGƯỠNG BENIGN (stealth thật sự)
        # Tốc độ thấp hơn nhiều so với kịch bản 5, để syn_ratio rơi gần vùng benign
        # ==================================================
        (
            "Attack",
            "Ultra-stealth SYN flood (near-benign rate)",
            random.randint(90, 150),
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd(f"hping3 -S -p 80 -i u{random.randint(15000, 30000)} 10.0.0.3 > /dev/null 2>&1 &")
            )
        ),

        # ==================================================
        # 13 ATTACK VỚI TỐC ĐỘ NGẪU NHIÊN (không cố định 1 trong 3 mức cũ)
        # ==================================================
        (
            "Attack",
            "Randomized-rate SYN flood",
            random.randint(90, 150),
            lambda: (
                start_background_traffic(h1, h2, h4),
                h2.cmd(f"hping3 -S -p 80 -i u{random.choice([1500, 3000, 6000, 12000])} 10.0.0.3 > /dev/null 2>&1 &")
            )
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
    h3.cmd("rm -f /tmp/h3_webroot/bigfile.bin")
    
    print("\n✅ [+] Dataset generation completed")
    print(f"✅ [+] Ground truth: {GROUND_TRUTH_FILE}")