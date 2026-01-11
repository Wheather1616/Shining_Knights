import os
import sys
import logging
import traceback
import pandas as pd
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# ─────── Logging setup ───────
LOG_DIR = Path.home() / "ReceiptsLogs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "receipts_app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

log = logging.getLogger("ReceiptsApp")
# ────────────────────────────

# ─────── Configuration ───────
EXCEL_DIR = r"/Users/williamheather/Downloads/Receipts"   # ⚠️ likely cause of Windows failure
DB_PATH   = os.path.join(EXCEL_DIR, "transactions.db")
# ─────────────────────────────

def extract_and_insert(excel_dir, db_path):
    """
    Read all .xlsx files in excel_dir, parse each sheet, and insert into SQLite.
    Adds a 'transaction_date' column from sheet name.
    """
    log.info("Starting database build")
    log.info(f"Excel directory: {excel_dir}")
    log.info(f"Database path: {db_path}")
    log.info(f"Current working directory: {os.getcwd()}")

    if not os.path.exists(excel_dir):
        raise FileNotFoundError(f"Excel directory does not exist: {excel_dir}")

    conn = sqlite3.connect(db_path)
    log.info("Connected to SQLite database")

    try:
        conn.execute("DROP TABLE IF EXISTS transactions")
        log.info("Dropped existing transactions table")

        for file in os.listdir(excel_dir):
            log.info(f"Inspecting file: {file}")

            if not file.lower().endswith(".xlsx"):
                continue

            file_path = os.path.join(excel_dir, file)
            log.info(f"Opening Excel file: {file_path}")

            try:
                xls = pd.ExcelFile(file_path)
            except Exception as e:
                log.error(f"Failed to open Excel file: {file_path}")
                log.error(str(e))
                log.error(traceback.format_exc())
                continue

            for sheet in xls.sheet_names:
                log.info(f"Parsing sheet: {sheet}")

                try:
                    df = xls.parse(sheet)
                except Exception as e:
                    log.warning(f"Failed to parse sheet {sheet} in {file}")
                    log.warning(str(e))
                    continue

                expected = {
                    "Description", "Payment amount", "Payment type",
                    "Member No.", "Receipt no.", "Notes"
                }

                if not expected.issubset(set(df.columns.str.strip())):
                    log.warning(f"Skipping sheet {sheet} due to missing columns")
                    continue

                df.columns = [c.strip() for c in df.columns]
                df["Transaction date"] = sheet
                df.columns = [
                    c.lower().replace(" ", "_").replace(".", "")
                    for c in df.columns
                ]

                try:
                    df.to_sql("transactions", conn, if_exists="append", index=False)
                    log.info(f"Inserted {len(df)} rows from {file} [{sheet}]")
                except Exception as e:
                    log.error("Failed to insert data into SQLite")
                    log.error(str(e))
                    log.error(traceback.format_exc())

    finally:
        conn.close()
        log.info("Closed SQLite connection")

class ExcelSQLApp(tk.Tk):
    def __init__(self):
        super().__init__()

        log.info("Application starting")

        self.title("Excel → SQL Explorer")
        self.geometry("950x650")

        try:
            extract_and_insert(EXCEL_DIR, DB_PATH)
        except Exception as e:
            log.critical("Database build failed on startup")
            log.critical(str(e))
            log.critical(traceback.format_exc())
            messagebox.showerror("Database Error", f"Failed to build DB.\n\nSee log:\n{LOG_FILE}")
            self.destroy()
            return

        self._build_ui()

    def _build_ui(self):
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(ctrl, text="Refresh Data", command=self.refresh_data).pack(side=tk.LEFT)

        ttk.Label(ctrl, text="Start Date (DD-MM-YYYY):").pack(side=tk.LEFT, padx=(10,0))
        self.start_entry = ttk.Entry(ctrl, width=12)
        self.start_entry.pack(side=tk.LEFT)

        ttk.Label(ctrl, text="End Date (DD-MM-YYYY):").pack(side=tk.LEFT, padx=(10,0))
        self.end_entry = ttk.Entry(ctrl, width=12)
        self.end_entry.pack(side=tk.LEFT)

        ttk.Label(ctrl, text="Payment Type:").pack(side=tk.LEFT, padx=(10,0))
        self.payment_entry = ttk.Entry(ctrl, width=10)
        self.payment_entry.pack(side=tk.LEFT)

        ttk.Label(ctrl, text="Member No.:").pack(side=tk.LEFT, padx=(10,0))
        self.member_entry = ttk.Entry(ctrl, width=8)
        self.member_entry.pack(side=tk.LEFT)

        ttk.Label(ctrl, text="Receipt No.:").pack(side=tk.LEFT, padx=(10,0))
        self.receipt_entry = ttk.Entry(ctrl, width=10)
        self.receipt_entry.pack(side=tk.LEFT)

        ttk.Button(ctrl, text="Run Query", command=self.run_query).pack(side=tk.LEFT, padx=(10,0))

        self.tree = ttk.Treeview(self, show="headings")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh_data(self):
        log.info("Refresh requested by user")

        try:
            extract_and_insert(EXCEL_DIR, DB_PATH)
            messagebox.showinfo("Data Refreshed", "Database updated from Excel files.")
            for row in self.tree.get_children():
                self.tree.delete(row)
        except Exception as e:
            log.error("Refresh failed")
            log.error(str(e))
            log.error(traceback.format_exc())
            messagebox.showerror("Refresh Error", f"Failed to refresh data.\n\nSee log:\n{LOG_FILE}")

    def run_query(self):
        log.info("Running query")

        filters, params = [], []

        if self.start_entry.get():
            filters.append("transaction_date >= ?")
            params.append(self.start_entry.get())

        if self.end_entry.get():
            filters.append("transaction_date <= ?")
            params.append(self.end_entry.get())

        if self.payment_entry.get():
            filters.append("payment_type = ?")
            params.append(self.payment_entry.get())

        if self.member_entry.get():
            filters.append("member_no = ?")
            params.append(self.member_entry.get())

        if self.receipt_entry.get():
            filters.append("receipt_no = ?")
            params.append(self.receipt_entry.get())

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        sql = f"SELECT * FROM transactions {where}"

        log.info(f"SQL: {sql}")
        log.info(f"Params: {params}")

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(sql, conn, params=params)
        except Exception as e:
            log.error("Query execution failed")
            log.error(str(e))
            log.error(traceback.format_exc())
            messagebox.showerror("Query Error", f"Query failed.\n\nSee log:\n{LOG_FILE}")
            return
        finally:
            conn.close()

        self.tree["columns"] = list(df.columns)
        for c in df.columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")

        for row in self.tree.get_children():
            self.tree.delete(row)

        for _, r in df.iterrows():
            self.tree.insert("", "end", values=list(r))

if __name__ == "__main__":
    try:
        app = ExcelSQLApp()
        app.mainloop()
    except Exception:
        log.critical("Unhandled fatal error")
        log.critical(traceback.format_exc())
