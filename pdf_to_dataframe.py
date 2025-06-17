import pandas as pd
import tabula
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_bank_statements_to_dataframe(pdf_files, **kwargs):
    """
    Extracts data from a list of PDF bank statement files and combines it into a single pandas DataFrame.

    Args:
        pdf_files (list): A list of file paths to the PDF bank statements.
        **kwargs: Optional keyword arguments to pass to tabula.read_pdf.
                  Examples: area, columns, pages, guess, stream, lattice, pandas_options.

    Returns:
        pandas.DataFrame: A DataFrame containing the combined data from all PDF files.
                          Returns an empty DataFrame if no data is extracted.
    """
    all_data = []

    # Default tabula arguments that can be overridden by kwargs
    tabula_options = {
        'pages': 'all',
        'multiple_tables': True,
        'pandas_options': {'header': None}
    }
    tabula_options.update(kwargs)

    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            logging.error(f"File not found at {pdf_file}")
            continue

        try:
            # Extract tables from the PDF using tabula-py
            tables = tabula.read_pdf(pdf_file, **tabula_options)

            if not tables: # handles cases where read_pdf returns empty list
                logging.warning(f"No tables found in {pdf_file} with current settings.")
                continue

            for table in tables:
                if not isinstance(table, pd.DataFrame):
                    logging.warning(f"Skipping non-DataFrame table from {pdf_file}")
                    continue
                all_data.append(table)

        except pd.errors.EmptyDataError:
            logging.warning(f"No data found in tables for {pdf_file} after parsing.")
        except tabula.errors.JavaNotFoundError:
            logging.error("Java is not installed or not found in your PATH. Tabula-py requires Java to be installed.")
            # Potentially re-raise or handle as a critical failure for this function
            break # Stop processing further files if Java is missing
        except FileNotFoundError as e: # Should be caught by os.path.exists, but as a safeguard for tabula call
            logging.error(f"File not found during tabula processing (should have been caught earlier): {pdf_file} - {e}")
        except Exception as e: # General tabula-py or other processing errors
            logging.error(f"Error processing file {pdf_file} with Tabula: {e}")
            logging.info("This could be due to an unreadable PDF, incorrect Tabula parameters, or other issues.")
            # Example of how one might catch a Java-related IO Exception if not wrapped by tabula-py's own errors
            # This is a bit speculative as tabula-py aims to wrap common Java errors.
            if "java.io.IOException" in str(e):
                logging.error(f"A Java I/O error occurred with {pdf_file}. The PDF might be corrupted or password-protected.")

    if not all_data:
        logging.info("No data extracted from any of the files.")
        return pd.DataFrame()

    # Concatenate all extracted tables into a single DataFrame
    if not all_data: # Check again in case loop appended non-DataFrames that got skipped
        return pd.DataFrame()

    combined_df = pd.concat(all_data, ignore_index=True)

    # Column renaming logic
    # User-provided column names via kwargs['columns_rename_list'] or tabula_options['columns'] for direct use by tabula
    # If 'columns' is in tabula_options, tabula might have already named them.
    # If pandas_options={'header': 0} was used, headers might be inferred.

    user_column_names = tabula_options.get('columns_rename_list', None) # A new kwarg for renaming after extraction

    if user_column_names:
        if len(user_column_names) == combined_df.shape[1]:
            combined_df.columns = user_column_names
            logging.info("Applied user-provided column names.")
        else:
            logging.warning(f"User-provided column names count ({len(user_column_names)}) does not match DataFrame column count ({combined_df.shape[1]}). Using default numbered columns.")
            combined_df.columns = [i for i in range(combined_df.shape[1])]
    elif tabula_options.get('pandas_options', {}).get('header') == 0:
        # Headers should be inferred by pandas from the first row of the table(s)
        # Check if column names are still default integers (e.g., 0, 1, 2...) which might mean inference failed or was not applicable
        if all(isinstance(col, int) for col in combined_df.columns):
            logging.warning("Header inference was set, but columns appear to be default integers. Inspect data or provide 'columns_rename_list'.")
        else:
            logging.info("Headers inferred by pandas using header=0.")
    elif 'columns' in tabula_options and tabula_options['columns'] is not None:
        # If 'columns' was passed to tabula.read_pdf, it might name them directly or use them for extraction.
        # However, tabula's 'columns' parameter is for X coordinates, not names directly in all cases.
        # This part might need refinement based on how tabula uses 'columns' for naming.
        # For now, assume if 'columns' was passed, it was for coordinates and names might still be integers.
        if all(isinstance(col, int) for col in combined_df.columns):
             logging.warning("Tabula 'columns' argument was used, but column names are still default integers. Consider using 'columns_rename_list' for explicit naming.")
        else:
            logging.info("Column names might have been set by Tabula based on 'columns' or other arguments.")
    else:
        # Default: if no specific column handling is done, log and use numbered columns
        logging.warning("No column names provided or inferred. Using default numbered columns. Provide 'columns_rename_list' or use pandas_options={'header':0} for better results.")
        combined_df.columns = [i for i in range(combined_df.shape[1])]

    return combined_df

if __name__ == '__main__':
    # Example usage:
    # Create dummy PDF files for demonstration if they don't exist.
    # In a real scenario, replace these with actual paths to your PDF bank statement files.
    pdf_files_to_test = ['dummy_statement1.pdf', 'dummy_statement2.pdf']

    # Ensure tabula can "read" these, even if they are not valid PDFs for actual data extraction.
    # For a real test, use actual, simple PDFs.
    # Attempt to create dummy PDF files for testing if they don't exist
    for f_name in pdf_files_to_test:
        if not os.path.exists(f_name):
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.units import inch

                c = canvas.Canvas(f_name, pagesize=letter)
                # Add a simple table-like structure
                textobject = c.beginText(1 * inch, 10 * inch)
                textobject.textLine("Header1,Header2,Header3") # CSV like data
                textobject.textLine("Data1A,Data1B,Data1C")
                textobject.textLine("Data2A,Data2B,Data2C")
                c.drawText(textobject)
                c.save()
                logging.info(f"Created dummy PDF with a simple table: {f_name}")
            except ImportError:
                logging.warning(
                    "ReportLab not installed. Cannot create dummy PDF with structured data. "
                    "Please install it (`pip install reportlab`) for more realistic dummy files, "
                    "or provide actual PDFs for testing. Falling back to empty file."
                )
                with open(f_name, 'w') as fp:
                    # Tabula will likely not extract anything from an empty file, leading to warnings.
                    fp.write("")
                logging.info(f"Created empty file as fallback for: {f_name}")
            except Exception as e:
                logging.error(f"Error creating dummy PDF {f_name}: {e}. Test functionality with actual PDFs.")

    # Example 1: Basic usage (like original, expecting default column naming and potential warnings if dummy files are empty)
    logging.info("--- Running Example 1: Basic ---")
    # If ReportLab was available, dummy PDFs might have 3 columns.
    # If not, they are empty, and this will likely produce an empty DataFrame or warnings.
    df_basic = extract_bank_statements_to_dataframe(pdf_files_to_test)
    if not df_basic.empty:
        logging.info("Basic extraction successful. DataFrame head:\n%s", df_basic.head())
        df_basic.info()
    else:
        logging.warning("Basic extraction resulted in an empty DataFrame. This is expected if dummy PDFs are empty or have no tables.")

    # Example 2: Using specific tabula arguments and custom column names via 'columns_rename_list'
    logging.info("\n--- Running Example 2: With tabula options and custom column names ---")
    # Note: 'area' for tabula usually require specific PDF coordinates.
    # These are placeholder values. For real PDFs, these need to be determined.
    custom_options_ex2 = {
        'pages': '1',  # Process only the first page
        'guess': True, # Allow tabula to guess table areas (useful for simple tables)
        'pandas_options': {'header': None}, # We'll rename columns manually
        'columns_rename_list': ['TransactionDate', 'Description', 'TransactionAmount']
        # 'area': "100,50,700,500", # Example: top,left,bottom,right (requires PDF analysis)
    }
    # If dummy PDFs were created by ReportLab, they might have 3 columns.
    # This example tries to rename them. If not, it will warn about column count mismatch.

    df_custom_rename = extract_bank_statements_to_dataframe(pdf_files_to_test, **custom_options_ex2)

    if not df_custom_rename.empty:
        logging.info("Custom extraction with rename list. DataFrame head:\n%s", df_custom_rename.head())
        df_custom_rename.info()
    else:
        logging.warning("Custom extraction with rename list resulted in an empty DataFrame. This is expected if dummy PDFs are empty or table structure doesn't match.")

    # Example 3: Attempting header inference using pandas_options={'header': 0}
    logging.info("\n--- Running Example 3: With header inference ---")
    options_header_infer_ex3 = {
        'pages': '1',
        'guess': True,
        'pandas_options': {'header': 0} # Instruct pandas to use the first row as headers
    }
    # If dummy PDFs were made with ReportLab, the first line was "Header1,Header2,Header3"
    df_header_infer = extract_bank_statements_to_dataframe(pdf_files_to_test, **options_header_infer_ex3)
    if not df_header_infer.empty:
        logging.info("Header inference attempt. DataFrame head:\n%s", df_header_infer.head())
        logging.info("Inferred column names: %s", df_header_infer.columns.tolist())
        df_header_infer.info()
    else:
        logging.warning("Header inference attempt resulted in an empty DataFrame. This is expected if dummy PDFs are empty or have no tables.")

    # Optional: Clean up dummy files created for testing
    # for f_name in pdf_files_to_test:
    #     if "dummy_" in f_name and os.path.exists(f_name): # Basic safety check
    #         try:
    #             os.remove(f_name)
    #             logging.info(f"Cleaned up dummy file: {f_name}")
    #         except Exception as e:
    #             logging.error(f"Error cleaning up dummy file {f_name}: {e}")