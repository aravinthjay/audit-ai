import shap

# Train a logistic regression on the loan dataset
feature_cols = ['income', 'credit_score', 'loan_amount', 'existing_loans', 'age']

# Encode categoricals
df_model = df.copy()
for col in ['gender', 'region', 'employment_type']:
    df_model[col + '_enc'] = LabelEncoder().fit_transform(df_model[col])

all_features = feature_cols + ['gender_enc', 'region_enc', 'employment_type_enc']
X = df_model[all_features]
y = df_model['rejected']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_train_sc = scaler.fit_transform(X_train)
X_test_sc  = scaler.transform(X_test)

clf = LogisticRegression(max_iter=500, random_state=42)
clf.fit(X_train_sc, y_train)
# Corrected line: Use the global round() function
print("Model accuracy:", round(clf.score(X_test_sc, y_test), 3))

# SHAP explainer
explainer = shap.LinearExplainer(clf, X_train_sc, feature_names=all_features)
shap_values = explainer(X_test_sc)

# Global feature importance
plt.figure(figsize=(9, 5))
shap.summary_plot(shap_values, X_test, feature_names=all_features, plot_type='bar', show=False)
plt.title("SHAP Feature Importance — CreditLens Rejection Model", fontweight='bold')
plt.tight_layout()
plt.show()

print("\n💡 Key question: Is 'gender_enc' or 'region_enc' in the top features?")
print("   If so, the model is USING protected attributes to make decisions — a compliance violation.")