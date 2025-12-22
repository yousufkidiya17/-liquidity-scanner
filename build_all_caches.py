#!/usr/bin/env python3
"""
Complete Cache Builder for ALL INDEX and SECTOR files
Builds cache for all stocks from both folders
"""
import yfinance as yf
import pandas as pd
import os
import shutil
import time
from pathlib import Path

# Use temp directory for building, only replace on success
temp_cache_dir = 'data_cache_temp'
final_cache_dir = 'data_cache'

# Remove temp from any previous failed build
if os.path.exists(temp_cache_dir):
    print("Cleaning up old temp cache...")
    shutil.rmtree(temp_cache_dir)

os.makedirs(temp_cache_dir, exist_ok=True)
cache_dir = temp_cache_dir  # Use temp during build

# All files to process
all_files = {
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

total_tickers = 0
successful_downloads = 0
failed_downloads = 0

print("\n" + "="*70)
print("COMPREHENSIVE CACHE BUILDER - ALL FILES")
print("="*70 + "\n")

for csv_file, label in all_files.items():
    if not os.path.exists(csv_file):
        print(f"⚠ SKIP: {label:<20} (File not found)")
        continue
    
    print(f"\n{'='*70}")
    print(f"PROCESSING: {label:<20} ({csv_file})")
    print(f"{'='*70}")
    
    try:
        # Read tickers from CSV
        tickers = pd.read_csv(csv_file, header=None)[0].str.strip().str.replace('"', '').tolist()
        tickers = [t for t in tickers if t]
        
        print(f"   Found: {len(tickers)} tickers")
        total_tickers += len(tickers)
        
        # Download for each ticker
        for idx, ticker in enumerate(tickers, 1):
            try:
                print(f"   [{idx}/{len(tickers)}] {ticker:<20}", end=" ", flush=True)
                
                # Try to download with retries
                for attempt in range(3):
                    try:
                        df = yf.download(
                            ticker,
                            period='6mo',
                            interval='1d',
                            progress=False,
                        )
                        
                        if df is None or df.empty:
                            print("(No data)", flush=True)
                            break
                        
                        # Handle multi-index columns
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        
                        # Select columns
                        df = df[["Open", "High", "Low", "Close"]].copy()
                        
                        # Set index name
                        df.index.name = 'Date'
                        
                        # Save to cache (temp directory)
                        cache_path = f'{cache_dir}/{ticker}_6mo_1d.csv'
                        df.to_csv(cache_path)
                        
                        print(f"✓ ({len(df)} candles)", flush=True)
                        successful_downloads += 1
                        break
                        
                    except Exception as e:
                        if attempt < 2:
                            wait_time = 3 * (attempt + 1)
                            print(f"(retry after {wait_time}s)", end="", flush=True)
                            time.sleep(wait_time)
                        else:
                            print(f"✗ Failed", flush=True)
                            failed_downloads += 1
                            break
                            
            except Exception as e:
                print(f"✗ Error: {str(e)[:30]}", flush=True)
                failed_downloads += 1
                
            time.sleep(1)  # Rate limit protection
        
        print(f"   ✓ {label} complete!")
        
    except Exception as e:
        print(f"   ✗ ERROR reading {csv_file}: {str(e)[:50]}")

# Replace old cache only if build was successful
try:
    if os.path.exists(final_cache_dir):
        print("\nBacking up old cache...")
        backup_dir = final_cache_dir + '_backup'
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.move(final_cache_dir, backup_dir)
    
    print("Moving new cache to final location...")
    shutil.move(temp_cache_dir, final_cache_dir)
    print("✓ Cache ready!")
except Exception as e:
    print(f"✗ Error finalizing cache: {e}")
    print(f"  (Temp cache still in {temp_cache_dir} if you want to inspect)")

print("\n" + "="*70)
print("CACHE BUILD COMPLETE!")
print("="*70)
print(f"\n📊 SUMMARY:")
print(f"   Total Tickers Processed: {total_tickers}")
print(f"   ✓ Successful Downloads: {successful_downloads}")
print(f"   ✗ Failed Downloads: {failed_downloads}")
cache_count = len(os.listdir(final_cache_dir)) if os.path.exists(final_cache_dir) else 0
print(f"   📁 Cache Files Created: {cache_count}")
print("\n" + "="*70 + "\n")
