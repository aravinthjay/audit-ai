# Numpy Imports
 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')
 
# Scikit-learn datasets & model selection
from sklearn.datasets import (make_classification, make_regression,
                                   load_breast_cancer, load_diabetes)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
 
# Classification models
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
 
# Regression models
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
 
# Evaluation metrics — THE CORE OF THIS NOTEBOOK
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, precision_recall_curve,
    confusion_matrix, classification_report,
    mean_squared_error, mean_absolute_error, r2_score,
    ConfusionMatrixDisplay
)
 
#Imports
 
# Plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette('husl')
np.random.seed(42)
 
print("✅ All libraries loaded successfully!")
print(f"NumPy: {np.__version__} | Pandas: {pd.__version__}")


# Dataset preparation
 
# Classification: Breast Cancer Dataset
cancer = load_breast_cancer()
X_clf, y_clf = cancer.data, cancer.target # 0=malignant, 1=benign
X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_clf, y_clf,
                                            test_size=0.2, random_state=42)
 
# Feature scaling - important for Logistic Regression and SVM
scaler_c = StandardScaler()
X_train_c = scaler_c.fit_transform(X_train_c)
X_test_c = scaler_c.transform(X_test_c)
 
# Diabaetes dataset
diabetes = load_diabetes()
X_reg, y_reg = diabetes.data, diabetes.target
 
X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
    X_reg, y_reg, test_size=0.2, random_state=42
)
 
scaler_r = StandardScaler()
X_train_r = scaler_r.fit_transform(X_train_r)
X_test_r = scaler_r.transform(X_test_r)
 
# ---Quick data summary---
print("CLASSIFICATION DATASER (Breast Cancer)")
print(f"  Train: {X_train_c.shape} | Test: {X_test_c.shape}")
print(f"  Class balance — Malignant: {(y_clf==0).sum()} | Benign: {(y_clf==1).sum()}\n")
print("REGRESSION DATASET (Diabetes)")
print(f"  Train: {X_train_r.shape} | Test: {X_test_r.shape}")
print(f"  Target range: [{y_reg.min():.0f}, {y_reg.max():.0f}]")


#print top 5 feature

print("Feature names:", cancer.feature_names[:5])


# Calculate imbalance ratio
malignant = (y_clf == 0).sum()
benign = (y_clf == 1).sum()

imbalance_ratio = malignant / benign
print(f"Class imbalance ratio: {imbalance_ratio:.2f}")



# Plot class distribution
labels = ['Malignant (0)', 'Benign (1)']
counts = [malignant, benign]

plt.bar(labels, counts, color=['red', 'green'])
plt.xlabel("Class")
plt.ylabel("Count")

plt.title("Class Distribution — Breast Cancer Dataset")
plt.show()


# Accuracy and Confusion Matrix
# Train three classifiers for comparison
models = {
    'Logistic Regression': LogisticRegression(max_iter=1000),
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42)
}
 
results = {}
 
for name, model in models.items():
    model.fit(X_train_c, y_train_c)
    y_pred = model.predict(X_test_c)
    y_proba = model.predict_proba(X_test_c)[:, 1]
 
    results[name] = {
        'model': model,
        'y_pred': y_pred,
        'y_proba': y_proba,
        'accuracy': accuracy_score(y_test_c, y_pred),
        'cm': confusion_matrix(y_test_c, y_pred)
    }
    print(f"{name}: Accuracy = {results[name]['accuracy']:.4f}")
 
# ── Visualise confusion matrices side by side ──
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
 
for ax, (name, res) in zip(axes, results.items()):
    disp = ConfusionMatrixDisplay(
        confusion_matrix=res['cm'],
        display_labels=cancer.target_names
    )
    disp.plot(ax=ax, colorbar=False, cmap='Blues')
    ax.set_title(f"{name}\nAcc: {res['accuracy']:.3f}", fontsize=11)
 
plt.tight_layout()
plt.suptitle("Confusion Matrices — All Models", y=1.02, fontsize=13, fontweight='bold')
plt.show()


# Train model (if not already done)
log_model = LogisticRegression()
log_model.fit(X_train_c, y_train_c)

# Predictions
y_pred_log = log_model.predict(X_test_c)


cm = confusion_matrix(y_test_c, y_pred_log)
print("Confusion Matrix:\n", cm)


TN = cm[0][0]
FP = cm[0][1]
FN = cm[1][0]
TP = cm[1][1]

print(f"TN: {TN}, FP: {FP}, FN: {FN}, TP: {TP}")


manual_accuracy = (TP + TN) / (TP + TN + FP + FN)
print(f"Manual Accuracy: {manual_accuracy:.4f}")


sklearn_accuracy = accuracy_score(y_test_c, y_pred_log)
print(f"Sklearn Accuracy: {sklearn_accuracy:.4f}")


 