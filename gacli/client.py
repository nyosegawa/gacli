from __future__ import annotations

from datetime import date, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
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


def run_report(
    credentials: Credentials,
    property_id: str,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
    days: int = 7,
) -> dict:
    client = get_client(credentials)
    if metrics is None:
        metrics = ["screenPageViews", "activeUsers", "sessions"]
    if dimensions is None:
        dimensions = ["date"]

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
    )
    response = client.run_report(request)
    return _parse_response(response, metrics, dimensions)


def run_pages_report(
    credentials: Credentials,
    property_id: str,
    days: int = 7,
    limit: int = 10,
) -> dict:
    client = get_client(credentials)
    metrics = ["screenPageViews", "activeUsers"]
    dimensions = ["pagePath"]

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
