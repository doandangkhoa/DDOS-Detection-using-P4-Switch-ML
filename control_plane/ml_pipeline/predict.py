import joblib
import pandas as pd
import numpy as np
import time
import threading

class TrafficPredictor:
    def __init__(self, model_path='random_forest.pkl', time_window=1.0, attack_thresh=0.6):
        self.time_window   = time_window
        self.attack_thresh = attack_thresh
        self.features      = ['tot_pck', 'tcp_pck', 'udp_pck', 'syn_pck']

        self.buffer      = []
        self.buffer_lock = threading.Lock()

        print("[*] Loading model...")
        try:
            self.model = joblib.load(model_path)
            print("[+] Model loaded successfully!")
        except Exception as e:
            print(f"[-] Loading failed: {e}")
            exit(1)

    def add_telemetry(self, report_dict):
        """Nhận 1 báo cáo Time-Window từ P4, đưa vào buffer"""
        with self.buffer_lock:
            self.buffer.append({**report_dict, 'timestamp': time.time()})

    def analyze_window(self):
        """
        Gom tất cả báo cáo trong time_window giây.
        Đưa ra kết luận tổng thể + tìm victim_ip.
        """
        now = time.time()

        with self.buffer_lock:
            # Chỉ giữ báo cáo trong time_window giây gần nhất
            window = [r for r in self.buffer
                      if now - r['timestamp'] <= self.time_window]
            self.buffer[:] = window  # xóa báo cáo cũ

        if not window:
            return None

        df          = pd.DataFrame(window)
        features_df = df[self.features].copy() 

        predictions = self.model.predict(features_df)
        probas      = self.model.predict_proba(features_df)

        attack_ratio = float(np.mean(predictions))
        is_attack    = attack_ratio >= self.attack_thresh

        # Tìm victim_ip bị tấn công nhiều nhất
        victim_ip = None
        if is_attack and 'dst_ip' in df.columns:
            # Chỉ lấy các flow bị predict là Attack
            attack_rows = df[predictions == 1]
            if not attack_rows.empty:
                victim_ip = attack_rows['dst_ip'].mode()[0]

        return {
            'label'        : 'Attack' if is_attack else 'Benign',
            'attack_ratio' : round(attack_ratio * 100, 2),
            'avg_p_attack' : round(float(np.mean(probas[:, 1])) * 100, 2),
            'sample_count' : len(window),
            'victim_ip'    : victim_ip,
        }