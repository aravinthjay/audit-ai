import pandas as pd
import numpy as np

df = pd.read_csv("sakshi_ppg_20260611T074737_len148s.csv")

# Missing percentage
missing_percent = (df.isnull().sum() / len(df)) * 100
missing_report = pd.DataFrame({
    "column": df.columns,
    "missing_count": df.isnull().sum().values,
    "missing_percentage": missing_percent.values
})

print("Missing value report:")
print(missing_report)

# -------------------------
# Suggested filling strategy
# -------------------------

# 1. Sort by timestamp first
df = df.sort_values("timestamp_ms").drop_duplicates(subset=["timestamp_ms"]).reset_index(drop=True)

# 2. Example fill strategy for time-series continuous signals
df_filled = df.copy()

signal_cols = ["red", "ir", "red_corrected", "ir_corrected"]

# Linear interpolation for signal columns
df_filled[signal_cols] = df_filled[signal_cols].interpolate(method="linear")

# If any still remain at the beginning or end, use forward/backward fill
df_filled[signal_cols] = df_filled[signal_cols].bfill().ffill()

print("\nAfter filling missing values:")
print(df_filled[signal_cols].isnull().sum())