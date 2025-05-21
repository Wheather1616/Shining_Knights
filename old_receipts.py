import os
import re
from datetime import datetime
import pandas as pd
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from openpyxl import load_workbook

# CONFIG - change these paths
INPUT_FOLDER = r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\OldWordFiles"
OUTPUT_FOLDER = r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts"

EXPECTED_COLUMNS = ['Description', 'Payment amount', 'Payment Type', 'Member No.', 'Receipt No.', 'Notes']

def day_suffix(day: int) -> str:
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

def extract_date(filename: str):
    # Match date at end of filename before extension: D or DD.MM.YYYY
    m = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})(?=\.docx$)', filename, re.IGNORECASE)
    if not m:
        return None
    try:
        # normalize single-digit day/month to two digits
        parts = m.group(1).split('.')
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        return datetime(year, month, day).date()
    except ValueError:
        return None

def read_docx_table_to_df(docx_path):
    # Attempt to open the .docx file
    try:
        doc = Document(docx_path)
    except PackageNotFoundError:
        print(f"⚠️ Cannot open '{docx_path}': not found or invalid .docx")
        return None

    if not doc.tables:
        print(f"⚠️ No tables found in '{docx_path}'")
        return None

    table = doc.tables[0]
    headers = [cell.text.strip() for cell in table.rows[0].cells]

    # Map expected columns to actual columns by case-insensitive match
    col_indices = {}
    for expected_col in EXPECTED_COLUMNS:
        for i, header in enumerate(headers):
            if header.lower() == expected_col.lower():
                col_indices[expected_col] = i
                break

    missing = set(EXPECTED_COLUMNS) - set(col_indices.keys())
    if missing:
        print(f"⚠️ Missing columns {missing} in '{docx_path}'")
        return None

    # Extract data rows
    data = []
    for row in table.rows[1:]:
        row_data = [row.cells[col_indices[col]].text.strip() for col in EXPECTED_COLUMNS]
        data.append(row_data)

    df = pd.DataFrame(data, columns=EXPECTED_COLUMNS)

    # Clean 'Payment amount' column
    df['Payment amount'] = (
        df['Payment amount']
        .str.replace('[$,]', '', regex=True)
        .str.strip()
    )

    # Convert to numeric, drop invalid
    df['Payment amount'] = pd.to_numeric(df['Payment amount'], errors='coerce')
    bad_rows = df[df['Payment amount'].isna()]
    if not bad_rows.empty:
        print(f"⚠️ {len(bad_rows)} row(s) with invalid 'Payment amount' in '{docx_path}' skipped.")
    df = df.dropna(subset=['Payment amount'])

    return df

def save_to_monthly_workbook(df, date, output_folder):
    month_str = date.strftime("%B")
    day_num = date.day
    suffix = day_suffix(day_num)
    day_sheet = f"{day_num}{suffix}"

    os.makedirs(output_folder, exist_ok=True)
    excel_path = os.path.join(output_folder, f"{month_str}.xlsx")

    if os.path.exists(excel_path):
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a') as writer:
            df.to_excel(writer, sheet_name=day_sheet, index=False)
    else:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=day_sheet, index=False)

    print(f"✅ Saved {len(df)} rows to {excel_path} sheet '{day_sheet}'")

def main():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.docx')]
    if not files:
        print(f"❌ No .docx files found in {INPUT_FOLDER}")
        return

    for file in files:
        path = os.path.join(INPUT_FOLDER, file)
        date = extract_date(file)
        if not date:
            print(f"⚠️ Skipping '{file}': could not extract valid date.")
            continue

        df = read_docx_table_to_df(path)
        if df is None or df.empty:
            print(f"⚠️ Skipping '{file}': no valid data found.")
            continue

        save_to_monthly_workbook(df, date, OUTPUT_FOLDER)

if __name__ == "__main__":
    main()


