# Invoice Validation Assistant

A beginner-friendly Streamlit app for checking invoice line totals.

The app lets you upload a CSV, `.xlsx` Excel, or PDF invoice file, checks whether each line total matches `Hours * Rate`, calculates VAT totals, and lets you download the checked results as a CSV.

## Expected Columns

Your invoice file should include these columns:

- `Description`
- `Hours`
- `Rate`
- `Line Total`
- `VAT Rate`

`VAT Rate` can be entered as a percentage such as `20%` or as a decimal such as `0.2`.

Excel `.xlsx` uploads are read with `openpyxl`, which is included in `requirements.txt`.

PDF uploads are read with `pdfplumber`. PDF table extraction works best when the PDF contains selectable table text. If the table cannot be read or mapped clearly, the app shows a warning instead of guessing.

## How to Run

1. Open a terminal in this folder.
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Start the Streamlit app:

```bash
python -m streamlit run app.py --server.port 8502 --server.address 127.0.0.1
```

The app will open at:

```text
http://localhost:8502
```

This keeps it separate from the Service Request Insight Tool, which may already be running on `http://localhost:8501`.

You can also double-click `run_invoice_app.bat` on Windows to start this app on port `8502`.

4. Upload an invoice file with the expected columns.

## What the App Checks

For each invoice line, the app:

- Calculates `Expected Line Total` using `Hours * Rate`
- Compares it with the uploaded `Line Total`
- Adds a `Difference` column
- Marks the row as `Passed` or `Needs Review`
- Calculates VAT and final line totals

The invoice status is:

- `Invoice Passed` when all rows match
- `Invoice Needs Review` when any row has a difference or invalid numeric value

## Files

- `app.py` - Streamlit app
- `requirements.txt` - Python dependencies
- `run_invoice_app.bat` - Windows launcher for this separate app
- `README.md` - setup and usage instructions
