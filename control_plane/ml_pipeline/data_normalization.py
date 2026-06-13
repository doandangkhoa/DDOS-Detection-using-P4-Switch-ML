import pandas as pd

# 1. Đọc file CSV (Chỉ load đúng 5 cột gốc cần thiết để tiết kiệm RAM tối đa)
# Lưu ý: Tên cột của CIC-DDoS2019 thường có dấu cách ở đằng trước
cols_to_use = [' Total Fwd Packets', ' Total Backward Packets', ' Protocol', ' SYN Flag Count', ' Label']

print("Đang đọc dữ liệu...")
df = pd.read_csv('du_duong_dan_file_dataset_tren_colab.csv', usecols=cols_to_use)

print("Đang trích xuất đặc trưng...")
# 2. Tính Tổng số gói tin (Total Packets = Forward + Backward)
df['tot_pck'] = df[' Total Fwd Packets'] + df[' Total Backward Packets']

# 3. Tách gói TCP và UDP dựa trên mã Protocol (6 là TCP, 17 là UDP)
# Dùng hàm lambda để gán giá trị: Nếu đúng giao thức thì lấy tổng số gói, sai thì gán bằng 0
df['tcp_pck'] = df.apply(lambda row: row['tot_pck'] if row[' Protocol'] == 6 else 0, axis=1)
df['udp_pck'] = df.apply(lambda row: row['tot_pck'] if row[' Protocol'] == 17 else 0, axis=1)

# 4. Trích xuất cờ SYN
df['syn_pck'] = df[' SYN Flag Count']

# 5. Gọt bộ khung: Chỉ giữ lại 4 cột đặc trưng mới tạo và cột Nhãn (Label)
final_df = df[['tot_pck', 'tcp_pck', 'udp_pck', 'syn_pck', ' Label']]

# Lọc bỏ các dòng bị rỗng (NaN) nếu có để tránh lỗi khi đưa vào mô hình AI
final_df = final_df.dropna()

print("Hoàn tất! Cấu trúc dữ liệu mới:")
print(final_df.head())

# 6. Xuất ra file CSV siêu nhẹ mang về máy
final_df.to_csv('Cleaned_DDoS_Data.csv', index=False)
print("Đã lưu thành file Cleaned_DDoS_Data.csv")