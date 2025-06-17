import pandas as pd
import tabula
import os

def extract_bank_statements_to_dataframe(pdf_files):
    """
    Extracts data from a list of PDF bank statement files and combines it into a single pandas DataFrame.

    Args:
        pdf_files (list): A list of file paths to the PDF bank statements.

    Returns:
        pandas.DataFrame: A DataFrame containing the combined data from all PDF files.
                          Returns an empty DataFrame if no data is extracted.
    """
    all_data = []
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"Error: File not found at {pdf_file}")
            continue

        try:
            # Extract tables from the PDF.
            # 'pages="all"' attempts to read tables from all pages.
            # 'multiple_tables=True' ensures all detected tables are captured.
            # 'pandas_options={'header': None}' is used assuming PDF tables may not have clear headers.
            # You might need to adjust parameters like 'area', 'columns', or 'guess=False'
            # depending on the structure of your specific PDF bank statements.
            tables = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True, pandas_options={'header': None})

            for table in tables:
                all_data.append(table)

        except Exception as e:
            print(f"Error processing file {pdf_file}: {e}")

    if not all_data:
        print("No data extracted from any of the files.")
        return pd.DataFrame()

    # Concatenate all extracted tables into a single DataFrame
    combined_df = pd.concat(all_data, ignore_index=True)

    # Assuming the columns are in order: Date, Transaction Name, Amount
    # You might need to adjust column indexing or mapping based on the actual PDF structure
    if combined_df.shape[1] >= 3:
        combined_df = combined_df.iloc[:, :3] # Select the first 3 columns
        combined_df.columns = ['Date', 'Transaction Name', 'Amount'] # Rename columns
    else:
        print("Warning: Not enough columns detected in the extracted data.")
        # Handle cases where fewer than 3 columns are found, maybe inspect the data
        # or try different tabula parameters.

    return combined_df

if __name__ == '__main__':
    # Example usage:
    # Replace with the actual paths to your PDF bank statement files
    pdf_files = ['statement1.pdf', 'statement2.pdf', 'statement3.pdf']

    # Create dummy empty files for demonstration purposes
    # In a real scenario, you would have actual PDF files here.
    for f in pdf_files:
        if not os.path.exists(f):
            with open(f, 'w') as fp:
                pass # Create an empty file

    df = extract_bank_statements_to_dataframe(pdf_files)

    if not df.empty:
        print("Successfully extracted data into DataFrame:")
        print(df.head()) # Print the first few rows of the DataFrame
        print("\nDataFrame Info:")
        df.info() # Print DataFrame information (columns, data types, etc.)
    else:
        print("DataFrame is empty.")