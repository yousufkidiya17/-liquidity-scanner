#!/usr/bin/env python3
"""
Quick Sector Cache Refresh - Defence & Chemicals only
"""
import yfinance as yf
import pandas as pd
import os
import time

sectors = {
    'SECTORS CSV/sector_defence.csv': 'DEFENCE',
    'SECTORS CSV/sector_chemicals.csv': 'CHEMICALS',
}

cache_dir = 'data_cache'
os.makedirs(cache_dir, exist_ok=True)

successful = 0
failed = 0

print("\n" + "="*70)
print("QUICK REFRESH - DEFENCE & CHEMICALS SECTORS")
print("="*70 + "\n")

for csv_file, label in sectors.items():
    if not os.path.exists(csv_file):
        print(f"⚠ SKIP: {label} (File not found)")
        continue
    
    print(f"\n{'='*70}")
    print(f"REFRESHING: {label}")
    print(f"{'='*70}")
    
    try:
        tickers = pd.read_csv(csv_file, header=None)[0].str.strip().str.replace('"', '').tolist()
        tickers = [t for t in tickers if t]
        
        print(f"   Found: {len(tickers)} tickers\n")
        
        for idx, ticker in enumerate(tickers, 1):
            print(f"   [{idx}/{len(tickers)}] {ticker:<20}", end=" ", flush=True)
            
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
                    
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    df = df[["Open", "High", "Low", "Close"]].copy()
                    df.index.name = 'Date'
                    
                    cache_path = f'{cache_dir}/{ticker}_6mo_1d.csv'
                    df.to_csv(cache_path)
                    
                    print(f"✓ ({len(df)} candles)", flush=True)
                    successful += 1
                    break
                    
                except Exception as e:
                    if attempt < 2:
                        wait_time = 3 * (attempt + 1)
                        print(f"(retry {attempt+1})", end="", flush=True)
                        time.sleep(wait_time)
                    else:
                        print(f"✗", flush=True)
                        failed += 1
                        break
            
            time.sleep(0.5)
        
        print(f"\n   ✓ {label} refreshed!")
        
    except Exception as e:
        print(f"   ✗ ERROR: {str(e)[:50]}")

print("\n" + "="*70)
print("REFRESH COMPLETE!")
print("="*70)
print(f"\n📊 SUMMARY:")
print(f"   ✓ Downloaded: {successful}")
print(f"   ✗ Failed: {failed}")
print(f"   📁 Total in cache: {len(os.listdir(cache_dir))}")
print("\n   Dashboard automatically use karega updated files!")
print("="*70 + "\n")
