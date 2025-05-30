import os
import pandas as pd
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

# ─────── Configuration ───────
EXCEL_DIR = r"C:\Users\reception\OneDrive - Coogee Legion Ex-Services Club\Documents\Receipts"
DB_PATH    = os.path.join(EXCEL_DIR, "transactions.db")
# ─────────────────────────────

def extract_and_insert(excel_dir, db_path):
    """
    Read all .xlsx files in excel_dir, parse each sheet, and insert into SQLite.
    Adds a 'transaction_date' column from sheet name.
    """
    conn = sqlite3.connect(db_path)
    for file in os.listdir(excel_dir):
        if not file.lower().endswith('.xlsx'):
            continue
        xls = pd.ExcelFile(os.path.join(excel_dir, file))
        for sheet in xls.sheet_names:
            try:
                df = xls.parse(sheet)
            except Exception:
                continue

            expected = {
                "Description", "Payment amount", "Payment type",
                "Member No.", "Receipt no.", "Notes"
            }
            if not expected.issubset(set(df.columns.str.strip())):
                continue

            df.columns = [c.strip() for c in df.columns]
            df["Transaction date"] = sheet  # e.g. "01-03-2025"
            df.columns = [c.lower().replace(" ", "_").replace(".", "") for c in df.columns]
            df.to_sql("transactions", conn, if_exists="append", index=False)
    conn.close()

class ExcelSQLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel → SQL Explorer")
        self.geometry("900x650")

        # Rebuild the database on every launch
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        try:
            extract_and_insert(EXCEL_DIR, DB_PATH)
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to build DB:\n{e}")
            self.destroy()
            return

        # Build the query UI
        self._build_query_ui()

    def _build_query_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.X, padx=10, pady=10)

        # Date range inputs
        ttk.Label(frm, text="Start Date (DD-MM-YYYY):").grid(row=0, column=0, sticky=tk.W)
        self.start_entry = ttk.Entry(frm); self.start_entry.grid(row=0, column=1)
        ttk.Label(frm, text="End Date (DD-MM-YYYY):").grid(row=0, column=2, sticky=tk.W, padx=20)
        self.end_entry = ttk.Entry(frm); self.end_entry.grid(row=0, column=3)

        # Payment type and Member No.
        ttk.Label(frm, text="Payment Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.payment_entry = ttk.Entry(frm); self.payment_entry.grid(row=1, column=1)
        ttk.Label(frm, text="Member No.: ").grid(row=1, column=2, sticky=tk.W, padx=20, pady=5)
        self.member_entry = ttk.Entry(frm); self.member_entry.grid(row=1, column=3)

        # Receipt No.
        ttk.Label(frm, text="Receipt No.: ").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.receipt_entry = ttk.Entry(frm); self.receipt_entry.grid(row=2, column=1)

        # Run Query button
        ttk.Button(frm, text="Run Query", command=self.run_query).grid(
            row=3, column=0, columnspan=4, pady=(10,0)
        )

        # Results table with vertical scrollbar
        self.tree = ttk.Treeview(self, show="headings")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def run_query(self):
        # Build filters based on any provided criteria
        filters, params = [], []
        if self.start_entry.get():
            filters.append("transaction_date >= ?"); params.append(self.start_entry.get())
        if self.end_entry.get():
            filters.append("transaction_date <= ?"); params.append(self.end_entry.get())
        if self.payment_entry.get():
            filters.append("payment_type = ?"); params.append(self.payment_entry.get())
        if self.member_entry.get():
            filters.append("member_no = ?"); params.append(self.member_entry.get())
        if self.receipt_entry.get():
            filters.append("receipt_no = ?"); params.append(self.receipt_entry.get())

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
        sql = f"SELECT * FROM transactions {where_clause}"

        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()

        # Display results
        cols = list(df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")

        # Clear old rows and insert new ones
        for row in self.tree.get_children():
            self.tree.delete(row)
        for _, r in df.iterrows():
            self.tree.insert("", "end", values=list(r))

if __name__ == "__main__":
    app = ExcelSQLApp()
    app.mainloop()
