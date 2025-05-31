import os
import re
import sqlite3
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from openpyxl import load_workbook
from dateutil.parser import parse

# ─────── Configuration ───────
DEFAULT_INPUT_DIR = r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts"
DEFAULT_OUTPUT_DB = os.path.join(DEFAULT_INPUT_DIR, "transactions.db")
# ───────────────────────────────

def extract_and_insert(excel_dir: str, db_path: str):
    """
    Scan `excel_dir` for Excel files, parse sheets with expected columns,
    drop & recreate `transactions` table, and save data into SQLite.
    """
    expected = {"description", "payment amount", "payment type", "member no", "receipt no", "notes"}
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    with sqlite3.connect(db_path) as conn:
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
                transaction_date TEXT  -- stored as YYYY-MM-DD for proper sorting
            );
            """
        )

        for fname in os.listdir(excel_dir):
            if not fname.lower().endswith(('.xlsx', '.xlsm', '.xltx', '.xltm')):
                continue
            fp = os.path.join(excel_dir, fname)
            try:
                wb = load_workbook(fp, data_only=True)
            except Exception as e:
                print(f"Skipping {fname}: {e}")
                continue

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                header = list(next(ws.iter_rows(values_only=True)))
                cols = [re.sub(r"[\W_]+", " ", str(h).strip().lower()).strip() for h in header]
                if not expected.issubset(cols):
                    continue

                db_cols = [c.replace(' ', '_') for c in cols] + ['transaction_date']
                placeholders = ",".join("?" for _ in db_cols)
                sql = f"INSERT INTO transactions ({','.join(db_cols)}) VALUES ({placeholders})"

                for row in ws.iter_rows(min_row=2, values_only=True):
                    row_dict = dict(zip(cols, row))
                    try:
                        date_obj = parse(str(sheet_name), dayfirst=True)
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except Exception:
                        date_str = sheet_name

                    values = [row_dict[c] for c in cols] + [date_str]
                    conn.execute(sql, values)
        conn.commit()
    print(f"Recreated DB at: {db_path}")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Receipt Query App")
        self.geometry("980x680")
        self.input_dir = DEFAULT_INPUT_DIR
        self.db_path = DEFAULT_OUTPUT_DB

        # Directory selector
        dir_frame = ttk.Frame(self)
        dir_frame.pack(fill='x', padx=10, pady=5)
        self.dir_label = ttk.Label(dir_frame, text=f"Input folder: {self.input_dir}")
        self.dir_label.pack(side='left', expand=True)
        ttk.Button(dir_frame, text="Change Folder", command=self.select_folder).pack(side='right')

        # Main controls
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=5)
        for txt, cmd in [("Recreate & Refresh DB", self.refresh_db),
                         ("Show All", self.show_all),
                         ("Export CSV", self.export_csv)]:
            ttk.Button(btn_frame, text=txt, command=cmd).pack(side='left', padx=(0,5))

        # Single-field searches
        self._add_search_field("Receipt No:", "receipt_no", self.search_receipt)
        self._add_search_field("Member No:", "member_no", self.search_member)
        self._add_search_field("Payment Amount:", "payment_amount", self.search_amount)

        # Single-date search
        date_frame = ttk.Frame(self)
        date_frame.pack(fill='x', padx=10, pady=2)
        ttk.Label(date_frame, text="Transaction Date (DD/MM/YYYY):").pack(side='left')
        self.day_var = tk.StringVar(); ttk.Entry(date_frame, textvariable=self.day_var, width=4).pack(side='left', padx=(5,2))
        ttk.Label(date_frame, text="/").pack(side='left')
        self.month_var = tk.StringVar(); ttk.Entry(date_frame, textvariable=self.month_var, width=4).pack(side='left', padx=2)
        ttk.Label(date_frame, text="/").pack(side='left')
        self.year_var = tk.StringVar(); ttk.Entry(date_frame, textvariable=self.year_var, width=6).pack(side='left', padx=(2,10))
        ttk.Button(date_frame, text="Search", command=self.search_date).pack(side='left')

        # Range searches
        range_frame = ttk.LabelFrame(self, text="Range Searches")
        range_frame.pack(fill='x', padx=10, pady=5)

        # Receipt No range
        rframe = ttk.Frame(range_frame)
        rframe.pack(fill='x', padx=5, pady=2)
        ttk.Label(rframe, text="Receipt No from:").pack(side='left')
        self.rec_start = tk.StringVar(); ttk.Entry(rframe, textvariable=self.rec_start, width=20).pack(side='left', padx=5)
        ttk.Label(rframe, text="to").pack(side='left')
        self.rec_end = tk.StringVar(); ttk.Entry(rframe, textvariable=self.rec_end, width=20).pack(side='left', padx=5)
        ttk.Button(rframe, text="Search", command=self.search_receipt_range).pack(side='left', padx=5)

        # Date range
        dframe = ttk.Frame(range_frame)
        dframe.pack(fill='x', padx=5, pady=2)
        ttk.Label(dframe, text="Date from (DD/MM/YYYY):").pack(side='left')
        self.date_start = tk.StringVar(); ttk.Entry(dframe, textvariable=self.date_start, width=12).pack(side='left', padx=5)
        ttk.Label(dframe, text="to").pack(side='left')
        self.date_end = tk.StringVar(); ttk.Entry(dframe, textvariable=self.date_end, width=12).pack(side='left', padx=5)
        ttk.Button(dframe, text="Search", command=self.search_date_range).pack(side='left', padx=5)

        # Results table
        self.tree = ttk.Treeview(self, show='headings')
        vsb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill='both', expand=True, padx=10, pady=(0,10))
        vsb.pack(side='right', fill='y'); hsb.pack(side='bottom', fill='x')

        # Store last results
        self.last_cols = []
        self.last_rows = []

    def _add_search_field(self, label, col, fn):
        f = ttk.Frame(self); f.pack(fill='x', padx=10, pady=2)
        ttk.Label(f, text=label).pack(side='left')
        var = tk.StringVar(); ttk.Entry(f, textvariable=var, width=30).pack(side='left', padx=5)
        ttk.Button(f, text="Search", command=lambda: fn(var.get().strip())).pack(side='left')
        setattr(self, f"{col}_var", var)

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=os.path.expanduser('~'), title="Select Folder")
        if folder:
            self.input_dir, self.dir_label['text'] = folder, f"Input folder: {folder}"

    def refresh_db(self):
        try:
            extract_and_insert(self.input_dir, self.db_path)
            messagebox.showinfo("Success", "DB recreated.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_all(self):
        self._run_search("1=1", ())

    def export_csv(self):
        if not self.last_rows:
            return messagebox.showwarning("No Data", "No results to export.")
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[("CSV","*.csv")])
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f); w.writerow(self.last_cols); w.writerows(self.last_rows)
                messagebox.showinfo("Exported", f"Saved to {path}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def search_receipt(self, r):
        if not r: return messagebox.showwarning("Input","Enter Receipt No.")
        self._run_search("receipt_no = ?", (r,))

    def search_member(self, m):
        if not m: return messagebox.showwarning("Input","Enter Member No.")
        self._run_search("member_no = ?", (m,))

    def search_amount(self, a):
        try: a = float(a)
        except: return messagebox.showwarning("Input","Enter numeric Amount.")
        self._run_search("payment_amount = ?", (a,))

    def search_date(self):
        d, m, y = self.day_var.get().zfill(2), self.month_var.get().zfill(2), self.year_var.get().zfill(4)
        if not (d.isdigit() and m.isdigit() and y.isdigit()):
            return messagebox.showwarning("Input","Enter numeric Day/Month/Year.")
        date_str = f"{y}-{m}-{d}"  # ISO format
        self._run_search("transaction_date = ?", (date_str,))

    def search_receipt_range(self):
        s, e = self.rec_start.get().strip(), self.rec_end.get().strip()
        if not (s and e): return messagebox.showwarning("Input","Provide start/end Receipt Nos.")
        self._run_search("receipt_no BETWEEN ? AND ?", (s, e))

    def search_date_range(self):
        s, e = self.date_start.get(), self.date_end.get()
        try:
            ds = parse(s, dayfirst=True).strftime('%Y-%m-%d')
            de = parse(e, dayfirst=True).strftime('%Y-%m-%d')
        except:
            return messagebox.showwarning("Input","Dates must be DD/MM/YYYY.")
        self._run_search("transaction_date BETWEEN ? AND ?", (ds, de))

    def _run_search(self, where, params):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor(); cur.execute(f"SELECT * FROM transactions WHERE {where};", params)
                rows = cur.fetchall(); cols = [d[0] for d in cur.description]
        except Exception as e:
            return messagebox.showerror("Search Error", str(e))
        if not rows:
            return messagebox.showinfo("No Results","No matching transactions.")
        self.last_cols, self.last_rows = cols, rows
        self.display_rows(rows, cols)

    def display_rows(self, rows, cols):
        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = cols
        for c in cols: self.tree.heading(c, text=c); self.tree.column(c, width=100, anchor='w')
        for r in rows: self.tree.insert('', 'end', values=r)

if __name__ == '__main__':
    App().mainloop()
