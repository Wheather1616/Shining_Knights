import pandas as pd
import os
import sys
from datetime import datetime
from openpyxl import load_workbook
import tkinter as tk
from tkinter import filedialog, messagebox

# === CONFIG ===
sheet_name  = 'Sheet1'        # Change if needed
date_column = 'Date'          # Must match column in your spreadsheet
output_dir  = os.path.expanduser("~/Desktop/Projects/Receipts")

class ExcelAnalyserApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel Payments Analyzer")
        self.geometry("400x150")
        self.resizable(False, False)

        tk.Label(self, text="Excel Payments Analyzer", font=("Helvetica", 14, "bold")).pack(pady=10)
        tk.Button(self, text="Select Excel File and Run", command=self.run_analysis, width=30).pack(pady=5)
        tk.Button(self, text="Quit", command=self.destroy, width=30).pack()

    def run_analysis(self):
        source_file = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not source_file:
            return  # user cancelled

        try:
            # Load
            df = pd.read_excel(source_file, sheet_name=sheet_name, engine='openpyxl')

            # Clean & rename
            df = df[[
                'Description',
                'Payment Amt',
                'Payment Type',
                'Member No.',
                'Receipt No.',
                'Notes',
                date_column
            ]].rename(columns={'Payment Amt': 'Payment Amount'})

            # Today's date
            today = datetime.today()
            day_suffix = "th" if 11 <= today.day <= 13 else {1:"st", 2:"nd", 3:"rd"}.get(today.day%10, "th")
            day_str   = f"{today.day}{day_suffix}"
            month_str = today.strftime("%B")

            # Filter
            df_today = df[pd.to_datetime(df[date_column]).dt.date == today.date()]
            if df_today.empty:
                messagebox.showinfo("No Data", "No payments for today.")
                return

            # Output path
            os.makedirs(output_dir, exist_ok=True)
            excel_path = os.path.join(output_dir, f"{month_str}.xlsx")

            # Write
            if os.path.exists(excel_path):
                with pd.ExcelWriter(excel_path, engine='openpyxl',
                                     mode='a', if_sheet_exists='replace') as writer:
                    df_today.drop(columns=[date_column]).to_excel(writer,
                                                                  sheet_name=day_str,
                                                                  index=False)
            else:
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    df_today.drop(columns=[date_column]).to_excel(writer,
                                                                  sheet_name=day_str,
                                                                  index=False)

            messagebox.showinfo(
                "Success",
                f"✅ Saved {len(df_today)} payment(s)\nto:\n{excel_path}\nsheet: {day_str}"
            )

        except KeyError as ke:
            messagebox.showerror("Column Error", f"Missing expected column: {ke}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = ExcelAnalyserApp()
    app.mainloop()
