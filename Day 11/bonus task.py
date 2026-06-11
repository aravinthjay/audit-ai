import pandas as pd
import matplotlib.pyplot as plt

INPUT_FILE = "sakshi_ppg_20260611T074737_len148s.csv"

# Load and clean data
signal_df = pd.read_csv(INPUT_FILE)
signal_df = signal_df.sort_values("timestamp_ms").drop_duplicates(subset=["timestamp_ms"]).reset_index(drop=True)

# Create time axis in seconds
signal_df["time_sec"] = (signal_df["timestamp_ms"] - signal_df["timestamp_ms"].iloc[0]) / 1000.0

# Standardize Red and IR signals
signal_df["red_zscore"] = (signal_df["red"] - signal_df["red"].mean()) / signal_df["red"].std(ddof=0)
signal_df["ir_zscore"] = (signal_df["ir"] - signal_df["ir"].mean()) / signal_df["ir"].std(ddof=0)

# Plot superimposed standardized signals
plt.figure(figsize=(14, 6))
plt.plot(signal_df["time_sec"], signal_df["red_zscore"], color="red", label="Red (standardized)", alpha=0.8)
plt.plot(signal_df["time_sec"], signal_df["ir_zscore"], color="blue", label="IR (standardized)", alpha=0.8)

plt.title("Superimposed Red and IR Signals After Standardization")
plt.xlabel("Time (seconds)")
plt.ylabel("Standardized value")
plt.legend()
plt.tight_layout()

# Save image also
plt.savefig("superimposed_red_ir_normalized.png", dpi=150, bbox_inches="tight")

# Display on local machine
plt.show()

# Save standardized values
signal_df[["time_sec", "red_zscore", "ir_zscore"]].to_csv("normalized_red_ir.csv", index=False)

print("Saved: superimposed_red_ir_normalized.png")
print("Saved: normalized_red_ir.csv")