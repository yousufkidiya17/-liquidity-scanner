import pandas as pd
import numpy as np
import os

os.chdir(r'c:\liquidity scanner')

# Settings
SWING_LOOKBACK_LEFT = 3
SWING_LOOKBACK_RIGHT = 2
STRONG_WICK_OVERRIDE = 0.65

# Check SAMHI
df = pd.read_csv("data_cache_backup/SAMHI.NS_6mo_1d.csv", parse_dates=["Date"], index_col="Date")

# Swing detection
df["swing_low"] = False
for i in range(SWING_LOOKBACK_LEFT, len(df) - SWING_LOOKBACK_RIGHT):
    curr_low = df["Low"].iloc[i]
    left_higher = all(df["Low"].iloc[i-j] > curr_low for j in range(1, SWING_LOOKBACK_LEFT + 1))
    right_higher = all(df["Low"].iloc[i+j] > curr_low for j in range(1, SWING_LOOKBACK_RIGHT + 1))
    if left_higher and right_higher:
        df.loc[df.index[i], "swing_low"] = True

# Find swing on 11-Dec
swing_idx = df[df.index.astype(str).str.contains('2025-12-11')].index[0]
swing_level = df.loc[swing_idx, "Low"]

print(f"SAMHI.NS Analysis")
print(f"="*50)
print(f"Swing Low (11-Dec): {swing_level:.2f}")

# Check 18-Dec
idx_18 = df[df.index.astype(str).str.contains('2025-12-18')].index[0]
row_18 = df.loc[idx_18]

print(f"\n18-Dec-2025:")
print(f"  Open: {row_18['Open']:.2f}")
print(f"  High: {row_18['High']:.2f}")
print(f"  Low: {row_18['Low']:.2f}")
print(f"  Close: {row_18['Close']:.2f}")

# Wick calc
candle_range = row_18['High'] - row_18['Low']
lower_wick = min(row_18['Open'], row_18['Close']) - row_18['Low']
wick_ratio = lower_wick / candle_range

print(f"\n  Wick Ratio: {wick_ratio*100:.1f}%")
print(f"  Strong Wick (>65%)? {wick_ratio >= STRONG_WICK_OVERRIDE}")

# Detection
swing_tolerance = swing_level * 0.01
low_touches = row_18['Low'] <= swing_level + swing_tolerance
close_above = row_18['Close'] > swing_level * 1.002

print(f"\n  Low touches swing? {low_touches}")
print(f"  Close above swing? {close_above}")

if low_touches and close_above and wick_ratio >= STRONG_WICK_OVERRIDE:
    print(f"\n>>> SAMHI DETECTED! <<<")
    # Score
    wick_score = min(100, wick_ratio * 130)
    vol_score = 25
    total = (vol_score/100)*25 + (wick_score/100)*30 + 10  # depth score
    print(f">>> Score: {total:.0f}/100")
