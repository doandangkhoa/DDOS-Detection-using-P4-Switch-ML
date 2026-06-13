Hệ thống học tăng cường (Incremental Learning):
- v1: Train từ CIC-DDoS2019 (offline)
- v2: Retrain từ data P4 thực tế (online)
→ Giải quyết hoàn toàn vấn đề syn_pck yếu
→ Điểm nhấn chuyên nghiệp cho báo cáo ✅

### Bước 1: Chuẩn bị môi trường (Đừng cài thủ công!)
Cách thông minh nhất là sử dụng luôn bộ script cài đặt tự động từ chính dự án p4lang của tổ chức P4. Nó sẽ cài Mininet, phần mềm Switch BMv2, và trình biên dịch P4C cho bạn.

Cài đặt một máy ảo Ubuntu 20.04 LTS (Khuyên dùng bản này vì độ ổn định với P4 rất cao).

Mở Terminal và chạy các lệnh sau để tải script tự động:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/p4lang/tutorials.git
cd tutorials/vm-ubuntu-20.04
```
Chạy script cài đặt (Sẽ mất khoảng 30 - 45 phút tùy cấu hình máy, bạn có thể đi uống cafe):

```bash
sudo ./root-bootstrap.sh
sudo su p4 -c "./user-bootstrap.sh"
```
Sau khi chạy xong, máy ảo của bạn đã có đủ đồ nghề: Mininet, Wireshark, BMv2 (P4 Switch), và p4c.

# Bước 2: Viết Script Topology (Mạng Mininet)
Bạn cần một file Python để khởi tạo mạng lưới gồm: 1 Switch P4 và 3 Hosts (2 Attacker, 1 Server).
Tạo file network_topo.py:

```python
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from p4_mininet import P4Switch, P4Host # Thư viện đi kèm khi cài đặt p4lang

class MyTopo(Topo):
    def __init__(self, **opts):
        Topo.__init__(self, **opts)

        # Thêm P4 Switch
        s1 = self.addSwitch('s1', sw_path='simple_switch', json_path='p4_compiled.json', thrift_port=9090)

        # Thêm Hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01') # Attacker 1
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02') # Attacker 2
        h3 = self.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03') # Victim Server

        # Nối dây
        self.addLink(h1, s1, port2=1)
        self.addLink(h2, s1, port2=2)
        self.addLink(h3, s1, port2=3)

if __name__ == '__main__':
    topo = MyTopo()
    net = Mininet(topo=topo, host=P4Host, switch=P4Switch, controller=None)
    net.start()
    
    print("Mạng Mininet đã khởi động. Gõ 'pingall' để kiểm tra.")
    CLI(net)
    net.stop()
```

### Bước 3: Tích hợp Controller ghi CSV
Bạn khởi động file sdn_controller.py (với hàm log_to_csv mà chúng ta đã thảo luận trước đó). Controller này sẽ lắng nghe ở port 50000 và chờ Switch P4 bắn Telemetry (DDoSReport) lên.

### Bước 4: Kịch bản Sinh Dataset (Thực chiến)
Khi Mininet đã chạy (bạn đang ở giao diện mininet>), hãy mở thêm các cửa sổ Terminal của từng Host bằng lệnh:
mininet> xterm h1 h2 h3

1. Thu thập dữ liệu Benign (Bình thường):
Trên cửa sổ h3 (Server): Mở cổng lắng nghe.

```bash
iperf3 -s
```
Trên cửa sổ h1 & h2 (User): Sinh traffic sạch. Sửa file sdn_controller.py để ghi nhãn là 'Benign'.

```bash
iperf3 -c 10.0.0.3 -t 600  # Tạo luồng TCP bình thường trong 10 phút
ping 10.0.0.3              # Tạo traffic ICMP xen kẽ
```
Lúc này, Switch P4 sẽ đếm tổng số gói tin, số gói SYN (rất ít) và gửi lên Controller. Controller ghi vào file CSV.

2. Thu thập dữ liệu Attack (SYN Flood):
Sửa code trong sdn_controller.py để đổi nhãn ghi file thành 'Syn'.

Trên cửa sổ h1 & h2 (Attacker): Sử dụng hping3 để tạo bão SYN Flood với IP giả mạo.

```bash
# Bắn liên tục gói SYN vào cổng 80 của Server, tốc độ cao (--flood), random IP nguồn
hping3 -S -p 80 --flood --rand-source 10.0.0.3
```
Lúc này, Switch P4 sẽ đếm được lượng traffic tăng vọt, trong đó cờ SYN chiếm 90-100%. Báo cáo gửi lên Controller sẽ được ghi lại thành những dòng dữ liệu tấn công sắc nét.