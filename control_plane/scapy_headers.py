from scapy.all import Packet, bind_layers, UDP, IP, send
from scapy.fields import IntField, ShortField, IPField
import time
import random

# ════════════════════════════════════════════════════════════
# PHẦN 1: TỪ ĐIỂN DỊCH THUẬT GÓI TIN TỪ P4
# ════════════════════════════════════════════════════════════
class DDoSReport(Packet):
    """
    Cấu trúc bản tin Telemetry từ P4 Switch (Tổng 16 Bytes).
    Khớp với định dạng header bạn đóng gói dưới Data Plane.
    """
    name = "P4_Telemetry_Report"
    
    fields_desc = [
        IntField("switch_id", 1),         # 4 Bytes: ID Switch
        ShortField("tot_pck", 0),         # 2 Bytes: Tổng số gói
        ShortField("tcp_pck", 0),         # 2 Bytes: TCP
        ShortField("udp_pck", 0),         # 2 Bytes: UDP
        ShortField("syn_pck", 0),         # 2 Bytes: SYN
        IPField("dst_ip", "0.0.0.0")      # 4 Bytes: IP của Server nạn nhân
    ]

# Báo cho Scapy biết: Cứ UDP Port 50000 thì ruột bên trong là DDoSReport
bind_layers(UDP, DDoSReport, dport=50000)


# ════════════════════════════════════════════════════════════
# PHẦN 2: CÔNG CỤ TEST (TRAFFIC GENERATOR)
# ════════════════════════════════════════════════════════════
def generate_fake_telemetry(controller_ip="127.0.0.1", port=50000):
    print(f"\n{'='*55}")
    print("🚀 BẮT ĐẦU KỊCH BẢN GIẢ LẬP TRAFFIC TỪ P4 SWITCH")
    print(f"{'='*55}\n")
    
    try:
        counter = 0
        while True:
            counter += 1
            
            # Kịch bản: 5 giây đầu là mạng Bình thường (Benign)
            if counter <= 5:
                print(f"[+] Giây {counter}: Người dùng bình thường đang lướt web...")
                tot = random.randint(100, 600)
                udp = random.randint(5, 50)
                tcp = tot - udp
                syn = int(tcp * random.uniform(0.01, 0.05)) # Tỷ lệ SYN rất thấp
                
            # Kịch bản: Sau giây thứ 5, bắt đầu xả bão SYN Flood (Attack)
            else:
                if counter == 6:
                    print("\n🚨 CẢNH BÁO: HACKER BẮT ĐẦU BẮN SYN FLOOD!\n")
                print(f"[!] Giây {counter}: Gửi bão SYN Flood -> Nạn nhân 10.0.0.5")
                tot = random.randint(1500, 3000)
                udp = random.randint(0, 10)
                tcp = tot - udp
                syn = int(tcp * random.uniform(0.85, 0.98)) # Tỷ lệ SYN cực cao

            fake_report = DDoSReport(
                switch_id = 1,
                tot_pck   = tot,
                tcp_pck   = tcp,
                udp_pck   = udp,
                syn_pck   = syn, 
                dst_ip    = "10.0.0.5"
            )
            
            pkt = IP(dst=controller_ip) / UDP(dport=port) / fake_report
            send(pkt, verbose=False)
            
            time.sleep(10) # Chuẩn hóa: 1 giây Switch gửi báo cáo 1 lần
            
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng công cụ giả lập.")

if __name__ == '__main__':
    # Chạy trực tiếp file này để test
    generate_fake_telemetry()