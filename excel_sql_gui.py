import os
import pandas as pd
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def extract_and_insert(excel_dir, db_path):
    """Read all .xlsx files in excel_dir, parse each sheet, and insert into SQLite."""
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
            expected = {"Description", "Payment amount", "Payment type", 
                        "Member No.", "Receipt no.", "Notes"}
            if not expected.issubset(set(df.columns.str.strip())):
                continue
            # clean up columns, add date
            df.columns = [c.strip() for c in df.columns]
            df['Transaction date'] = sheet  # sheet name like "01-03-2025"
            df.columns = [c.lower().replace(' ', '_').replace('.', '') for c in df.columns]
            df.to_sql('transactions', conn, if_exists='append', index=False)
    conn.close()

class ExcelSQLGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel → SQL Explorer")
        self.geometry('900x600')

        # 1) Select Excel folder
        self.excel_dir = filedialog.askdirectory(title="Select folder of Excel files")
        if not self.excel_dir:
            messagebox.showerror("Error", "No folder selected. Exiting.")
            self.destroy(); return

        # 2) Choose where to save DB
        db_file = filedialog.asksaveasfilename(
            defaultextension='.db',
            filetypes=[('SQLite DB', '*.db')],
            title="Save SQLite Database As"
        )
        if not db_file:
            messagebox.showerror("Error", "No database file selected. Exiting.")
            self.destroy(); return

        # 3) Build the database
        try:
            extract_and_insert(self.excel_dir, db_file)
            messagebox.showinfo("Done", f"Database created at:\n{db_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create DB:\n{e}")
            self.destroy(); return

        self.db_path = db_file
        self._build_query_ui()

    def _build_query_ui(self):
        frm = ttk.Frame(self); frm.pack(fill=tk.X, padx=10, pady=10)

        # Date range
        ttk.Label(frm, text="Start Date (DD-MM-YYYY):").grid(row=0, column=0, sticky=tk.W)
        self.start_entry = ttk.Entry(frm); self.start_entry.grid(row=0, column=1)
        ttk.Label(frm, text="End Date (DD-MM-YYYY):").grid(row=0, column=2, sticky=tk.W, padx=20)
        self.end_entry = ttk.Entry(frm); self.end_entry.grid(row=0, column=3)

        # Payment type
        ttk.Label(frm, text="Payment Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.payment_entry = ttk.Entry(frm); self.payment_entry.grid(row=1, column=1)
        # Member No.
        ttk.Label(frm, text="Member No.:").grid(row=1, column=2, sticky=tk.W, padx=20, pady=5)
        self.member_entry = ttk.Entry(frm); self.member_entry.grid(row=1, column=3)

        # Run button
        ttk.Button(frm, text="Run Query", command=self.run_query).grid(
            row=2, column=0, columnspan=4, pady=(10,0)
        )

        # Results table
        self.tree = ttk.Treeview(self, show='headings')
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def run_query(self):
        # build WHERE
        filters, params = [], []
        if self.start_entry.get():
            filters.append("transaction_date >= ?"); params.append(self.start_entry.get())
        if self.end_entry.get():
            filters.append("transaction_date <= ?"); params.append(self.end_entry.get())
        if self.payment_entry.get():
            filters.append("payment_type = ?"); params.append(self.payment_entry.get())
        if self.member_entry.get():
            filters.append("member_no = ?"); params.append(self.member_entry.get())
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        sql = f"SELECT * FROM transactions {where}"

        # execute
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()

        # show in treeview
        # configure columns
        self.tree['columns'] = list(df.columns)
        for c in df.columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor='center')
        # clear & insert
        for row in self.tree.get_children(): self.tree.delete(row)
        for _, r in df.iterrows():
            self.tree.insert('', 'end', values=list(r))

if __name__ == '__main__':
    app = ExcelSQLGUI()
    app.mainloop()
