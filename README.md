# PDF Financial Analyzer

## Overview

The PDF Financial Analyzer is a web application designed to help users gain insights into their finances by processing PDF bank statements. It extracts transaction data, cleans it, categorizes transactions, generates summary statistics, and visualizes financial trends through charts. Users can upload their PDF statements via a simple web interface and view the analysis results directly in their browser.

## Features

*   **PDF Parsing**: Extracts tabular data from bank statement PDF files.
*   **File Upload via Web Interface**: User-friendly interface to upload multiple PDF files.
*   **Automated Data Cleaning**: Handles missing values, standardizes date formats, and cleans transaction names.
*   **Transaction Categorization**: Basic keyword-based categorization of transactions into Income, Expenses, Transfers, etc.
*   **Summary Statistics**: Calculates total income, total expenses, net financial flow, and spending per category.
*   **Chart Generation**:
    *   Bar chart for spending by category.
    *   Line chart for monthly income vs. expense trends.
*   **Web UI for Interaction**: Provides a simple web page for uploading files and viewing analysis results, including charts.

## Requirements & Dependencies

*   **Python 3.7+**
*   **Java Development Kit (JDK)**: `tabula-py`, which is used for PDF parsing, requires a working Java installation. Ensure the JDK is installed and the `java` command is available in your system's PATH.
*   **Python Packages**: All required Python packages are listed in `requirements.txt`. Key packages include:
    *   FastAPI (web framework)
    *   Uvicorn (ASGI server)
    *   Pandas (data manipulation)
    *   Tabula-py (PDF table extraction)
    *   Matplotlib (charting)
    *   Jinja2 (templating)
    *   Python-multipart (FastAPI file uploads)

## Setup and Installation

1.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install Java Development Kit (JDK)**:
    *   Download and install the JDK (e.g., from Oracle, OpenJDK).
    *   Verify the installation by running `java -version` in your terminal. Make sure `java` is in your system's PATH.

3.  **Install Python Dependencies**:
    It's recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
    Then install the packages:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1.  **Start the Development Server**:
    From the project root directory, run:
    ```bash
    uvicorn main:app --reload
    ```
    Alternatively, if `devserver.sh` is configured to do the same:
    ```bash
    ./devserver.sh
    ```

2.  **Access the Application**:
    Open your web browser and navigate to:
    [http://127.0.0.1:8000](http://127.0.0.1:8000)

## How to Use

1.  Navigate to the application URL (default: `http://127.0.0.1:8000`).
2.  You will see an upload form. Click "Choose PDF files" (or similar, depending on your browser) to select one or more PDF bank statements from your computer.
3.  Click the "Analyze Statements" button.
4.  The application will process the files. Once done, a results page will be displayed showing:
    *   Extraction information (files processed, rows extracted).
    *   Summary financial statistics.
    *   Charts visualizing spending by category and income/expense trends.
    *   A sample of the cleaned transaction data.
5.  You can then navigate back to upload more files if needed.

## Project Structure

*   `main.py`: The main FastAPI application file. Handles API routing, request processing, and serves HTML templates.
*   `pdf_to_dataframe.py`: Module responsible for extracting data from PDF files using `tabula-py`.
*   `insights_generator.py`: Module for cleaning extracted data, categorizing transactions, and calculating summary statistics.
*   `chart_plotter.py`: Module for generating charts (bar chart for spending, line chart for trends) using Matplotlib.
*   `templates/`: Directory containing HTML templates (`index.html` for upload, `results.html` for displaying results).
*   `requirements.txt`: Lists all Python dependencies.
*   `README.md`: This file.

## Contributing (Optional - Placeholder)

Contributions are welcome! Please fork the repository and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License (Optional - Placeholder)

This project is licensed under the MIT License - see the LICENSE.md file for details (if one exists).