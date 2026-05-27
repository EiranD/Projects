import io
import re

import numpy as np
import pandas as pd
import streamlit as st


EXPECTED_COLUMNS = ["Description", "Hours", "Rate", "Line Total", "VAT Rate"]
TOLERANCE = 0.01
CURRENCY_LABEL = "GBP"
SERVICE_REQUEST_COLUMNS = {
    "date",
    "service area",
    "request type",
    "priority",
    "status",
    "time spent hours",
}
PDF_COLUMN_ALIASES = {
    "Description": ["description", "details", "item", "service", "work description"],
    "Hours": ["hours", "hrs", "time", "quantity", "qty"],
    "Rate": ["rate", "hourly rate", "hour rate", "unit rate", "price per hour"],
    "Line Total": ["line total", "line amount", "amount", "total", "net amount"],
    "VAT Rate": ["vat rate", "vat", "vat percent", "tax rate", "tax percent"],
}


class InvoiceReadWarning(ValueError):
    """Raised when a file can be read, but the invoice table is unclear."""


def read_invoice_file(uploaded_file):
    """Read an uploaded CSV, Excel, or PDF invoice file into a DataFrame."""
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if file_name.endswith(".xlsx"):
        # Use openpyxl for modern Excel workbooks.
        return pd.read_excel(uploaded_file, engine="openpyxl")

    if file_name.endswith(".pdf"):
        return read_pdf_invoice_file(uploaded_file)

    raise ValueError("Please upload a CSV, .xlsx Excel, or PDF file.")


def read_pdf_invoice_file(uploaded_file):
    """Extract invoice table data from a PDF using pdfplumber."""
    try:
        import pdfplumber
    except ModuleNotFoundError as error:
        raise ValueError(
            "PDF support requires pdfplumber. Install it with pip install -r requirements.txt."
        ) from error

    uploaded_file.seek(0)
    extracted_tables = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                table_data = convert_pdf_table_to_dataframe(table)

                if table_data is not None:
                    extracted_tables.append(table_data)

    if not extracted_tables:
        raise InvoiceReadWarning(
            "The PDF table could not be read clearly. Try uploading a CSV or .xlsx file, "
            "or use a PDF with selectable table text."
        )

    combined_data = pd.concat(extracted_tables, ignore_index=True)
    mapped_data = map_pdf_columns_to_expected_columns(combined_data)

    if mapped_data is None:
        raise InvoiceReadWarning(
            "A table was found in the PDF, but its columns could not be mapped clearly "
            "to Description, Hours, Rate, Line Total, and VAT Rate."
        )

    return mapped_data


def clean_pdf_cell(value):
    """Convert a PDF table cell into simple text."""
    if value is None:
        return ""

    return str(value).replace("\n", " ").strip()


def make_unique_column_names(column_names):
    """Give every extracted PDF column a usable and unique name."""
    unique_names = []
    used_names = {}

    for index, column_name in enumerate(column_names, start=1):
        base_name = clean_pdf_cell(column_name) or f"Column {index}"
        used_names[base_name] = used_names.get(base_name, 0) + 1

        if used_names[base_name] == 1:
            unique_names.append(base_name)
        else:
            unique_names.append(f"{base_name} {used_names[base_name]}")

    return unique_names


def normalize_text(value):
    """Normalize header text so similar PDF column names can be matched."""
    text = clean_pdf_cell(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def find_pdf_header_row(rows):
    """Find the row most likely to contain invoice table headers."""
    best_header_index = None
    best_match_count = 0

    # Header rows usually appear near the top of the extracted table.
    for row_index, row in enumerate(rows[:5]):
        column_names = make_unique_column_names(row)
        match_count = len(get_pdf_column_mapping(column_names))

        if match_count > best_match_count:
            best_match_count = match_count
            best_header_index = row_index

    # Require at least three matches so a random row is not treated as a header.
    if best_match_count >= 3:
        return best_header_index

    return None


def convert_pdf_table_to_dataframe(table):
    """Convert one pdfplumber table into a DataFrame when the headers are clear."""
    rows = [
        [clean_pdf_cell(cell) for cell in row]
        for row in table
        if row and any(clean_pdf_cell(cell) for cell in row)
    ]

    if len(rows) < 2:
        return None

    header_index = find_pdf_header_row(rows)

    if header_index is None:
        return None

    column_names = make_unique_column_names(rows[header_index])
    body_rows = rows[header_index + 1 :]
    column_count = len(column_names)
    normalized_rows = []

    for row in body_rows:
        row_values = row[:column_count]
        row_values = row_values + [""] * (column_count - len(row_values))

        if any(row_values):
            normalized_rows.append(row_values)

    if not normalized_rows:
        return None

    return pd.DataFrame(normalized_rows, columns=column_names)


def get_pdf_column_mapping(column_names):
    """Map extracted PDF column names to the expected invoice columns."""
    normalized_columns = [normalize_text(column_name) for column_name in column_names]
    mapping = {}
    used_column_indexes = set()

    for expected_column in EXPECTED_COLUMNS:
        aliases = [normalize_text(expected_column)]
        aliases += [normalize_text(alias) for alias in PDF_COLUMN_ALIASES[expected_column]]

        # First look for an exact match.
        for index, normalized_column in enumerate(normalized_columns):
            if index in used_column_indexes:
                continue

            if normalized_column in aliases:
                mapping[expected_column] = column_names[index]
                used_column_indexes.add(index)
                break

        if expected_column in mapping:
            continue

        # Then allow partial matches such as "Hourly Rate GBP".
        for index, normalized_column in enumerate(normalized_columns):
            if index in used_column_indexes:
                continue

            if expected_column == "Rate" and (
                "vat" in normalized_column or "tax" in normalized_column
            ):
                continue

            if any(alias in normalized_column for alias in aliases):
                mapping[expected_column] = column_names[index]
                used_column_indexes.add(index)
                break

    return mapping


def map_pdf_columns_to_expected_columns(dataframe):
    """Return the PDF table with the standard invoice column names."""
    column_mapping = get_pdf_column_mapping(list(dataframe.columns))

    if any(column not in column_mapping for column in EXPECTED_COLUMNS):
        return None

    mapped_data = pd.DataFrame()

    for expected_column in EXPECTED_COLUMNS:
        mapped_data[expected_column] = dataframe[column_mapping[expected_column]]

    # Remove rows that are completely empty after mapping.
    mapped_data = mapped_data.replace("", np.nan).dropna(how="all").fillna("")

    if mapped_data.empty:
        return None

    return mapped_data


def map_uploaded_columns_to_expected_columns(dataframe):
    """Map uploaded column names to the expected invoice column names when possible."""
    column_mapping = get_pdf_column_mapping(list(dataframe.columns))
    mapped_data = dataframe.copy()

    for expected_column, uploaded_column in column_mapping.items():
        if expected_column != uploaded_column:
            mapped_data = mapped_data.rename(columns={uploaded_column: expected_column})

    return mapped_data


def get_missing_invoice_columns(dataframe):
    """Return invoice columns that are not present in the uploaded file."""
    return [column for column in EXPECTED_COLUMNS if column not in dataframe.columns]


def looks_like_service_request_file(column_names):
    """Check whether the uploaded columns look like the other Streamlit app's data."""
    normalized_columns = {normalize_text(column_name) for column_name in column_names}
    matching_columns = normalized_columns.intersection(SERVICE_REQUEST_COLUMNS)

    return len(matching_columns) >= 3


def show_column_warning(uploaded_columns, missing_columns):
    """Show a helpful warning when the uploaded file is not an invoice file."""
    st.error(
        "This file does not have the invoice columns needed for validation."
    )

    if looks_like_service_request_file(uploaded_columns):
        st.warning(
            "This looks like the Service Request Insight Tool sample file. "
            "For this app, upload an invoice file such as `sample_invoice.csv` "
            "or `sample_invoice.xlsx`."
        )

    st.write("Missing invoice columns:")
    st.write(", ".join(missing_columns))

    with st.expander("Show detected columns"):
        for column in uploaded_columns:
            st.write(f"- {column}")


def clean_money_or_number(column):
    """Convert values such as '1,000', '$100', or '100.00' into numbers."""
    cleaned_column = column.astype(str).str.upper().str.strip()

    # Remove common currency text and symbols before converting to numbers.
    values_to_remove = [",", "\u00a3", "$", "\u20ac", "GBP", "USD", "EUR"]

    for value in values_to_remove:
        cleaned_column = cleaned_column.str.replace(value, "", regex=False)

    return pd.to_numeric(cleaned_column, errors="coerce")


def clean_vat_rate(column):
    """Convert VAT rates such as '20%' or '0.2' into decimal rates."""
    cleaned_column = column.astype(str).str.replace("%", "", regex=False).str.strip()
    numeric_rate = pd.to_numeric(cleaned_column, errors="coerce")

    # Treat values greater than 1 as percentages: 20 becomes 0.20.
    return numeric_rate.where(numeric_rate <= 1, numeric_rate / 100)


def check_invoice(invoice_data):
    """Add validation columns and return the checked invoice data."""
    checked_data = invoice_data.copy()

    hours = clean_money_or_number(checked_data["Hours"])
    rate = clean_money_or_number(checked_data["Rate"])
    actual_line_total = clean_money_or_number(checked_data["Line Total"])
    vat_rate = clean_vat_rate(checked_data["VAT Rate"])

    checked_data["Expected Line Total"] = (hours * rate).round(2)
    checked_data["Difference"] = (
        checked_data["Expected Line Total"] - actual_line_total
    ).round(2)
    checked_data["VAT Amount"] = (actual_line_total * vat_rate).round(2)
    checked_data["Final Line Total"] = (
        actual_line_total + checked_data["VAT Amount"]
    ).round(2)

    numeric_values_are_present = (
        hours.notna()
        & rate.notna()
        & actual_line_total.notna()
        & vat_rate.notna()
    )
    difference_is_ok = checked_data["Difference"].abs() <= TOLERANCE

    checked_data["Check Status"] = np.where(
        numeric_values_are_present & difference_is_ok,
        "Passed",
        "Needs Review",
    )

    return checked_data


def format_currency(amount):
    """Format money amounts consistently for the summary metrics."""
    return f"{CURRENCY_LABEL} {amount:,.2f}"


def convert_dataframe_to_csv(dataframe):
    """Convert a DataFrame into CSV bytes for the download button."""
    csv_buffer = io.StringIO()
    dataframe.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")


def get_sample_invoice_csv():
    """Return a small invoice sample that users can download from the app."""
    sample_data = pd.DataFrame(
        [
            ["Consulting services", 10, 100, 1000, "20%"],
            ["Design work", 5, 80, 400, "20%"],
            ["Support package", 3, 75, 220, "20%"],
            ["Training session", 2.5, 120, 300, "0%"],
            ["Report writing", 4, 90, 360, "5%"],
        ],
        columns=EXPECTED_COLUMNS,
    )

    return convert_dataframe_to_csv(sample_data)


def calculate_summary_values(checked_data):
    """Calculate the values used by the status and summary sections."""
    passed_checks = (checked_data["Check Status"] == "Passed").sum()
    failed_checks = (checked_data["Check Status"] == "Needs Review").sum()
    total_difference = checked_data["Difference"].abs().sum()

    subtotal = clean_money_or_number(checked_data["Line Total"]).sum()
    vat_amount = checked_data["VAT Amount"].sum()
    final_total = subtotal + vat_amount

    return {
        "invoice_lines": len(checked_data),
        "passed_checks": int(passed_checks),
        "failed_checks": int(failed_checks),
        "total_difference": float(total_difference),
        "subtotal": float(subtotal),
        "vat_amount": float(vat_amount),
        "final_total": float(final_total),
        "invoice_passed": int(failed_checks) == 0,
    }


def show_top_status(summary_values):
    """Show the main pass/fail result near the top of the page."""
    if summary_values["invoice_passed"]:
        status_message = "Invoice Passed"
        status_detail = "All invoice lines matched the expected Hours x Rate total."
        st.success(f"**{status_message}**")
    else:
        status_message = "Invoice Needs Review"
        status_detail = (
            "One or more invoice lines has a difference or an invalid numeric value."
        )
        st.error(f"**{status_message}**")

    with st.container(border=True):
        status_columns = st.columns([2, 1, 1])

        with status_columns[0]:
            st.subheader(status_message)
            st.write(status_detail)

        status_columns[1].metric("Failed Checks", summary_values["failed_checks"])
        status_columns[2].metric(
            "Total Difference",
            format_currency(summary_values["total_difference"]),
        )


def show_summary_metrics(summary_values):
    """Show validation metrics and invoice totals."""
    metric_columns = st.columns(4)
    metric_columns[0].metric("Invoice Lines", summary_values["invoice_lines"])
    metric_columns[1].metric("Passed Checks", summary_values["passed_checks"])
    metric_columns[2].metric("Failed Checks", summary_values["failed_checks"])
    metric_columns[3].metric(
        "Total Difference",
        format_currency(summary_values["total_difference"]),
    )

    total_columns = st.columns(3)
    total_columns[0].metric("Subtotal", format_currency(summary_values["subtotal"]))
    total_columns[1].metric(
        "VAT Amount",
        format_currency(summary_values["vat_amount"]),
    )
    total_columns[2].metric(
        "Final Total",
        format_currency(summary_values["final_total"]),
    )


def show_sidebar_instructions():
    """Show simple instructions without crowding the main workspace."""
    with st.sidebar:
        st.header("How to Use")
        st.write("1. Prepare a CSV, .xlsx Excel, or PDF invoice file.")
        st.write("2. Make sure it includes the required columns.")
        st.write("3. Upload the file and review the status summary.")
        st.write("4. Download the checked results as a CSV.")

        st.header("Required Columns")
        for column in EXPECTED_COLUMNS:
            st.write(f"- {column}")


def main():
    st.set_page_config(
        page_title="Invoice Validation Assistant",
        page_icon=None,
        layout="wide",
    )

    st.title("Invoice Validation Assistant")
    st.caption(
        "Check invoice line totals, VAT, and validation status from CSV, Excel, or PDF files."
    )

    show_sidebar_instructions()

    st.header("1. Upload Invoice")
    with st.container(border=True):
        st.write("Accepted file types: CSV, XLSX, or PDF.")
        st.write("PDF uploads work best when the invoice has a clear selectable table.")
        st.write("Need a test file? Download the invoice sample below.")

        st.download_button(
            label="Download Sample Invoice CSV",
            data=get_sample_invoice_csv(),
            file_name="sample_invoice.csv",
            mime="text/csv",
        )

        uploaded_file = st.file_uploader(
            "Choose an invoice file",
            type=["csv", "xlsx", "pdf"],
        )

    if uploaded_file is None:
        st.info("Upload a file to begin.")
        return

    try:
        invoice_data = read_invoice_file(uploaded_file)
    except InvoiceReadWarning as warning:
        st.warning(str(warning))
        return
    except Exception as error:
        st.error(f"Could not read the uploaded file: {error}")
        return

    # Remove accidental spaces from column names, such as " Hours ".
    invoice_data.columns = invoice_data.columns.str.strip()
    uploaded_columns = list(invoice_data.columns)
    invoice_data = map_uploaded_columns_to_expected_columns(invoice_data)

    missing_columns = get_missing_invoice_columns(invoice_data)

    if missing_columns:
        show_column_warning(uploaded_columns, missing_columns)
        return

    invoice_data = invoice_data[EXPECTED_COLUMNS]
    checked_data = check_invoice(invoice_data)
    summary_values = calculate_summary_values(checked_data)

    st.header("2. Invoice Status")
    show_top_status(summary_values)

    st.header("3. Summary")
    show_summary_metrics(summary_values)

    st.header("4. Review Details")
    results_tab, original_tab = st.tabs(["Checked Results", "Uploaded Data"])

    with results_tab:
        st.write(
            "Rows marked `Needs Review` should be checked before approving the invoice."
        )
        st.dataframe(checked_data, use_container_width=True)

    with original_tab:
        st.write("This is the invoice data exactly as read from the uploaded file.")
        st.dataframe(invoice_data, use_container_width=True)

    st.download_button(
        label="Download Checked Results as CSV",
        data=convert_dataframe_to_csv(checked_data),
        file_name="checked_invoice_results.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
