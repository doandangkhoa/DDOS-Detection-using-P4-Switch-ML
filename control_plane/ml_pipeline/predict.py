import joblib
import pandas as pd
import numpy as np
import time
import threading

class TrafficPredictor:
    def __init__(self, model_path='random_forest.pkl', time_window=1.0, attack_thresh=0.8):
        self.time_window   = time_window
        self.attack_thresh = attack_thresh
        self.features      = ['avg_length', 'tcp_ratio', 'udp_ratio', 'tcp_udp_ratio', 'syn_ratio']

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
        """Receive time-window P4-Switch report then saved to buffer"""
        with self.buffer_lock:
            self.buffer.append({**report_dict, 'timestamp': time.time()})

    def analyze_window(self):
        """
        Analyze the time-window report to decide based-on time frame T
        """
        now = time.time()

        with self.buffer_lock:
            # window stored the reports which have timestamp in the time frame
            window = [report for report in self.buffer
                      if now - report['timestamp'] <= self.time_window]
            self.buffer[:] = window  # override the buffer to delete the outdated data

        if not window:
            return None

        # convert to dataframe
        df = pd.DataFrame(window)

        # FEATURE ENGINEERING
        df['avg_length'] = df['tot_bytes'] / (df['tot_pck'] + 1e-9)
        df['tcp_ratio'] = df['tcp_pck'] / (df['tot_pck'] + 1e-9)
        df['udp_ratio'] = df['udp_pck'] / (df['tot_pck'] + 1e-9)
        df['tcp_udp_ratio'] = df['tcp_pck'] / (df['udp_pck'] + 1e-9)
        df['syn_ratio'] = df['syn_pck'] / (df['tot_pck'] + 1e-9)
        
        features_df = df[self.features].copy() 

        predictions = self.model.predict(features_df)
        probas      = self.model.predict_proba(features_df)

        attack_ratio = float(np.mean(predictions))
        is_attack    = attack_ratio >= self.attack_thresh

        return {
            'label'        : 'Attack' if is_attack else 'Benign',
            'attack_ratio' : round(attack_ratio * 100, 2),
            'avg_p_attack' : round(float(np.mean(probas[:, 1])) * 100, 2),
            'sample_count' : len(window),
        }