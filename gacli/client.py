from __future__ import annotations

from datetime import date, datetime, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    RunRealtimeReportRequest,
    RunReportRequest,
)
from google.oauth2.credentials import Credentials


def get_client(credentials: Credentials) -> BetaAnalyticsDataClient:
    return BetaAnalyticsDataClient(credentials=credentials)


def run_realtime_report(
    credentials: Credentials,
    property_id: str,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
) -> dict:
    client = get_client(credentials)
    if metrics is None:
        metrics = ["activeUsers"]

    request = RunRealtimeReportRequest(
        property=f"properties/{property_id}",
        metrics=[Metric(name=m) for m in metrics],
        dimensions=[Dimension(name=d) for d in dimensions] if dimensions else [],
    )
    response = client.run_realtime_report(request)
    return _parse_response(response, metrics, dimensions or [])


def _build_hour_filter(hours: int) -> tuple[date, FilterExpression]:
    """Return (start_date, dimension_filter) for the last N hours."""
    now = datetime.now()
    hour_values = []
    for i in range(hours):
        dt = now - timedelta(hours=i)
        hour_values.append(dt.strftime("%Y%m%d%H"))

    start_date = (now - timedelta(hours=hours - 1)).date()

    dimension_filter = FilterExpression(
        filter=Filter(
            field_name="dateHour",
            in_list_filter=Filter.InListFilter(values=hour_values),
        ),
    )
    return start_date, dimension_filter


def run_report(
    credentials: Credentials,
    property_id: str,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
    days: int = 7,
    hours: int | None = None,
) -> dict:
    client = get_client(credentials)
    if metrics is None:
        metrics = ["screenPageViews", "activeUsers", "sessions"]
    if dimensions is None:
        dimensions = ["dateHour"] if hours else ["date"]

    dimension_filter = None
    if hours is not None:
        start_date, dimension_filter = _build_hour_filter(hours)
        end_date = date.today()
    else:
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        metrics=[Metric(name=m) for m in metrics],
        dimensions=[Dimension(name=d) for d in dimensions],
        dimension_filter=dimension_filter,
    )
    response = client.run_report(request)
    return _parse_response(response, metrics, dimensions)


def run_pages_report(
    credentials: Credentials,
    property_id: str,
    days: int = 7,
    limit: int = 10,
    hours: int | None = None,
) -> dict:
    client = get_client(credentials)
    metrics = ["screenPageViews", "activeUsers"]
    dimensions = ["pagePath"]

    dimension_filter = None
    if hours is not None:
        start_date, dimension_filter = _build_hour_filter(hours)
        end_date = date.today()
    else:
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[
            DateRange(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ],
        metrics=[Metric(name=m) for m in metrics],
        dimensions=[Dimension(name=d) for d in dimensions],
        limit=limit,
        order_bys=[
            {
                "metric": {"metric_name": "screenPageViews"},
                "desc": True,
            }
        ],
        dimension_filter=dimension_filter,
    )
    response = client.run_report(request)
    return _parse_response(response, metrics, dimensions)


def _parse_response(
    response, metrics: list[str], dimensions: list[str]
) -> dict:
    rows = []
    for row in response.rows:
        entry = {}
        for i, dim in enumerate(dimensions):
            entry[dim] = row.dimension_values[i].value
        for i, met in enumerate(metrics):
            entry[met] = row.metric_values[i].value
        rows.append(entry)
    return {
        "dimensions": dimensions,
        "metrics": metrics,
        "rows": rows,
        "row_count": response.row_count,
    }
