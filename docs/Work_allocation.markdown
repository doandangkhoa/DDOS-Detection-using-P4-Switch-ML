# TÀI LIỆU QUẢN LÝ ĐỒ ÁN P4-DDoS
**Bao gồm:** Cấu trúc dự án, Lộ trình phát triển 3 tuần & Biên bản thống nhất kỹ thuật hệ thống.

---

## PHẦN A: CẤU TRÚC CÂY THƯ MỤC DỰ ÁN (REPOSITORY STRUCTURE)
Để tránh xung đột mã nguồn (Git conflicts), dự án được phân chia ranh giới vật lý rõ ràng giữa Data Plane và Control Plane.

```text
ddos-p4-rf-project/
│
├── data_plane/                  # 🛠️ KHU VỰC THÀNH VIÊN B (P4)
│   ├── p4src/
│   │   ├── includes/            # Chứa các file định nghĩa
│   │   │   ├── headers.p4       # Định nghĩa Ethernet, IP, TCP, my_int_header_t
│   │   │   └── parsers.p4       # Logic bóc tách gói tin
│   │   ├── ingress.p4           # Logic chính: Đếm Registers, check 10.000 gói, Clone
│   │   ├── egress.p4            # Logic gửi gói tin đi
│   │   └── main.p4              # File gốc gộp tất cả các file trên lại
│   └── build/                   # Nơi chứa file đã biên dịch (.json)
│
├── control_plane/               # 🧠 KHU VỰC THÀNH VIÊN A (Python/AI)
│   ├── ml_pipeline/
│   │   ├── dataset/             # Chứa file CSV của CIC-DDoS2019
│   │   ├── train_rf.py          # Script biến đổi dữ liệu 4 cột và train mô hình
│   │   └── random_forest.pkl    # File mô hình AI đã train xong (để load nhanh)
│   ├── scapy_headers.py         # Class DDoSReport định nghĩa header cho Scapy
│   └── sdn_controller.py        # Lắng nghe báo cáo, chạy AI, bắn lệnh API chặn DDoS
│
├── topology/                    # 🌐 MÔI TRƯỜNG CHẠY CHUNG (Mininet)
│   ├── network_topo.py          # Script Mininet dựng mạng (1 Switch P4, các Hosts)
│   ├── s1-commands.txt          # Các lệnh khởi tạo bảng ban đầu (nếu cần nạp tay)
│   └── run_demo.sh              # Script tự động bật Mininet và nạp P4
│
├── traffic_data/                # 🚦 DỮ LIỆU THỰC NGHIỆM
│   ├── normal_traffic.pcap      # Lưu lượng mạng bình thường
│   └── ddos_attack.pcap         # Tấn công SYN Flood để test bằng tcpreplay
│
├── docs/                        # 📝 TÀI LIỆU
│   ├── tech_contract.md         # Biên bản thống nhất kỹ thuật
│   └── report_draft.docx        # Bản nháp báo cáo đồ án
│
├── .gitignore                   # Chặn push file rác và file dữ liệu nặng
└── README.md                    # Hướng dẫn cài đặt và gõ lệnh chạy dự án
```

---

## PHẦN B: CHI TIẾT LỘ TRÌNH 3 TUẦN (21 NGÀY)

### TUẦN 1: Nghiên cứu lý thuyết, Chuẩn bị dữ liệu & Dựng môi trường (Ngày 1 - Ngày 7)
* **Ngày 1 - 2 (Cơ sở lý thuyết):** Cả hai cùng đọc kỹ lại kiến trúc hệ thống lai (Network-assisted). Thống nhất danh sách 4 đặc trưng cốt lõi sẽ trích xuất: Tổng số gói IP, số gói TCP, số gói UDP, và số gói TCP SYN trong một cửa sổ lưu lượng.
* **Ngày 3 - 5 (Hành động song song - Thành viên A):** Tải tập dữ liệu CIC-DDoS2019 (bản CSV). Viết script Python bằng Pandas để làm sạch, trích xuất đúng 4 đặc trưng đã thống nhất. Huấn luyện mô hình Random Forest bằng Scikit-learn. Xuất mô hình thành công ra file cấu hình định dạng `.pkl` hoặc `.json`.
* **Ngày 3 - 5 (Hành động song song - Thành viên B):** Cài đặt hệ điều hành Ubuntu (v20.04 hoặc v22.04 LTS). Cài đặt các công cụ: Mininet, BMv2 (Software Switch), và trình biên dịch P4C. Tạo thử một cấu hình liên kết mạng (Topology) cơ bản trên Mininet (1 Switch, 3 Hosts).
* **Ngày 6 - 7 (Chốt chặn Tuần 1):** Thành viên A bàn giao file mô hình và danh sách các ngưỡng cắt (thresholds) của các cây quyết định cho Thành viên B để chuẩn bị ánh xạ cấu trúc bảng.

### TUẦN 2: Lập trình song song hai mặt phẳng Data Plane & Control Plane (Ngày 8 - Ngày 14)
* **Ngày 8 - 11 (Xây dựng khung xương - Thành viên B):** Viết code parser để đọc các trường header. Khai báo 4 khối register phần cứng để đếm gói. Viết logic kiểm tra cửa sổ gói tin (ví dụ: đếm đủ 10,000 gói thì kích hoạt). Cấu hình lệnh `clone_ingress_to_egress` để nhân bản gói tin báo cáo ra ngoài băng tần (Out-of-band).
* **Ngày 8 - 11 (Xây dựng bộ não - Thành viên A):** Viết script Controller bằng Python. Sử dụng thư viện socket hoặc P4Runtime để lắng nghe gói tin báo cáo được gửi từ switch lên. Viết hàm tự động load file model Random Forest đã train ở Tuần 1 để sẵn sàng dự đoán.
* **Ngày 12 - 14 (Tích hợp sơ bộ):** Biên dịch file P4 bằng `p4c`. Kết nối script Python của Thành viên A với Switch BMv2 của Thành viên B. Thử nghiệm nạp một vài luật chặn (`table_add`) thủ công từ Controller xuống switch xem switch có nhận lệnh và thực thi drop gói tin hay không.

### TUẦN 3: Tích hợp hệ thống, Chạy thực nghiệm & Hoàn thiện báo cáo (Ngày 15 - Ngày 21)
* **Ngày 15 - 16 (Tích hợp toàn diện):** Khởi chạy toàn bộ hệ thống. Kiểm tra luồng tự động: Gói tin chạy qua mạng -> Switch P4 tự đếm -> Đủ chu kỳ tự nhân bản và chèn thêm extra header gửi lên Controller -> Script Python tự dự đoán bằng Random Forest -> Nếu là DDoS, Controller tự động bắn rule xuống switch để drop luồng độc hại.
* **Ngày 17 - 18 (Thực nghiệm & Lấy số liệu):** Dùng `tcpreplay` để phát lại file PCAP thực tế của bộ dữ liệu CIC-DDoS2019. Dùng `hping3` sinh cuộc tấn công SYN Flood dồn dập để kiểm thử. Dùng `iperf3` đo đạc và thu thập số liệu Throughput, Latency. Ghi lại log hệ thống làm minh chứng.
* **Ngày 19 - 21 (Viết báo cáo & Kết luận):** Ghép toàn bộ nội dung thành file báo cáo hoàn chỉnh (Tổng quan, Thiết kế, Cài đặt, Thực nghiệm, Kết luận). Vẽ biểu đồ so sánh hiệu năng mạng dựa trên số liệu ngày 17-18 để tạo điểm nhấn chuyên nghiệp.

---

## PHẦN C: BIÊN BẢN THỐNG NHẤT KỸ THUẬT

### PHẦN 1: Cấu trúc "Thùng chứa" Báo cáo (Telemetry Header)
**Yêu cầu:** Thống nhất định dạng Header (Bắt buộc tuân thủ thứ tự và số bit) và chèn ngay sau chuẩn UDP (sử dụng UDP Port 50000 làm cờ hiệu).
1. `switch_id`: 32-bit (Định danh switch gửi báo cáo).
2. `tot_pck`: 16-bit (Tổng số gói tin).
3. `tcp_pck`: 16-bit (Tổng gói TCP).
4. `udp_pck`: 16-bit (Tổng gói UDP).
5. `syn_pck`: 16-bit (Tổng gói mang cờ TCP SYN).

| Phân công nhiệm vụ | Chi tiết công việc |
| :--- | :--- |
| **Người làm P4 (Data Plane)** | Định nghĩa header `my_int_header_t` với kích thước bit chính xác như trên. Viết action ghép header này vào bản sao (clone) của gói tin thứ N. |
| **Người làm Python (Control Plane)** | Viết class `MyDDoSTelemetry(Packet)` trong thư viện Scapy khớp chính xác 5 trường trên. Sử dụng `bind_layers(UDP, MyDDoSTelemetry, dport=50000)` để bắt gói. |

### PHẦN 2: Tập đặc trưng (Feature Set) đưa vào AI
**Yêu cầu:** Mô hình Random Forest chỉ được phép học dựa trên những gì phần cứng P4 có khả năng đếm được. Tuyệt đối không thêm các đặc trưng tính toán thời gian phức tạp (như IAT).
1. `tot_pck`
2. `tcp_pck`
3. `udp_pck`
4. `syn_pck`

| Phân công nhiệm vụ | Chi tiết công việc |
| :--- | :--- |
| **Người làm P4 (Data Plane)** | Cấu hình 4 khối Registers phần cứng. Đảm bảo logic đếm hoạt động đúng: gặp gói TCP thì thanh ghi TCP tăng 1, gặp gói IP thì thanh ghi Total tăng 1. |
| **Người làm Python (Control Plane)** | Khi xử lý bộ dataset CIC-DDoS2019, chỉ giữ lại 4 cột dữ liệu tương ứng với 4 đặc trưng này để train mô hình Random Forest. Bỏ hết các cột khác. |

### PHẦN 3: Chu kỳ kích hoạt (Trigger Window)
**Yêu cầu:** Cần xác định bao lâu thì Switch báo cáo lên bộ não một lần. Báo cáo quá nhanh thì Python sập, báo cáo quá chậm thì Server mục tiêu chết.
* **Ngưỡng chu kỳ:** Kích hoạt nhân bản gói tin và gửi báo cáo sau mỗi 10.000 gói tin đi qua Switch.

| Phân công nhiệm vụ | Chi tiết công việc |
| :--- | :--- |
| **Người làm P4 (Data Plane)** | Viết khối lệnh điều kiện: `if (meta.counter_tot == 10000)`. Khi thỏa mãn, gọi chuỗi hành động: Đọc thanh ghi -> Reset thanh ghi về 0 -> Clone gói tin gửi lên cổng CPU. |
| **Người làm Python (Control Plane)** | Viết hàm Python theo cơ chế bất đồng bộ (Asynchronous) hoặc dùng đa luồng (Threading) để đảm bảo có thể bắt và xử lý liên tục các gói báo cáo mà không bị rớt mạng. |

### PHẦN 4: Lệnh chặn tấn công (Mitigation API Protocol)
**Yêu cầu:** Khi AI phát hiện DDoS, nó phải ra lệnh cho P4 chặn ngay lập tức. Hai bên phải khớp tên biến để gọi API (P4Runtime).
* **Tên Bảng thực thi chặn:** `table_block_malicious_ipv4`
* **Khóa tra cứu (Match Key):** Dựa vào IP Nguồn (`hdr.ipv4.srcAddr`) kiểu tra cứu Exact (Chính xác 100%).
* **Hành động (Action):** `action_drop_packet`

| Phân công nhiệm vụ | Chi tiết công việc |
| :--- | :--- |
| **Người làm P4 (Data Plane)** | Khởi tạo bảng `table_block_malicious_ipv4` trống ở giai đoạn đầu của Ingress Pipeline. Nếu gói tin lọt vào bảng này và khớp IP, thực thi lệnh `mark_to_drop()`. |
| **Người làm Python (Control Plane)** | Trích xuất IP Nguồn từ báo cáo. Nếu Random Forest trả kết quả DDoS (1), gọi API đẩy lệnh `table_add table_block_malicious_ipv4 action_drop_packet [IP_Nguồn]` xuống switch. |