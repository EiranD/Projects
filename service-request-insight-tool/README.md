# Service Request Insight Tool

A beginner-friendly Streamlit app for exploring council service request data from a CSV file.

## Expected CSV columns

The uploaded CSV should include these columns:

- Date
- Service Area
- Request Type
- Priority
- Status
- Time Spent Hours

## How to run the app

### Option 1: Double-click the runner

After installing the required packages, you can double-click:

```text
run_service_request_app.bat
```

### Option 2: Run from the terminal

1. Open a terminal in this folder.
2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

3. Start the Streamlit app:

```bash
streamlit run app.py
```

4. Open the local URL shown in the terminal.
5. Upload `sample_service_requests.csv` to test the app.

## GitHub setup note

This project can be uploaded in either of these clean ways.

If you want a separate GitHub repo just for this app, use this folder as the repository root:

```text
Service Request Insight Tool
```

Do not upload or initialise Git from the parent `Codex Projects` folder unless you want one large repo containing all of your projects.

A clean GitHub repo for this app should show files like this at the top level:

```text
app.py
README.md
requirements.txt
run_service_request_app.bat
sample_service_requests.csv
```

If you use one larger GitHub repo for several apps, keep this app in its own folder:

```text
service-request-insight-tool/
```

This keeps it separate from other apps, such as an invoice validation app.

## What the app shows

- Uploaded request data in a table
- Summary metrics for total, open, and closed requests
- Average time spent
- Most common request type
- Charts for service area, status, request type, and requests over time
- Filters for service area, status, and priority
- Improvement opportunities based on the top 3 request types
