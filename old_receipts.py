import os
import re
from datetime import datetime
import pandas as pd
from docx import Document

def extract_date_from_filename(filename):
    match = re.search(r'(\d{2}\.\d{2}\.\d{4})', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            pass
    return None

def word_to_excel(word_path, output_dir):
    filename = os.path.basename(word_path)
    date_for_payments = extract_date_from_filename(filename)
    if not date_for_payments:
        print(f"⚠️ Could not find valid date in filename: {filename}")
        return

    print(f"Processing '{filename}' for date {date_for_payments}")

    doc = Document(word_path)

    if not doc.tables:
        print(f"⚠️ No tables found in '{filename}'")
        return
    table = doc.tables[0]

    headers = [cell.text.strip() for cell in table.rows[0].cells]

    expected_cols = ['Description', 'Payment amount', 'Payment Type', 'Member No.', 'Receipt No.', 'Notes']

    col_map = {}
    for expected_col in expected_cols:
        for i, header in enumerate(headers):
            if header.lower() == expected_col.lower():
                col_map[expected_col] = i
                break

    if len(col_map) < len(expected_cols):
        missing = set(expected_cols) - set(col_map.keys())
        print(f"⚠️ Missing expected columns in Word table: {missing}")
        return

    data = []
    for row in table.rows[1:]:
        row_data = []
        for col in expected_cols:
            cell_text = row.cells[col_map[col]].text.strip()
            row_data.append(cell_text)
        data.append(row_data)

    df = pd.DataFrame(data, columns=expected_cols)

    def clean_payment_amt(x):
        return float(x.replace('$','').replace(',','').strip()) if x else 0.0
    df['Payment amount'] = df['Payment amount'].apply(clean_payment_amt)

    df.rename(columns={'Payment amount': 'Payment Amount'}, inplace=True)

    df['Date'] = pd.to_datetime(date_for_payments)

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(filename)[0]
    excel_path = os.path.join(output_dir, base_name + ".xlsx")

    df.to_excel(excel_path, sheet_name='Sheet1', index=False)
    print(f"✅ Converted '{filename}' to '{excel_path}' with {len(df)} rows.")

if __name__ == "__main__":
    input_folder = "/path/to/your/word_files"   # <--- CHANGE THIS to your folder with .docx files
    output_folder = "/path/to/save/excel_files" # <--- CHANGE THIS to where you want Excel files saved

    word_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.docx')]

    if not word_files:
        print(f"❌ No Word (.docx) files found in {input_folder}")
        exit(1)

    for wf in word_files:
        full_path = os.path.join(input_folder, wf)
        word_to_excel(full_path, output_folder)

    print("🎉 All done!")
