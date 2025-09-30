from flask import Flask, request, render_template, flash, redirect, url_for, send_file, session
import os
import sys
import tempfile
import pandas as pd
from werkzeug.utils import secure_filename

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import well-tested functions from main.py
from main import (
    REQUIRED_COLUMNS, 
    create_new_excel_dataframe,
    add_items_to_excel,
    save_excel_with_formatting
)
from extract_data import extract_products
from extract_full_text import extract_text_from_pdf

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Use system temp directory instead of uploads folder
TEMP_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls'}

# Import all the well-tested functions from main.py
from main import (
    REQUIRED_COLUMNS, 
    validate_excel_columns, 
    check_duplicate_invoice,
    create_new_excel_dataframe,
    add_items_to_excel,
    save_excel_with_formatting
)
from extract_data import extract_products
from extract_full_text import extract_text_from_pdf

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def web_validate_excel_columns(excel_path):
    """Web-friendly version of validate_excel_columns that doesn't use tkinter"""
    try:
        # First, check if file exists and has content
        if not os.path.exists(excel_path):
            return False, "Excel file not found."
        
        file_size = os.path.getsize(excel_path)
        if file_size == 0:
            return False, "Excel file is empty (0 bytes)."
        
        if file_size < 100:  # Excel files are typically much larger
            return False, "Excel file appears to be corrupted (too small)."
        
        # Determine engine based on file extension
        if excel_path.lower().endswith('.xlsx'):
            engine = 'openpyxl'
        elif excel_path.lower().endswith('.xls'):
            engine = 'xlrd'
        else:
            return False, "Unsupported Excel file format. Please use .xlsx or .xls files."
        
        # Try to read the Excel file
        df = pd.read_excel(excel_path, engine=engine)
        
        # Check if the DataFrame is empty
        if df.empty:
            return False, "Excel file contains no data."
        
        existing_columns = list(df.columns)
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in existing_columns]
        
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        return True, df
        
    except ImportError as e:
        if 'openpyxl' in str(e):
            return False, "Missing openpyxl library. Please install it to read .xlsx files."
        elif 'xlrd' in str(e):
            return False, "Missing xlrd library. Please install it to read .xls files."
        else:
            return False, f"Missing required library: {str(e)}"
    except pd.errors.EmptyDataError:
        return False, "Excel file is empty or contains no readable data."
    except Exception as e:
        error_msg = str(e).lower()
        if "no valid workbook part" in error_msg:
            return False, "Invalid Excel file format. The file may be corrupted, renamed from another format, or not a real Excel file. Please check the file and try again."
        elif "corrupted" in error_msg or "invalid" in error_msg:
            return False, "Excel file appears to be corrupted. Please try saving it again from Excel."
        elif "permission" in error_msg:
            return False, "Permission denied reading Excel file. Make sure the file is not open in Excel."
        else:
            return False, f"Failed to read Excel file: {str(e)}"

def web_check_duplicate_invoice(df, invoice_id):
    """Web-friendly version of check_duplicate_invoice that doesn't use tkinter"""
    if 'Factura' in df.columns and not df.empty:
        existing_invoices = df['Factura'].tolist()
        if invoice_id in existing_invoices:
            return True
    return False

@app.route('/')
def index():
    from flask import session
    # Check for success message from session
    if 'success_message' in session:
        flash(session.pop('success_message'))
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_files():
    if 'pdf_files' not in request.files:
        flash('No PDF files selected')
        return redirect(url_for('index'))
    
    pdf_files = request.files.getlist('pdf_files')
    excel_file = request.files.get('excel_file')
    custom_filename = request.form.get('output_filename', '').strip()
    
    if not pdf_files or all(f.filename == '' for f in pdf_files):
        flash('No PDF files selected')
        return redirect(url_for('index'))
    
    # Filter valid PDF files
    valid_pdfs = []
    invalid_files = []
    
    for pdf_file in pdf_files:
        if pdf_file.filename != '' and allowed_file(pdf_file.filename):
            valid_pdfs.append(pdf_file)
        elif pdf_file.filename != '':
            invalid_files.append(pdf_file.filename)
    
    if not valid_pdfs:
        flash('No valid PDF files found')
        return redirect(url_for('index'))
    
    # Show invalid files warning if any
    if invalid_files:
        flash(f'⚠️ Invalid files skipped: {", ".join(invalid_files)}')
    
    try:
        # Handle Excel file setup
        base_df = None
        excel_temp_path = None
        
        if excel_file and excel_file.filename != '':
            if not allowed_file(excel_file.filename):
                flash('Invalid Excel file format')
                return redirect(url_for('index'))
            
            # Use temporary file for Excel
            excel_temp_fd, excel_temp_path = tempfile.mkstemp(suffix='.xlsx')
            os.close(excel_temp_fd)  # Close file descriptor, keep path
            excel_file.save(excel_temp_path)
            
            valid, result = web_validate_excel_columns(excel_temp_path)
            if not valid:
                os.remove(excel_temp_path)  # Clean up on error
                flash(f'Excel validation failed: {result}')
                return redirect(url_for('index'))
            
            base_df = result
        else:
            base_df = create_new_excel_dataframe()
        
        # Process each PDF file sequentially, updating the Excel progressively
        current_df = base_df
        processed_invoices = []
        skipped_invoices = []
        total_products = 0
        
        for pdf_file in valid_pdfs:
            pdf_temp_path = None
            try:
                # Use temporary file for PDF
                pdf_temp_fd, pdf_temp_path = tempfile.mkstemp(suffix='.pdf')
                os.close(pdf_temp_fd)  # Close file descriptor, keep path
                pdf_file.save(pdf_temp_path)
                
                # Extract data from PDF
                text = extract_text_from_pdf(pdf_temp_path)
                products = extract_products(text)
                
                if not products:
                    skipped_invoices.append(f"{pdf_file.filename} (no products found)")
                    continue
                
                invoice_id = products[0].get('id', '') if products else ''
                
                # Check for duplicates in current Excel state
                if web_check_duplicate_invoice(current_df, invoice_id):
                    skipped_invoices.append(f"{pdf_file.filename} (invoice {invoice_id} already exists)")
                    continue
                
                # Add products to current Excel state - this updates row numbers correctly
                current_df = add_items_to_excel(current_df, products)
                total_products += len(products)
                processed_invoices.append(f"{pdf_file.filename} (invoice {invoice_id})")
                
            except Exception as e:
                skipped_invoices.append(f"{pdf_file.filename} (error: {str(e)})")
                continue
            finally:
                # Always clean up temporary PDF file
                if pdf_temp_path and os.path.exists(pdf_temp_path):
                    os.remove(pdf_temp_path)
        
        # Clean up temporary Excel file if uploaded
        if excel_temp_path and os.path.exists(excel_temp_path):
            os.remove(excel_temp_path)
        
        if not processed_invoices:
            flash('❌ No invoices could be processed successfully')
            if skipped_invoices:
                flash(f'Skipped files: {"; ".join(skipped_invoices)}')
            return redirect(url_for('index'))
        
        # Use the progressively updated Excel as final result
        final_df = current_df
        
        # Create output filename - use custom name if provided, otherwise auto-generate
        if custom_filename:
            # Remove .xlsx extension if user included it
            if custom_filename.lower().endswith('.xlsx'):
                custom_filename = custom_filename[:-5]
            # Sanitize filename for safety
            import re
            custom_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename)
            output_filename = f"{custom_filename}.xlsx"
        else:
            output_filename = f"processed_invoices_{len(processed_invoices)}_files.xlsx"
        
        # Use temporary file for output Excel
        output_temp_fd, output_temp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(output_temp_fd)  # Close file descriptor, keep path
        save_excel_with_formatting(final_df, output_temp_path)
        
        # Prepare success message
        success_msg = f'✅ Successfully processed {len(processed_invoices)} invoices with {total_products} total products'
        
        if skipped_invoices:
            success_msg += f' | ⚠️ Skipped: {"; ".join(skipped_invoices)}'
        
        # Store success message in session for after reload
        session['success_message'] = success_msg
        
        try:
            return send_file(output_temp_path, as_attachment=True, download_name=output_filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        finally:
            # Clean up temporary output file after a delay (Flask needs time to send it)
            import threading
            def cleanup_after_delay():
                import time
                time.sleep(5)  # Wait 5 seconds for download to complete
                if os.path.exists(output_temp_path):
                    os.remove(output_temp_path)
            
            cleanup_thread = threading.Thread(target=cleanup_after_delay)
            cleanup_thread.daemon = True
            cleanup_thread.start()
        
    except Exception as e:
        flash(f'❌ Error processing files: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)