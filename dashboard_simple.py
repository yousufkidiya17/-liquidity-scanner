#!/usr/bin/env python3
"""
Liquidity Grab Scanner Dashboard - Clean & Simple Version
"""
import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import scanner functions
from smc_alerts import (
    load_tickers, get_data, detect_liquidity_grab, 
    print_alerts, setup_cache, USE_CACHE, CACHE_DIR, PERIOD
)

st.set_page_config(
    page_title="Liquidity Scanner", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# Simple Clean CSS
st.markdown("""
<style>
    /* Clean Dark Theme */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(90deg, #1e3a5f, #2d5a87);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 4px solid #00d4ff;
    }
    
    .main-header h1 {
        color: #ffffff;
        font-size: 1.8em;
        margin: 0;
        font-weight: 600;
    }
    
    .main-header p {
        color: #a0c4e8;
        margin: 5px 0 0 0;
        font-size: 0.95em;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
    }
    
    /* Cards */
    .metric-card {
        background: #1e2530;
        padding: 15px 20px;
        border-radius: 8px;
        border-left: 3px solid #00d4ff;
        margin: 5px 0;
    }
    
    .metric-card h3 {
        color: #8b949e;
        font-size: 0.85em;
        margin: 0;
        font-weight: 400;
    }
    
    .metric-card .value {
        color: #ffffff;
        font-size: 1.8em;
        font-weight: 600;
        margin: 5px 0 0 0;
    }
    
    /* Signal Cards */
    .signal-bullish {
        background: linear-gradient(90deg, rgba(0, 200, 83, 0.1), transparent);
        border-left: 3px solid #00c853;
        padding: 12px 15px;
        border-radius: 5px;
        margin: 8px 0;
    }
    
    .signal-bearish {
        background: linear-gradient(90deg, rgba(255, 82, 82, 0.1), transparent);
        border-left: 3px solid #ff5252;
        padding: 12px 15px;
        border-radius: 5px;
        margin: 8px 0;
    }
    
    /* Stock name */
    .stock-name {
        color: #00d4ff;
        font-weight: 600;
        font-size: 1.1em;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #0066cc, #0088ff);
        color: white;
        border: none;
        padding: 10px 25px;
        border-radius: 6px;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background: linear-gradient(90deg, #0077dd, #0099ff);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #1e2530;
        border-radius: 5px;
    }
    
    /* Info boxes */
    .info-box {
        background: #1e2530;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #30363d;
    }
    
    /* Status indicator */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-green { background: #00c853; }
    .status-red { background: #ff5252; }
    .status-yellow { background: #ffc107; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 Liquidity Grab Scanner</h1>
    <p>Multi-Index • Multi-Sector • Daily Analysis</p>
</div>
""", unsafe_allow_html=True)

# Setup cache
setup_cache()

# Check cache status
cache_exists = os.path.exists(CACHE_DIR)
cache_count = len(os.listdir(CACHE_DIR)) if cache_exists else 0

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("### ⚙️ Scan Settings")
    
    # Cache Status
    if cache_count > 0:
        st.success(f"✅ Cache Ready: {cache_count} stocks")
    else:
        st.error("❌ No cache found! Run build script first.")
    
    st.markdown("---")
    
    # Scan Type Selection
    scan_type = st.radio(
        "📁 Select Scan Type",
        ["INDEX", "SECTOR", "CUSTOM"],
        horizontal=True
    )
    
    selected_files = []
    
    if scan_type == "INDEX":
        index_path = "INDEX CSV"
        if os.path.exists(index_path):
            all_files = sorted([f for f in os.listdir(index_path) if f.endswith('.csv')])
            selected_ui = st.multiselect(
                "Select Indices",
                all_files,
                default=all_files[:2] if len(all_files) >= 2 else all_files
            )
            selected_files = [os.path.join(index_path, f) for f in selected_ui]
        else:
            st.warning("INDEX CSV folder not found")
            
    elif scan_type == "SECTOR":
        sector_path = "SECTORS CSV"
        if os.path.exists(sector_path):
            all_files = sorted([f for f in os.listdir(sector_path) if f.endswith('.csv')])
            selected_ui = st.multiselect(
                "Select Sectors",
                all_files,
                default=all_files[:3] if len(all_files) >= 3 else all_files
            )
            selected_files = [os.path.join(sector_path, f) for f in selected_ui]
        else:
            st.warning("SECTORS CSV folder not found")
            
    else:  # CUSTOM
        root_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        if root_files:
            custom_file = st.selectbox("Select CSV File", root_files)
            selected_files = [custom_file] if custom_file else []
        else:
            st.warning("No CSV files in root directory")
    
    st.markdown("---")
    
    # Filter Options
    st.markdown("### 🎯 Filters")
    days_filter = st.slider("Show signals from last N days", 1, 30, 7)
    
    st.markdown("---")
    
    # Scan Button
    scan_clicked = st.button("🚀 Start Scan", use_container_width=True, type="primary")

# ========== MAIN CONTENT ==========
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <h3>Cache Status</h3>
        <div class="value">{}</div>
    </div>
    """.format(f"✅ {cache_count}" if cache_count > 0 else "❌ Empty"), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <h3>Period</h3>
        <div class="value">{}</div>
    </div>
    """.format(PERIOD), unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <h3>Selected Files</h3>
        <div class="value">{}</div>
    </div>
    """.format(len(selected_files)), unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card">
        <h3>Last Update</h3>
        <div class="value">{}</div>
    </div>
    """.format(datetime.now().strftime("%d-%b")), unsafe_allow_html=True)

st.markdown("---")

# ========== SCAN EXECUTION ==========
if scan_clicked:
    if not selected_files:
        st.error("⚠️ Please select at least one file to scan!")
    else:
        # Progress
        progress = st.progress(0)
        status = st.empty()
        
        all_alerts = {}
        total = len(selected_files)
        
        for idx, csv_file in enumerate(selected_files):
            file_name = os.path.basename(csv_file).replace('.csv', '').upper()
            status.info(f"🔄 Scanning: {file_name} ({idx+1}/{total})")
            
            try:
                # Load tickers
                tickers_df = pd.read_csv(csv_file, header=None)
                tickers = tickers_df.iloc[:, 0].astype(str).str.strip().tolist()
                
                file_alerts = {}
                
                for ticker in tickers:
                    cache_path = os.path.join(CACHE_DIR, f"{ticker}_{PERIOD}_1d.csv")
                    
                    if not os.path.exists(cache_path):
                        continue
                    
                    df = get_data(ticker, "1d")
                    if df.empty:
                        continue
                    
                    df = detect_liquidity_grab(df)
                    alerts = print_alerts(ticker, df, "1d", filter_yesterday=True)
                    
                    if alerts:
                        file_alerts[ticker] = alerts
                
                if file_alerts:
                    all_alerts[file_name] = file_alerts
                    
            except Exception as e:
                st.warning(f"Error in {file_name}: {str(e)[:40]}")
            
            progress.progress((idx + 1) / total)
        
        progress.empty()
        status.empty()
        
        # ========== RESULTS ==========
        st.markdown("## 📋 Scan Results")
        
        if not all_alerts:
            st.info("ℹ️ No signals found in selected files.")
        else:
            # Summary
            total_signals = sum(sum(len(a) for a in f.values()) for f in all_alerts.values())
            total_stocks = sum(len(f) for f in all_alerts.values())
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📊 Total Signals", total_signals)
            col2.metric("📈 Stocks with Signals", total_stocks)
            col3.metric("📁 Files with Signals", len(all_alerts))
            
            st.markdown("---")
            
            # Results by File
            for file_name in sorted(all_alerts.keys()):
                file_data = all_alerts[file_name]
                signal_count = sum(len(a) for a in file_data.values())
                
                with st.expander(f"📁 {file_name} — {signal_count} signals", expanded=True):
                    # Table
                    rows = []
                    for ticker, alerts_list in sorted(file_data.items()):
                        for alert in alerts_list:
                            rows.append({
                                "Stock": ticker,
                                "Signal": alert.strip()
                            })
                    
                    if rows:
                        df_display = pd.DataFrame(rows)
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Export
            st.markdown("---")
            st.markdown("### 💾 Export")
            
            col1, col2, col3 = st.columns(3)
            
            # CSV Export
            export_rows = []
            for fn, fd in all_alerts.items():
                for t, al in fd.items():
                    for a in al:
                        export_rows.append({"File": fn, "Stock": t, "Signal": a})
            
            df_export = pd.DataFrame(export_rows)
            
            with col1:
                csv_data = df_export.to_csv(index=False)
                st.download_button("📥 CSV", csv_data, "signals.csv", "text/csv")
            
            with col2:
                import json
                json_data = json.dumps(all_alerts, indent=2)
                st.download_button("📥 JSON", json_data, "signals.json", "application/json")
            
            with col3:
                txt = "\n".join([f"{r['File']} | {r['Stock']} | {r['Signal']}" for r in export_rows])
                st.download_button("📥 TXT", txt, "signals.txt", "text/plain")

# ========== FOOTER ==========
st.markdown("---")
with st.expander("ℹ️ Help & Info"):
    st.markdown("""
    **Liquidity Grab Pattern:**
    - Swing low is detected
    - Price wick goes below swing level  
    - Candle closes above swing level (reversal signal)
    
    **Usage:**
    1. Select INDEX/SECTOR/CUSTOM
    2. Choose files to scan
    3. Click Start Scan
    4. Export results if needed
    
    **Cache:**
    - Run `python build_all_caches.py` for fresh data
    - Cache auto-cleans old dates
    """)

st.markdown("""
<div style="text-align: center; color: #6e7681; padding: 20px; font-size: 0.85em;">
    Liquidity Scanner v2.0 • Built with Streamlit
</div>
""", unsafe_allow_html=True)
