import os
import pandas as pd
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

# ─────── Configuration ───────
EXCEL_DIR = r"/Users/williamheather/Downloads/Receipts"
DB_PATH    = os.path.join(EXCEL_DIR, "transactions.db")
# ─────────────────────────────

def extract_and_insert(excel_dir, db_path):
    """
    Read all .xlsx files in excel_dir, parse each sheet, and insert into SQLite.
    Adds a 'transaction_date' column from sheet name.
    """
    conn = sqlite3.connect(db_path)
    # Clear existing table if present
    conn.execute("DROP TABLE IF EXISTS transactions")
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
        self.geometry("950x650")

        # Build the initial database
        try:
            extract_and_insert(EXCEL_DIR, DB_PATH)
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to build DB:\n{e}")
            self.destroy()
            return

        self._build_ui()

    def _build_ui(self):
        # Top controls frame
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=10, pady=5)

        # Refresh button
        ttk.Button(ctrl, text="Refresh Data", command=self.refresh_data).pack(side=tk.LEFT)

        # Date range inputs
        ttk.Label(ctrl, text="Start Date (DD-MM-YYYY):").pack(side=tk.LEFT, padx=(10,0))
        self.start_entry = ttk.Entry(ctrl, width=12); self.start_entry.pack(side=tk.LEFT)
        ttk.Label(ctrl, text="End Date (DD-MM-YYYY):").pack(side=tk.LEFT, padx=(10,0))
        self.end_entry = ttk.Entry(ctrl, width=12); self.end_entry.pack(side=tk.LEFT)

        # Payment type
        ttk.Label(ctrl, text="Payment Type:").pack(side=tk.LEFT, padx=(10,0))
        self.payment_entry = ttk.Entry(ctrl, width=10); self.payment_entry.pack(side=tk.LEFT)

        # Member No.
        ttk.Label(ctrl, text="Member No.:").pack(side=tk.LEFT, padx=(10,0))
        self.member_entry = ttk.Entry(ctrl, width=8); self.member_entry.pack(side=tk.LEFT)

        # Receipt No.
        ttk.Label(ctrl, text="Receipt No.:").pack(side=tk.LEFT, padx=(10,0))
        self.receipt_entry = ttk.Entry(ctrl, width=10); self.receipt_entry.pack(side=tk.LEFT)

        # Run Query button
        ttk.Button(ctrl, text="Run Query", command=self.run_query).pack(side=tk.LEFT, padx=(10,0))

        # Results table
        self.tree = ttk.Treeview(self, show="headings")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh_data(self):
        """Rebuild the database from Excel files."""
        try:
            extract_and_insert(EXCEL_DIR, DB_PATH)
            messagebox.showinfo("Data Refreshed", "Database has been updated from the Excel files.")
            # Clear table view
            for row in self.tree.get_children(): self.tree.delete(row)
        except Exception as e:
            messagebox.showerror("Refresh Error", f"Failed to refresh data:\n{e}")

    def run_query(self):
        # Build filters
        filters, params = [], []
        if self.start_entry.get(): filters.append("transaction_date >= ?"); params.append(self.start_entry.get())
        if self.end_entry.get():   filters.append("transaction_date <= ?"); params.append(self.end_entry.get())
        if self.payment_entry.get(): filters.append("payment_type = ?"); params.append(self.payment_entry.get())
        if self.member_entry.get():  filters.append("member_no = ?"); params.append(self.member_entry.get())
        if self.receipt_entry.get(): filters.append("receipt_no = ?"); params.append(self.receipt_entry.get())

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        sql = f"SELECT * FROM transactions {where}"

        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()

        # Display results
        cols = list(df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")

        # Clear old rows
        for row in self.tree.get_children(): self.tree.delete(row)
        for _, r in df.iterrows(): self.tree.insert("", "end", values=list(r))

if __name__ == "__main__":
    app = ExcelSQLApp()
    app.mainloop()
