#!/usr/bin/env python3
"""
TAWAQQUL SCANNER - Liquidity Sweep + Fair Price Zone Detection
==============================================================
Mode 1: Liquidity Sweep - Detects swing low sweeps (bullish)
Mode 2: Fair Price - Detects Order Block zones after sweep

by @yousufkidiya17
"""
import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta
import base64
from PIL import Image
import hashlib
import json

# ========== USER DATABASE FILE ==========
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# Admin username - ONLY THIS USER CAN ACCESS ADMIN PANEL
ADMIN_USERNAME = "M.Yousuf"

# Default admin user
DEFAULT_USERS = {
    "M.Yousuf": {"password": hashlib.sha256("MohdYousuf.17@".encode()).hexdigest(), "name": "M.Yousuf", "created": "2024-01-01"},
}

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_USERS.copy()
    return DEFAULT_USERS.copy()

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def add_user(username, password, name=""):
    """Add new user to database"""
    users = load_users()
    if username.lower() in [u.lower() for u in users.keys()]:
        return False, "Username already exists!"
    
    users[username] = {
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "name": name if name else username,
        "created": datetime.now().strftime("%Y-%m-%d")
    }
    save_users(users)
    return True, "Account created successfully!"

def verify_user(username, password):
    """Verify user credentials"""
    users = load_users()
    if username in users:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        return users[username]["password"] == hashed
    return False

def get_user_count():
    """Get total registered users"""
    return len(load_users())

def delete_user(username):
    """Delete a user (admin only)"""
    if username == ADMIN_USERNAME:
        return False, "Cannot delete admin!"
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        return True, f"User '{username}' deleted!"
    return False, "User not found!"

def get_all_users():
    """Get all users for admin panel"""
    users = load_users()
    user_list = []
    for username, data in users.items():
        user_list.append({
            "username": username,
            "name": data.get("name", username),
            "created": data.get("created", "Unknown"),
            "is_admin": username == ADMIN_USERNAME
        })
    return user_list

def is_admin():
    """Check if current user is admin"""
    return st.session_state.get('username', '').lower() == ADMIN_USERNAME.lower()

# Load favicon
favicon_path = os.path.join(os.path.dirname(__file__), "logo.png")
if os.path.exists(favicon_path):
    favicon = Image.open(favicon_path)
else:
    favicon = "🎯"

st.set_page_config(
    page_title="TAWAQQUL Scanner", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon=favicon
)

# ========== LOGIN STYLES ==========
st.markdown("""
<style>
    .login-container {
        max-width: 400px;
        margin: 50px auto;
        padding: 40px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 20px;
        border: 1px solid rgba(0, 212, 255, 0.3);
        box-shadow: 0 8px 32px rgba(0, 212, 255, 0.2);
    }
    .login-header {
        text-align: center;
        margin-bottom: 30px;
    }
    .login-header h1 {
        color: #ffffff;
        font-size: 2em;
        margin: 10px 0;
    }
    .login-header .arabic {
        color: #ffd700;
        font-size: 1.3em;
        direction: rtl;
    }
    .login-logo {
        width: 80px;
        height: 80px;
        margin: 0 auto 20px;
        background: #000;
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: logoGlow 3s ease-in-out infinite;
    }
    @keyframes logoGlow {
        0%, 100% { box-shadow: 0 0 10px #ffd700, 0 0 20px rgba(255,215,0,0.3); }
        50% { box-shadow: 0 0 20px #ffd700, 0 0 40px rgba(255,215,0,0.5); }
    }
    @keyframes textGlow {
        0%, 100% { text-shadow: 0 0 5px #ffd700, 0 0 10px rgba(255,215,0,0.3); }
        50% { text-shadow: 0 0 15px #ffd700, 0 0 25px rgba(255,215,0,0.5), 0 0 35px rgba(255,215,0,0.3); }
    }
    .welcome-text {
        text-align: center;
        color: #00ff88;
        font-size: 1.1em;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ========== AUTHENTICATION FUNCTIONS ==========
def check_password(username, password):
    """Check if username and password match"""
    return verify_user(username, password)

def get_logo_base64():
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

# ========== LOGIN PAGE ==========
def show_login_page():
    logo_b64 = get_logo_base64()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
        """, unsafe_allow_html=True)
        
        if logo_b64:
            st.markdown(f"""
            <div style="text-align: center;">
                <div class="login-logo">
                    <img src="data:image/png;base64,{logo_b64}" style="width: 50px; filter: invert(1);">
                </div>
                <h1 style="color: #ffffff; margin: 10px 0;">🔐 TAWAQQUL SCANNER</h1>
                <p style="color: #ffd700; font-size: 1.2em; direction: rtl; animation: textGlow 3s ease-in-out infinite;">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</p>
                <p style="color: #a0c4e8;">Premium Liquidity Scanner</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabs for Login and Sign Up
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                st.markdown("### 👤 Login to Continue")
                username = st.text_input("Username", placeholder="Enter username", key="login_user")
                password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass")
                
                submit = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
                
                if submit:
                    if username and password:
                        if check_password(username, password):
                            st.session_state['authenticated'] = True
                            st.session_state['username'] = username
                            st.success(f"✅ Welcome back, {username}!")
                            # Login Success Animation - Rocket Launch Effect
                            st.markdown("""
                            <style>
                            @keyframes rocket-launch {
                                0% { transform: translateY(100px) scale(1); opacity: 0; }
                                50% { transform: translateY(-20px) scale(1.2); opacity: 1; }
                                100% { transform: translateY(-200px) scale(0.5); opacity: 0; }
                            }
                            @keyframes pulse-glow {
                                0%, 100% { box-shadow: 0 0 20px #00ff88, 0 0 40px rgba(0,255,136,0.4); }
                                50% { box-shadow: 0 0 40px #00ff88, 0 0 80px rgba(0,255,136,0.6); }
                            }
                            @keyframes text-pop {
                                0% { transform: scale(0); opacity: 0; }
                                50% { transform: scale(1.3); }
                                100% { transform: scale(1); opacity: 1; }
                            }
                            .login-success-container {
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                pointer-events: none;
                                z-index: 9999;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                            }
                            .rocket {
                                font-size: 60px;
                                animation: rocket-launch 2s ease-out forwards;
                            }
                            .welcome-box {
                                background: linear-gradient(135deg, #0d4f3c 0%, #1a7f5a 100%);
                                padding: 20px 40px;
                                border-radius: 15px;
                                animation: pulse-glow 1s ease-in-out infinite, text-pop 0.5s ease-out;
                            }
                            .welcome-box h2 {
                                color: #fff;
                                margin: 0;
                                font-size: 1.5em;
                            }
                            .stars-container {
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                pointer-events: none;
                                z-index: 9998;
                            }
                            .star {
                                position: absolute;
                                font-size: 20px;
                                animation: rocket-launch 1.5s ease-out forwards;
                            }
                            </style>
                            <div class="stars-container">
                                <div class="star" style="left: 20%; top: 60%; animation-delay: 0.1s;">✨</div>
                                <div class="star" style="left: 40%; top: 70%; animation-delay: 0.2s;">⭐</div>
                                <div class="star" style="left: 60%; top: 65%; animation-delay: 0.3s;">🌟</div>
                                <div class="star" style="left: 80%; top: 75%; animation-delay: 0.4s;">💫</div>
                                <div class="star" style="left: 30%; top: 80%; animation-delay: 0.5s;">✨</div>
                                <div class="star" style="left: 70%; top: 85%; animation-delay: 0.6s;">⭐</div>
                            </div>
                            <div class="login-success-container">
                                <div class="rocket">🚀</div>
                            </div>
                            <div style="text-align: center; margin-top: 20px;">
                                <div class="welcome-box">
                                    <h2>🎯 Let's Go Trading! 🎯</h2>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password!")
                    else:
                        st.warning("⚠️ Please enter both username and password!")
        
        with tab2:
            with st.form("signup_form"):
                st.markdown("### 📝 Create New Account")
                new_username = st.text_input("Choose Username", placeholder="Enter username", key="signup_user")
                new_name = st.text_input("Your Name (Optional)", placeholder="Enter your name", key="signup_name")
                new_password = st.text_input("Create Password", type="password", placeholder="Min 4 characters", key="signup_pass")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="signup_confirm")
                
                signup_btn = st.form_submit_button("✨ Create Account", use_container_width=True, type="primary")
                
                if signup_btn:
                    if not new_username or not new_password:
                        st.warning("⚠️ Username and Password are required!")
                    elif len(new_username) < 3:
                        st.warning("⚠️ Username must be at least 3 characters!")
                    elif len(new_password) < 4:
                        st.warning("⚠️ Password must be at least 4 characters!")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords don't match!")
                    else:
                        success, message = add_user(new_username, new_password, new_name)
                        if success:
                            st.success(f"✅ {message}")
                            st.info("👆 Now go to Login tab and login!")
                            # Celebration Animation - Confetti + Sparkles
                            st.markdown("""
                            <style>
                            @keyframes confetti-fall {
                                0% { transform: translateY(-100vh) rotate(0deg); opacity: 1; }
                                100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
                            }
                            @keyframes sparkle {
                                0%, 100% { opacity: 0; transform: scale(0); }
                                50% { opacity: 1; transform: scale(1); }
                            }
                            .confetti-container {
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                pointer-events: none;
                                z-index: 9999;
                                overflow: hidden;
                            }
                            .confetti {
                                position: absolute;
                                font-size: 25px;
                                animation: confetti-fall 4s ease-out forwards;
                            }
                            .sparkle-text {
                                text-align: center;
                                font-size: 2em;
                                animation: sparkle 0.5s ease-in-out infinite;
                            }
                            </style>
                            <div class="confetti-container">
                                <div class="confetti" style="left: 5%; animation-delay: 0s;">🎉</div>
                                <div class="confetti" style="left: 15%; animation-delay: 0.2s;">⭐</div>
                                <div class="confetti" style="left: 25%; animation-delay: 0.4s;">🎊</div>
                                <div class="confetti" style="left: 35%; animation-delay: 0.1s;">✨</div>
                                <div class="confetti" style="left: 45%; animation-delay: 0.3s;">🌟</div>
                                <div class="confetti" style="left: 55%; animation-delay: 0.5s;">🎉</div>
                                <div class="confetti" style="left: 65%; animation-delay: 0.2s;">💫</div>
                                <div class="confetti" style="left: 75%; animation-delay: 0.4s;">⭐</div>
                                <div class="confetti" style="left: 85%; animation-delay: 0.1s;">🎊</div>
                                <div class="confetti" style="left: 95%; animation-delay: 0.3s;">✨</div>
                                <div class="confetti" style="left: 10%; animation-delay: 0.6s;">🌟</div>
                                <div class="confetti" style="left: 30%; animation-delay: 0.7s;">💫</div>
                                <div class="confetti" style="left: 50%; animation-delay: 0.8s;">🎉</div>
                                <div class="confetti" style="left: 70%; animation-delay: 0.9s;">⭐</div>
                                <div class="confetti" style="left: 90%; animation-delay: 1s;">🎊</div>
                            </div>
                            <div class="sparkle-text">🎉 Welcome to TAWAQQUL! 🎉</div>
                            """, unsafe_allow_html=True)
                            st.snow()
                        else:
                            st.error(f"❌ {message}")
        
        st.markdown("""
        <div style="text-align: center; margin-top: 30px; color: #6e7681; font-size: 0.85em;">
            <p>📧 kidiyayousuf17@gmail.com</p>
            <p>🔒 Secure Login System</p>
        </div>
        """, unsafe_allow_html=True)

# ========== LOGOUT BUTTON ==========
def show_logout_button():
    with st.sidebar:
        st.markdown(f"**👤 Welcome, {st.session_state.get('username', 'User')}!**")
        if is_admin():
            st.markdown("🔑 **Admin Access**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state['authenticated'] = False
            st.session_state['username'] = None
            st.rerun()
        st.markdown("---")

# ========== ADMIN PANEL (Only for Admin) ==========
def show_admin_panel():
    """Admin panel - only visible to admin user"""
    if not is_admin():
        return
    
    with st.sidebar:
        with st.expander("🛡️ ADMIN PANEL", expanded=False):
            st.markdown("### 👥 User Management")
            
            users = get_all_users()
            st.metric("Total Users", len(users))
            
            st.markdown("---")
            st.markdown("**Registered Users:**")
            
            for user in users:
                col1, col2 = st.columns([3, 1])
                with col1:
                    badge = "👑" if user['is_admin'] else "👤"
                    st.markdown(f"{badge} **{user['username']}**")
                    st.caption(f"📅 {user['created']}")
                with col2:
                    if not user['is_admin']:
                        if st.button("🗑️", key=f"del_{user['username']}", help=f"Delete {user['username']}"):
                            success, msg = delete_user(user['username'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
            
            st.markdown("---")
            st.caption("🔒 Only admin can see this panel")

# ========== CHECK AUTHENTICATION ==========
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    show_login_page()
    st.stop()

# ========== SHOW LOGOUT IN SIDEBAR ==========
show_logout_button()

# ========== SHOW ADMIN PANEL (Only for Admin) ==========
show_admin_panel()

# ========== SETTINGS ==========
PERIOD = "6mo"
SWING_LENGTHS = [2, 3, 5]
MIN_WICK_PERCENT = 25
MIN_DEPTH_PERCENT = 0.1
OB_LOOKBACK = 3

# ========== STYLES WITH LIGHT ANIMATIONS ==========
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    
    @keyframes glow {
        0%, 100% { text-shadow: 0 0 5px #ffd700; }
        50% { text-shadow: 0 0 15px #ffd700, 0 0 25px #ffd700; }
    }
    @keyframes fadeText {
        0%, 100% { opacity: 0.8; }
        50% { opacity: 1; }
    }
    @keyframes logoPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.03); }
    }
    @keyframes borderGlow {
        0%, 100% { box-shadow: 0 0 5px #00d4ff, 0 0 10px rgba(0,212,255,0.3); }
        50% { box-shadow: 0 0 15px #00d4ff, 0 0 25px rgba(0,212,255,0.5), 0 0 35px rgba(0,212,255,0.2); }
    }
    
    /* Simple Logo Container - Main Header */
    .logo-container {
        width: 80px;
        height: 80px;
        border-radius: 12px;
        background: #000000;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 10px;
        animation: logoGlow 3s ease-in-out infinite;
    }
    @keyframes logoGlow {
        0%, 100% { box-shadow: 0 0 5px #ffd700, 0 0 10px rgba(255,215,0,0.3); }
        50% { box-shadow: 0 0 15px #ffd700, 0 0 25px rgba(255,215,0,0.5), 0 0 35px rgba(255,215,0,0.3); }
    }
    .logo-container img {
        height: 60px;
        width: 60px;
        object-fit: contain;
        filter: invert(1);
    }
    
    /* Sidebar Logo - Simple Style */
    [data-testid="stSidebar"] .stImage {
        display: flex;
        justify-content: center;
        margin-bottom: 15px;
    }
    [data-testid="stSidebar"] .stImage img {
        width: 45px !important;
        height: 45px !important;
        padding: 8px;
        background: #000000;
        border-radius: 10px;
        filter: invert(1);
        box-shadow: 0 0 10px rgba(255,215,0,0.4);
    }
    
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 25px 30px;
        border-radius: 20px;
        margin-bottom: 25px;
        border: 1px solid rgba(0, 212, 255, 0.3);
        box-shadow: 0 8px 32px rgba(0, 212, 255, 0.15), inset 0 0 60px rgba(0, 212, 255, 0.05);
    }
    .main-header h1 { 
        color: #ffffff; 
        font-size: 2.2em; 
        margin: 0; 
        font-weight: 800;
        letter-spacing: 1px;
        text-shadow: 0 2px 10px rgba(0,212,255,0.3);
    }
    .main-header .arabic { 
        font-size: 1.5em; 
        color: #ffd700; 
        font-family: 'Traditional Arabic', serif;
        direction: rtl;
        margin: 12px 0;
        animation: glow 3s ease-in-out infinite;
    }
    .main-header .tagline { 
        color: #a0c4e8; 
        margin: 8px 0 0 0; 
        font-size: 1em;
        animation: fadeText 4s ease-in-out infinite;
        letter-spacing: 0.5px;
    }
    .main-header .tagline .highlight { 
        color: #00ff88; 
        font-weight: 600;
    }
    
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #131722 0%, #1e222d 100%);
        border-right: 1px solid rgba(41, 98, 255, 0.3);
    }
    
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
    
    .fp-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        border-left: 4px solid #00ff88;
    }
    .fp-card h3 { color: #00ff88; margin: 0 0 10px 0; font-size: 1.3em; }
    .fp-card .ticker { color: #ffffff; font-size: 1.5em; font-weight: 700; }
    .fp-card .zone { color: #ffd700; font-size: 1.1em; }
    
    .at-fp {
        background: linear-gradient(135deg, #0d4f3c 0%, #1a7f5a 100%);
        border-left: 4px solid #00ff88;
    }
    
    .mode-tag {
        display: inline-block;
        padding: 8px 18px;
        border-radius: 25px;
        font-size: 0.9em;
        font-weight: 700;
        margin: 5px 5px 5px 0;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .mode-sweep { background: linear-gradient(90deg, #00d4ff, #0099cc); color: #000; }
    .mode-fp { background: linear-gradient(90deg, #00ff88, #00cc6a); color: #000; }
</style>
""", unsafe_allow_html=True)

# ========== HEADER WITH ANIMATION ==========
logo_b64 = get_logo_base64()
if logo_b64:
    st.markdown(f"""
    <div class="main-header" style="display: flex; align-items: center; gap: 30px;">
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_b64}">
        </div>
        <div>
            <h1>TAWAQQUL SCANNER</h1>
            <p class="arabic">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</p>
            <p class="tagline">Institutional Liquidity Detection • <span class="highlight">Fair Value Discovery</span></p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="main-header">
        <h1>🎯 TAWAQQUL SCANNER</h1>
        <p class="arabic">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</p>
        <p class="tagline">Institutional Liquidity Detection • <span class="highlight">Fair Value Discovery</span></p>
    </div>
    """, unsafe_allow_html=True)

# ========== DATA DOWNLOAD ==========
@st.cache_data(ttl=3600)
def download_data(ticker):
    try:
        df = yf.download(ticker, period=PERIOD, interval="1d", progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

# ========== SWING DETECTION ==========
def detect_pivot_lows_multi(df, lengths=[2, 3, 5]):
    """Detect pivot lows with multiple swing lengths"""
    pivot_lows = []
    
    for length in lengths:
        for i in range(length, len(df) - length):
            is_pivot = True
            current_low = df['Low'].iloc[i]
            
            for j in range(1, length + 1):
                if df['Low'].iloc[i - j] <= current_low or df['Low'].iloc[i + j] <= current_low:
                    is_pivot = False
                    break
            
            if is_pivot:
                already_exists = any(
                    abs(p['index'] - i) <= 2 and abs(p['price'] - current_low) / current_low < 0.01
                    for p in pivot_lows
                )
                if not already_exists:
                    pivot_lows.append({
                        'index': i,
                        'date': df.index[i],
                        'price': current_low,
                        'swing_type': length
                    })
    
    return sorted(pivot_lows, key=lambda x: x['index'])

# ========== LIQUIDITY SWEEP DETECTION ==========
def detect_liquidity_sweep(df, pivot_lows):
    """Detect bullish liquidity sweeps"""
    sweeps = []
    
    for pivot in pivot_lows:
        pivot_idx = pivot['index']
        swing_low = pivot['price']
        swing_type = pivot['swing_type']
        
        for i in range(pivot_idx + 1, min(pivot_idx + 15, len(df))):
            candle_low = df['Low'].iloc[i]
            candle_close = df['Close'].iloc[i]
            candle_open = df['Open'].iloc[i]
            candle_high = df['High'].iloc[i]
            
            if candle_low < swing_low and candle_close > swing_low:
                body = abs(candle_close - candle_open)
                total_range = candle_high - candle_low
                lower_wick = min(candle_open, candle_close) - candle_low
                
                if total_range > 0:
                    wick_percent = (lower_wick / total_range) * 100
                    depth_percent = ((swing_low - candle_low) / swing_low) * 100
                else:
                    continue
                
                if wick_percent >= MIN_WICK_PERCENT and depth_percent >= MIN_DEPTH_PERCENT:
                    close_position = (candle_close - candle_low) / total_range * 100 if total_range > 0 else 0
                    score = calculate_score(wick_percent, depth_percent, close_position, swing_type)
                    
                    sweeps.append({
                        'ticker': '',
                        'date': df.index[i],
                        'sweep_idx': i,
                        'swing_low': swing_low,
                        'sweep_low': candle_low,
                        'close': candle_close,
                        'wick_percent': wick_percent,
                        'depth_percent': depth_percent,
                        'swing_type': swing_type,
                        'score': score,
                        'grade': get_grade(score)
                    })
                break
    
    return sweeps

def calculate_score(wick_pct, depth_pct, close_pos, swing_type):
    score = 0
    score += min(wick_pct / 2, 30)
    score += min(depth_pct * 20, 30)
    score += min(close_pos / 5, 20)
    if swing_type >= 5:
        score += 20
    elif swing_type >= 3:
        score += 15
    else:
        score += 10
    return min(score, 100)

def get_grade(score):
    if score >= 70: return "A+"
    elif score >= 55: return "B"
    elif score >= 40: return "C"
    else: return "D"

def get_swing_label(swing_type):
    if swing_type >= 5: return "Major"
    elif swing_type >= 3: return "Medium"
    else: return "Minor"

# ========== FAIR PRICE (ORDER BLOCK) DETECTION ==========
def detect_fair_price_zone(df, sweep):
    """Detect Fair Price zone (Order Block) after liquidity sweep"""
    sweep_idx = sweep['sweep_idx']
    
    for i in range(sweep_idx, max(sweep_idx - OB_LOOKBACK, 0), -1):
        if df['Close'].iloc[i] < df['Open'].iloc[i]:
            return {
                'fp_idx': i,
                'fp_date': df.index[i],
                'fp_high': df['High'].iloc[i],
                'fp_low': df['Low'].iloc[i]
            }
    
    return {
        'fp_idx': sweep_idx,
        'fp_date': df.index[sweep_idx],
        'fp_high': df['High'].iloc[sweep_idx],
        'fp_low': df['Low'].iloc[sweep_idx]
    }

def is_price_at_fp(current_price, fp_high, fp_low, tolerance=1.0):
    """Check if price is at Fair Price zone"""
    zone_range = fp_high - fp_low
    extended_high = fp_high + (zone_range * tolerance / 100)
    extended_low = fp_low - (zone_range * tolerance / 100)
    return extended_low <= current_price <= extended_high

def scan_fair_price_setups(df, ticker, max_days=20):
    """Scan for Fair Price setups"""
    if len(df) < 30:
        return []
    
    pivot_lows = detect_pivot_lows_multi(df, SWING_LENGTHS)
    if not pivot_lows:
        return []
    
    sweeps = detect_liquidity_sweep(df, pivot_lows)
    if not sweeps:
        return []
    
    setups = []
    current_price = df['Close'].iloc[-1]
    current_date = df.index[-1]
    
    for sweep in sweeps:
        fp = detect_fair_price_zone(df, sweep)
        days_ago = (current_date - fp['fp_date']).days
        
        if days_ago > max_days:
            continue
        
        fp_valid = True
        for i in range(fp['fp_idx'] + 1, len(df)):
            if df['Close'].iloc[i] < fp['fp_low']:
                fp_valid = False
                break
        
        if fp_valid:
            at_fp = is_price_at_fp(current_price, fp['fp_high'], fp['fp_low'])
            distance = 0
            if current_price > fp['fp_high']:
                distance = ((current_price - fp['fp_high']) / fp['fp_high']) * 100
            elif current_price < fp['fp_low']:
                distance = ((fp['fp_low'] - current_price) / fp['fp_low']) * 100
            
            setups.append({
                'ticker': ticker,
                'sweep_date': sweep['date'],
                'sweep_score': sweep['score'],
                'fp_date': fp['fp_date'],
                'fp_high': fp['fp_high'],
                'fp_low': fp['fp_low'],
                'current_price': current_price,
                'at_fp_zone': at_fp,
                'days_ago': days_ago,
                'distance': distance
            })
    
    return setups

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("### ⚙️ Scan Settings")
    
    st.markdown("#### 🎯 Select Mode")
    scan_mode = st.radio(
        "Choose what to scan:",
        ["💧 Liquidity Sweep", "💰 Fair Price Zone"],
        horizontal=False,
        help="Liquidity Sweep = Recent sweeps | Fair Price = OB zones after sweep"
    )
    
    if scan_mode == "💧 Liquidity Sweep":
        st.info("🔍 Finds stocks where liquidity was just swept")
    else:
        st.success("🎯 Finds stocks at Fair Price zone")
    
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
    
    st.markdown("#### 📅 Select Date Range")
    start_date = st.date_input("From Date", value=datetime.now() - timedelta(days=15 if scan_mode == "💰 Fair Price Zone" else 10))
    days_filter = (datetime.now().date() - start_date).days
    
    if scan_mode == "💰 Fair Price Zone":
        show_at_fp_only = True
    
    st.markdown("---")
    scan_clicked = st.button("🚀 Start Scan", use_container_width=True, type="primary")

# ========== MAIN SCAN LOGIC ==========
if scan_clicked:
    if not selected_files:
        st.error("⚠️ Please select at least one file!")
    else:
        progress = st.progress(0)
        status = st.empty()
        
        if scan_mode == "💧 Liquidity Sweep":
            all_signals = []
            cutoff_date = datetime.now() - timedelta(days=days_filter)
            
            total = len(selected_files)
            for file_idx, file_path in enumerate(selected_files):
                try:
                    tickers_df = pd.read_csv(file_path)
                    ticker_col = tickers_df.columns[0]
                    tickers = tickers_df[ticker_col].tolist()
                    
                    for i, ticker in enumerate(tickers):
                        ticker = str(ticker).strip()
                        if not ticker.endswith('.NS'):
                            ticker = f"{ticker}.NS"
                        
                        status.text(f"Scanning {ticker}...")
                        df = download_data(ticker)
                        
                        if df.empty or len(df) < 30:
                            continue
                        
                        pivot_lows = detect_pivot_lows_multi(df, SWING_LENGTHS)
                        sweeps = detect_liquidity_sweep(df, pivot_lows)
                        
                        for sweep in sweeps:
                            sweep['ticker'] = ticker
                            if sweep['date'] >= pd.Timestamp(cutoff_date):
                                all_signals.append(sweep)
                        
                        progress.progress((file_idx + (i+1)/len(tickers)) / total)
                except Exception as e:
                    continue
            
            progress.empty()
            status.empty()
            
            st.markdown("---")
            st.markdown(f"""
            <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 20px;">
                <span class="mode-tag mode-sweep">💧 LIQUIDITY SWEEP MODE</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Sort by date first (latest), then by score
            all_signals.sort(key=lambda x: (x['date'], x['score']), reverse=True)
            
            a_signals = [s for s in all_signals if s['grade'] == 'A+']
            b_signals = [s for s in all_signals if s['grade'] == 'B']
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Signals", len(all_signals))
            with col2:
                st.metric("🏆 A+ Signals", len(a_signals))
            with col3:
                st.metric("✅ B Signals", len(b_signals))
            with col4:
                st.metric("Stocks", len(set(s['ticker'] for s in all_signals)))
            
            st.markdown("---")
            
            if all_signals:
                st.markdown("## 📊 Scan Results (BULLISH Sweeps)")
                
                if a_signals:
                    st.markdown("### 🏆 Grade A+ (Score ≥ 70) - BEST SETUPS")
                    for sig in a_signals:
                        st.markdown(f"""<div class="signal-good">
                        <strong>{sig['ticker'].replace('.NS','')}</strong> | {sig['date'].strftime('%d-%b')} | Score: {sig['score']:.0f}/100 | Swing: ₹{sig['swing_low']:.2f} ({get_swing_label(sig['swing_type'])}) | Depth: {sig['depth_percent']:.2f}% | Wick: {sig['wick_percent']:.0f}%
                        </div>""", unsafe_allow_html=True)
                
                if b_signals:
                    st.markdown("### ✅ Grade B (Score 55-69)")
                    for sig in b_signals:
                        st.markdown(f"""<div class="signal-medium">
                        <strong>{sig['ticker'].replace('.NS','')}</strong> | {sig['date'].strftime('%d-%b')} | Score: {sig['score']:.0f}/100 | Depth: {sig['depth_percent']:.2f}%
                        </div>""", unsafe_allow_html=True)
            else:
                st.info("No liquidity sweep signals found with current filters.")
        
        else:
            all_setups = []
            
            total = len(selected_files)
            for file_idx, file_path in enumerate(selected_files):
                try:
                    tickers_df = pd.read_csv(file_path)
                    ticker_col = tickers_df.columns[0]
                    tickers = tickers_df[ticker_col].tolist()
                    
                    for i, ticker in enumerate(tickers):
                        ticker = str(ticker).strip()
                        if not ticker.endswith('.NS'):
                            ticker = f"{ticker}.NS"
                        
                        status.text(f"Scanning {ticker}...")
                        df = download_data(ticker)
                        
                        if df.empty or len(df) < 30:
                            continue
                        
                        setups = scan_fair_price_setups(df, ticker, days_filter)
                        all_setups.extend(setups)
                        
                        progress.progress((file_idx + (i+1)/len(tickers)) / total)
                except Exception as e:
                    continue
            
            progress.empty()
            status.empty()
            
            if show_at_fp_only:
                all_setups = [s for s in all_setups if s['at_fp_zone']]
            
            all_setups.sort(key=lambda x: (not x['at_fp_zone'], x['days_ago']))
            
            st.markdown("---")
            st.markdown(f"""
            <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 20px;">
                <span class="mode-tag mode-fp">💰 FAIR PRICE MODE</span>
            </div>
            """, unsafe_allow_html=True)
            
            at_fp_count = len([s for s in all_setups if s['at_fp_zone']])
            near_fp_count = len([s for s in all_setups if not s['at_fp_zone'] and s['distance'] < 3])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Setups", len(all_setups))
            with col2:
                st.metric("🎯 At Fair Price", at_fp_count)
            with col3:
                st.metric("📍 Near FP (<3%)", near_fp_count)
            with col4:
                st.metric("Stocks", len(set(s['ticker'] for s in all_setups)))
            
            st.markdown("---")
            
            if all_setups:
                at_fp_setups = [s for s in all_setups if s['at_fp_zone']]
                if at_fp_setups:
                    st.markdown("## 🔥 PRICE AT FAIR PRICE ZONE - HOT SETUPS!")
                    st.caption("These stocks are currently at institutional buy zones!")
                    
                    for setup in at_fp_setups:
                        st.markdown(f"""
                        <div class="fp-card at-fp">
                            <div class="ticker">{setup['ticker'].replace('.NS', '')}</div>
                            <div class="zone">📍 Fair Price Zone: ₹{setup['fp_low']:.2f} - ₹{setup['fp_high']:.2f}</div>
                            <div style="color: #a0c4e8; margin-top: 8px;">
                                💧 Sweep: {setup['sweep_date'].strftime('%d-%b')} | Quality: {setup['sweep_score']:.0f}/100
                            </div>
                            <div style="color: #ffffff; margin-top: 5px;">
                                💰 Current Price: ₹{setup['current_price']:.2f}
                            </div>
                            <div style="color: #00ff88; margin-top: 10px; font-weight: 600;">
                                ✅ PRICE AT FAIR PRICE ZONE - WATCH FOR BOUNCE! 🎯
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                other_setups = [s for s in all_setups if not s['at_fp_zone']]
                if other_setups:
                    st.markdown("---")
                    st.markdown("## 📋 Other Fair Price Setups")
                    st.caption("Valid zones - wait for price to reach Fair Price")
                    
                    data = []
                    for s in other_setups[:20]:
                        status_txt = "⬆️ Above" if s['current_price'] > s['fp_high'] else "⬇️ Below"
                        data.append({
                            'Ticker': s['ticker'].replace('.NS', ''),
                            'Fair Price Zone': f"₹{s['fp_low']:.0f} - ₹{s['fp_high']:.0f}",
                            'Current': f"₹{s['current_price']:.0f}",
                            'Distance': f"{s['distance']:.1f}%",
                            'Status': status_txt,
                            'Date': s['fp_date'].strftime('%d-%b')
                        })
                    
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.info("No Fair Price setups found with current filters.")

# ========== HOW IT WORKS ==========
with st.expander("ℹ️ How It Works"):
    st.markdown("""
    ### 💧 Liquidity Sweep Mode
    Detects when price sweeps below a swing low and closes above it - a bullish reversal signal.
    
    ### 💰 Fair Price Mode
    After a liquidity sweep, marks the "Fair Price Zone" where institutions bought.
    
    **🎯 Best Entry:** When price is AT Fair Price zone after a valid sweep!
    """)

# ========== FOOTER ==========
st.markdown("---")
st.markdown("""<div style="text-align: center; color: #6e7681; padding: 20px; font-size: 0.85em;">
    TAWAQQUL SCANNER v2.0 • Liquidity Sweep + Fair Price Detection • by @yousufkidiya17
</div>""", unsafe_allow_html=True)
