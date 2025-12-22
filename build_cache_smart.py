#!/usr/bin/env python3
"""
Smart Cache Builder with Auto-Cleanup
- Downloads fresh data daily
- Automatically deletes old cache (keeps only today's)
- Date-based cache management
"""
import yfinance as yf
import pandas as pd
import os
import shutil
import time
import glob
from pathlib import Path
from datetime import datetime, timedelta

# ============ CONFIGURATION ============
CACHE_DIR = 'data_cache'
BACKUP_DIR = 'data_cache_backup'
TEMP_DIR = 'data_cache_temp'

# Today's date for tracking
TODAY = datetime.now().strftime("%Y%m%d")

# All source files
ALL_FILES = {
    # INDEX FILES
    'INDEX CSV/nifty50.csv': 'NIFTY50',
    'INDEX CSV/nifty500.csv': 'NIFTY500',
    'INDEX CSV/microcap250.csv': 'MICROCAP250',
    'INDEX CSV/midcap100.csv': 'MIDCAP100',
    'INDEX CSV/midcapselect.csv': 'MIDCAPSELECT',
    'INDEX CSV/midsmallcap400.csv': 'MIDSMALLCAP400',
    'INDEX CSV/next50.csv': 'NEXT50',
    'INDEX CSV/smallcap100.csv': 'SMALLCAP100',
    'INDEX CSV/smallcap250.csv': 'SMALLCAP250',
    'INDEX CSV/smallcap50.csv': 'SMALLCAP50',
    
    # SECTOR FILES
    'SECTORS CSV/sector_auto.csv': 'AUTO',
    'SECTORS CSV/sector_chemicals.csv': 'CHEMICALS',
    'SECTORS CSV/sector_commodities.csv': 'COMMODITIES',
    'SECTORS CSV/sector_consumerdurables.csv': 'CONSUMERDURABLES',
    'SECTORS CSV/sector_consumption.csv': 'CONSUMPTION',
    'SECTORS CSV/sector_defence.csv': 'DEFENCE',
    'SECTORS CSV/sector_energy.csv': 'ENERGY',
    'SECTORS CSV/sector_ev_newage.csv': 'EV_NEWAGE',
    'SECTORS CSV/sector_fmcg.csv': 'FMCG',
    'SECTORS CSV/sector_healthcare.csv': 'HEALTHCARE',
    'SECTORS CSV/sector_infra.csv': 'INFRA',
    'SECTORS CSV/sector_ipo.csv': 'IPO',
    'SECTORS CSV/sector_it.csv': 'IT',
    'SECTORS CSV/sector_media.csv': 'MEDIA',
    'SECTORS CSV/sector_metal.csv': 'METAL',
    'SECTORS CSV/sector_oilgas.csv': 'OILGAS',
    'SECTORS CSV/sector_pharma.csv': 'PHARMA',
    'SECTORS CSV/sector_realty.csv': 'REALTY',
    'SECTORS CSV/sector_service.csv': 'SERVICE',
}

def print_header():
    print("\n" + "="*60)
    print("   📊 SMART CACHE BUILDER WITH AUTO-CLEANUP")
    print("="*60)
    print(f"   📅 Date: {datetime.now().strftime('%d-%b-%Y %H:%M')}")
    print(f"   📁 Cache Directory: {CACHE_DIR}")
    print("="*60 + "\n")

def cleanup_old_caches():
    """
    Delete old dated cache directories
    Keep only: data_cache (main) and data_cache_backup
    """
    print("🧹 CLEANING OLD CACHES...")
    
    # Find all data_cache_* directories
    cache_pattern = "data_cache_*"
    old_caches = glob.glob(cache_pattern)
    
    # Keep backup, remove others
    deleted = 0
    for cache_dir in old_caches:
        if cache_dir == BACKUP_DIR:
            continue  # Keep backup
        if cache_dir == TEMP_DIR:
            # Remove temp from failed builds
            try:
                shutil.rmtree(cache_dir)
                print(f"   ❌ Deleted temp: {cache_dir}")
                deleted += 1
            except:
                pass
        elif cache_dir.startswith("data_cache_2"):  # Date-based like data_cache_20241220
            try:
                shutil.rmtree(cache_dir)
                print(f"   ❌ Deleted old: {cache_dir}")
                deleted += 1
            except Exception as e:
                print(f"   ⚠️ Could not delete {cache_dir}: {e}")
    
    if deleted == 0:
        print("   ✅ No old caches to clean")
    else:
        print(f"   ✅ Cleaned {deleted} old cache(s)")
    
    print()

def get_all_tickers():
    """Collect unique tickers from all source files"""
    all_tickers = set()
    
    for csv_file, label in ALL_FILES.items():
        if not os.path.exists(csv_file):
            continue
        try:
            tickers = pd.read_csv(csv_file, header=None)[0].str.strip().str.replace('"', '').tolist()
            tickers = [t for t in tickers if t and isinstance(t, str)]
            all_tickers.update(tickers)
        except Exception as e:
            print(f"   ⚠️ Error reading {csv_file}: {e}")
    
    return sorted(list(all_tickers))

def download_ticker(ticker, cache_dir, retries=3):
    """Download data for a single ticker with retries"""
    for attempt in range(retries):
        try:
            df = yf.download(
                ticker,
                period='6mo',
                interval='1d',
                progress=False,
            )
            
            if df is None or df.empty:
                return False, "No data"
            
            # Handle multi-index columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Select columns
            df = df[["Open", "High", "Low", "Close"]].copy()
            df.index.name = 'Date'
            
            # Save to cache
            cache_path = f'{cache_dir}/{ticker}_6mo_1d.csv'
            df.to_csv(cache_path)
            
            return True, len(df)
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
            else:
                return False, str(e)[:30]
    
    return False, "Max retries"

def build_cache():
    """Build fresh cache for all tickers"""
    
    # 1. Cleanup old caches first
    cleanup_old_caches()
    
    # 2. Remove temp if exists
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # 3. Get all unique tickers
    print("📋 COLLECTING TICKERS...")
    all_tickers = get_all_tickers()
    print(f"   Found {len(all_tickers)} unique tickers\n")
    
    # 4. Download data
    print("⬇️ DOWNLOADING DATA...")
    print("-"*60)
    
    success = 0
    failed = 0
    
    for idx, ticker in enumerate(all_tickers, 1):
        print(f"   [{idx:4d}/{len(all_tickers)}] {ticker:<20}", end="", flush=True)
        
        ok, result = download_ticker(ticker, TEMP_DIR)
        
        if ok:
            print(f"✅ ({result} candles)")
            success += 1
        else:
            print(f"❌ ({result})")
            failed += 1
        
        # Rate limiting
        time.sleep(0.5)
    
    print("-"*60)
    print(f"\n   ✅ Success: {success}")
    print(f"   ❌ Failed: {failed}")
    
    # 5. Finalize cache
    print("\n📦 FINALIZING CACHE...")
    
    try:
        # Backup old cache
        if os.path.exists(CACHE_DIR):
            if os.path.exists(BACKUP_DIR):
                shutil.rmtree(BACKUP_DIR)
            shutil.move(CACHE_DIR, BACKUP_DIR)
            print(f"   📁 Old cache backed up to {BACKUP_DIR}")
        
        # Move new cache
        shutil.move(TEMP_DIR, CACHE_DIR)
        print(f"   ✅ New cache ready at {CACHE_DIR}")
        
    except Exception as e:
        print(f"   ❌ Error finalizing: {e}")
        print(f"   ℹ️ Temp cache still at {TEMP_DIR}")
    
    # Summary
    cache_count = len(os.listdir(CACHE_DIR)) if os.path.exists(CACHE_DIR) else 0
    
    print("\n" + "="*60)
    print("   ✅ CACHE BUILD COMPLETE!")
    print("="*60)
    print(f"   📊 Total Tickers: {len(all_tickers)}")
    print(f"   ✅ Downloaded: {success}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📁 Cache Files: {cache_count}")
    print(f"   📅 Date: {datetime.now().strftime('%d-%b-%Y %H:%M')}")
    print("="*60 + "\n")

def quick_update():
    """
    Quick update - only download tickers not in cache
    Useful for adding new stocks without full rebuild
    """
    print("\n🔄 QUICK UPDATE MODE")
    print("-"*40)
    
    if not os.path.exists(CACHE_DIR):
        print("   ❌ No cache found! Running full build...")
        build_cache()
        return
    
    # Get existing cached tickers
    cached = set(f.replace('_6mo_1d.csv', '') for f in os.listdir(CACHE_DIR) if f.endswith('.csv'))
    
    # Get all required tickers
    all_tickers = set(get_all_tickers())
    
    # Find missing
    missing = all_tickers - cached
    
    if not missing:
        print("   ✅ Cache is up to date!")
        return
    
    print(f"   📋 Missing tickers: {len(missing)}")
    
    success = 0
    for idx, ticker in enumerate(sorted(missing), 1):
        print(f"   [{idx}/{len(missing)}] {ticker:<20}", end="", flush=True)
        ok, result = download_ticker(ticker, CACHE_DIR)
        if ok:
            print(f"✅")
            success += 1
        else:
            print(f"❌")
        time.sleep(0.5)
    
    print(f"\n   ✅ Added {success}/{len(missing)} tickers")

if __name__ == "__main__":
    import sys
    
    print_header()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_update()
    else:
        build_cache()
