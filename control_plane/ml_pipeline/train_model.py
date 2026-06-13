import pandas as pd
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import joblib

# Load data
print("Data loading...")
df_train = pd.read_csv("dataset/Custom_Telemetry_Train.csv")
df_test = pd.read_csv("dataset/Custom_Telemetry_Test.csv")

# Covert String --> Binary number (Understanable by Machine)
label_mapping = {'Benign': 0, 'Syn': 1}
df_train['Label'] = df_train['Label'].map(label_mapping)
df_test['Label'] = df_test['Label'].map(label_mapping)

features = ['tot_pck', 'tcp_pck', 'udp_pck', 'syn_pck']

X_train = df_train[features]
y_train = df_train['Label']

X_test = df_test[features]
y_test = df_test['Label']

# Train Model
print("Model is training...")
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# Evaluate Model
y_pred = rf_model.predict(X_test)
print("\n── EVALUATION ──────────────────────────────")
print(f"Accuracy: {accuracy_score(y_test, y_pred): .4f}")
print(classification_report(y_test, y_pred, target_names=['Benign', 'Syn']))
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Feature Importance
importances = rf_model.feature_importances_
print("\n── FEATURE IMPORTANCE ──────────────────────")
for feature, importance in zip(features, importances):
    bar = '█' * int(importance * 50) 
    print(f"{feature:10s} : {bar} {importance:.4f}")

# Draw Plot
os.makedirs('./training_results', exist_ok=True)
plt.figure(figsize=(8, 4))
plt.bar(features, importances, color='steelblue')
plt.ylabel('Importance Score')
plt.xlabel('Features')
plt.title('Feature Importance - Random Forest')
plt.tight_layout()
plt.savefig('./training_results/feature_importance.png') 
#plt.show()

print(df_train[features].describe())
print(df_train['syn_pck'].value_counts())

# Saved Model
model_filename = 'random_forest.pkl'
joblib.dump(rf_model, model_filename)
print(f"\nTraining successfully! Saved to: {model_filename}")

print(df_train[features].describe())