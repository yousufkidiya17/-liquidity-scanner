#!/usr/bin/env python3
"""
Liquidity Grab Scanner Dashboard
Interactive Streamlit Dashboard to scan multiple indices/sectors
"""
import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import scanner functions
from smc_alerts import (
    load_tickers, get_data, detect_liquidity_grab, 
    print_alerts, setup_cache, USE_CACHE, CACHE_DIR, PERIOD
)

st.set_page_config(page_title="Liquidity Grab Scanner", layout="wide", initial_sidebar_state="expanded")

# Custom CSS - TradingView Style with Neon Gradients
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
    
    * {
        margin: 0;
        padding: 0;
    }
    
    /* Space Background */
    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #0a1a2e 100%);
        background-attachment: fixed;
    }
    
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(2px 2px at 20px 30px, #00d4ff, transparent),
            radial-gradient(2px 2px at 40px 70px, #7c3aed, transparent),
            radial-gradient(1px 1px at 90px 40px, #ec4899, transparent),
            radial-gradient(2px 2px at 160px 120px, #00d4ff, transparent),
            radial-gradient(1px 1px at 230px 80px, #ffffff, transparent),
            radial-gradient(2px 2px at 300px 150px, #7c3aed, transparent),
            radial-gradient(1px 1px at 380px 200px, #ec4899, transparent),
            radial-gradient(2px 2px at 450px 50px, #00d4ff, transparent),
            radial-gradient(1px 1px at 520px 180px, #ffffff, transparent),
            radial-gradient(2px 2px at 600px 100px, #7c3aed, transparent),
            radial-gradient(1px 1px at 680px 250px, #ec4899, transparent),
            radial-gradient(2px 2px at 750px 30px, #00d4ff, transparent),
            radial-gradient(1px 1px at 820px 160px, #ffffff, transparent),
            radial-gradient(2px 2px at 900px 90px, #7c3aed, transparent),
            radial-gradient(1px 1px at 100px 300px, #00d4ff, transparent),
            radial-gradient(2px 2px at 200px 350px, #ec4899, transparent),
            radial-gradient(1px 1px at 350px 400px, #ffffff, transparent),
            radial-gradient(2px 2px at 500px 320px, #7c3aed, transparent),
            radial-gradient(1px 1px at 650px 380px, #00d4ff, transparent),
            radial-gradient(2px 2px at 800px 450px, #ec4899, transparent);
        background-repeat: repeat;
        background-size: 1000px 500px;
        animation: moveStars 100s linear infinite;
        pointer-events: none;
        z-index: 0;
        opacity: 0.8;
    }
    
    @keyframes moveStars {
        from { background-position: 0 0; }
        to { background-position: 1000px 500px; }
    }
    
    /* Shooting Star */
    .stApp::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            linear-gradient(135deg, transparent 60%, rgba(0, 212, 255, 0.8) 60.5%, transparent 61%);
        background-size: 200% 200%;
        animation: shootingStar 8s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
        opacity: 0;
    }
    
    @keyframes shootingStar {
        0%, 90%, 100% { opacity: 0; background-position: 200% 0; }
        95% { opacity: 1; background-position: -100% 200%; }
    }
    
    body {
        color: #e0e0e0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Main container */
    .main {
        background: transparent !important;
        position: relative;
        z-index: 1;
    }
    
    .main .block-container {
        background: rgba(10, 10, 30, 0.7);
        backdrop-filter: blur(5px);
        border-radius: 20px;
        padding: 30px !important;
        border: 1px solid rgba(0, 212, 255, 0.2);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 52, 96, 0.95) 0%, rgba(10, 10, 30, 0.95) 100%) !important;
        border-right: 2px solid #00d4ff;
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
    }
    
    /* Header Container - Space Theme */
    .header-container {
        position: relative;
        width: 100%;
        margin-bottom: 30px;
        overflow: visible;
    }
    
    /* Floating Particles */
    .header-container::before {
        content: '✨';
        position: absolute;
        font-size: 20px;
        top: 10px;
        left: 5%;
        animation: float 6s ease-in-out infinite;
        z-index: 0;
    }
    
    .header-container::after {
        content: '🌟';
        position: absolute;
        font-size: 16px;
        top: 20px;
        right: 10%;
        animation: float 4s ease-in-out infinite 1s;
        z-index: 0;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.7; }
        50% { transform: translateY(-20px) rotate(180deg); opacity: 1; }
    }
    
    /* Header - Animated Neon */
    .header {
        background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 50%, #ec4899 100%);
        padding: 40px;
        border-radius: 20px;
        color: white !important;
        position: relative;
        z-index: 1;
        box-shadow: 0 0 50px rgba(0, 212, 255, 0.6), 
                    0 0 100px rgba(124, 58, 237, 0.4),
                    0 0 150px rgba(236, 72, 153, 0.2);
        border: 2px solid rgba(255, 255, 255, 0.3);
        animation: headerPulse 4s ease-in-out infinite;
        overflow: hidden;
    }
    
    /* Animated border */
    .header::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(45deg, #00d4ff, #7c3aed, #ec4899, #00d4ff);
        background-size: 400% 400%;
        border-radius: 22px;
        z-index: -1;
        animation: borderGlow 3s ease infinite;
    }
    
    @keyframes borderGlow {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .header h1 {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 2.5em !important;
        font-weight: 900 !important;
        color: white !important;
        background: none !important;
        -webkit-background-clip: unset !important;
        -webkit-text-fill-color: white !important;
        background-clip: unset !important;
        text-shadow: 0 0 20px rgba(255,255,255,0.5),
                     0 0 40px rgba(0, 212, 255, 0.5);
        margin-bottom: 10px;
        letter-spacing: 5px;
        text-transform: uppercase;
    }
    
    .header p {
        font-size: 1.2em;
        color: rgba(255,255,255,0.95) !important;
        letter-spacing: 3px;
        font-weight: 500;
        text-shadow: 0 0 10px rgba(0,0,0,0.5);
    }
    
    @keyframes headerPulse {
        0%, 100% {
            box-shadow: 0 0 50px rgba(0, 212, 255, 0.6), 
                        0 0 100px rgba(124, 58, 237, 0.4);
            transform: scale(1);
        }
        50% {
            box-shadow: 0 0 70px rgba(0, 212, 255, 0.8), 
                        0 0 140px rgba(124, 58, 237, 0.6),
                        0 0 50px rgba(236, 72, 153, 0.4);
            transform: scale(1.01);
        }
    }
    
    @keyframes headerPulse {
        0%, 100% {
            box-shadow: 0 0 40px rgba(0, 212, 255, 0.6), 
                        0 0 80px rgba(124, 58, 237, 0.4);
        }
        50% {
            box-shadow: 0 0 60px rgba(0, 212, 255, 0.8), 
                        0 0 120px rgba(124, 58, 237, 0.6),
                        0 0 30px rgba(236, 72, 153, 0.4);
        }
    }
    
    @keyframes slideInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Signal Cards */
    .signal-card {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%);
        padding: 15px;
        border-left: 4px solid #00d4ff;
        border-radius: 8px;
        margin: 12px 0;
        border: 1px solid rgba(0, 212, 255, 0.3);
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .signal-card:hover {
        transform: translateX(5px);
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.4),
                    0 0 40px rgba(124, 58, 237, 0.2);
        border-color: rgba(0, 212, 255, 0.6);
    }
    
    .signal-positive {
        border-left-color: #00ff00;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
    }
    
    .signal-positive:hover {
        box-shadow: 0 0 25px rgba(0, 255, 0, 0.4),
                    0 0 40px rgba(124, 58, 237, 0.2);
    }
    
    .signal-negative {
        border-left-color: #ff1744;
        box-shadow: 0 0 15px rgba(255, 23, 68, 0.2);
    }
    
    .signal-negative:hover {
        box-shadow: 0 0 25px rgba(255, 23, 68, 0.4),
                    0 0 40px rgba(124, 58, 237, 0.2);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 1em !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.5) !important;
        transition: all 0.3s ease !important;
        letter-spacing: 1px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.8), 
                    0 0 50px rgba(124, 58, 237, 0.5) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Expandable sections */
    [data-testid="stExpander"] {
        background: linear-gradient(135deg, rgba(15, 52, 96, 0.8) 0%, rgba(26, 26, 46, 0.8) 100%) !important;
        border: 1px solid rgba(0, 212, 255, 0.3) !important;
        border-radius: 10px !important;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.1) !important;
    }
    
    /* Dataframe styling */
    .dataframe {
        background: linear-gradient(135deg, rgba(0, 0, 0, 0.5) 0%, rgba(30, 30, 60, 0.5) 100%) !important;
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        border-radius: 8px !important;
    }
    
    /* Metrics */
    .metric {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(124, 58, 237, 0.15) 100%) !important;
        border: 1px solid rgba(0, 212, 255, 0.3) !important;
        border-radius: 10px !important;
        padding: 20px !important;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.15) !important;
    }
    
    /* Divider */
    hr {
        border: 0 !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.5), transparent) !important;
        margin: 20px 0 !important;
    }
    
    /* Text styling - only for non-header h2/h3 */
    .main h2, .main h3 {
        background: linear-gradient(135deg, #00d4ff, #7c3aed, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
    }
    
    /* Radio buttons */
    [role="radio"] {
        accent-color: #00d4ff !important;
    }
    
    /* Checkbox */
    [type="checkbox"] {
        accent-color: #00d4ff !important;
    }
    
    /* Animations */
    @keyframes neonGlow {
        0%, 100% {
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.5),
                        0 0 60px rgba(124, 58, 237, 0.3);
        }
        50% {
            box-shadow: 0 0 40px rgba(0, 212, 255, 0.7),
                        0 0 80px rgba(124, 58, 237, 0.5);
        }
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Apply animations */
    .signal-card {
        animation: slideIn 0.5s ease-out;
    }
    
    /* Select box */
    select {
        background: linear-gradient(135deg, #0f3460 0%, #1a1a2e 100%) !important;
        color: #00d4ff !important;
        border: 1px solid #00d4ff !important;
        border-radius: 5px !important;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: rgba(0, 255, 0, 0.1) !important;
        color: #00ff00 !important;
        border: 1px solid rgba(0, 255, 0, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2) !important;
    }
    
    .stError {
        background-color: rgba(255, 23, 68, 0.1) !important;
        color: #ff1744 !important;
        border: 1px solid rgba(255, 23, 68, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(255, 23, 68, 0.2) !important;
    }
    
    .stInfo {
        background-color: rgba(0, 212, 255, 0.1) !important;
        color: #00d4ff !important;
        border: 1px solid rgba(0, 212, 255, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.2) !important;
    }
    
    .stWarning {
        background-color: rgba(255, 193, 7, 0.1) !important;
        color: #ffc107 !important;
        border: 1px solid rgba(255, 193, 7, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(255, 193, 7, 0.2) !important;
    }
</style>

@keyframes neonGlow {
    0%, 100% { box-shadow: 0 0 30px rgba(0, 212, 255, 0.5), 0 0 60px rgba(124, 58, 237, 0.3); }
    50% { box-shadow: 0 0 40px rgba(0, 212, 255, 0.7), 0 0 80px rgba(124, 58, 237, 0.5); }
}

""", unsafe_allow_html=True)

# Title
st.markdown("""
<div class="header-container">
    <div class="stars"></div>
    <div class="stars"></div>
    <div class="stars"></div>
    <div class="header">
        <h1>🚀 LIQUIDITY GRAB SCANNER</h1>
        <p>⚡ Multi-Index | Multi-Sector | Real-time Analysis</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Setup cache
setup_cache()

# ========== SIDEBAR ==========
st.sidebar.title("⚙️ Configuration")

scan_mode = st.sidebar.radio(
    "Choose Scan Type:",
    ("📈 INDEX (Market Indices)", "🏭 SECTOR (Industry Sectors)", "🎯 CUSTOM (Single File)")
)

selected_files = []
custom_file = None

if scan_mode == "📈 INDEX (Market Indices)":
    index_path = "INDEX CSV"
    if os.path.exists(index_path):
        all_files = sorted([f for f in os.listdir(index_path) if f.endswith('.csv')])
        selected_files_ui = st.sidebar.multiselect(
            "Select Indices:",
            all_files,
            default=all_files[:3]  # Default first 3
        )
        selected_files = [os.path.join(index_path, f) for f in selected_files_ui]

elif scan_mode == "🏭 SECTOR (Industry Sectors)":
    sector_path = "SECTORS CSV"
    if os.path.exists(sector_path):
        all_files = sorted([f for f in os.listdir(sector_path) if f.endswith('.csv')])
        selected_files_ui = st.sidebar.multiselect(
            "Select Sectors:",
            all_files,
            default=all_files[:3]  # Default first 3
        )
        selected_files = [os.path.join(sector_path, f) for f in selected_files_ui]

else:  # CUSTOM
    root_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    custom_file = st.sidebar.selectbox("Select File:", root_files if root_files else ["No CSV found"])
    if custom_file:
        selected_files = [custom_file]

st.sidebar.markdown("---")

# Scan button
if st.sidebar.button("🚀 START SCAN", key="scan_button"):
    if not selected_files:
        st.error("⚠️ Please select at least one file!")
    else:
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_alerts = {}
        total_files = len(selected_files)
        
        for idx, csv_file in enumerate(selected_files):
            file_name = os.path.basename(csv_file).replace('.csv', '')
            status_text.text(f"🔄 Scanning: {file_name} ({idx+1}/{total_files})")
            
            try:
                # Load tickers from file
                tickers_df = pd.read_csv(csv_file, header=None)
                tickers = tickers_df.iloc[:, 0].astype(str).str.strip().tolist()
                
                file_alerts = {}
                
                for ticker in tickers:
                    cache_path = os.path.join(CACHE_DIR, f"{ticker}_{PERIOD}_1d.csv")
                    
                    # Skip if cache doesn't exist
                    if not os.path.exists(cache_path):
                        continue
                    
                    # Get data
                    df = get_data(ticker, "1d")
                    if df.empty:
                        continue
                    
                    # Detect liquidity grabs
                    df = detect_liquidity_grab(df)
                    alerts = print_alerts(ticker, df, "1d", filter_yesterday=True)
                    
                    if alerts:
                        file_alerts[ticker] = alerts
                
                if file_alerts:
                    all_alerts[file_name] = file_alerts
            
            except Exception as e:
                st.warning(f"⚠️ Error scanning {file_name}: {str(e)[:50]}")
            
            # Update progress
            progress_bar.progress((idx + 1) / total_files)
        
        progress_bar.empty()
        status_text.empty()
        
        # ========== RESULTS DISPLAY ==========
        st.markdown("---")
        st.subheader("📋 Scan Results")
        
        if not all_alerts:
            st.info("ℹ️ No signals found in selected files. Cache may be incomplete.")
        else:
            # Summary Statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_files_scanned = len(all_alerts)
            total_signals = sum(sum(len(alerts) for alerts in file_alerts.values()) 
                               for file_alerts in all_alerts.values())
            total_stocks = sum(len(file_alerts) for file_alerts in all_alerts.values())
            
            col1.metric("📁 Files Scanned", total_files_scanned)
            col2.metric("🎯 Signals Found", total_signals)
            col3.metric("📊 Stocks with Signals", total_stocks)
            col4.metric("📈 Period", PERIOD)
            
            st.markdown("---")
            
            # Detailed Results by File
            for file_name in sorted(all_alerts.keys()):
                file_alerts = all_alerts[file_name]
                signal_count = sum(len(alerts) for alerts in file_alerts.values())
                
                with st.expander(f"📁 {file_name} ({signal_count} signals)", expanded=True):
                    # File statistics
                    col1, col2 = st.columns(2)
                    col1.metric("Stocks with Signals", len(file_alerts))
                    col2.metric("Total Signals", signal_count)
                    
                    # Create table data
                    table_data = []
                    for ticker, alerts_list in sorted(file_alerts.items()):
                        for alert in alerts_list:
                            # Parse alert text
                            # Format: [1D] TICKER @ DATE TIME | PRICE (Depth: X%)
                            table_data.append({
                                "Ticker": ticker,
                                "Details": alert.strip()
                            })
                    
                    if table_data:
                        df_display = pd.DataFrame(table_data)
                        # Extract date from Details for sorting
                        # Format: "@ DD-Mon-YYYY HH:MM IST"
                        def extract_date(detail_str):
                            try:
                                # Find the date part after "@"
                                import re
                                match = re.search(r'@ (\d{2}-\w{3}-\d{4})', detail_str)
                                if match:
                                    date_str = match.group(1)
                                    # Convert to datetime for proper sorting
                                    from datetime import datetime
                                    return datetime.strptime(date_str, '%d-%b-%Y')
                            except:
                                pass
                            return pd.Timestamp.min
                        
                        df_display['sort_date'] = df_display['Details'].apply(extract_date)
                        df_display = df_display.sort_values('sort_date', ascending=False).reset_index(drop=True)
                        df_display = df_display[['Ticker', 'Details']]
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Export option
            st.markdown("---")
            st.subheader("💾 Export Results")
            
            export_format = st.radio("Format:", ("CSV", "JSON", "TEXT"))
            
            if st.button("📥 Export"):
                if export_format == "CSV":
                    # Create CSV export
                    export_data = []
                    for file_name, file_alerts in all_alerts.items():
                        for ticker, alerts_list in file_alerts.items():
                            for alert in alerts_list:
                                export_data.append({
                                    "File": file_name,
                                    "Ticker": ticker,
                                    "Signal": alert
                                })
                    
                    df_export = pd.DataFrame(export_data)
                    csv = df_export.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="liquidity_signals.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    import json
                    json_str = json.dumps(all_alerts, indent=2)
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_str,
                        file_name="liquidity_signals.json",
                        mime="application/json"
                    )
                
                else:  # TEXT
                    text_output = "LIQUIDITY GRAB SIGNALS\n"
                    text_output += "="*70 + "\n\n"
                    for file_name, file_alerts in all_alerts.items():
                        text_output += f"\n{file_name}\n"
                        text_output += "-"*70 + "\n"
                        for ticker, alerts_list in file_alerts.items():
                            for alert in alerts_list:
                                text_output += alert + "\n"
                    
                    st.download_button(
                        label="📥 Download TEXT",
                        data=text_output,
                        file_name="liquidity_signals.txt",
                        mime="text/plain"
                    )

# ========== INFO SECTION ==========
st.markdown("---")
with st.expander("ℹ️ About & Help"):
    st.markdown("""
    ### Liquidity Grab Scanner Dashboard
    
    **What is Liquidity Grab Pattern?**
    - Swing low detected
    - Low breaks below swing level
    - Close breaks above swing level (in same candle)
    - Creates liquidity grab setup
    
    **How to Use:**
    1. Select scan type (INDEX/SECTOR/CUSTOM)
    2. Choose files to scan
    3. Click START SCAN
    4. View results and export if needed
    
    **Data Info:**
    - Period: 6 months historical data
    - Timeframe: 1D (Daily candles)
    - Timezone: IST (Indian Standard Time)
    - Cache: Auto-loads from cache_final.py
    
    **Performance:**
    - Cache required for data loading
    - Run `build_cache_final.py` first for fresh data
    - Signals filtered for last 7 days
    """)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Run `build_cache_final.py` first to download fresh stock data!")
