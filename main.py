import os
import sys
from typing import List
import tempfile
import shutil
import json # For parsing cleaned_df_json for the template

from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse # To specify HTML response for the GET endpoint
import uvicorn

# Assuming your processing logic is in pdf_to_dataframe.py
# We'll import the function from there
from pdf_to_dataframe import extract_bank_statements_to_dataframe
from insights_generator import generate_insights
from chart_plotter import plot_spending_by_category, plot_income_vs_expense_trend # Import chart functions
import pandas as pd
import base64 # For encoding chart images
import logging # For logging chart generation errors

app = FastAPI()

# Configure basic logging for the main application if not already configured elsewhere
# This is for messages from main.py itself, like chart generation errors.
# Modules like insights_generator and chart_plotter configure their own logging.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main page with the file upload form."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process_statements/", response_class=HTMLResponse)
async def process_statements(request: Request, files: List[UploadFile] = File(...), **kwargs):
    """
    Receives one or more PDF files, saves them temporarily,
    processes them, generates insights and charts, and returns an HTML page
    displaying these results.

    Args:
        files (List[UploadFile]): A list of PDF files uploaded by the user.
        **kwargs: Additional keyword arguments to pass to the PDF extraction logic
                  (e.g., tabula-py options like `pages`, `area`).

    Returns:
        dict: A dictionary containing:
              - status_message (str): General status of the processing.
              - extraction_info (dict): Details about the PDF extraction phase.
              - insights (dict, optional): Output from the insights generation.
              - charts_data (dict, optional): Base64 encoded PNG images for charts.
    """
    if not files:
        # This case might not be hit if using HTML form with 'required' attribute,
        # but good for API robustness.
        # For HTML response, render results with an error.
        return templates.TemplateResponse("results.html", {
            "request": request,
            "error_message": "No PDF files provided.",
            "status_message": "Error",
            "extraction_info": None, "insights": None, "charts_data": None
        })

    temp_dir = tempfile.mkdtemp()
    temp_file_paths = []

    try:
        for uploaded_file in files:
            if not uploaded_file.filename:
                # Should not happen with FastAPI File(...) but good to check
                continue
            if not uploaded_file.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"Invalid file type: {uploaded_file.filename}. Only PDF files are allowed.")

            temp_file_path = os.path.join(temp_dir, uploaded_file.filename)
            try:
                with open(temp_file_path, "wb") as buffer:
                    shutil.copyfileobj(uploaded_file.file, buffer)
                temp_file_paths.append(temp_file_path)
            finally:
                uploaded_file.file.close() # Ensure the uploaded file stream is closed

        if not temp_file_paths:
            raise HTTPException(status_code=400, detail="No valid PDF files were processed from the upload.")

        # Call the function from your pdf_to_dataframe.py script
        # Pass any additional query parameters (kwargs) from the endpoint to the extraction function
        # Let's rename df to df_extracted for clarity
        df_extracted = extract_bank_statements_to_dataframe(temp_file_paths, **kwargs)

    except HTTPException as http_exc: # Catch FastAPI specific HTTP exceptions
        # For HTML response, render results with an error.
        error_message = http_exc.detail
        status_msg = f"Processing Error: {http_exc.status_code}"
        if temp_dir and os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        return templates.TemplateResponse("results.html", {
            "request": request, "error_message": error_message, "status_message": status_msg,
            "extraction_info": None, "insights": None, "charts_data": None
        })
    except Exception as e:
        logging.error(f"An unexpected error occurred during file processing: {str(e)}", exc_info=True)
        if temp_dir and os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        return templates.TemplateResponse("results.html", {
            "request": request, "error_message": "An unexpected server error occurred.",
            "status_message": "Server Error",
            "extraction_info": None, "insights": None, "charts_data": None
        })
    finally:
        if temp_dir and os.path.exists(temp_dir): # Ensure cleanup happens if not caught by specific error returns
            shutil.rmtree(temp_dir)

    extraction_info = {
        "files_processed_count": len(temp_file_paths),
        "files_processed_names": [os.path.basename(p) for p in temp_file_paths],
        "initial_rows_extracted": 0,
        "initial_columns_extracted": []
    }

    context = {
        "request": request,
        "status_message": "",
        "extraction_info": extraction_info,
        "insights": None,
        "charts_data": None,
        "error_message": None
    }

    if df_extracted.empty:
        extraction_info["notes"] = "No data was extracted from the provided PDF files."
        context["status_message"] = "Processing completed, but no data was extracted. Check PDF files and extraction parameters."
    else:
        extraction_info["initial_rows_extracted"] = len(df_extracted)
        extraction_info["initial_columns_extracted"] = list(df_extracted.columns)

        insights_data = None
        try:
            insights_data = generate_insights(df_extracted)
            # Parse cleaned_df_json for template display, if present
            if insights_data and insights_data.get("cleaned_df_json"):
                try:
                    insights_data["cleaned_transactions_list"] = json.loads(insights_data["cleaned_df_json"])
                except json.JSONDecodeError:
                    logging.error("Failed to parse cleaned_df_json for template display.")
                    insights_data["cleaned_transactions_list"] = [] # or some error indicator
            context["insights"] = insights_data
        except Exception as e:
            logging.error(f"Insights generation failed: {str(e)}", exc_info=True)
            context["status_message"] = f"PDFs processed, but insights generation failed: {str(e)}"
            # extraction_info is already set
            return templates.TemplateResponse("results.html", context)

        # If insights were successfully generated, proceed to generate charts
        charts_data_dict = {
            "spending_by_category_png_base64": None,
            "income_expense_trend_png_base64": None
        }

        if insights_data:
            try:
                spending_data = insights_data.get("summary_statistics", {}).get("spending_by_category")
                if spending_data:
                    chart_bytes = plot_spending_by_category(spending_data)
                    if chart_bytes:
                        charts_data_dict["spending_by_category_png_base64"] = base64.b64encode(chart_bytes).decode('utf-8')
                else:
                    logging.warning("No spending_by_category data for chart.")
            except Exception as e:
                logging.error(f"Failed to generate spending by category chart: {e}", exc_info=True)

            try:
                json_df_data = insights_data.get("cleaned_df_json")
                if json_df_data:
                    chart_bytes = plot_income_vs_expense_trend(json_df_data)
                    if chart_bytes:
                        charts_data_dict["income_expense_trend_png_base64"] = base64.b64encode(chart_bytes).decode('utf-8')
                else:
                    logging.warning("No cleaned_df_json for trend chart.")
            except Exception as e:
                logging.error(f"Failed to generate income vs. expense trend chart: {e}", exc_info=True)

            context["charts_data"] = charts_data_dict
            context["status_message"] = "Successfully processed PDF files, generated insights, and attempted chart generation."

    return templates.TemplateResponse("results.html", context)

if __name__ == "__main__":
    # To run this: uvicorn main:app --reload
    # Ensure you have python-multipart installed: pip install python-multipart
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))