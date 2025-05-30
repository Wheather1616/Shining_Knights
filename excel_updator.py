from openpyxl import load_workbook

def copy_sheets_by_index(source_file, target_file):
    # Load workbooks
    src_wb = load_workbook(source_file)
    tgt_wb = load_workbook(target_file)

    src_sheets = src_wb.worksheets
    tgt_sheets = tgt_wb.worksheets

    count = min(len(src_sheets), len(tgt_sheets))
    print(f"\n📁 Copying data from '{source_file}' to '{target_file}'")
    print(f"➡️  Matching {count} sheet(s) by index...")

    for i in range(count):
        src_ws = src_sheets[i]
        tgt_ws = tgt_sheets[i]
        print(f"  Sheet {i+1}: '{src_ws.title}' → '{tgt_ws.title}'")

        for row in src_ws.iter_rows():
            for cell in row:
                tgt_ws[cell.coordinate].value = cell.value
                tgt_ws[cell.coordinate].number_format = cell.number_format

    tgt_wb.save(target_file)
    print(f"✅ Saved: {target_file}")

def copy_multiple_pairs(file_pairs):
    for source_file, target_file in file_pairs:
        copy_sheets_by_index(source_file, target_file)

if __name__ == "__main__":
    # 🔁 Define your list of (source, target) pairs
    file_pairs = [
        (r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\February.xlsx", r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\February_2025.xlsx"),
        (r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\March.xlsx", r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\March_2025.xlsx"),
        (r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\April.xlsx", r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\April_2025.xlsx"),
        (r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\May.xlsx", r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts\May_2025.xlsx") 
    ]

    copy_multiple_pairs(file_pairs)

