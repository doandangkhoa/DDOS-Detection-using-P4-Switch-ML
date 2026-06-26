#!/bin/bash

# Hàm chạy lệnh cho host
run_h1_h4() {
    # Chạy iperf và loop curl
    iperf -c 10.0.0.3 -p 80 -t 99999 &
    while true; do
        curl -s 10.0.0.3 > /dev/null
        sleep 1
    done
}

# Hàm chạy lệnh cho host h2
run_h2() {
    hping3 -S -p 80 --flood 10.0.0.3
}

# Xuất hàm để có thể gọi từ Mininet
export -f run_h1_h4
export -f run_h2

# Thực thi trên các host
# Nếu bạn đang trong Mininet CLI, bạn dùng lệnh bên dưới