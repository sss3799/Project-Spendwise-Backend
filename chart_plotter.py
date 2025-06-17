import pandas as pd
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend to prevent issues in environments without GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def plot_spending_by_category(spending_by_category: dict) -> bytes:
    """
    Generates a bar chart for spending by category.

    Args:
        spending_by_category (dict): A dictionary where keys are category names (str)
                                     and values are amounts (float/int).
                                     Example: {'Expenses': 500, 'Transfers': 200, 'Uncategorized': 50}
                                     (as produced by insights_generator, these are positive values)

    Returns:
        bytes: PNG image data of the generated chart, or None if an error occurs.
    """
    logging.info(f"Generating spending by category chart for: {spending_by_category}")
    if not spending_by_category or not isinstance(spending_by_category, dict):
        logging.warning("spending_by_category data is empty or invalid. Cannot generate chart.")
        return None

    # Filter out zero or negative values as they don't make sense in a spending bar chart
    # (insights_generator now produces positive values for spending categories)
    positive_spending = {cat: val for cat, val in spending_by_category.items() if val > 0}
    if not positive_spending:
        logging.warning("No positive spending data available. Cannot generate chart.")
        return None

    categories = list(positive_spending.keys())
    amounts = list(positive_spending.values())

    fig, ax = plt.subplots(figsize=(10, 7)) # Adjusted figure size for better readability

    try:
        bars = ax.bar(categories, amounts, color=['skyblue', 'lightcoral', 'lightgreen', 'gold', 'orchid', 'deepskyblue'])

        # Add value labels on top of bars
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.01 * max(amounts), f'{yval:,.2f}', ha='center', va='bottom', fontsize=9)

        ax.set_ylabel('Amount Spent')
        ax.set_xlabel('Category')
        ax.set_title('Spending by Category')

        # Rotate x-axis labels for better readability if many categories or long names
        plt.xticks(rotation=45, ha="right")

        ax.grid(axis='y', linestyle='--', alpha=0.7) # Add a light grid for the y-axis

        plt.tight_layout() # Adjust layout to prevent labels from being cut off

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_bytes = buf.getvalue()
        logging.info("Spending by category chart generated successfully.")
        return image_bytes
    except Exception as e:
        logging.error(f"Error generating spending by category chart: {e}", exc_info=True)
        return None
    finally:
        if 'fig' in locals(): # Ensure fig was created before trying to close
            plt.close(fig) # Close the figure to free memory


def plot_income_vs_expense_trend(cleaned_df_json: str) -> bytes:
    """
    Generates a line chart showing monthly income vs. expenses.

    Args:
        cleaned_df_json (str): JSON string representation of the cleaned DataFrame.
                               Expected columns: 'Date', 'Amount', 'Category'.
                               'Amount' should be absolute values.

    Returns:
        bytes: PNG image data of the generated chart, or None if an error occurs.
    """
    logging.info("Generating income vs. expense trend chart.")
    if not cleaned_df_json:
        logging.warning("cleaned_df_json is empty. Cannot generate trend chart.")
        return None

    try:
        df = pd.read_json(cleaned_df_json, orient='records')
        if df.empty:
            logging.warning("DataFrame from cleaned_df_json is empty.")
            return None

        if 'Date' not in df.columns or 'Amount' not in df.columns or 'Category' not in df.columns:
            logging.warning("Required columns ('Date', 'Amount', 'Category') not all present in DataFrame.")
            return None

        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']) # Remove rows where date could not be parsed

        if df.empty:
            logging.warning("DataFrame is empty after date conversion or dropping NaT dates.")
            return None

        # Filter for 'Income' and 'Expenses' categories
        # Amounts are absolute. For expenses, we'll sum them as positive.
        # For net flow calculation, expenses are subtracted.
        income_df = df[df['Category'] == 'Income'].copy()
        expenses_df = df[df['Category'] == 'Expenses'].copy()

        # It's possible one or both are empty, handle this before resampling
        if income_df.empty and expenses_df.empty:
            logging.warning("No 'Income' or 'Expenses' transactions found for trend plot.")
            return None

        # Resample data by month
        # Use a common date index for merging later if needed, though unstack handles it well
        monthly_data_list = []
        if not income_df.empty:
            monthly_income = income_df.set_index('Date').resample('M')['Amount'].sum().rename('Income')
            monthly_data_list.append(monthly_income)
        if not expenses_df.empty:
            monthly_expenses = expenses_df.set_index('Date').resample('M')['Amount'].sum().rename('Expenses')
            monthly_data_list.append(monthly_expenses)

        if not monthly_data_list: # Should be caught by earlier check, but as a safeguard
            logging.warning("No data to plot after resampling.")
            return None

        monthly_summary = pd.concat(monthly_data_list, axis=1).fillna(0)

        if monthly_summary.empty:
            logging.warning("Monthly summary is empty after processing income/expenses.")
            return None


        fig, ax = plt.subplots(figsize=(12, 7)) # Adjusted figure size

        if 'Income' in monthly_summary.columns and not monthly_summary['Income'].empty:
            ax.plot(monthly_summary.index, monthly_summary['Income'], label='Total Income', marker='o', linestyle='-', color='green')
        if 'Expenses' in monthly_summary.columns and not monthly_summary['Expenses'].empty:
            ax.plot(monthly_summary.index, monthly_summary['Expenses'], label='Total Expenses', marker='x', linestyle='--', color='red')

        ax.set_title('Monthly Income vs. Expenses Trend')
        ax.set_xlabel('Month')
        ax.set_ylabel('Amount')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)

        # Format x-axis to show month and year
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45, ha="right")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_bytes = buf.getvalue()
        logging.info("Income vs. expense trend chart generated successfully.")
        return image_bytes
    except Exception as e:
        logging.error(f"Error generating income vs. expense trend chart: {e}", exc_info=True)
        return None
    finally:
        if 'fig' in locals():
            plt.close(fig)


if __name__ == '__main__':
    logging.info("Starting example usage of chart_plotter...")

    # 1. Example for plot_spending_by_category
    sample_spending_data = {
        'Expenses': 1331.49, # From previous example logic
        'Transfers': 500.00,
        'Uncategorized': 20.00,
        'Payments': 0 # Example of a category that might exist but have 0 spending
    }
    spending_chart_bytes = plot_spending_by_category(sample_spending_data)
    if spending_chart_bytes:
        with open('spending_by_category_chart.png', 'wb') as f:
            f.write(spending_chart_bytes)
        logging.info("Saved plot_spending_by_category example to spending_by_category_chart.png")
    else:
        logging.warning("Failed to generate spending_by_category_chart.")

    # Test with empty or invalid data for spending plot
    plot_spending_by_category({}) # Empty dict
    plot_spending_by_category({'Food': -100}) # No positive spending


    # 2. Example for plot_income_vs_expense_trend
    # Create a sample cleaned_df_json string
    sample_transactions_for_trend = [
        {'Date': '2023-01-01', 'Transaction Name': 'Salary Jan', 'Amount': 5000, 'Category': 'Income'},
        {'Date': '2023-01-15', 'Transaction Name': 'Groceries Jan', 'Amount': 150, 'Category': 'Expenses'},
        {'Date': '2023-01-20', 'Transaction Name': 'Rent Jan', 'Amount': 1200, 'Category': 'Expenses'},
        {'Date': '2023-02-01', 'Transaction Name': 'Salary Feb', 'Amount': 5100, 'Category': 'Income'},
        {'Date': '2023-02-10', 'Transaction Name': 'Utilities Feb', 'Amount': 100, 'Category': 'Expenses'},
        {'Date': '2023-02-18', 'Transaction Name': 'Groceries Feb', 'Amount': 130, 'Category': 'Expenses'},
        {'Date': '2023-03-01', 'Transaction Name': 'Salary Mar', 'Amount': 5050, 'Category': 'Income'},
        {'Date': '2023-03-05', 'Transaction Name': 'Travel Mar', 'Amount': 300, 'Category': 'Expenses'},
        {'Date': '2023-03-20', 'Transaction Name': 'Rent Mar', 'Amount': 1200, 'Category': 'Expenses'},
        {'Date': '2023-01-05', 'Transaction Name': 'Consulting Gig', 'Amount': 300, 'Category': 'Income'}, # Another Jan income
        {'Date': '2023-02-08', 'Transaction Name': 'Freelance Feb', 'Amount': 400, 'Category': 'Income'}, # Another Feb income
        {'Date': '2023-03-10', 'Transaction Name': 'Side Project Mar', 'Amount': 250, 'Category': 'Income'}, # Another Mar income
        # Add a month with only expenses
        {'Date': '2023-04-10', 'Transaction Name': 'Big Purchase Apr', 'Amount': 500, 'Category': 'Expenses'},
        {'Date': '2023-04-15', 'Transaction Name': 'Bills Apr', 'Amount': 200, 'Category': 'Expenses'},
         # Add a month with only income
        {'Date': '2023-05-05', 'Transaction Name': 'Bonus May', 'Amount': 1000, 'Category': 'Income'},
    ]
    sample_cleaned_df_json = json.dumps(sample_transactions_for_trend)

    trend_chart_bytes = plot_income_vs_expense_trend(sample_cleaned_df_json)
    if trend_chart_bytes:
        with open('income_vs_expense_trend_chart.png', 'wb') as f:
            f.write(trend_chart_bytes)
        logging.info("Saved plot_income_vs_expense_trend example to income_vs_expense_trend_chart.png")
    else:
        logging.warning("Failed to generate income_vs_expense_trend_chart.")

    # Test with empty or invalid data for trend plot
    plot_income_vs_expense_trend("") # Empty JSON string
    plot_income_vs_expense_trend(json.dumps([{'Date': '2023-01-01', 'Amount': 100, 'Category': 'Other'}])) # No income/expense

    logging.info("Example usage of chart_plotter finished.")
