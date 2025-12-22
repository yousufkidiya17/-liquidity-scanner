#!/usr/bin/env python3
"""
Liquidity Grab Scanner Dashboard - Multi Swing Detection
Detects 2-candle, 3-candle, and 5-candle swing lows
"""
import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta

st.set_page_config(
    page_title="TAWAQQUL Scanner", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="🎯"
)

# ========== SETTINGS ==========
PERIOD = "6mo"
SWING_LENGTHS = [2, 3, 5]  # Multiple swing lengths - 2, 3, and 5 candles
MIN_WICK_PERCENT = 25  # Minimum wick percentage
MIN_DEPTH_PERCENT = 0.1  # Minimum depth below swing

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
    .metric-card .value { color: #ffffff; font-size: 1.5em; font-weight: 600; margin: 5px 0 0 0; }
    .signal-good { background: rgba(0,200,83,0.15); border-left: 4px solid #00c853; padding: 12px; border-radius: 5px; margin: 8px 0; }
    .signal-medium { background: rgba(255,193,7,0.15); border-left: 4px solid #ffc107; padding: 12px; border-radius: 5px; margin: 8px 0; }
    .signal-weak { background: rgba(255,82,82,0.1); border-left: 4px solid #ff5252; padding: 12px; border-radius: 5px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# Header with Logo
import base64

def get_logo_base64():
    """Get logo as base64 for embedding"""
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

logo_b64 = get_logo_base64()
if logo_b64:
    st.markdown(f"""
    <div class="main-header" style="display: flex; align-items: center; gap: 20px;">
        <img src="data:image/png;base64,{logo_b64}" style="height: 70px; filter: invert(1);">
        <div>
            <h1 style="margin: 0;">TAWAQQUL SCANNER</h1>
            <p style="margin: 8px 0 0 0; font-size: 1.3em; font-family: 'Traditional Arabic', 'Scheherazade', serif; direction: rtl; letter-spacing: 2px; color: #ffd700;">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</p>
            <p style="margin: 5px 0 0 0; font-size: 0.85em; opacity: 0.9; letter-spacing: 1px;">Institutional Liquidity Detection</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="main-header">
        <h1>🎯 TAWAQQUL SCANNER</h1>
        <p style="font-size: 1.3em; font-family: 'Traditional Arabic', 'Scheherazade', serif; direction: rtl; letter-spacing: 2px; color: #ffd700;">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</p>
        <p style="font-size: 0.85em; opacity: 0.9;">Institutional Liquidity Detection</p>
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

def detect_pivot_lows_multi(df, lengths=[2, 3, 5]):
    """
    Detect pivot lows with MULTIPLE swing lengths
    - 2 candle swing = recent/small swings
    - 3 candle swing = medium swings  
    - 5 candle swing = major swings
    """
    all_pivots = []
    seen_indices = set()
    
    for length in lengths:
        for i in range(length, len(df) - length):
            if i in seen_indices:
                continue
                
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
                all_pivots.append({
                    'index': i,
                    'date': df.index[i],
                    'price': current_low,
                    'swing_type': length
                })
                seen_indices.add(i)
    
    return all_pivots

def detect_liquidity_sweep(df, pivot_lows):
    """
    Detect liquidity sweep:
    - Low goes BELOW swing low (sweep/hunt)
    - Close stays ABOVE swing low (rejection = BULLISH)
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
            
        # Lower wick
        body_low = min(candle_open, candle_close)
        lower_wick = body_low - candle_low
        wick_percent = (lower_wick / candle_range) * 100
        
        # Check against each pivot low
        for pivot in pivot_lows:
            pivot_idx = pivot['index']
            swing_low = pivot['price']
            swing_type = pivot['swing_type']
            
            # Pivot must be BEFORE current candle
            if pivot_idx >= i:
                continue
            
            # Not too old (within 50 bars)
            if pivot_idx < i - 50:
                continue
            
            # === BULLISH SWEEP CONDITIONS ===
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
                score = calculate_score(wick_percent, depth_percent, candle_close, swing_low, swing_type)
                
                # Bullish candle bonus
                is_bullish = candle_close > candle_open
                
                signals.append({
                    'date': current_date,
                    'index': i,
                    'swing_low': swing_low,
                    'swing_type': swing_type,
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

def calculate_score(wick_pct, depth_pct, close, swing, swing_type):
    """Calculate signal quality score (0-100)"""
    score = 0
    
    # Wick score (max 30)
    if wick_pct >= 55:
        score += 30
    elif wick_pct >= 40:
        score += 22
    elif wick_pct >= 25:
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
    
    # Swing type bonus (max 20)
    # Bigger swing = more significant
    if swing_type >= 5:
        score += 20  # Major swing
    elif swing_type >= 3:
        score += 15  # Medium swing
    else:
        score += 10  # Small swing
    
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

def get_swing_label(swing_type):
    if swing_type >= 5:
        return "Major"
    elif swing_type >= 3:
        return "Medium"
    else:
        return "Minor"

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("### ⚙️ Scan Settings")
    st.success("🌐 Multi-Swing Detection")
    st.caption("Detects 2, 3 & 5 candle swings")
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

# ========== SCAN ==========
if scan_clicked:
    if not selected_files:
        st.error("⚠️ Please select at least one file!")
    else:
        progress = st.progress(0)
        status = st.empty()
        
        all_signals = []
        total = len(selected_files)
        cutoff_date = datetime.now() - timedelta(days=days_filter)
        
        for idx, csv_file in enumerate(selected_files):
            file_name = os.path.basename(csv_file).replace('.csv', '').upper()
            status.info(f"🔄 Scanning: {file_name} ({idx+1}/{total})")
            
            try:
                tickers_df = pd.read_csv(csv_file, header=None)
                tickers = tickers_df.iloc[:, 0].astype(str).str.strip().tolist()
                
                ticker_progress = st.empty()
                
                for t_idx, ticker in enumerate(tickers):
                    ticker_progress.text(f"   {ticker} ({t_idx+1}/{len(tickers)})")
                    
                    df = download_data(ticker)
                    if df.empty or len(df) < 20:
                        continue
                    
                    # Multi-swing detection
                    pivot_lows = detect_pivot_lows_multi(df, SWING_LENGTHS)
                    signals = detect_liquidity_sweep(df, pivot_lows)
                    
                    # Filter signals
                    for sig in signals:
                        sig_date = sig['date']
                        if hasattr(sig_date, 'to_pydatetime'):
                            sig_date = sig_date.to_pydatetime()
                        if hasattr(sig_date, 'replace'):
                            sig_date = sig_date.replace(tzinfo=None)
                        
                        if sig_date >= cutoff_date and sig['score'] >= min_score:
                            sig['ticker'] = ticker
                            sig['file'] = file_name
                            all_signals.append(sig)
                
                ticker_progress.empty()
                    
            except Exception as e:
                st.warning(f"Error in {file_name}: {str(e)[:40]}")
            
            progress.progress((idx + 1) / total)
        
        progress.empty()
        status.empty()
        
        # ========== RESULTS ==========
        st.markdown("## 📋 Scan Results (BULLISH Sweeps)")
        
        if not all_signals:
            st.info(f"ℹ️ No quality signals found in last {days_filter} days with score >= {min_score}")
        else:
            # Sort by score
            all_signals = sorted(all_signals, key=lambda x: x['score'], reverse=True)
            
            # Summary
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📊 Total Signals", len(all_signals))
            col2.metric("🏆 A+ Signals", len([s for s in all_signals if s['grade'] == 'A+']))
            col3.metric("✅ B Signals", len([s for s in all_signals if s['grade'] == 'B']))
            col4.metric("📈 Stocks", len(set(s['ticker'] for s in all_signals)))
            
            st.markdown("---")
            
            # Grade A+ signals
            a_plus = [s for s in all_signals if s['grade'] == 'A+']
            if a_plus:
                st.markdown("### 🏆 Grade A+ (Score ≥ 70) - BEST SETUPS")
                for s in a_plus:
                    date_str = s['date'].strftime('%d-%b') if hasattr(s['date'], 'strftime') else str(s['date'])
                    swing_label = get_swing_label(s['swing_type'])
                    st.markdown(f"""
                    <div class="signal-good">
                        <b style="font-size:1.2em;">{s['ticker']}</b> &nbsp;|&nbsp; {date_str} &nbsp;|&nbsp; 
                        Score: <b>{s['score']}/100</b> &nbsp;|&nbsp;
                        Swing: ₹{s['swing_low']:.2f} ({swing_label}) &nbsp;|&nbsp;
                        Depth: {s['depth_percent']:.2f}% &nbsp;|&nbsp;
                        Wick: {s['wick_percent']:.0f}%
                    </div>
                    """, unsafe_allow_html=True)
            
            # Grade B signals
            b_grade = [s for s in all_signals if s['grade'] == 'B']
            if b_grade:
                st.markdown("### ✅ Grade B (Score 55-69) - GOOD SETUPS")
                for s in b_grade:
                    date_str = s['date'].strftime('%d-%b') if hasattr(s['date'], 'strftime') else str(s['date'])
                    swing_label = get_swing_label(s['swing_type'])
                    st.markdown(f"""
                    <div class="signal-medium">
                        <b style="font-size:1.1em;">{s['ticker']}</b> &nbsp;|&nbsp; {date_str} &nbsp;|&nbsp; 
                        Score: <b>{s['score']}/100</b> &nbsp;|&nbsp;
                        Swing: ₹{s['swing_low']:.2f} ({swing_label}) &nbsp;|&nbsp;
                        Depth: {s['depth_percent']:.2f}% &nbsp;|&nbsp;
                        Wick: {s['wick_percent']:.0f}%
                    </div>
                    """, unsafe_allow_html=True)
            
            # Grade C/D signals
            lower = [s for s in all_signals if s['grade'] in ['C', 'D']]
            if lower:
                st.markdown("### 📋 Other Signals (Score < 55)")
                rows = []
                for s in lower:
                    date_str = s['date'].strftime('%d-%b') if hasattr(s['date'], 'strftime') else str(s['date'])
                    rows.append({
                        'Stock': s['ticker'],
                        'Date': date_str,
                        'Score': s['score'],
                        'Grade': s['grade'],
                        'Swing': f"₹{s['swing_low']:.2f}",
                        'Type': get_swing_label(s['swing_type']),
                        'Depth%': f"{s['depth_percent']:.2f}",
                        'Wick%': f"{s['wick_percent']:.0f}"
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            
            # Export
            st.markdown("---")
            st.markdown("### 💾 Export")
            
            export_rows = []
            for s in all_signals:
                date_str = s['date'].strftime('%Y-%m-%d') if hasattr(s['date'], 'strftime') else str(s['date'])
                export_rows.append({
                    'Stock': s['ticker'],
                    'Date': date_str,
                    'Score': s['score'],
                    'Grade': s['grade'],
                    'Swing_Low': s['swing_low'],
                    'Swing_Type': get_swing_label(s['swing_type']),
                    'Depth_Percent': s['depth_percent'],
                    'Wick_Percent': s['wick_percent'],
                    'Close': s['close']
                })
            
            df_export = pd.DataFrame(export_rows)
            csv_data = df_export.to_csv(index=False)
            st.download_button("📥 Download CSV", csv_data, "liquidity_signals.csv", "text/csv")

# Footer
st.markdown("---")
with st.expander("ℹ️ How It Works"):
    st.markdown("""
    **Multi-Swing Liquidity Sweep Detection:**
    
    🔹 **Swing Detection:**
    - 2-candle swing = Minor/Recent swings
    - 3-candle swing = Medium swings
    - 5-candle swing = Major swings
    
    🔹 **Sweep Conditions:**
    - Wick goes BELOW swing low (liquidity grabbed)
    - Close stays ABOVE swing low (bullish rejection)
    - Minimum 25% wick required
    - Minimum 0.1% depth required
    
    🔹 **Scoring (0-100):**
    - Wick size: up to 30 pts
    - Depth: up to 25 pts  
    - Close position: up to 25 pts
    - Swing significance: up to 20 pts
    
    🔹 **Grades:**
    - A+ (≥70): Best setups - High conviction
    - B (55-69): Good setups - Worth watching
    - C (40-54): Weak setups - Risky
    - D (<40): Avoid
    """)

st.markdown("""<div style="text-align: center; color: #6e7681; padding: 20px; font-size: 0.85em;">
    TAWAQQUL SCANNER v1.0 • by @yousufkidiya17 • Smart Money Concepts
</div>""", unsafe_allow_html=True)
