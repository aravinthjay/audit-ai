import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import periodogram
from statsmodels.tsa.seasonal import seasonal_decompose

# -----------------------------------
# 1. Load and prepare data
# -----------------------------------
df = pd.read_csv("sakshi_ppg_20260611T074737_len148s.csv")
df = df.sort_values("timestamp_ms").drop_duplicates(subset=["timestamp_ms"]).reset_index(drop=True)

# Create time in milliseconds relative to start
df["time_ms_from_start"] = df["timestamp_ms"] - df["timestamp_ms"].iloc[0]

# Use a proper datetime-like index for resampling
df["time_index"] = pd.to_datetime(df["time_ms_from_start"], unit="ms")
df = df.set_index("time_index")

# -----------------------------------
# 2. Resample to 20 ms and interpolate
# -----------------------------------
df_resampled = df.resample("20ms").mean(numeric_only=True)
df_resampled["ir_corrected"] = df_resampled["ir_corrected"].interpolate(method="linear").bfill().ffill()

# -----------------------------------
# 3. Estimate period automatically
# -----------------------------------
signal = df_resampled["ir_corrected"].dropna().astype(float).values
fs = 50   # 20 ms = 0.02 sec => 50 Hz

signal_centered = signal - np.mean(signal)
freqs, power = periodogram(signal_centered, fs=fs)

mask = (freqs >= 0.5) & (freqs <= 3.0)

dominant_freq = freqs[mask][np.argmax(power[mask])]
period_samples = int(round(fs / dominant_freq))

print("Estimated period (samples):", period_samples)

# -----------------------------------
# 4. Decompose
# -----------------------------------
series = pd.Series(signal)   # numeric index avoids plotting issue

result = seasonal_decompose(
    series,
    model="additive",
    period=period_samples,
    extrapolate_trend="freq"
)

# -----------------------------------
# 5. Manual plotting (safe)
# -----------------------------------
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

axes[0].plot(result.observed)
axes[0].set_title("Observed")

axes[1].plot(result.trend)
axes[1].set_title("Trend")

axes[2].plot(result.seasonal)
axes[2].set_title("Seasonal")

axes[3].plot(result.resid)
axes[3].set_title("Residual")

plt.tight_layout()
plt.show()