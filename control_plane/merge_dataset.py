import pandas as pd
import glob
import os

# Đường dẫn thư mục dataset
DATASET_DIR = "ml_pipeline/dataset"
all_files = glob.glob(os.path.join(DATASET_DIR, "dataset_v*.csv"))

df_list = []
for file in all_files:
    df = pd.read_csv(file)
    df_list.append(df)

# Gộp tất cả lại
master_df = pd.concat(df_list, ignore_index=True)

# Lưu thành file dataset cuối cùng để đưa vào Random Forest
MASTER_CSV = os.path.join(DATASET_DIR, "Master_Labeled_Dataset.csv")
master_df.to_csv(MASTER_CSV, index=False)

print(f"✅ Đã gộp thành công {len(all_files)} file.")
print(f"✅ Tổng số dòng dữ liệu thu được: {len(master_df)} dòng.")
print(f"✅ Lưu tại: {MASTER_CSV}")