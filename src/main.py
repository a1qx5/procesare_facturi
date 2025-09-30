import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import pandas as pd
import os
from extract_data import extract_products
from extract_full_text import extract_text_from_pdf

REQUIRED_COLUMNS = [
    "Nr. crt.", "Factura", "Data emiterii", "Client", "CIF client", "LINIA", "IQID", "Moneda", 
    "Valoare fara TVA", "Valoare TVA", "Valoare Totala", 
    "CURS BNR", "Valoare Totala(RON)"
]

def select_pdf_file():
    root = tk.Tk()
    root.withdraw()
    
    pdf_path = filedialog.askopenfilename(
        title="Select Invoice PDF",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    root.destroy()
    return pdf_path

def select_excel_option():
    root = tk.Tk()
    root.withdraw()
    
    choice = messagebox.askyesno(
        "Excel File Option",
        "Do you want to create a NEW Excel file?\n\n"
        "Yes = Create new Excel file\n"
        "No = Upload existing Excel file"
    )
    root.destroy()
    return choice

def select_excel_file():
    root = tk.Tk()
    root.withdraw()
    
    excel_path = filedialog.askopenfilename(
        title="Select Existing Excel File",
        filetypes=[("Excel files", "*.xlsx"), ("Excel files", "*.xls"), ("All files", "*.*")]
    )
    root.destroy()
    return excel_path

def get_save_path():
    root = tk.Tk()
    root.withdraw()
    
    save_path = filedialog.asksaveasfilename(
        title="Save Excel File As",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )
    root.destroy()
    return save_path

def validate_excel_columns(excel_path):
    try:
        df = pd.read_excel(excel_path)
        existing_columns = list(df.columns)
        
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in existing_columns]
        
        if missing_columns:
            messagebox.showerror(
                "Invalid Excel File",
                f"Missing required columns:\n{', '.join(missing_columns)}\n\n"
                f"Required columns:\n{', '.join(REQUIRED_COLUMNS)}"
            )
            return False, None
        
        return True, df
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read Excel file: {str(e)}")
        return False, None

def check_duplicate_invoice(df, invoice_id):
    if 'Factura' in df.columns and not df.empty:
        existing_invoices = df['Factura'].tolist()
        if invoice_id in existing_invoices:
            messagebox.showwarning(
                "Duplicate Invoice",
                f"Invoice '{invoice_id}' already exists in the Excel file!\n\n"
                f"The invoice will not be added to avoid duplicates."
            )
            return True
    return False

def create_new_excel_dataframe():
    return pd.DataFrame(columns=REQUIRED_COLUMNS)

def save_excel_with_formatting(df, file_path):
    column_widths = [6, 10, 11.5, 30, 13, 7, 27, 7.5, 15, 15, 15, 9, 20]
    
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        worksheet = writer.sheets['Sheet1']
        
        for i, width in enumerate(column_widths):
            col_letter = chr(65 + i)
            worksheet.set_column(f'{col_letter}:{col_letter}', width)

def add_items_to_excel(df, products):
    new_rows = []
    starting_row_number = len(df) + 1
    
    for i, product in enumerate(products):
        row = {
            "Nr. crt.": starting_row_number + i,
            "Factura": product.get('id', ''),
            "Data emiterii": product.get('issue_date', ''),
            "Client": product.get('client', ''),
            "CIF client": product.get('cif', ''),
            "LINIA": 'Linia ' + str(products.index(product) + 1),
            "IQID": product.get('IQID', ''),
            "Moneda": "RON" if product.get('currency', '') == "Lei" else product.get('currency', ''),
            "Valoare fara TVA": float(product.get('value_without_vat', '')),
            "Valoare TVA": float(product.get('vat_value', '')),
            "Valoare Totala": product.get('total_value', ''),
            "CURS BNR": float(product.get('exchange_rate', '')) if product.get('exchange_rate', '') else "-",
            "Valoare Totala(RON)": product.get('total_value_ron', '')
        }
        new_rows.append(row)
    
    new_df = pd.DataFrame(new_rows)
    result_df = pd.concat([df, new_df], ignore_index=True)
    
    return result_df

def main():
    pdf_path = select_pdf_file()
    if not pdf_path:
        return
    
    try:
        text = extract_text_from_pdf(pdf_path)
        products = extract_products(text)
        
        if not products:
            messagebox.showerror("Error", "No products found in the PDF!")
            return
        
        invoice_id = products[0].get('id', '') if products else ''
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to extract data from PDF: {str(e)}")
        return
    
    create_new = select_excel_option()
    
    if create_new:
        df = create_new_excel_dataframe()
        save_path = get_save_path()
        if not save_path:
            return
    else:
        excel_path = select_excel_file()
        if not excel_path:
            return
        
        valid, df = validate_excel_columns(excel_path)
        if not valid:
            return
        
        if check_duplicate_invoice(df, invoice_id):
            return
        
        save_path = excel_path
    
    try:
        final_df = add_items_to_excel(df, products)
        save_excel_with_formatting(final_df, save_path)
        
        messagebox.showinfo(
            "Success!",
            f"Invoice data successfully added to Excel!\n\n"
            f"File: {os.path.basename(save_path)}\n"
            f"Added: {len(products)} products\n"
            f"Total rows: {len(final_df)}"
        )
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save Excel file: {str(e)}")

if __name__ == "__main__":
    main()