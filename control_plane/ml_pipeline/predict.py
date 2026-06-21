import joblib
import pandas as pd
import numpy as np

class TrafficPredictor:
    def __init__(self, model_path='ml_pipeline/random_forest.pkl', time_window=1.0, attack_thresh=0.8):
        self.time_window   = time_window
        self.attack_thresh = attack_thresh
        self.features      = ['avg_length', 'tcp_ratio', 'udp_ratio', 'tcp_udp_ratio', 'syn_ratio']

        # KHÔNG CẦN BUFFER HAY LOCK NỮA VÌ CONTROLLER ĐÃ GOM SẴN

        print("[*] Loading model...")
        try:
            self.model = joblib.load(model_path)
            print("[+] Model loaded successfully!")
        except Exception as e:
            print(f"[-] Loading failed: {e}")
            exit(1)

    def analyze_single_window(self, stats_dict):
        """
        Nhận trực tiếp 1 Dictionary chứa TỔNG dữ liệu của 1 giây từ Controller
        """
        # Nếu không có gói tin nào, bỏ qua
        if stats_dict.get('tot_pck', 0) == 0:
            return None

        # Chuyển đổi dictionary thành DataFrame (chỉ có đúng 1 dòng)
        df = pd.DataFrame([stats_dict])

        # FEATURE ENGINEERING (Tính toán đặc trưng dựa trên tổng 1 giây)
        df['avg_length']    = df['tot_bytes'] / (df['tot_pck'] + 1e-9)
        df['tcp_ratio']     = df['tcp_pck'] / (df['tot_pck'] + 1e-9)
        df['udp_ratio']     = df['udp_pck'] / (df['tot_pck'] + 1e-9)
        df['tcp_udp_ratio'] = df['tcp_pck'] / (df['udp_pck'] + 1e-9)
        df['syn_ratio']     = df['syn_pck'] / (df['tot_pck'] + 1e-9)
        
        features_df = df[self.features].copy() 

        # DỰ ĐOÁN
        # Vì chỉ có 1 dòng, ta lấy luôn phần tử [0]
        prediction = self.model.predict(features_df)[0]
        probas     = self.model.predict_proba(features_df)[0]

        # probas[1] là xác suất AI cho rằng đây là Attack
        prob_attack = float(probas[1])
        is_attack   = prob_attack >= self.attack_thresh

        return {
            'label'        : 'Attack' if is_attack else 'Benign',
            'attack_ratio' : round(prob_attack * 100, 2), # Dùng xác suất làm tỷ lệ độc hại
            'avg_p_attack' : round(prob_attack * 100, 2),
            'sample_count' : 1, # 1 Window tổng hợp
        }