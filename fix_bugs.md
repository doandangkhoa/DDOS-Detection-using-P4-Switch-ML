
Error:
```bash
ubuntu@ubuntu:~/DDOS-Detection-using-P4-Switch-ML/topology$ sudo apt install python3-mininet -y
Reading package lists... Done
Building dependency tree       
Reading state information... Done
E: Unable to locate package python3-mininet
```

Bước 1: Cài đặt module Mininet cho Python 3
Bash
cd ~
# Tải mã nguồn Mininet (nếu terminal báo thư mục "already exists" thì bạn cứ kệ và gõ tiếp lệnh sau)
git clone https://github.com/mininet/mininet.git

# Di chuyển vào thư mục và ép cài đặt thư viện hệ thống cho Python 3
cd mininet
sudo PYTHON=python3 make install
Lệnh make install này sẽ tự động gắn module mininet vào đúng đường dẫn gốc của Python 3 (thường là /usr/local/lib/python3.8/dist-packages/), giúp lệnh sudo python3 của bạn có thể gọi được nó ở bất cứ đâu.

Bước 2: Đảm bảo có module p4_mininet.py
Như tôi có nhắc ở tin nhắn trước, file topology của bạn đang gọi thêm một module đặc chế của P4. Hãy đảm bảo copy nó sang thư mục làm việc để không bị lỗi No module named 'p4_mininet':

Bash
cp ~/tutorials/utils/p4_mininet.py ~/DDOS-Detection-using-P4-Switch-ML/topology/
Bước 3: Khởi động lại
Quay lại thư mục dự án và chạy lại lệnh khởi tạo mạng ảo:

Bash
cd ~/DDOS-Detection-using-P4-Switch-ML/topology
sudo python3 network_topo.py

Error:
```bash
ubuntu@ubuntu:~/mininet$ sudo PYTHON=python3 make install
cc -Wall -Wextra  \
-DVERSION=\"`PYTHONPATH=. python3 -B bin/mn --version 2>&1`\" mnexec.c -o mnexec
install -D mnexec /usr/bin/mnexec
PYTHONPATH=. help2man -N -n "create a Mininet network." \
--no-discard-stderr "python3 -B bin/mn" -o mn.1
/bin/sh: 1: help2man: not found
make: *** [Makefile:74: mn.1] Error 127
```
Bước 1: Cài đặt công cụ bị thiếu
Bạn gõ lệnh này để cài help2man:

Bash
sudo apt install help2man -y
Bước 2: Chạy lại lệnh cài Mininet
Quay trở lại thư mục mininet và gọi lại lệnh cài đặt:

Bash
cd ~/mininet
sudo PYTHON=python3 make install
Lần này lệnh sẽ chạy tuốt luốt từ đầu đến cuối, nó sẽ sinh ra file mn.1 thành công và copy toàn bộ thư viện vào lõi Python 3 của bạn.

Bước 3: Khởi chạy mạng ảo
Bây giờ module mininet đã chính thức nằm trong Python. Hãy quay lại thư mục dự án và bật công tắc hệ thống lên:

Bash
cd ~/DDOS-Detection-using-P4-Switch-ML/topology
sudo python3 network_topo.py


Error:
```bash
ubuntu@ubuntu:~/DDOS-Detection-using-P4-Switch-ML/topology$ sudo python3 network_topo.py 
Traceback (most recent call last):
  File "network_topo.py", line 5, in <module>
    from p4_mininet import P4Switch, P4Host
  File "/home/ubuntu/DDOS-Detection-using-P4-Switch-ML/topology/p4_mininet.py", line 13, in <module>
    from netstat import check_listening_on_port
ModuleNotFoundError: No module named 'netstat'
```
Bước 1: Copy file netstat.py

Bash
cp ~/tutorials/utils/netstat.py ~/DDOS-Detection-using-P4-Switch-ML/topology/
Bước 2: Khởi động lại mạng ảo

Bash
sudo python3 network_topo.py
