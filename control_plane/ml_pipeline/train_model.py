import os
import joblib
import seaborn as sns
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_curve, auc

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(CURRENT_DIR, "dataset", "final_dataset.csv")
MODEL_PATH = os.path.join(CURRENT_DIR, "random_forest.pkl")
RESULTS_DIR = os.path.join(CURRENT_DIR, "training_results")

print("[*] Đang tải dữ liệu...")
if not os.path.exists(DATASET_PATH):
    print(f"[-] Không tìm thấy file: {DATASET_PATH}")
    print("[-] Vui lòng chạy sudo python3 auto_collect_dataset.py trước!")
    exit(1)

df = pd.read_csv(DATASET_PATH)

label_mapping = {'Benign': 0, 'Attack': 1}
df['Label'] = df['Label'].map(label_mapping)
df = df.dropna(subset=['Label'])

def extract_features(df_input):
    df_out = df_input.copy()
    df_out['avg_length']    = df_out['tot_bytes'] / (df_out['tot_pck'] + 1e-9)
    df_out['tcp_ratio']     = df_out['tcp_pck'] / (df_out['tot_pck'] + 1e-9)
    df_out['udp_ratio']     = df_out['udp_pck'] / (df_out['tot_pck'] + 1e-9)
    df_out['tcp_udp_ratio'] = df_out['tcp_pck'] / (df_out['udp_pck'] + 1e-9)
    df_out['syn_ratio']     = df_out['syn_pck'] / (df_out['tot_pck'] + 1e-9)
    return df_out

print("[*] Dọn dẹp nhiễu chuyển giao (Transition Noise)...")
# Cắt bỏ 1 dòng đầu và 1 dòng cuối của mỗi kịch bản để tránh độ trễ Mininet
df = df.groupby('event_id', group_keys=False).apply(lambda x: x.iloc[1:-1] if len(x) > 2 else x)

print("[*] Feature Engineering...")
df = extract_features(df)

features = ['avg_length', 'tcp_ratio', 'udp_ratio', 'tcp_udp_ratio', 'syn_ratio']

X = df[features]
y = df['Label']
groups = df['event_id']

print(f"\n[*] Tổng số kịch bản (group) duy nhất: {groups.nunique()}")
print("[*] Phân phối nhãn toàn dataset:\n", y.value_counts())

gss = GroupShuffleSplit(test_size=0.2, n_splits=1, random_state=123)
train_idx, test_idx = next(gss.split(X, y, groups=groups))

X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

print("\n── KIỂM TRA PHÂN PHỐI SAU SPLIT ──")
print("Train:\n", y_train.value_counts())
print("Test:\n", y_test.value_counts())

if y_test.nunique() < 2:
    print("\n⚠️  CẢNH BÁO: Test set chỉ có 1 lớp! Đổi random_state hoặc thêm dữ liệu rồi chạy lại.")
    exit(1)

print("[*] Model đang huấn luyện...")
rf_model = RandomForestClassifier(
    n_estimators=200,            # Tăng số lượng cây quyết định từ 100 lên 200 để học kỹ hơn
    max_depth=15,                # Cho phép cây mọc sâu hơn để phân tích các pattern ẩn
    class_weight="balanced",     # Ép mô hình phạt nặng hơn nếu đoán sai class Attack
    min_samples_leaf=2,          # Chống overfit nhẹ
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)

y_prob = rf_model.predict_proba(X_test)[:, 1]
y_pred = (y_prob >= 0.5).astype(int)

print("\n── BÁO CÁO ĐÁNH GIÁ ────────────────────────────")
print(f"Accuracy: {accuracy_score(y_test, y_pred): .4f}")
print(classification_report(y_test, y_pred, target_names=['Benign', 'Attack']))

# ==========================================================
# XUẤT BIỂU ĐỒ CHUẨN HỌC THUẬT (SCIENTIFIC PLOTS)
# ==========================================================
os.makedirs(RESULTS_DIR, exist_ok=True)
sns.set_theme(style="whitegrid") # Áp dụng theme chuẩn báo cáo

# 1. Vẽ Confusion Matrix (Heatmap)
plt.figure(figsize=(6, 5))
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
            xticklabels=['Benign', 'Attack'], 
            yticklabels=['Benign', 'Attack'],
            annot_kws={"size": 14}) # Phóng to chữ số bên trong
plt.ylabel('True Label', fontsize=12, fontweight='bold')
plt.xlabel('Predicted Label', fontsize=12, fontweight='bold')
plt.title('Confusion Matrix - Random Forest', fontsize=14, pad=15)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, '1_confusion_matrix.png'), dpi=300) # Xuất ảnh 300 DPI siêu nét

# 2. Vẽ đường cong ROC (ROC Curve & AUC)
fpr, tpr, thresholds = roc_curve(y_test, y_prob)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(6, 5))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.4f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([-0.01, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate', fontsize=12)
plt.ylabel('True Positive Rate', fontsize=12)
plt.title('Receiver Operating Characteristic (ROC)', fontsize=14, pad=15)
plt.legend(loc="lower right", fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, '2_roc_curve.png'), dpi=300)

# 3. Vẽ Feature Importance
importances = rf_model.feature_importances_
# Sắp xếp các đặc trưng theo độ quan trọng
indices = np.argsort(importances)[::-1]
sorted_features = [features[i] for i in indices]
sorted_importances = importances[indices]

plt.figure(figsize=(8, 5))
sns.barplot(x=sorted_importances, y=sorted_features, palette="viridis")
plt.xlabel('Importance Score', fontsize=12)
plt.ylabel('Features', fontsize=12)
plt.title('Feature Importance Analysis', fontsize=14, pad=15)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, '3_feature_importance.png'), dpi=300)

# ==========================================================
joblib.dump(rf_model, MODEL_PATH)
print(f"\n[+] Huấn luyện thành công! Đã lưu model tại: {MODEL_PATH}")
print(f"[+] Đã xuất 3 biểu đồ báo cáo khoa học (300 DPI) tại mục: {RESULTS_DIR}")