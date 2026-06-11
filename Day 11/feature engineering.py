import pandas as pd

# Load dataset
df = pd.read_csv("sakshi_ppg_20260611T074737_len148s.csv")

# Drop seq and timestamp_ms
df = df.drop(columns=["seq", "timestamp_ms"])

print("Feature engineering columns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())