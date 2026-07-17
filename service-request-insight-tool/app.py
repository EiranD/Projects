import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# Page setup
# ------------------------------------------------------------
# This controls the browser tab title and gives the app more horizontal space.
st.set_page_config(
    page_title="Service Request Insight Tool",
    layout="wide",
)


# The app expects uploaded CSV files to use these exact column names.
EXPECTED_COLUMNS = [
    "Date",
    "Service Area",
    "Request Type",
    "Priority",
    "Status",
    "Time Spent Hours",
]


def load_service_request_data(uploaded_csv_file):
    """Read the uploaded CSV and prepare it for analysis."""
    service_requests_df = pd.read_csv(uploaded_csv_file)

    # Remove extra spaces from column names. This helps if a CSV has " Date "
    # instead of "Date".
    service_requests_df.columns = service_requests_df.columns.str.strip()

    # Check for missing columns before trying to build metrics or charts.
    missing_columns = [
        column for column in EXPECTED_COLUMNS if column not in service_requests_df.columns
    ]
    if missing_columns:
        return service_requests_df, missing_columns

    # Convert the Date column into real dates so requests can be grouped over time.
    # Invalid dates become blank values instead of crashing the app.
    service_requests_df["Date"] = pd.to_datetime(
        service_requests_df["Date"],
        errors="coerce",
    )

    # Convert time spent into numbers so averages can be calculated.
    service_requests_df["Time Spent Hours"] = pd.to_numeric(
        service_requests_df["Time Spent Hours"],
        errors="coerce",
    )

    return service_requests_df, []


def show_page_header():
    """Show the app title and a short explanation."""
    st.title("Service Request Insight Tool")
    st.caption(
        "Upload council service request data, filter it, and spot patterns that "
        "could guide service improvement."
    )


def filter_service_requests(service_requests_df):
    """Add sidebar filters and return only the rows selected by the user."""
    st.sidebar.title("Filters")
    st.sidebar.caption("Use these filters to focus the dashboard.")

    # These lists become the options in each filter.
    available_service_areas = sorted(service_requests_df["Service Area"].dropna().unique())
    available_statuses = sorted(service_requests_df["Status"].dropna().unique())
    available_priorities = sorted(service_requests_df["Priority"].dropna().unique())

    selected_service_areas = st.sidebar.multiselect(
        "Service area",
        options=available_service_areas,
        default=available_service_areas,
    )
    selected_statuses = st.sidebar.multiselect(
        "Status",
        options=available_statuses,
        default=available_statuses,
    )
    selected_priorities = st.sidebar.multiselect(
        "Priority",
        options=available_priorities,
        default=available_priorities,
    )

    # Keep rows where all three filter choices match.
    filtered_service_requests_df = service_requests_df[
        service_requests_df["Service Area"].isin(selected_service_areas)
        & service_requests_df["Status"].isin(selected_statuses)
        & service_requests_df["Priority"].isin(selected_priorities)
    ]

    return filtered_service_requests_df


def get_most_common_request_type(service_requests_df):
    """Return the most frequent request type, or a friendly fallback message."""
    if service_requests_df.empty:
        return "No data"

    return service_requests_df["Request Type"].mode().iloc[0]


def format_average_hours(average_hours):
    """Format average hours and handle cases where no average can be calculated."""
    if pd.isna(average_hours):
        return "No data"

    return f"{average_hours:.1f} hrs"


def format_percentage(count, total):
    """Convert a count into a percentage string."""
    if total == 0:
        return "0%"

    percentage = count / total
    return f"{percentage:.0%}"


def get_top_value_and_count(service_requests_df, column_name):
    """Find the most common value in a column and how often it appears."""
    value_counts = service_requests_df[column_name].value_counts()

    if value_counts.empty:
        return "No data", 0

    top_value = value_counts.index[0]
    top_count = value_counts.iloc[0]

    return top_value, top_count


def get_date_range_text(service_requests_df):
    """Create a short date range description for the executive summary."""
    valid_dates = service_requests_df["Date"].dropna()

    if valid_dates.empty:
        return "with no valid request dates"

    earliest_date = valid_dates.min().strftime("%d %b %Y")
    latest_date = valid_dates.max().strftime("%d %b %Y")

    if earliest_date == latest_date:
        return f"on {earliest_date}"

    return f"between {earliest_date} and {latest_date}"


def show_executive_summary(service_requests_df):
    """Explain the main findings in plain English."""
    total_requests = len(service_requests_df)
    normalised_status = service_requests_df["Status"].str.lower()
    open_requests = normalised_status.eq("open").sum()
    closed_requests = normalised_status.eq("closed").sum()
    average_time_spent = service_requests_df["Time Spent Hours"].mean()

    busiest_service_area, busiest_area_count = get_top_value_and_count(
        service_requests_df,
        "Service Area",
    )
    most_common_request_type, request_type_count = get_top_value_and_count(
        service_requests_df,
        "Request Type",
    )
    date_range_text = get_date_range_text(service_requests_df)

    st.subheader("Executive Summary")

    # A bordered container makes the summary stand out from the charts and table.
    with st.container(border=True):
        st.write(
            f"This view contains **{total_requests:,}** service requests "
            f"{date_range_text}."
        )
        st.write(
            f"**{busiest_service_area}** is the busiest service area, with "
            f"**{busiest_area_count:,}** requests."
        )
        st.write(
            f"The most common request type is **{most_common_request_type}**, "
            f"appearing **{request_type_count:,}** times."
        )
        st.write(
            f"**{open_requests:,}** requests are open "
            f"({format_percentage(open_requests, total_requests)}), and "
            f"**{closed_requests:,}** are closed "
            f"({format_percentage(closed_requests, total_requests)})."
        )
        st.write(
            "The average time spent per request is "
            f"**{format_average_hours(average_time_spent)}**."
        )


def show_summary_metrics(service_requests_df):
    """Show the headline numbers for the filtered requests."""
    total_requests = len(service_requests_df)
    normalised_status = service_requests_df["Status"].str.lower()
    open_requests = normalised_status.eq("open").sum()
    closed_requests = normalised_status.eq("closed").sum()
    average_time_spent = service_requests_df["Time Spent Hours"].mean()
    most_common_request_type = get_most_common_request_type(service_requests_df)

    st.subheader("Summary")
    metric_columns = st.columns(5, gap="small")
    metric_columns[0].metric("Total requests", f"{total_requests:,}")
    metric_columns[1].metric("Open requests", f"{open_requests:,}")
    metric_columns[2].metric("Closed requests", f"{closed_requests:,}")
    metric_columns[3].metric("Average time spent", format_average_hours(average_time_spent))
    metric_columns[4].metric("Most common type", most_common_request_type)


def show_chart(chart_title, chart_data, chart_type="bar"):
    """Show one chart with a consistent heading and empty-data message."""
    st.markdown(f"#### {chart_title}")

    if chart_data.empty:
        st.info("No data to show for the current filters.")
        return

    if chart_type == "line":
        st.line_chart(chart_data, use_container_width=True)
    else:
        st.bar_chart(chart_data, use_container_width=True)


def show_charts(service_requests_df):
    """Create charts that summarise the filtered request data."""
    st.subheader("Charts")

    first_chart_column, second_chart_column = st.columns(2, gap="large")

    with first_chart_column:
        requests_by_service_area = service_requests_df["Service Area"].value_counts()
        show_chart("Requests by Service Area", requests_by_service_area)

        top_10_request_types = service_requests_df["Request Type"].value_counts().head(10)
        show_chart("Top 10 Request Types", top_10_request_types)

    with second_chart_column:
        requests_by_status = service_requests_df["Status"].value_counts()
        show_chart("Requests by Status", requests_by_status)

        # Drop blank dates before grouping requests by day.
        dated_requests = service_requests_df.dropna(subset=["Date"])
        requests_over_time = dated_requests.groupby(dated_requests["Date"].dt.date).size()
        requests_over_time = requests_over_time.rename("Requests")
        show_chart("Requests Over Time", requests_over_time, chart_type="line")


def show_improvement_opportunities(service_requests_df):
    """Highlight common request types that may be worth improving."""
    st.subheader("Improvement Opportunities")

    top_three_request_types = service_requests_df["Request Type"].value_counts().head(3)

    if top_three_request_types.empty:
        st.info("No request types are available for the current filters.")
        return

    st.write("These high-volume request types may be useful places to start:")

    # Display the three opportunities side by side so this section is easy to scan.
    opportunity_columns = st.columns(len(top_three_request_types), gap="medium")

    for opportunity_column, (request_type, count) in zip(
        opportunity_columns,
        top_three_request_types.items(),
    ):
        with opportunity_column:
            # The bordered container gives each opportunity a simple card layout.
            # It keeps this section tidy without needing custom CSS.
            with st.container(border=True):
                st.markdown(f"**{request_type}**")
                st.write(f"{count:,} requests")
                st.caption(
                    "Consider process improvement, clearer resident guidance, or "
                    "automation for this request type."
                )


def show_uploaded_data_table(service_requests_df):
    """Show the filtered data in a table."""
    st.subheader("Uploaded Data")
    st.dataframe(
        service_requests_df,
        use_container_width=True,
        hide_index=True,
    )


def convert_dataframe_to_csv(service_requests_df):
    """Convert the filtered data into a CSV file for download."""
    # index=False keeps the extra pandas row number out of the downloaded file.
    csv_text = service_requests_df.to_csv(index=False)

    # Streamlit download buttons need bytes, so encode the text as UTF-8.
    return csv_text.encode("utf-8")


def show_csv_download_button(service_requests_df):
    """Show a button that downloads the filtered data as a CSV file."""
    csv_file = convert_dataframe_to_csv(service_requests_df)

    st.download_button(
        label="Download filtered data as CSV",
        data=csv_file,
        file_name="filtered_service_requests.csv",
        mime="text/csv",
        use_container_width=True,
    )


def show_upload_panel():
    """Show the CSV upload control."""
    with st.container(border=True):
        st.markdown("#### Upload CSV")
        st.write("Choose a CSV file with the expected service request columns.")
        uploaded_csv_file = st.file_uploader(
            "Upload your service request CSV",
            type=["csv"],
            label_visibility="collapsed",
        )

    return uploaded_csv_file


def show_missing_columns_error(missing_columns):
    """Explain which CSV columns are missing."""
    st.error("The uploaded CSV is missing required columns.")

    error_column, expected_column = st.columns(2)
    with error_column:
        st.markdown("**Missing columns**")
        st.write(missing_columns)

    with expected_column:
        st.markdown("**Expected columns**")
        st.write(EXPECTED_COLUMNS)


def show_dashboard(service_requests_df):
    """Show the dashboard once a valid CSV has been uploaded."""
    filtered_service_requests_df = filter_service_requests(service_requests_df)

    st.caption(f"Showing {len(filtered_service_requests_df):,} filtered requests.")

    if filtered_service_requests_df.empty:
        st.warning("No rows match the current filters.")
        return

    overview_tab, charts_tab, data_tab = st.tabs(
        ["Overview", "Charts", "Data"]
    )

    with overview_tab:
        show_executive_summary(filtered_service_requests_df)
        st.divider()
        show_summary_metrics(filtered_service_requests_df)
        st.divider()
        show_improvement_opportunities(filtered_service_requests_df)

    with charts_tab:
        show_charts(filtered_service_requests_df)

    with data_tab:
        show_csv_download_button(filtered_service_requests_df)
        show_uploaded_data_table(filtered_service_requests_df)


# ------------------------------------------------------------
# Main app flow
# ------------------------------------------------------------
# This section connects the helper functions above into one Streamlit app.
show_page_header()
uploaded_csv_file = show_upload_panel()

if uploaded_csv_file is None:
    st.info("Upload a CSV file to begin. Try `sample_service_requests.csv` first.")
else:
    service_requests_df, missing_columns = load_service_request_data(uploaded_csv_file)

    if missing_columns:
        show_missing_columns_error(missing_columns)
    else:
        show_dashboard(service_requests_df)
