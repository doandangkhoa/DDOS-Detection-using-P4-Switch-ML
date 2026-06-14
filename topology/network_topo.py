from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.link import TCLink  # Thư viện cực kỳ quan trọng để giới hạn băng thông
from p4_mininet import P4Switch, P4Host
import os

class RealisticDDoSTopo(Topo):
    def __init__(self, **opts):
        Topo.__init__(self, **opts)

        # 1. Khởi tạo P4 Switch (Đóng vai trò là Edge Firewall / Router)
        # Tắt tính năng pcap_dump mặc định của BMv2 để tránh đầy ổ cứng khi bị DDoS
        s1 = self.addSwitch('s1', 
                            sw_path='simple_switch',
                            json_path='p4_compiled.json', 
                            thrift_port=9090,
                            pcap_dump=False) 

        # 2. Khởi tạo các Hosts (Tách biệt rõ ràng các Zone)
        # 🌐 ZONE: EXTERNAL (Internet)
        h1_user    = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01') # Người dùng bình thường
        h2_hacker  = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02') # Máy chủ Botnet

        # 🏢 ZONE: INTERNAL (DMZ / Data Center)
        h3_server  = self.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03') # Server nạn nhân

        # 3. Kéo cáp vật lý (Sử dụng TCLink để giới hạn băng thông thực tế)
        # Giả lập cáp quang ngoài Internet: Băng thông rộng (100 Mbps), độ trễ 5ms
        self.addLink(h1_user, s1, port2=1, cls=TCLink, bw=100, delay='5ms')
        self.addLink(h2_hacker, s1, port2=2, cls=TCLink, bw=100, delay='5ms')

        # Giả lập cáp mạng nội bộ vào Server: Băng thông hẹp hơn (10 Mbps), độ trễ 1ms
        # Nút thắt cổ chai (Bottleneck) nằm ở đây. Khi hacker bơm 100Mbps vào Switch, cổng số 3 sẽ bị nghẽn!
        self.addLink(h3_server, s1, port2=3, cls=TCLink, bw=10, delay='1ms')


def disable_ipv6():
    """Tắt IPv6 trên tất cả các interface để tránh nhiễu dữ liệu Telemetry"""
    print("[*] Đang tắt IPv6 để làm sạch môi trường mạng...")
    os.system("sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1")
    os.system("sysctl -w net.ipv6.conf.default.disable_ipv6=1 > /dev/null 2>&1")
    os.system("sysctl -w net.ipv6.conf.lo.disable_ipv6=1 > /dev/null 2>&1")


if __name__ == '__main__':
    # Tắt IPv6 trước khi dựng mạng
    disable_ipv6()
    
    # Khởi tạo Topology
    topo = RealisticDDoSTopo()
    
    # Chạy Mininet với controller mặc định bị vô hiệu hóa (vì P4 tự xử lý Forwarding)
    net = Mininet(topo=topo, host=P4Host, switch=P4Switch, controller=None)
    
    print("\n" + "="*50)
    print("🚀 KHỞI ĐỘNG MÔI TRƯỜNG MẠNG SDN/P4 THỰC TẾ")
    print("="*50)
    print("  [+] Switch P4 s1 đang lắng nghe Thrift CLI tại port 9090")
    print("  [+] Băng thông h1, h2 (Internet) -> s1 : 100 Mbps")
    print("  [+] Băng thông s1 -> h3 (DMZ Server)   : 10 Mbps (Bottleneck)")
    print("="*50 + "\n")
    
    net.start()
    
    # Mở giao diện tương tác
    CLI(net)
    
    # Dọn dẹp sau khi gõ lệnh 'exit'
    net.stop()