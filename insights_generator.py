import pandas as pd
import logging
import numpy as np # Will be needed for NaN comparison and numeric types

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Basic keyword-based categorization mapping
DEFAULT_CATEGORIES = {
    'salary': 'Income',
    'deposit': 'Income',
    'groceries': 'Expenses',
    'supermarket': 'Expenses',
    'restaurant': 'Expenses',
    'rent': 'Expenses',
    'mortgage': 'Expenses',
    'utilities': 'Expenses',
    'gas': 'Expenses',
    'transport': 'Expenses',
    'travel': 'Expenses',
    'shopping': 'Expenses',
    'pharmacy': 'Expenses',
    'doctor': 'Expenses',
    'health': 'Expenses',
    'insurance': 'Expenses',
    'gym': 'Expenses',
    'entertainment': 'Expenses',
    'transfer': 'Transfers',
    'payment': 'Payments',
    'withdrawal': 'Expenses', # Or Transfers depending on context
    'atm': 'Expenses', # Or Transfers
    'interest': 'Income',
    'freelance': 'Income',
    'invoice': 'Income',
    'coffee': 'Expenses',
    'netflix': 'Expenses',
    'subscription': 'Expenses',
    'received payment': 'Income', # More specific for income payments
    'client payment': 'Income'
}

def generate_insights(df: pd.DataFrame, category_keywords: dict = None) -> dict:
    """
    Cleans transaction data, categorizes transactions, and calculates summary statistics.

    Args:
        df (pd.DataFrame): Input DataFrame with transaction data. Expected columns:
                           'Date', 'Transaction Name', 'Amount'.
        category_keywords (dict, optional): A dictionary of keywords to categories.
                                            Defaults to DEFAULT_CATEGORIES.

    Returns:
        dict: A dictionary containing the cleaned and categorized DataFrame (as JSON)
              and summary statistics.
    """
    if not isinstance(df, pd.DataFrame):
        logging.error("Input is not a pandas DataFrame.")
        raise ValueError("Input must be a pandas DataFrame.")

    if df.empty:
        logging.warning("Input DataFrame is empty. Returning empty results.")
        return {
            "cleaned_df_json": pd.DataFrame().to_json(orient='records'),
            "summary_statistics": {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_flow": 0.0,
                "spending_by_category": {}
            }
        }

    # Work on a copy to avoid modifying the original DataFrame
    cleaned_df = df.copy()

    if category_keywords is None:
        category_keywords = DEFAULT_CATEGORIES

    # --- Data Cleaning ---
    logging.info("Starting data cleaning process...")

    # 1. Handle 'Transaction Name'
    if 'Transaction Name' in cleaned_df.columns:
        original_na_count = cleaned_df['Transaction Name'].isna().sum()
        if original_na_count > 0:
            logging.warning(f"Found {original_na_count} missing values in 'Transaction Name'. Filling with 'Unknown'.")
        cleaned_df['Transaction Name'] = cleaned_df['Transaction Name'].fillna('Unknown').astype(str).str.strip()
    else:
        logging.warning("'Transaction Name' column not found. Skipping related cleaning and categorization.")
        cleaned_df['Transaction Name'] = 'Unknown' # Add if missing for categorization logic

    # 2. Handle 'Amount'
    if 'Amount' in cleaned_df.columns:
        original_amount_na_count = cleaned_df['Amount'].isna().sum()
        cleaned_df['Amount'] = pd.to_numeric(cleaned_df['Amount'], errors='coerce')
        coerced_na_count = cleaned_df['Amount'].isna().sum() - original_amount_na_count # NaNs created by coercion

        if coerced_na_count > 0:
            logging.warning(f"{coerced_na_count} non-numeric values found in 'Amount' were coerced to NaN.")

        final_na_count = cleaned_df['Amount'].isna().sum()
        if final_na_count > 0:
            logging.warning(f"Found {final_na_count} total missing/unparseable values in 'Amount'. Filling with 0.0.")
        cleaned_df['Amount'] = cleaned_df['Amount'].fillna(0.0)

        # As per prompt: "assume amounts are absolute and categorization defines them as income/expense."
        # If amounts can be negative (as in sample data), take their absolute value.
        # The 'Category' will determine if it's an income or expense.
        num_negatives = (cleaned_df['Amount'] < 0).sum()
        if num_negatives > 0:
            logging.info(f"Found {num_negatives} negative values in 'Amount' column. Converting to absolute values as per processing rule.")
            cleaned_df['Amount'] = cleaned_df['Amount'].abs()
    else:
        logging.error("'Amount' column not found. This column is crucial for insights. Returning empty results.")
        # Or create a dummy column if partial processing is desired, but for now, it's critical
        return {
             "cleaned_df_json": cleaned_df.to_json(orient='records'), # Return partially cleaned
            "summary_statistics": {"error": "Amount column missing"}
        }


    # 3. Handle 'Date'
    if 'Date' in cleaned_df.columns:
        original_dates = cleaned_df['Date'].copy()
        cleaned_df['Date'] = pd.to_datetime(cleaned_df['Date'], errors='coerce')
        unparseable_dates_count = cleaned_df['Date'].isna().sum()
        if unparseable_dates_count > 0:
            logging.warning(f"{unparseable_dates_count} 'Date' entries could not be parsed and were set to NaT.")
            # Optionally, log the actual unparseable dates:
            # unparseable_entries = original_dates[cleaned_df['Date'].isna()]
            # logging.debug(f"Unparseable date entries: {unparseable_entries.tolist()}")
    else:
        logging.warning("'Date' column not found. Skipping date standardization.")

    logging.info("Data cleaning finished.")

    # --- Basic Transaction Categorization ---
    logging.info("Starting transaction categorization...")
    cleaned_df['Category'] = 'Uncategorized'

    if 'Transaction Name' in cleaned_df.columns:
        for keyword, category in category_keywords.items():
            try:
                # Ensure 'Transaction Name' is string type before using .str accessor
                mask = cleaned_df['Transaction Name'].astype(str).str.contains(keyword, case=False, na=False)
                cleaned_df.loc[mask, 'Category'] = category
            except Exception as e:
                logging.error(f"Error applying keyword '{keyword}' for category '{category}': {e}")
    logging.info("Transaction categorization finished.")

    # --- Calculate Summary Statistics ---
    logging.info("Calculating summary statistics...")

    # Assuming positive amounts for income, and positive amounts for expenses that need to be summed.
    # If expenses are represented as negative numbers, the logic for total_expenses would need adjustment.
    # For this implementation, 'Category' dictates if an amount is income or expense.

    total_income = cleaned_df[cleaned_df['Category'] == 'Income']['Amount'].sum()

    # Sum amounts for all categories that are typically expenses
    expense_categories = [cat for key, cat in category_keywords.items() if cat == 'Expenses'] # Get all unique expense category names
    expense_categories.append('Expenses') # Ensure 'Expenses' itself is included if used directly
    expense_categories = list(set(expense_categories)) # Unique list

    # More robustly, define expense categories directly or based on a property in your category_keywords map
    # For now, we assume any category *named* 'Expenses' or those mapped to 'Expenses' are expenses.
    # A better approach would be: category_keywords = {'salary': {'name': 'Income', 'type': 'income'}, ...}

    # Filter for rows where 'Category' is one of the identified expense types
    # This also includes 'Uncategorized' if we decide it should be an expense by default
    # For now, only explicit 'Expenses' categories are summed.
    # Let's assume for now that any category not 'Income' or 'Transfers' could be an expense,
    # but for explicit "Total Expenses", we'll be more specific.

    # For a simpler interpretation: sum all 'Amount' where Category is 'Expenses'
    # This means keywords like 'groceries', 'rent' correctly map to 'Expenses' category first.
    total_expenses = cleaned_df[cleaned_df['Category'] == 'Expenses']['Amount'].sum()

    net_flow = total_income - total_expenses

    # Spending by Category (focus on 'Expenses' category and its sub-types if they were different)
    # Since our current categorization maps specific keywords to a general 'Expenses' category,
    # we group by 'Transaction Name' for detail or rely on more granular categories if defined.
    # For this version, let's get sums for all categories that aren't 'Income'.
    # Since 'Amount' is now absolute, all sums will be positive.

    all_categories_sum = cleaned_df.groupby('Category')['Amount'].sum().to_dict()

    # spending_by_category should reflect actual spending categories.
    # This could be 'Expenses' category itself, or other non-Income, non-Transfer categories.
    # For now, let's define it as sum of amounts for categories explicitly marked as 'Expenses'
    # and also include 'Uncategorized' as it often represents spending.
    # However, the current DEFAULT_CATEGORIES maps things like 'groceries' to 'Expenses'.
    # So, grouping by 'Category' and then picking out 'Expenses' is correct.
    # If there were sub-types like 'Expenses - Groceries', 'Expenses - Utilities', that would be different.

    # The all_categories_sum for 'Expenses' will be the total of all items categorized as 'Expenses'.
    # Other categories like 'Payments', 'Transfers', 'Uncategorized' will also have their sums.
    spending_by_category = {
        cat: val for cat, val in all_categories_sum.items()
        if cat not in ['Income'] # Exclude 'Income' from spending breakdown; other categories are forms of outflow or neutral.
    }

    logging.info("Summary statistics calculation finished.")

    # --- Prepare Output ---
    # Convert DataFrame to JSON string (list of records) for API friendliness
    # Handle NaT dates for JSON conversion
    if 'Date' in cleaned_df.columns:
        cleaned_df['Date'] = cleaned_df['Date'].astype(str) # Convert NaT/datetime to string

    cleaned_df_json = cleaned_df.to_json(orient='records')

    summary_stats_output = {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_flow": net_flow,
        "spending_by_category": spending_by_category,
        "transactions_count": len(cleaned_df),
        "categorized_transactions": len(cleaned_df[cleaned_df['Category'] != 'Uncategorized']),
        "uncategorized_transactions": len(cleaned_df[cleaned_df['Category'] == 'Uncategorized']),
    }

    return {
        "cleaned_df_json": cleaned_df_json,
        "summary_statistics": summary_stats_output
    }

if __name__ == '__main__':
    logging.info("Starting example usage of insights_generator...")

    # Sample DataFrame mimicking data after PDF extraction
    data = {
        'Date': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', '2023-01/10', None, '2023-01-07', '2023-01-08'],
        'Transaction Name': ['Salary Deposit Corp X', 'Groceries at Store Y', 'Monthly Rent Payment', 'Transfer to Savings', 'Random Withdrawal', '  Coffee Shop Z  ', 'Unknown Transaction', 'Netflix Subscription', 'Received Payment from Client A'],
        'Amount': [5000, -75.50, -1200, -500, -40, 'abc', 20.0, -15.99, 300], # Include a non-numeric amount, positive and negative values
        'Source_File': ['stmt1.pdf', 'stmt1.pdf', 'stmt1.pdf', 'stmt2.pdf', 'stmt2.pdf', 'stmt2.pdf', 'stmt3.pdf', 'stmt3.pdf', 'stmt3.pdf']
    }
    sample_df = pd.DataFrame(data)

    logging.info(f"Sample DataFrame created with {len(sample_df)} rows.")

    # --- Test Case 1: Standard run ---
    print("\n--- Test Case 1: Standard Run ---")
    insights_results = generate_insights(sample_df.copy()) # Use copy to allow multiple runs with original sample_df

    print("\nSummary Statistics:")
    for key, value in insights_results['summary_statistics'].items():
        print(f"  {key}: {value}")

    print("\nCleaned DataFrame (first 5 records as JSON):")
    # Parsing JSON to pretty print a snippet
    import json
    df_from_json = pd.read_json(insights_results['cleaned_df_json'])
    print(df_from_json.head().to_string())


    # --- Test Case 2: Empty DataFrame ---
    print("\n--- Test Case 2: Empty DataFrame ---")
    empty_df = pd.DataFrame(columns=['Date', 'Transaction Name', 'Amount'])
    insights_empty = generate_insights(empty_df)
    print("\nSummary Statistics (Empty DF):")
    for key, value in insights_empty['summary_statistics'].items():
        print(f"  {key}: {value}")
    print(f"Cleaned DF JSON (Empty DF): {insights_empty['cleaned_df_json']}")

    # --- Test Case 3: DataFrame with missing crucial columns ---
    print("\n--- Test Case 3: Missing 'Amount' column ---")
    df_missing_amount = pd.DataFrame({'Date': ['2023-01-01'], 'Transaction Name': ['Test']})
    insights_missing_amount = generate_insights(df_missing_amount)
    print("\nSummary Statistics (Missing Amount):")
    print(insights_missing_amount['summary_statistics'])


    # --- Test Case 4: Custom Categories ---
    print("\n--- Test Case 4: Custom Categories ---")
    custom_cats = {
        'salary': 'Job Income',
        'coffee': 'Food & Drink',
        'groceries': 'Food & Drink',
        'netflix': 'Entertainment'
    }
    insights_custom_cats = generate_insights(sample_df.copy(), category_keywords=custom_cats)
    print("\nSummary Statistics (Custom Categories):")
    for key, value in insights_custom_cats['summary_statistics'].items():
        print(f"  {key}: {value}")
    print("\nCleaned DataFrame with Custom Categories (first 5 records as JSON):")
    df_custom_from_json = pd.read_json(insights_custom_cats['cleaned_df_json'])
    print(df_custom_from_json.head().to_string())
    print("\nCategories from custom run:")
    print(df_custom_from_json['Category'].value_counts())

    logging.info("Example usage finished.")
