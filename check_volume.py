import pandas as pd
import os

# Check which files have Volume data
cache_dir = 'data_cache_backup'
files_with_vol = []

print('Checking all files for Volume column...')
print('='*50)

for f in os.listdir(cache_dir):
    if f.endswith('.csv'):
        try:
            df = pd.read_csv(os.path.join(cache_dir, f), nrows=1)
            if 'Volume' in df.columns:
                files_with_vol.append(f.replace('_6mo_1d.csv', ''))
        except:
            pass

print(f'Total files with Volume: {len(files_with_vol)}')
print('='*50)
print('Stocks with Volume data:')
for s in files_with_vol[:20]:
    print(f'  - {s}')
if len(files_with_vol) > 20:
    print(f'  ... and {len(files_with_vol)-20} more')
