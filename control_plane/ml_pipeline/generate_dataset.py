import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split

np.random.seed(42)

NUM_BENIGN = 10000
NUM_ATTACK = 10000

print("⏳ Đang tạo tập Benign (Có P2P/Crawler gây nhiễu)...")
# 1. 85% Người dùng bình thường: Traffic thấp, SYN rất thấp (1-5%)
b_norm_tot = np.random.randint(100, 600, int(NUM_BENIGN * 0.85))
b_norm_syn_r = np.random.uniform(0.01, 0.05, len(b_norm_tot))

# 2. 10% Flash Crowd: Đứt cáp/Sự kiện -> Traffic cực cao, SYN thấp (5-15%)
b_flash_tot = np.random.randint(1500, 3000, int(NUM_BENIGN * 0.10))
b_flash_syn_r = np.random.uniform(0.05, 0.15, len(b_flash_tot))

# 3. 5% VÙNG GIAO THOA (P2P/Scanner): Traffic vừa, tỷ lệ SYN cao bất thường (30-60%)
b_noise_tot = np.random.randint(400, 1000, int(NUM_BENIGN * 0.05))
b_noise_syn_r = np.random.uniform(0.30, 0.60, len(b_noise_tot))

# Gộp Benign
benign_tot = np.concatenate([b_norm_tot, b_flash_tot, b_noise_tot])
benign_syn_ratio = np.concatenate([b_norm_syn_r, b_flash_syn_r, b_noise_syn_r])
benign_udp = np.random.randint(5, 50, NUM_BENIGN)
benign_tcp = np.maximum(benign_tot - benign_udp, 0)
benign_syn = (benign_tcp * benign_syn_ratio).astype(int)

benign_df = pd.DataFrame({
    'tot_pck': benign_tot, 'tcp_pck': benign_tcp, 'udp_pck': benign_udp, 'syn_pck': benign_syn, 'Label': 'Benign'
})

print("🚀 Đang tạo tập SYN Flood (Có Botnet ngụy trang)...")
# 1. 85% Bão SYN truyền thống: Traffic cực cao, SYN cực cao (80-98%)
a_heavy_tot = np.random.randint(1500, 3000, int(NUM_ATTACK * 0.85))
a_heavy_syn_r = np.random.uniform(0.80, 0.98, len(a_heavy_tot))

# 2. 10% Low-rate DDoS: Traffic thấp, SYN vẫn cao (70-90%)
a_low_tot = np.random.randint(100, 600, int(NUM_ATTACK * 0.10))
a_low_syn_r = np.random.uniform(0.70, 0.90, len(a_low_tot))

# 3. 5% VÙNG GIAO THOA (Ngụy trang): Traffic vừa, tỷ lệ SYN cố tình hạ thấp (30-60%)
a_noise_tot = np.random.randint(400, 1000, int(NUM_ATTACK * 0.05))
a_noise_syn_r = np.random.uniform(0.30, 0.60, len(a_noise_tot))

# Gộp Attack
attack_tot = np.concatenate([a_heavy_tot, a_low_tot, a_noise_tot])
attack_syn_ratio = np.concatenate([a_heavy_syn_r, a_low_syn_r, a_noise_syn_r])
attack_udp = np.random.randint(0, 20, NUM_ATTACK)
attack_tcp = np.maximum(attack_tot - attack_udp, 0)
attack_syn = (attack_tcp * attack_syn_ratio).astype(int)

attack_df = pd.DataFrame({
    'tot_pck': attack_tot, 'tcp_pck': attack_tcp, 'udp_pck': attack_udp, 'syn_pck': attack_syn, 'Label': 'Syn'
})

# --- TRỘN VÀ CHIA DATASET ---
final_df = pd.concat([benign_df, attack_df]).sample(frac=1, random_state=42).reset_index(drop=True)

train_df, test_df = train_test_split(
    final_df, test_size=0.2, random_state=42, stratify=final_df['Label']
)

os.makedirs('dataset', exist_ok=True)
train_df.to_csv('dataset/Custom_Telemetry_Train.csv', index=False)
test_df.to_csv('dataset/Custom_Telemetry_Test.csv', index=False)

print(f"\n✅ Hoàn tất!")
print(f"Train size: {len(train_df)} | Test size: {len(test_df)}")