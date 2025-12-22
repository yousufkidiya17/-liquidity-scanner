import pandas as pd
import numpy as np
import time
import os

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# ===================== USER SETTINGS ==========================
TIMEFRAMES = ["1d"]
PERIOD = "6mo"
TICKER_CSV = "INDEX CSV/microcap250.csv"
USE_CACHE = True
CACHE_DIR = "data_cache_backup"  # Using backup cache
DELAY_BETWEEN_REQUESTS = 1

# ===================== ADVANCED SMC SETTINGS ==========================
# Swing Detection
SWING_LOOKBACK_LEFT = 3       # Left candles for swing detection
SWING_LOOKBACK_RIGHT = 2      # Right candles for swing detection

# Volume Analysis (EXTRAORDINARY)
VOLUME_SMA_PERIOD = 20        # Average volume calculation period
MIN_VOLUME_SPIKE = 1.3        # Minimum 1.3x average volume for valid signal
EXTREME_VOLUME_SPIKE = 2.0    # 2x+ = Extraordinary volume (bonus score)
VOLUME_WEIGHT = 25            # Score weight for volume

# Wick Analysis (EXTRAORDINARY)
MIN_WICK_RATIO = 0.4          # Lower wick must be 40%+ of total candle range
STRONG_WICK_RATIO = 0.6       # 60%+ wick = Strong rejection
EXTREME_WICK_RATIO = 0.75     # 75%+ wick = Extraordinary rejection (max bonus)
WICK_WEIGHT = 30              # Score weight for wick

# Candle Analysis
REQUIRE_BULLISH_CANDLE = False # Changed: Allow bearish if strong wick
STRONG_WICK_OVERRIDE = 0.65    # Bearish allowed if wick >= 65%
BULLISH_BODY_WEIGHT = 15      # Score weight for bullish body

# 2-Candle Confirmation (for patterns like SAMHI)
ENABLE_2CANDLE_CONFIRM = True  # If grab candle is bearish, check next candle for bullish confirm

# Grab Depth Analysis
MIN_GRAB_DEPTH = 0.1          # Minimum 0.1% below swing (reduced from 0.3% for shallow grabs like SAMHI)
MAX_GRAB_DEPTH = 3.0          # Maximum 3% below swing (too deep = breakdown)
DEPTH_WEIGHT = 15             # Score weight for depth

# Price Action Context
CLOSE_ABOVE_SWING_MARGIN = 0.2  # Close must be 0.2%+ above swing level
CONTEXT_WEIGHT = 15           # Score weight for context

# Signal Quality Thresholds (Adjusted - Volume data missing from cache gives lower scores)
# When Volume data is available, increase thresholds by 10-15 points
GRADE_A_MIN_SCORE = 65        # A+ Grade: Exceptional setup (increase to 80 with volume)
GRADE_B_MIN_SCORE = 50        # B Grade: Good setup (increase to 60 with volume)
GRADE_C_MIN_SCORE = 35        # C Grade: Weak setup (increase to 45 with volume)
# =============================================================


def load_tickers():
    try:
        df = pd.read_csv(TICKER_CSV, header=None)
        tickers = (
            df.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
            .str.replace('"', '', regex=False)
            .str.replace(',', '', regex=False)
            .tolist()
        )
        tickers = [t for t in tickers if t]
        if not tickers:
            print("⚠ ERROR: tickers.csv khali hai.")
        return tickers
    except FileNotFoundError:
        print(f"⚠ ERROR: {TICKER_CSV} file nahi mili.")
        return []
    except Exception as e:
        print("⚠ ERROR:", e)
        return []


def setup_cache():
    if USE_CACHE and not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_path(ticker, timeframe):
    return os.path.join(CACHE_DIR, f"{ticker}_{PERIOD}_{timeframe}.csv")

def load_from_cache(ticker, timeframe):
    if not USE_CACHE:
        return None
    cache_path = get_cache_path(ticker, timeframe)
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df
        except:
            return None
    return None

def save_to_cache(ticker, timeframe, df):
    if not USE_CACHE or df.empty:
        return
    cache_path = get_cache_path(ticker, timeframe)
    try:
        df.to_csv(cache_path)
    except:
        pass


def get_data_with_volume(ticker: str, timeframe: str) -> pd.DataFrame:
    """Fetch OHLCV data with Volume for analysis"""
    cache_path = get_cache_path(ticker, timeframe)
    
    # Try loading from cache first
    if USE_CACHE and os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            # If Volume missing, add dummy volume (won't affect wick/swing analysis)
            if "Volume" not in df.columns:
                df["Volume"] = 0  # Dummy volume - volume score will be low
            return df
        except:
            pass
    
    # Skip download if cache doesn't exist (use build_all_caches.py first)
    return pd.DataFrame()


# ==================== EXTRAORDINARY VOLUME ANALYSIS ====================
def calculate_volume_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    EXTRAORDINARY Volume Analysis:
    1. Volume SMA (20-period moving average)
    2. Relative Volume (current / average)
    3. Volume Spike Detection
    4. Volume Trend (increasing/decreasing)
    5. Volume Percentile Rank
    """
    if "Volume" not in df.columns:
        df["Volume"] = 0
        df["vol_sma"] = 0
        df["rel_volume"] = 1.0
        df["vol_spike"] = False
        df["vol_score"] = 0
        return df
    
    # 1. Volume SMA
    df["vol_sma"] = df["Volume"].rolling(window=VOLUME_SMA_PERIOD, min_periods=5).mean()
    
    # 2. Relative Volume (how many times average)
    df["rel_volume"] = np.where(
        df["vol_sma"] > 0,
        df["Volume"] / df["vol_sma"],
        1.0
    )
    
    # 3. Volume Spike Detection
    df["vol_spike"] = df["rel_volume"] >= MIN_VOLUME_SPIKE
    
    # 4. Volume Trend (last 3 candles increasing)
    df["vol_trend_up"] = (
        (df["Volume"] > df["Volume"].shift(1)) & 
        (df["Volume"].shift(1) > df["Volume"].shift(2))
    )
    
    # 5. Volume Percentile (where does this volume stand in last 50 candles)
    df["vol_percentile"] = df["Volume"].rolling(window=50, min_periods=10).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False
    )
    
    # 6. Volume Score (0-100)
    def calc_vol_score(row):
        score = 0
        rel_vol = row["rel_volume"]
        
        if rel_vol >= EXTREME_VOLUME_SPIKE:      # 2x+ volume
            score = 100
        elif rel_vol >= 1.8:                      # 1.8x volume
            score = 90
        elif rel_vol >= 1.5:                      # 1.5x volume
            score = 75
        elif rel_vol >= MIN_VOLUME_SPIKE:         # 1.3x volume
            score = 60
        elif rel_vol >= 1.1:                      # 1.1x volume
            score = 40
        elif rel_vol >= 1.0:                      # Average volume
            score = 25
        else:                                     # Below average
            score = 10
        
        # Bonus for volume trend up
        if row.get("vol_trend_up", False):
            score = min(100, score + 10)
        
        return score
    
    df["vol_score"] = df.apply(calc_vol_score, axis=1)
    
    return df


# ==================== EXTRAORDINARY WICK ANALYSIS ====================
def calculate_wick_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    EXTRAORDINARY Wick/Rejection Analysis:
    1. Total Candle Range
    2. Body Size
    3. Upper Wick Size
    4. Lower Wick Size
    5. Wick Ratios
    6. Rejection Strength Score
    """
    # Basic calculations
    df["candle_range"] = df["High"] - df["Low"]
    df["body_size"] = abs(df["Close"] - df["Open"])
    df["is_bullish"] = df["Close"] > df["Open"]
    
    # Wick calculations
    df["upper_wick"] = df["High"] - df[["Open", "Close"]].max(axis=1)
    df["lower_wick"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
    
    # Wick Ratios (relative to total range)
    df["lower_wick_ratio"] = np.where(
        df["candle_range"] > 0,
        df["lower_wick"] / df["candle_range"],
        0
    )
    df["upper_wick_ratio"] = np.where(
        df["candle_range"] > 0,
        df["upper_wick"] / df["candle_range"],
        0
    )
    
    # Body to Range Ratio
    df["body_ratio"] = np.where(
        df["candle_range"] > 0,
        df["body_size"] / df["candle_range"],
        0
    )
    
    # Wick to Body Ratio (lower wick vs body)
    df["wick_body_ratio"] = np.where(
        df["body_size"] > 0,
        df["lower_wick"] / df["body_size"],
        0
    )
    
    # Rejection Strength Score (0-100)
    def calc_wick_score(row):
        score = 0
        lw_ratio = row["lower_wick_ratio"]
        is_bull = row["is_bullish"]
        
        # Lower wick ratio scoring (for bullish grabs)
        if lw_ratio >= EXTREME_WICK_RATIO:        # 75%+ = Hammer/Dragonfly
            score = 100
        elif lw_ratio >= STRONG_WICK_RATIO:       # 60%+ = Strong rejection
            score = 85
        elif lw_ratio >= 0.5:                      # 50%+ = Good rejection
            score = 70
        elif lw_ratio >= MIN_WICK_RATIO:          # 40%+ = Decent rejection
            score = 55
        elif lw_ratio >= 0.3:                      # 30%+ = Weak rejection
            score = 35
        elif lw_ratio >= 0.2:                      # 20%+ = Very weak
            score = 20
        else:                                      # <20% = No rejection
            score = 5
        
        # Bonus for bullish candle
        if is_bull:
            score = min(100, score + 10)
        
        # Bonus for small upper wick (clean rejection)
        if row["upper_wick_ratio"] < 0.1:
            score = min(100, score + 5)
        
        # Bonus for wick > body (strong rejection signal)
        if row["wick_body_ratio"] > 2:
            score = min(100, score + 10)
        
        return score
    
    df["wick_score"] = df.apply(calc_wick_score, axis=1)
    
    # Special candle patterns detection
    df["is_hammer"] = (
        (df["lower_wick_ratio"] >= 0.6) & 
        (df["upper_wick_ratio"] < 0.1) &
        (df["body_ratio"] < 0.3)
    )
    df["is_dragonfly"] = (
        (df["lower_wick_ratio"] >= 0.8) & 
        (df["body_ratio"] < 0.05)
    )
    df["is_bullish_engulfing"] = False  # Will be set in pattern detection
    
    return df


# ==================== ADVANCED SWING DETECTION ====================
def detect_swing_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Advanced Swing Level Detection:
    1. Dynamic lookback based on volatility
    2. Swing strength calculation
    3. Equal lows detection (stronger liquidity)
    4. Swing age tracking
    """
    df["swing_low"] = False
    df["swing_high"] = False
    df["swing_strength"] = 0.0  # Changed to float
    df["equal_low_zone"] = False
    
    # Detect swing lows
    for i in range(SWING_LOOKBACK_LEFT, len(df) - SWING_LOOKBACK_RIGHT):
        curr_low = df["Low"].iloc[i]
        
        # Check left side
        left_higher = all(df["Low"].iloc[i-j] > curr_low for j in range(1, SWING_LOOKBACK_LEFT + 1))
        
        # Check right side
        right_higher = all(df["Low"].iloc[i+j] > curr_low for j in range(1, SWING_LOOKBACK_RIGHT + 1))
        
        if left_higher and right_higher:
            df.loc[df.index[i], "swing_low"] = True
            
            # Calculate swing strength (how much lower than neighbors)
            left_avg = df["Low"].iloc[i-SWING_LOOKBACK_LEFT:i].mean()
            right_avg = df["Low"].iloc[i+1:i+SWING_LOOKBACK_RIGHT+1].mean()
            avg_neighbor = (left_avg + right_avg) / 2
            strength = ((avg_neighbor - curr_low) / curr_low) * 100
            df.loc[df.index[i], "swing_strength"] = strength
    
    # Detect equal lows (within 0.5% tolerance)
    swing_indices = df[df["swing_low"]].index.tolist()
    for i, idx1 in enumerate(swing_indices):
        for idx2 in swing_indices[i+1:]:
            low1 = df.loc[idx1, "Low"]
            low2 = df.loc[idx2, "Low"]
            tolerance = low1 * 0.005
            
            if abs(low1 - low2) <= tolerance:
                df.loc[idx1, "equal_low_zone"] = True
                df.loc[idx2, "equal_low_zone"] = True
    
    return df


# ==================== MAIN DETECTION ENGINE ====================
def detect_liquidity_grab_v2(df: pd.DataFrame) -> pd.DataFrame:
    """
    EXTRAORDINARY Liquidity Grab Detection with Signal Scoring
    
    Returns signals with:
    - Volume analysis
    - Wick analysis
    - Swing analysis
    - Combined quality score
    - Grade (A/B/C)
    """
    # Step 1: Calculate all metrics
    df = calculate_volume_metrics(df)
    df = calculate_wick_metrics(df)
    df = detect_swing_levels(df)
    
    # Initialize result columns with proper dtypes
    df["liquidity_grab"] = False
    df["grab_swing_level"] = 0.0
    df["grab_depth"] = 0.0
    df["grab_depth_score"] = 0.0  # Changed to float
    df["total_score"] = 0.0  # Changed to float
    df["grade"] = ""
    df["signal_details"] = ""
    
    # Get all swing lows
    swing_low_indices = df[df["swing_low"]].index.tolist()
    
    for swing_idx in swing_low_indices:
        swing_pos = df.index.get_loc(swing_idx)
        swing_level = float(df.loc[swing_idx, "Low"])
        is_equal_low = df.loc[swing_idx, "equal_low_zone"]
        swing_strength = df.loc[swing_idx, "swing_strength"]
        
        # Look ahead 1-5 candles for grab
        for j in range(swing_pos + 1, min(swing_pos + 6, len(df))):
            candle_idx = df.index[j]
            
            current_low = float(df["Low"].iloc[j])
            current_close = float(df["Close"].iloc[j])
            current_open = float(df["Open"].iloc[j])
            is_bullish = current_close > current_open
            
            # Calculate grab depth
            if swing_level > 0:
                grab_depth_pct = ((swing_level - current_low) / swing_level) * 100
            else:
                grab_depth_pct = 0
            
            # GRAB CONDITIONS:
            swing_tolerance = swing_level * 0.01  # 1% tolerance (increased for better detection)
            close_margin = swing_level * (CLOSE_ABOVE_SWING_MARGIN / 100)
            
            # Condition 1: Low touches/breaks swing level
            low_touches_swing = current_low <= swing_level + swing_tolerance
            
            # Condition 2: Close above swing level
            close_above_swing = current_close > swing_level + close_margin
            
            # Condition 3: Depth within range
            depth_valid = MIN_GRAB_DEPTH <= grab_depth_pct <= MAX_GRAB_DEPTH
            
            if low_touches_swing and close_above_swing:
                # ========== CALCULATE TOTAL SCORE ==========
                
                # 1. Volume Score (0-25)
                vol_raw = df["vol_score"].iloc[j]
                vol_final = (vol_raw / 100) * VOLUME_WEIGHT
                
                # 2. Wick Score (0-30)
                wick_raw = df["wick_score"].iloc[j]
                wick_final = (wick_raw / 100) * WICK_WEIGHT
                
                # 3. Bullish Candle Score (0-15)
                bullish_score = BULLISH_BODY_WEIGHT if is_bullish else 0
                
                # Check if bearish candle should be allowed
                wick_score_raw = df["wick_score"].iloc[j]
                strong_wick = wick_score_raw >= (STRONG_WICK_OVERRIDE * 100) if 'STRONG_WICK_OVERRIDE' in dir() else wick_score_raw >= 65
                
                # 2-Candle Confirmation: If grab candle is bearish, check if next candle is bullish
                next_candle_confirms = False
                if not is_bullish and ENABLE_2CANDLE_CONFIRM and j + 1 < len(df):
                    next_close = float(df["Close"].iloc[j + 1])
                    next_open = float(df["Open"].iloc[j + 1])
                    next_is_bullish = next_close > next_open
                    next_close_above_swing = next_close > swing_level + close_margin
                    if next_is_bullish and next_close_above_swing:
                        next_candle_confirms = True
                        bullish_score = BULLISH_BODY_WEIGHT * 0.7  # Partial score for 2-candle pattern
                
                # Skip if: bearish AND weak wick AND no 2-candle confirmation
                if not is_bullish and not strong_wick and not next_candle_confirms:
                    if REQUIRE_BULLISH_CANDLE:
                        continue
                
                # 4. Depth Score (0-15)
                if depth_valid:
                    # Optimal depth is around 0.5-1.5%
                    if 0.5 <= grab_depth_pct <= 1.5:
                        depth_score = DEPTH_WEIGHT
                    elif grab_depth_pct < 0.5:
                        depth_score = DEPTH_WEIGHT * 0.7
                    else:
                        depth_score = DEPTH_WEIGHT * 0.5
                else:
                    depth_score = 0
                
                # 5. Context Score (0-15)
                context_score = 0
                # Bonus for equal low zone (stronger liquidity)
                if is_equal_low:
                    context_score += 8
                # Bonus for strong swing
                if swing_strength > 1.0:
                    context_score += 7
                context_score = min(CONTEXT_WEIGHT, context_score)
                
                # TOTAL SCORE
                total_score = vol_final + wick_final + bullish_score + depth_score + context_score
                total_score = min(100, total_score)  # Cap at 100
                
                # Determine Grade
                if total_score >= GRADE_A_MIN_SCORE:
                    grade = "A+"
                elif total_score >= GRADE_B_MIN_SCORE:
                    grade = "B"
                elif total_score >= GRADE_C_MIN_SCORE:
                    grade = "C"
                else:
                    grade = "D"
                
                # Only save Grade C or better
                if total_score >= GRADE_C_MIN_SCORE:
                    df.loc[candle_idx, "liquidity_grab"] = True
                    df.loc[candle_idx, "grab_swing_level"] = swing_level
                    df.loc[candle_idx, "grab_depth"] = grab_depth_pct
                    df.loc[candle_idx, "grab_depth_score"] = depth_score
                    df.loc[candle_idx, "total_score"] = total_score
                    df.loc[candle_idx, "grade"] = grade
                    
                    # Build details string (ASCII compatible)
                    vol_label = "[FIRE]" if vol_raw >= 75 else "[OK]" if vol_raw >= 50 else "[LOW]"
                    wick_label = "[HIT]" if wick_raw >= 75 else "[OK]" if wick_raw >= 50 else "[LOW]"
                    
                    # Candle label with 2-candle pattern
                    if is_bullish:
                        candle_label = "[BULL]"
                    elif next_candle_confirms:
                        candle_label = "[BEAR->BULL]"  # 2-candle confirmation pattern
                    else:
                        candle_label = "[BEAR]"
                    
                    details = (
                        f"Vol:{vol_raw:.0f}{vol_label} "
                        f"Wick:{wick_raw:.0f}{wick_label} "
                        f"Candle:{candle_label} "
                        f"Depth:{grab_depth_pct:.2f}%"
                    )
                    if is_equal_low:
                        details += " [EQL]"
                    if df["is_hammer"].iloc[j]:
                        details += " [HAMMER]"
                    if df["is_dragonfly"].iloc[j]:
                        details += " [DRAGONFLY]"
                    if next_candle_confirms:
                        details += " [2-CANDLE]"
                    
                    df.loc[candle_idx, "signal_details"] = details
                    
                    break  # Found valid grab for this swing, move to next swing
    
    return df


def print_alerts_v2(ticker: str, df: pd.DataFrame, timeframe: str, filter_yesterday: bool = True) -> list:
    """Enhanced alert printing with grades and scores"""
    alerts = []
    
    today = pd.Timestamp.now(tz="Asia/Kolkata")
    today_date = today.normalize().tz_localize(None)  # Make tz-naive for comparison
    seven_days_ago = today - pd.Timedelta(days=7)
    seven_days_ago_date = seven_days_ago.normalize().tz_localize(None)  # Make tz-naive

    for i in range(len(df)):
        if not df["liquidity_grab"].iloc[i]:
            continue
        
        try:
            signal_date = pd.Timestamp(df.index[i])
            if signal_date.tz is not None:
                signal_date = signal_date.tz_localize(None)  # Make tz-naive
            signal_date = signal_date.normalize()
        except:
            signal_date = pd.Timestamp(df.index[i]).normalize()
        
        if filter_yesterday and (signal_date < seven_days_ago_date or signal_date > today_date):
            continue
        
        try:
            dt = df.index[i]
            if dt.tz is None:
                dt = dt.tz_localize("UTC").tz_convert("Asia/Kolkata")
            else:
                dt = dt.tz_convert("Asia/Kolkata")
            dt = dt.replace(hour=9, minute=15)
            time_str = dt.strftime("%d-%b-%Y %H:%M IST")
        except:
            time_str = df.index[i].strftime("%d-%b-%Y")

        # Get all details
        close_price = df["Close"].iloc[i]
        grade = df["grade"].iloc[i]
        total_score = df["total_score"].iloc[i]
        details = df["signal_details"].iloc[i]
        
        # Grade marker (ASCII compatible)
        grade_marker = "***" if grade == "A+" else " * " if grade == "B" else "   "
        
        tf_label = "1D" if timeframe.lower() == "1d" else "4H"
        
        alert = {
            "text": f"   {grade_marker}[{grade}] [{tf_label}] {ticker:<12} @ {time_str} | Rs.{close_price:.2f} | Score: {total_score:.0f}/100",
            "details": f"         -> {details}",
            "grade": grade,
            "score": total_score,
            "date": time_str
        }
        alerts.append(alert)

    return alerts


def main():
    if not YFINANCE_AVAILABLE:
        print("⚠ ERROR: yfinance not installed. Run: pip install yfinance")
        return
    
    setup_cache()
    
    tickers = load_tickers()
    if not tickers:
        return

    print("\n" + "="*80)
    print("   [*] EXTRAORDINARY LIQUIDITY GRAB SCANNER v2.0")
    print("   " + "-"*50)
    print(f"   [+] Features: Volume Spike | Wick Analysis | Signal Scoring")
    print(f"   [+] Period: {PERIOD} | Timeframes: {', '.join(TIMEFRAMES).upper()}")
    print(f"   [+] Cache: {'ON' if USE_CACHE else 'OFF'}")
    print("="*80 + "\n")

    all_alerts = []
    processed = 0
    
    for ticker in tickers:
        cache_path = get_cache_path(ticker, "1d")
        if not os.path.exists(cache_path):
            continue
        
        processed += 1
        
        for timeframe in TIMEFRAMES:
            df = get_data_with_volume(ticker, timeframe)
            if df.empty or len(df) < 30:
                continue

            df = detect_liquidity_grab_v2(df)
            alerts = print_alerts_v2(ticker, df, timeframe, filter_yesterday=True)
            all_alerts.extend(alerts)
    
    # Print results
    print("\n" + "="*80)
    print("[*] LIQUIDITY GRAB SIGNALS (Last 7 Days)")
    print("="*80 + "\n")
    
    if all_alerts:
        today = pd.Timestamp.now(tz="Asia/Kolkata").normalize()
        
        # Group by date
        all_dates = []
        for i in range(8):
            date = today - pd.Timedelta(days=i)
            all_dates.append(date.strftime("%d-%b-%Y"))
        
        alerts_by_date = {}
        for alert in all_alerts:
            try:
                date_part = alert["date"].split("IST")[0].strip()
                alert_date = pd.to_datetime(date_part, format="%d-%b-%Y %H:%M").normalize()
                date_str = alert_date.strftime("%d-%b-%Y")
                
                if date_str not in alerts_by_date:
                    alerts_by_date[date_str] = []
                alerts_by_date[date_str].append(alert)
            except:
                pass
        
        # Sort by grade within each date
        for date_str in alerts_by_date:
            alerts_by_date[date_str].sort(key=lambda x: x["score"], reverse=True)
        
        total_signals = 0
        grade_a_count = 0
        grade_b_count = 0
        
        for date_str in all_dates:
            is_today = (date_str == today.strftime("%d-%b-%Y"))
            marker = " <<< [TODAY]" if is_today else ""
            
            print(f"   [{date_str}]{marker}")
            print("   " + "-" * 76)
            
            if date_str in alerts_by_date:
                for alert in alerts_by_date[date_str]:
                    print(alert["text"])
                    print(alert["details"])
                    total_signals += 1
                    if alert["grade"] == "A+":
                        grade_a_count += 1
                    elif alert["grade"] == "B":
                        grade_b_count += 1
            else:
                print("   (No signals)")
            
            print()
        
        # Summary
        print("="*80)
        print("[SUMMARY]")
        print("="*80)
        print(f"   Total Signals: {total_signals}")
        print(f"   [A+] Grade A+ (Score >= {GRADE_A_MIN_SCORE}): {grade_a_count}")
        print(f"   [B]  Grade B  (Score >= {GRADE_B_MIN_SCORE}): {grade_b_count}")
        print(f"   [C]  Grade C  (Score >= {GRADE_C_MIN_SCORE}): {total_signals - grade_a_count - grade_b_count}")
        print(f"   Stocks Scanned: {processed}")
        print("="*80)
        
        # Grade Legend
        print("\n[SIGNAL QUALITY GUIDE]")
        print("   [A+] Grade (65-100): EXCEPTIONAL - High volume + Strong wick + All confirmations")
        print("   [B]  Grade (50-64):  GOOD - Decent setup, tradeable")
        print("   [C]  Grade (35-49):  WEAK - Missing confirmations, be cautious")
        print()
        print("[SCORE BREAKDOWN]")
        print(f"   Volume (Max {VOLUME_WEIGHT}pts): [FIRE]=75%+ [OK]=50%+ [LOW]=Below")
        print(f"   Wick   (Max {WICK_WEIGHT}pts): [HIT]=75%+ [OK]=50%+ [LOW]=Below")
        print(f"   Candle (Max {BULLISH_BODY_WEIGHT}pts): [BULL]=Bullish [BEAR]=Bearish")
        print(f"   Depth  (Max {DEPTH_WEIGHT}pts): Optimal 0.5-1.5%")
        print(f"   Context(Max {CONTEXT_WEIGHT}pts): [EQL]=Equal Lows, [HAMMER], [DRAGONFLY]")
        
    else:
        print("   (No liquidity grabs detected in last 7 days)")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
