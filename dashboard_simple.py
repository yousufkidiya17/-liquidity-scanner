#!/usr/bin/env python3
"""
Liquidity Grab Scanner Dashboard - LuxAlgo Style
Proper swing detection with scoring system
"""
import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Liquidity Scanner", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# ========== LUXALGO SETTINGS ==========
PERIOD = "6mo"
SWING_LENGTH = 5  # 5 bars left + 5 bars right (like LuxAlgo)
MIN_WICK_PERCENT = 30  # Minimum 30% wick of total candle
MIN_DEPTH_PERCENT = 0.1  # Minimum 0.1% below swing

# Simple Clean CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .main-header {
        background: linear-gradient(90deg, #1e3a5f, #2d5a87);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 4px solid #00d4ff;
    }
    .main-header h1 { color: #ffffff; font-size: 1.8em; margin: 0; font-weight: 600; }
    .main-header p { color: #a0c4e8; margin: 5px 0 0 0; font-size: 0.95em; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .metric-card {
        background: #1e2530;
        padding: 15px 20px;
        border-radius: 8px;
        border-left: 3px solid #00d4ff;
        margin: 5px 0;
    }
    .metric-card h3 { color: #8b949e; font-size: 0.85em; margin: 0; font-weight: 400; }
    .metric-card .value { color: #ffffff; font-size: 1.8em; font-weight: 600; margin: 5px 0 0 0; }
    .signal-good { background: rgba(0,200,83,0.1); border-left: 3px solid #00c853; padding: 10px; border-radius: 5px; margin: 5px 0; }
    .signal-weak { background: rgba(255,193,7,0.1); border-left: 3px solid #ffc107; padding: 10px; border-radius: 5px; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 Liquidity Grab Scanner (LuxAlgo Style)</h1>
    <p>BULLISH Swing Low Sweeps Only • Proper Detection</p>
</div>
""", unsafe_allow_html=True)

# ========== HELPER FUNCTIONS ==========
@st.cache_data(ttl=3600)
def download_data(ticker):
    """Download data from yfinance"""
    try:
        df = yf.download(ticker, period=PERIOD, interval="1d", progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

def detect_pivot_lows(df, length=5):
    """
    LuxAlgo style pivot low detection
    A pivot low needs 'length' bars on left AND right to be higher
    """
    pivot_lows = []
    
    for i in range(length, len(df) - length):
        current_low = df['Low'].iloc[i]
        is_pivot = True
        
        # Check left side
        for j in range(1, length + 1):
            if df['Low'].iloc[i - j] <= current_low:
                is_pivot = False
                break
        
        # Check right side
        if is_pivot:
            for j in range(1, length + 1):
                if df['Low'].iloc[i + j] <= current_low:
                    is_pivot = False
                    break
        
        if is_pivot:
            pivot_lows.append({
                'index': i,
                'date': df.index[i],
                'price': current_low
            })
    
    return pivot_lows

def luxalgo_sweep_detection(df, pivot_lows):
    """
    LuxAlgo style sweep detection:
    - Low goes BELOW swing low (sweep)
    - Close stays ABOVE swing low (rejection = BULLISH)
    - Must have significant wick
    """
    signals = []
    
    for i in range(len(df)):
        current = df.iloc[i]
        current_date = df.index[i]
        
        candle_low = current['Low']
        candle_high = current['High']
        candle_close = current['Close']
        candle_open = current['Open']
        
        # Calculate candle metrics
        candle_range = candle_high - candle_low
        if candle_range == 0:
            continue
            
        # Lower wick (for bullish - wick below body)
        body_low = min(candle_open, candle_close)
        lower_wick = body_low - candle_low
        wick_percent = (lower_wick / candle_range) * 100
        
        # Check against each pivot low
        for pivot in pivot_lows:
            pivot_idx = pivot['index']
            swing_low = pivot['price']
            
            # Pivot must be BEFORE current candle
            if pivot_idx >= i:
                continue
            
            # Not too old (within 50 bars)
            if pivot_idx < i - 50:
                continue
            
            # === BULLISH SWEEP CONDITIONS ===
            # 1. Low must go BELOW swing low (liquidity grab)
            # 2. Close must be ABOVE swing low (rejection/reversal)
            # 3. Must have decent wick
            
            if candle_low < swing_low and candle_close > swing_low:
                # Calculate depth
                depth_points = swing_low - candle_low
                depth_percent = (depth_points / swing_low) * 100
                
                # Filter: minimum depth
                if depth_percent < MIN_DEPTH_PERCENT:
                    continue
                
                # Filter: minimum wick
                if wick_percent < MIN_WICK_PERCENT:
                    continue
                
                # Calculate score
                score = calculate_score(wick_percent, depth_percent, candle_close, swing_low, candle_range)
                
                # Determine if bullish candle
                is_bullish = candle_close > candle_open
                
                signals.append({
                    'date': current_date,
                    'index': i,
                    'swing_low': swing_low,
                    'candle_low': candle_low,
                    'close': candle_close,
                    'depth_percent': depth_percent,
                    'wick_percent': wick_percent,
                    'score': score,
                    'is_bullish_candle': is_bullish,
                    'grade': get_grade(score)
                })
                break  # One signal per candle
    
    return signals

def calculate_score(wick_pct, depth_pct, close, swing, candle_range):
    """Calculate signal quality score (0-100)"""
    score = 0
    
    # Wick score (max 30)
    if wick_pct >= 60:
        score += 30
    elif wick_pct >= 45:
        score += 22
    elif wick_pct >= 30:
        score += 15
    else:
        score += 8
    
    # Depth score (max 25)
    if 0.3 <= depth_pct <= 1.5:
        score += 25  # Optimal
    elif depth_pct > 1.5:
        score += 15  # Too deep
    elif depth_pct >= 0.1:
        score += 18
    
    # Close position score (max 25)
    close_above = ((close - swing) / swing) * 100
    if close_above >= 1.0:
        score += 25
    elif close_above >= 0.5:
        score += 18
    elif close_above >= 0.2:
        score += 12
    else:
        score += 5
    
    # Candle structure (max 20)
    score += 15  # Base for valid pattern
    
    return min(score, 100)

def get_grade(score):
    if score >= 70:
        return "A+"
    elif score >= 55:
        return "B"
    elif score >= 40:
        return "C"
    else:
        return "D"

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("### ⚙️ Scan Settings")
    st.success("🌐 Live Data | LuxAlgo Logic")
    st.markdown("---")
    
    scan_type = st.radio("📁 Select Scan Type", ["INDEX", "SECTOR"], horizontal=True)
    
    selected_files = []
    
    if scan_type == "INDEX":
        index_path = "INDEX CSV"
        if os.path.exists(index_path):
            all_files = sorted([f for f in os.listdir(index_path) if f.endswith('.csv')])
            selected_ui = st.multiselect("Select Indices", all_files, default=["nifty50.csv"] if "nifty50.csv" in all_files else all_files[:1])
            selected_files = [os.path.join(index_path, f) for f in selected_ui]
        else:
            st.warning("INDEX CSV folder not found")
            
    else:
        sector_path = "SECTORS CSV"
        if os.path.exists(sector_path):
            all_files = sorted([f for f in os.listdir(sector_path) if f.endswith('.csv')])
            selected_ui = st.multiselect("Select Sectors", all_files, default=all_files[:2] if len(all_files) >= 2 else all_files)
            selected_files = [os.path.join(sector_path, f) for f in selected_ui]
        else:
            st.warning("SECTORS CSV folder not found")
    
    st.markdown("---")
    days_filter = st.slider("Show signals from last N days", 1, 30, 10)
    min_score = st.slider("Minimum Score", 0, 100, 40)
    st.markdown("---")
    scan_clicked = st.button("🚀 Start Scan", use_container_width=True, type="primary")

# ========== MAIN CONTENT ==========
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""<div class="metric-card"><h3>Logic</h3><div class="value">LuxAlgo</div></div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="metric-card"><h3>Swing Length</h3><div class="value">{SWING_LENGTH}</div></div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div class="metric-card"><h3>Min Wick</h3><div class="value">{MIN_WICK_PERCENT}%</div></div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class="metric-card"><h3>Min Depth</h3><div class="value">{MIN_DEPTH_PERCENT}%</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# ========== SCAN ==========
if scan_clicked:
    if not selected_files:
        st.error("⚠️ Please select at least one file!")
    else:
        progress = st.progress(0)
        status = st.empty()
        
        all_signals = {}
        total = len(selected_files)
        cutoff_date = datetime.now() - timedelta(days=days_filter)
        
        for idx, csv_file in enumerate(selected_files):
            file_name = os.path.basename(csv_file).replace('.csv', '').upper()
            status.info(f"🔄 Scanning: {file_name} ({idx+1}/{total})")
            
            try:
                tickers_df = pd.read_csv(csv_file, header=None)
                tickers = tickers_df.iloc[:, 0].astype(str).str.strip().tolist()
                
                file_signals = []
                ticker_progress = st.empty()
                
                for t_idx, ticker in enumerate(tickers):
                    ticker_progress.text(f"   {ticker} ({t_idx+1}/{len(tickers)})")
                    
                    df = download_data(ticker)
                    if df.empty or len(df) < 20:
                        continue
                    
                    # LuxAlgo detection
                    pivot_lows = detect_pivot_lows(df, SWING_LENGTH)
                    signals = luxalgo_sweep_detection(df, pivot_lows)
                    
                    # Filter signals
                    for sig in signals:
                        sig_date = sig['date']
                        if hasattr(sig_date, 'to_pydatetime'):
                            sig_date = sig_date.to_pydatetime()
                        if hasattr(sig_date, 'replace'):
                            sig_date = sig_date.replace(tzinfo=None)
                        
                        if sig_date >= cutoff_date and sig['score'] >= min_score:
                            file_signals.append({
                                'ticker': ticker,
                                'date': sig['date'],
                                'swing': sig['swing_low'],
                                'depth': sig['depth_percent'],
                                'wick': sig['wick_percent'],
                                'score': sig['score'],
                                'grade': sig['grade'],
                                'close': sig['close']
                            })
                
                ticker_progress.empty()
                
                if file_signals:
                    all_signals[file_name] = file_signals
                    
            except Exception as e:
                st.warning(f"Error in {file_name}: {str(e)[:40]}")
            
            progress.progress((idx + 1) / total)
        
        progress.empty()
        status.empty()
        
        # ========== RESULTS ==========
        st.markdown("## 📋 Scan Results (BULLISH Sweeps Only)")
        
        if not all_signals:
            st.info(f"ℹ️ No quality signals found in last {days_filter} days with score >= {min_score}")
        else:
            total_sigs = sum(len(s) for s in all_signals.values())
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📊 Total Signals", total_sigs)
            col2.metric("📈 Stocks with Signals", sum(len(set(s['ticker'] for s in sigs)) for sigs in all_signals.values()))
            col3.metric("📁 Files with Signals", len(all_signals))
            
            st.markdown("---")
            
            # Sort by score
            all_sorted = []
            for file_name, sigs in all_signals.items():
                for s in sigs:
                    s['file'] = file_name
                    all_sorted.append(s)
            
            all_sorted = sorted(all_sorted, key=lambda x: x['score'], reverse=True)
            
            # Grade A+ signals
            a_plus = [s for s in all_sorted if s['grade'] == 'A+']
            if a_plus:
                st.markdown("### 🏆 Grade A+ Signals (Score ≥ 70)")
                for s in a_plus:
                    date_str = s['date'].strftime('%d-%b') if hasattr(s['date'], 'strftime') else str(s['date'])
                    st.markdown(f"""
                    <div class="signal-good">
                        <b>{s['ticker']}</b> | {date_str} | Score: <b>{s['score']}/100</b> | 
                        Swing: ₹{s['swing']:.2f} | Depth: {s['depth']:.2f}% | Wick: {s['wick']:.0f}%
                    </div>
                    """, unsafe_allow_html=True)
            
            # Grade B signals
            b_grade = [s for s in all_sorted if s['grade'] == 'B']
            if b_grade:
                st.markdown("### ✅ Grade B Signals (Score 55-69)")
                for s in b_grade:
                    date_str = s['date'].strftime('%d-%b') if hasattr(s['date'], 'strftime') else str(s['date'])
                    st.markdown(f"""
                    <div class="signal-weak">
                        <b>{s['ticker']}</b> | {date_str} | Score: <b>{s['score']}/100</b> | 
                        Swing: ₹{s['swing']:.2f} | Depth: {s['depth']:.2f}% | Wick: {s['wick']:.0f}%
                    </div>
                    """, unsafe_allow_html=True)
            
            # Lower grades in table
            lower = [s for s in all_sorted if s['grade'] in ['C', 'D']]
            if lower:
                st.markdown("### 📋 Other Signals")
                df_display = pd.DataFrame(lower)[['ticker', 'date', 'score', 'grade', 'swing', 'depth', 'wick']]
                df_display.columns = ['Stock', 'Date', 'Score', 'Grade', 'Swing', 'Depth%', 'Wick%']
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Export
            st.markdown("---")
            st.markdown("### 💾 Export")
            
            df_export = pd.DataFrame(all_sorted)
            csv_data = df_export.to_csv(index=False)
            st.download_button("📥 Download CSV", csv_data, "liquidity_signals.csv", "text/csv")

# Footer
st.markdown("---")
with st.expander("ℹ️ How It Works"):
    st.markdown("""
    **LuxAlgo Style Liquidity Sweep Detection:**
    
    1. **Find Swing Lows** - Price must be lowest for 5 bars on BOTH sides
    2. **Detect Sweep** - Wick goes BELOW swing low (liquidity grabbed)
    3. **Confirm Reversal** - Close must be ABOVE swing low (bullish rejection)
    4. **Quality Filter** - Minimum 30% wick, minimum 0.1% depth
    5. **Score** - Based on wick size, depth, close position (0-100)
    
    **Grades:** A+ (≥70) | B (55-69) | C (40-54) | D (<40)
    """)

st.markdown("""<div style="text-align: center; color: #6e7681; padding: 20px; font-size: 0.85em;">
    Liquidity Scanner v3.0 • LuxAlgo Logic • BULLISH Only
</div>""", unsafe_allow_html=True)
