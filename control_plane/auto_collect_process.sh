#!/bin/bash

FAIL_COUNT=0
MAX_CONSECUTIVE_FAILS=2

for i in $(seq 1 5); do
    echo "===== LẦN CHẠY $i/5 — $(date) ====="

    sudo python3 auto_collect_dataset.py
    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo "❌ LẦN $i THẤT BẠI (exit code $EXIT_CODE)"
        FAIL_COUNT=$((FAIL_COUNT + 1))

        if [ $FAIL_COUNT -ge $MAX_CONSECUTIVE_FAILS ]; then
            echo "🛑 Dừng hẳn: đã thất bại $MAX_CONSECUTIVE_FAILS lần liên tiếp."
            echo "   Kiểm tra RAM/môi trường trước khi chạy lại tay."
            exit 1
        fi

        echo "   Đợi 30s rồi dọn môi trường kỹ hơn trước khi thử lại..."
        sleep 30
        sudo pkill -9 -f simple_switch
        sudo pkill -9 -f hping3
        sudo pkill -9 -f iperf
        sudo mn -c > /dev/null 2>&1
    else
        echo "✅ LẦN $i THÀNH CÔNG"
        FAIL_COUNT=0
    fi

    echo "   RAM hiện tại:"
    free -h | grep Mem

    AVAILABLE_MB=$(free -m | awk '/Mem:/ {print $7}')
    if [ "$AVAILABLE_MB" -lt 1000 ]; then
        echo "⚠️  RAM khả dụng chỉ còn ${AVAILABLE_MB}MB — đợi thêm 60s nữa để giải phóng..."
        sleep 60
    fi

    echo "   Nghỉ 60s trước lần kế tiếp..."
    sleep 30
done

echo "===== HOÀN TẤT TOÀN BỘ $i LẦN CHẠY ====="