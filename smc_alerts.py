import pandas as pd
import time
import os

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# ===================== USER SETTINGS ==========================
# Sirf in cheezon ko change kar:

TIMEFRAMES = ["1d"]               # Using 1D (4H needs rate limit reset)
PERIOD = "6mo"                # "1d", "5d", "1mo", "3mo", "6mo", "1y"
TICKER_CSV = "microcap_250.csv"        # 250 stocks wali file
USE_CACHE = True              # Cache data to CSV to avoid re-downloading
CACHE_DIR = "data_cache"      # folder jahan data save hoga
DELAY_BETWEEN_REQUESTS = 1    # seconds - to avoid rate limit

# Advanced detection settings
SWING_LEFT = 2
SWING_RIGHT = 2
ATR_PERIOD = 14
MIN_BREAK_ATR = 0.15
# =============================================================


# --------- TICKERS CSV SE PADHNA (HEADER NAHI CHAHIYE) ----------
def load_tickers():
    try:
        # header=None  => pehli row ko bhi data maan lo
        df = pd.read_csv(TICKER_CSV, header=None)

        # first column me jo bhi values hain, unko ticker list maan lo
        tickers = (
            df.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
            .str.replace('"', '', regex=False)  # Remove quotes
            .str.replace(',', '', regex=False)  # Remove commas
            .tolist()
        )

        # Filter empty strings
        tickers = [t for t in tickers if t]

        if not tickers:
            print("⚠ ERROR: tickers.csv khali hai.")
        return tickers

    except FileNotFoundError:
        print(f"⚠ ERROR: {TICKER_CSV} file nahi mili. Same folder me honi chahiye.")
        return []
    except Exception as e:
        print("⚠ ERROR: tickers.csv read karte waqt problem aayi:", e)
        return []


# --------- CACHE MANAGEMENT ----------
def setup_cache():
    """Create cache directory if needed"""
    if USE_CACHE and not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_path(ticker, timeframe):
    """Return cache file path for ticker"""
    return os.path.join(CACHE_DIR, f"{ticker}_{PERIOD}_{timeframe}.csv")

def load_from_cache(ticker, timeframe):
    """Load data from cache if exists"""
    if not USE_CACHE:
        return None
    cache_path = get_cache_path(ticker, timeframe)
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            print(f"   ✓ {timeframe.upper()} Loaded from cache")
            return df
        except:
            return None
    return None

def save_to_cache(ticker, timeframe, df):
    """Save data to cache"""
    if not USE_CACHE or df.empty:
        return
    cache_path = get_cache_path(ticker, timeframe)
    try:
        df.to_csv(cache_path)
    except:
        pass


# --------- OHLC DATA ----------
def get_data(ticker: str, timeframe: str) -> pd.DataFrame:
    """Fetch data with caching support - for multiple timeframes"""
    # Try cache first
    df = load_from_cache(ticker, timeframe)
    if df is not None and not df.empty:
        return df
    
    time.sleep(DELAY_BETWEEN_REQUESTS)
    
    if not YFINANCE_AVAILABLE:
        print(f"   ⚠ {ticker}: yfinance not installed")
        return pd.DataFrame()
    
    try:
        print(f"   {timeframe.upper()}: Fetching from yfinance...", end=" ")
        df = yf.download(
            ticker,
            period=PERIOD,
            interval=timeframe,
            progress=False,
        )
        
        if df is None or df.empty:
            print(f"No data")
            return pd.DataFrame()
        
        # Handle multi-index columns
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        except:
            pass
        
        # Select columns
        try:
            df = df[["Open", "High", "Low", "Close"]].copy()
        except KeyError:
            print(f"Column error")
            return pd.DataFrame()
        
        print(f"OK ({len(df)} candles)")
        
        # Save to cache
        save_to_cache(ticker, timeframe, df)
        
        return df
        
    except Exception as e:
        print(f"Error: {str(e)[:50]}")
        return pd.DataFrame()


# --------- LIQUIDITY GRAB DETECTION (Low breaks swing → Close above swing) ----------
def detect_liquidity_grab(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect liquidity grab pattern:
    - Swing low detected
    - Next 1-4 candles: Low goes NEAR swing level (touches)
    - Same candle: Close ABOVE swing level (the grab)
    
    More relaxed detection to catch more patterns
    """
    df["liquidity_grab"] = False
    df["grab_swing_level"] = 0.0
    df["grab_depth"] = 0.0
    
    for i in range(1, len(df) - 3):
        # Look for swing lows (lower than neighbors)
        if i > 0 and i < len(df) - 1:
            curr_low = df["Low"].iloc[i]
            prev_low = df["Low"].iloc[i-1]
            next_low = df["Low"].iloc[i+1]
            
            # Swing low: current < previous AND current < next
            is_swing_low = (curr_low < prev_low) and (curr_low < next_low)
            
            if is_swing_low:
                swing_level = float(curr_low)
                
                # Look ahead 1-4 candles for grab pattern (more relaxed window)
                for j in range(i + 1, min(i + 5, len(df))):
                    current_low = float(df["Low"].iloc[j])
                    current_close = float(df["Close"].iloc[j])
                    
                    # LIQUIDITY GRAB (RELAXED):
                    # 1. Low touches/goes near swing level (within 0.5% tolerance)
                    # 2. Close ABOVE swing level
                    swing_tolerance = swing_level * 0.005  # 0.5% tolerance
                    
                    if (current_low <= swing_level + swing_tolerance) and (current_close > swing_level):
                        df.loc[df.index[j], "liquidity_grab"] = True
                        df.loc[df.index[j], "grab_swing_level"] = swing_level
                        df.loc[df.index[j], "grab_depth"] = (swing_level - current_low) / swing_level * 100
                        break
    
    return df

# --------- ALERT PRINT ----------
def print_alerts(ticker: str, df: pd.DataFrame, timeframe: str, filter_yesterday: bool = True) -> list:
    """Returns list of liquidity grab alerts - filters for last 7 days if enabled"""
    alerts = []
    
    # Get date range (India timezone)
    today = pd.Timestamp.now(tz="Asia/Kolkata")
    today_date = today.normalize()
    seven_days_ago = today - pd.Timedelta(days=7)
    seven_days_ago_date = seven_days_ago.normalize()

    for i in range(len(df)):
        # Skip if not a liquidity grab
        if not df["liquidity_grab"].iloc[i]:
            continue
        
        # Check if signal is from last 7 days (if filter enabled)
        try:
            signal_date = pd.Timestamp(df.index[i])
            if signal_date.tz is None:
                signal_date = signal_date.tz_localize("UTC").tz_convert("Asia/Kolkata")
            else:
                signal_date = signal_date.tz_convert("Asia/Kolkata")
            signal_date = signal_date.normalize()
        except:
            signal_date = pd.Timestamp(df.index[i]).normalize()
        
        # Skip if not within last 7 days (only if filter is enabled)
        if filter_yesterday and (signal_date < seven_days_ago_date or signal_date > today_date):
            continue
        
        # Format time in IST
        try:
            dt = df.index[i]
            if dt.tz is None:
                dt = dt.tz_localize("UTC").tz_convert("Asia/Kolkata")
            else:
                dt = dt.tz_convert("Asia/Kolkata")
            
            # For 4H, show actual time. For 1D, show 9:15 AM
            if timeframe.lower() == "4h":
                time_str = dt.strftime("%d-%b %H:%M IST")
            else:
                dt = dt.replace(hour=9, minute=15)
                time_str = dt.strftime("%d-%b-%Y %H:%M IST")
        except:
            time_str = df.index[i].strftime("%d-%b-%Y")

        # Get details
        swing_level = df["grab_swing_level"].iloc[i]
        grab_depth = df["grab_depth"].iloc[i]
        close_price = df["Close"].iloc[i]
        
        # Format alert
        tf_label = "1D" if timeframe.lower() == "1d" else "4H"
        
        alert = f"   [{tf_label}] {ticker:<12} @ {time_str} | {close_price:.2f} (Depth: {grab_depth:.2f}%)"
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

    print("\n" + "="*70)
    print("   LIQUIDITY GRAB SCANNER (4H + 1D)")
    print(f"   Period: {PERIOD} | Timeframes: {', '.join(TIMEFRAMES).upper()}")
    print(f"   Cache: {'ON' if USE_CACHE else 'OFF'}")
    print("="*70 + "\n")

    all_alerts = []
    
    for ticker in tickers:
        print(f"   {ticker}")
        
        # Check if cache exists first - skip if not
        cache_path = get_cache_path(ticker, "1d")
        if not os.path.exists(cache_path):
            print(f"   [SKIP] Cache missing")
            continue
        
        # Scan both timeframes
        for timeframe in TIMEFRAMES:
            df = get_data(ticker, timeframe)
            if df.empty:
                continue

            # Detect liquidity grabs
            df = detect_liquidity_grab(df)
            alerts = print_alerts(ticker, df, timeframe, filter_yesterday=True)  # Only Today + Yesterday
            all_alerts.extend(alerts)
    
    # Print only detected alerts at the end
    print("\n" + "="*70)
    print("LIQUIDITY GRAB SIGNALS (Last 7 Days - Including Today)")
    print("="*70 + "\n")
    
    if all_alerts:
        # Get date range
        today = pd.Timestamp.now(tz="Asia/Kolkata").normalize()
        seven_days_ago = today - pd.Timedelta(days=7)
        
        # Generate all dates in range (newest to oldest)
        all_dates_in_range = []
        for i in range(8):  # 0 to 7 days ago (8 days total)
            date = today - pd.Timedelta(days=i)
            all_dates_in_range.append(date.strftime("%d-%b-%Y"))
        
        # Group alerts by date
        alerts_by_date = {}
        
        for alert in all_alerts:
            # Parse date from alert string
            try:
                date_part = alert.split("@")[1].split("IST")[0].strip()
                alert_date = pd.to_datetime(date_part, format="%d-%b-%Y %H:%M").normalize()
                alert_date_str = alert_date.strftime("%d-%b-%Y")
                
                if alert_date_str not in alerts_by_date:
                    alerts_by_date[alert_date_str] = []
                alerts_by_date[alert_date_str].append(alert)
            except:
                if "Other" not in alerts_by_date:
                    alerts_by_date["Other"] = []
                alerts_by_date["Other"].append(alert)
        
        # Display ALL dates in range, even if no signals
        signal_count = 0
        for date_str in all_dates_in_range:
            is_today = (date_str == today.strftime("%d-%b-%Y"))
            marker = " [TODAY]" if is_today else ""
            
            print(f"   {date_str}{marker}")
            print("   " + "-" * 66)
            
            if date_str in alerts_by_date:
                for alert in alerts_by_date[date_str]:
                    print(alert)
                signal_count += len(alerts_by_date[date_str])
            else:
                print("   (No signals)")
            
            print()
        
        # Show summary
        print("="*70)
        print(f"SUMMARY:")
        print(f"   Total Signals (Last 7 Days): {signal_count}")
        print("="*70)
    else:
        print("   (No liquidity grabs in last 7 days)")
        print("="*70)
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
