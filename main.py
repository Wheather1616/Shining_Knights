import os
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from openpyxl import load_workbook

# ─────── Configuration ───────
# ─────── Configuration ───────
DEFAULT_INPUT_DIR = r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts"
DEFAULT_OUTPUT_DB = os.path.join(DEFAULT_INPUT_DIR, "transactions.db")
# ───────────────────────────────

# ───────────────────────────────

def extract_and_insert(excel_dir: str, db_path: str):
    """
    Scan `excel_dir` for Excel files, parse sheets with expected columns,
    drop & recreate `transactions` table, and save data into SQLite.
    """
    expected = {"description", "payment amount", "payment type", "member no", "receipt no", "notes"}
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)

    # Drop and recreate the transactions table
    conn.execute("DROP TABLE IF EXISTS transactions;")
    conn.execute(
        """
        CREATE TABLE transactions (
            description      TEXT,
            payment_amount   REAL,
            payment_type     TEXT,
            member_no        TEXT,
            receipt_no       TEXT,
            notes            TEXT,
            transaction_date TEXT
        );
        """
    )

    # Process each Excel file
    for fname in os.listdir(excel_dir):
        if not fname.lower().endswith(('.xlsx', '.xlsm', '.xltx', '.xltm')):
            continue
        wb = load_workbook(os.path.join(excel_dir, fname), data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            # Read header row values (values_only=True returns raw values)
            header = list(next(ws.iter_rows(values_only=True)))
            cols = [str(h).strip().lower().replace('.', '') for h in header]
            if not expected.issubset(cols):
                continue

            # Prepare DB columns & insert SQL
            db_cols = [c.replace(' ', '_') for c in cols] + ['transaction_date']
            placeholders = ",".join("?" for _ in db_cols)
            sql = f"INSERT INTO transactions ({','.join(db_cols)}) VALUES ({placeholders})"

            # Insert each data row
            for row in ws.iter_rows(min_row=2, values_only=True):
                row_dict = dict(zip(cols, row))
                values = [row_dict[c] for c in cols] + [sheet_name]
                conn.execute(sql, values)

    conn.commit()
    conn.close()
    print(f"Recreated DB at: {db_path}")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Receipt Query App")
        self.geometry("900x600")
        self.input_dir = DEFAULT_INPUT_DIR
        self.db_path = DEFAULT_OUTPUT_DB

        # Directory selector
        dir_frame = ttk.Frame(self)
        dir_frame.pack(fill='x', padx=10, pady=5)
        self.dir_label = ttk.Label(dir_frame, text=f"Input folder: {self.input_dir}")
        self.dir_label.pack(side='left', expand=True)
        ttk.Button(dir_frame, text="Change Folder", command=self.select_folder).pack(side='right')

        # Refresh button
        ttk.Button(self, text="Recreate & Refresh Database", command=self.refresh_db)\
            .pack(fill='x', padx=10, pady=5)

        # Receipt No search
        self._add_search_field("Receipt No:", "receipt_no", self.search_receipt)

        # Member No search
        self._add_search_field("Member No:", "member_no", self.search_member)

        # Payment Amount search
        self._add_search_field("Payment Amount:", "payment_amount", self.search_amount)

        # Transaction Date search (three boxes: DD/MM/YYYY)
        date_frame = ttk.Frame(self)
        date_frame.pack(fill='x', padx=10, pady=2)
        ttk.Label(date_frame, text="Transaction Date:").pack(side='left')
        self.day_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.year_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.day_var, width=4).pack(side='left', padx=(5,2))
        ttk.Label(date_frame, text="/").pack(side='left')
        ttk.Entry(date_frame, textvariable=self.month_var, width=4).pack(side='left', padx=2)
        ttk.Label(date_frame, text="/").pack(side='left')
        ttk.Entry(date_frame, textvariable=self.year_var, width=6).pack(side='left', padx=(2,10))
        ttk.Button(date_frame, text="Search", command=self.search_date).pack(side='left')

        # Results table
        self.tree = ttk.Treeview(self, show='headings')
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill='both', expand=True, padx=10, pady=(0,10))
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')

    def _add_search_field(self, label_text, column, callback):
        frame = ttk.Frame(self)
        frame.pack(fill='x', padx=10, pady=2)
        ttk.Label(frame, text=label_text).pack(side='left')
        var = tk.StringVar()
        ttk.Entry(frame, textvariable=var, width=30).pack(side='left', padx=(5,10))
        ttk.Button(frame, text="Search", command=lambda: callback(var.get().strip())).pack(side='left')
        setattr(self, f"{column}_var", var)

    def select_folder(self):
        folder = filedialog.askdirectory(
            initialdir=os.path.expanduser('~'),
            title="Select Receipts Folder"
        )
        if folder:
            self.input_dir = folder
            self.dir_label.config(text=f"Input folder: {self.input_dir}")

    def refresh_db(self):
        try:
            extract_and_insert(self.input_dir, self.db_path)
            messagebox.showinfo("Success", "Database recreated successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_receipt(self, receipt_no):
        if not receipt_no:
            messagebox.showwarning("Input Needed", "Please enter a Receipt No.")
            return
        self._run_search("receipt_no = ?", (receipt_no,))

    def search_member(self, member_no):
        if not member_no:
            messagebox.showwarning("Input Needed", "Please enter a Member No.")
            return
        self._run_search("member_no = ?", (member_no,))

    def search_amount(self, amount):
        if not amount:
            messagebox.showwarning("Input Needed", "Please enter a Payment Amount.")
            return
        try:
            amt = float(amount)
        except ValueError:
            messagebox.showwarning("Invalid Input", "Payment Amount must be a number.")
            return
        self._run_search("payment_amount = ?", (amt,))

    def search_date(self):
        d = self.day_var.get().zfill(2)
        m = self.month_var.get().zfill(2)
        y = self.year_var.get().zfill(4)
        if not (d.isdigit() and m.isdigit() and y.isdigit()):
            messagebox.showwarning("Invalid Date", "Please enter numeric Day, Month, and Year.")
            return
        date_str = f"{d}-{m}-{y}"
        self._run_search("transaction_date = ?", (date_str,))

    def _run_search(self, where_clause, params):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            sql = f"SELECT * FROM transactions WHERE {where_clause};"
            cur.execute(sql, params)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            conn.close()
        except Exception as e:
            messagebox.showerror("Search Error", str(e))
            return

        if not rows:
            messagebox.showinfo("No Results", "No matching transactions found.")
            return

        self.display_rows(rows, cols)

    def display_rows(self, rows, cols):
        """Populate the Treeview with given rows & columns."""
        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='w')
        for row in rows:
            self.tree.insert('', 'end', values=row)

if __name__ == '__main__':
    app = App()
    app.mainloop()
