import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook

# === CONFIG ===
source_file = 'source.xlsx'  # Your input file
sheet_name = 'Sheet1'        # Change if needed
date_column = 'Date'         # Must match column in your spreadsheet
output_dir = r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club"

# === STEP 1: Load source data ===
df = pd.read_excel(source_file, sheet_name=sheet_name, engine='openpyxl')

# === STEP 2: Clean and rename columns ===
df = df[[
    'Description',
    'Payment Amt',
    'Payment Type',
    'Member No.',
    'Receipt No.',
    'Notes',
    date_column
]].rename(columns={
    'Payment Amt': 'Payment Amount'
})

# === STEP 3: Get today's date ===
today = datetime.today()
day_str = f"{today.day}{'st' if today.day == 1 else 'nd' if today.day == 2 else 'rd' if today.day == 3 else 'th'}"
month_str = today.strftime("%B")  # e.g., "May"

# === STEP 4: Filter to only today’s payments ===
df_today = df[pd.to_datetime(df[date_column]).dt.date == today.date()]

if df_today.empty:
    print("No payments for today.")
    exit()

# === STEP 5: Create workbook path ===
excel_path = os.path.join(output_dir, f"{month_str}.xlsx")

# === STEP 6: Write today's data to correct worksheet ===
if os.path.exists(excel_path):
    # Load existing workbook
    with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df_today.drop(columns=[date_column]).to_excel(writer, sheet_name=day_str, index=False)
else:
    # Create new workbook
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_today.drop(columns=[date_column]).to_excel(writer, sheet_name=day_str, index=False)

print(f"Saved {len(df_today)} payment(s) to {excel_path}, sheet: {day_str}")
