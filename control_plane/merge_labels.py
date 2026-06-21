import pandas as pd
import os

# ── Xác định path tuyệt đối ──
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))   # .../control_plane
DATASET_DIR = os.path.join(CURRENT_DIR, "ml_pipeline", "dataset")

RAW_CSV = os.path.join(DATASET_DIR, "raw_telemetry.csv")
TRUTH_CSV = os.path.join(DATASET_DIR, "ground_truth.csv")
FINAL_CSV = os.path.join(DATASET_DIR, "Final_Labeled_Dataset.csv")

# Đọc file bằng đường dẫn tuyệt đối
raw = pd.read_csv(RAW_CSV)
truth = pd.read_csv(TRUTH_CSV)

def find_label(ts):
    match = truth[(truth['start_ts'] <= ts) & (ts <= truth['end_ts'])]
    if len(match) > 0:
        row = match.iloc[-1]
        return row['label'], row['start_ts']   # start_ts dùng làm group_id duy nhất cho mỗi kịch bản
    return None, None

raw[['Label', 'event_id']] = raw['timestamp'].apply(
    lambda ts: pd.Series(find_label(ts))
)
raw = raw.dropna(subset=['Label'])

final = raw[['tot_pck', 'tot_bytes', 'tcp_pck', 'udp_pck', 'syn_pck', 'Label', 'event_id']]
final.to_csv(FINAL_CSV, index=False)

print(f"✅ Đã gán nhãn thành công. Có {len(final)} dòng dữ liệu chuẩn tại: {FINAL_CSV}")