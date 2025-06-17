import os
import sys
from typing import List

from fastapi import FastAPI, HTTPException
import uvicorn

# Assuming your processing logic is in pdf_to_dataframe.py
# We'll import the function from there
from pdf_to_dataframe import extract_bank_statements_to_dataframe

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Site is working!"}

@app.post("/process_statements/")
async def process_statements(pdf_paths: List[str]):
    """
    Receives a list of absolute PDF file paths, processes them using the bank statement
    extraction logic, and returns a success message.

    Args:
        pdf_paths (List[str]): A list of strings, where each string is the
                               absolute path to a PDF bank statement file.

    Returns:
        dict: A dictionary with a message indicating the status of the processing.
    """
    if not pdf_paths:
        raise HTTPException(status_code=400, detail="No PDF file paths provided.")

    # Validate that paths are absolute (optional but good practice)
    for path in pdf_paths:
        if not os.path.isabs(path):
            raise HTTPException(status_code=400, detail=f"Provided path is not absolute: {path}")
        if not os.path.exists(path):
             raise HTTPException(status_code=404, detail=f"File not found at absolute path: {path}")

    # Call the function from your pdf_to_dataframe.py script
    df = extract_bank_statements_to_dataframe(pdf_paths)

    if df.empty:
        return {"message": "Processing completed, but no data was extracted from the provided files. Please check the absolute file paths and content."}
    else:
        # In a real application, you might want to save the DataFrame
        # or perform further analysis here. For now, we'll just indicate
        # success and some info about the extracted data.
        return {
            "message": "Successfully processed PDF files.",
            "rows_extracted": len(df),
            "columns": list(df.columns)
        }

if __name__ == "__main__":
    # To run this: uvicorn main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)