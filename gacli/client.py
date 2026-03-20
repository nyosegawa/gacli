from __future__ import annotations

from datetime import date, datetime, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    FilterExpressionList,
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


# ---------------------------------------------------------------------------
# Escape-hatch helpers
# ---------------------------------------------------------------------------

_STRING_OPS = {
    "contains": Filter.StringFilter.MatchType.CONTAINS,
    "exact": Filter.StringFilter.MatchType.EXACT,
    "begins_with": Filter.StringFilter.MatchType.BEGINS_WITH,
    "ends_with": Filter.StringFilter.MatchType.ENDS_WITH,
    "regex": Filter.StringFilter.MatchType.FULL_REGEXP,
}

_NUMERIC_OPS = {
    ">=": Filter.NumericFilter.Operation.GREATER_THAN_OR_EQUAL,
    "<=": Filter.NumericFilter.Operation.LESS_THAN_OR_EQUAL,
    "==": Filter.NumericFilter.Operation.EQUAL,
    ">": Filter.NumericFilter.Operation.GREATER_THAN,
    "<": Filter.NumericFilter.Operation.LESS_THAN,
}


def _parse_filter(filter_str: str) -> tuple[FilterExpression, bool]:
    """Parse ``'field op value'``.  Returns *(expr, is_metric_filter)*.

    String ops  → dimension filter: contains, exact, begins_with, ends_with, regex
    Numeric ops → metric filter:    >, <, >=, <=, ==
    """
    for op in (">=", "<=", "==", ">", "<"):
        if f" {op} " in filter_str:
            field, value = filter_str.split(f" {op} ", 1)
            field, value = field.strip(), value.strip()
            num_val = (
                {"double_value": float(value)}
                if "." in value
                else {"int64_value": int(value)}
            )
            return FilterExpression(
                filter=Filter(
                    field_name=field,
                    numeric_filter=Filter.NumericFilter(
                        operation=_NUMERIC_OPS[op],
                        value=num_val,
                    ),
                ),
            ), True

    parts = filter_str.split(None, 2)
    if len(parts) != 3:
        raise ValueError(
            f"Invalid filter: '{filter_str}'. Expected: 'field op value'"
        )
    field, op, value = parts
    if op not in _STRING_OPS:
        raise ValueError(f"Unknown operator: '{op}'")
    return FilterExpression(
        filter=Filter(
            field_name=field,
            string_filter=Filter.StringFilter(
                match_type=_STRING_OPS[op],
                value=value,
            ),
        ),
    ), False


def _combine_expressions(
    exprs: list[FilterExpression],
) -> FilterExpression | None:
    if not exprs:
        return None
    if len(exprs) == 1:
        return exprs[0]
    return FilterExpression(
        and_group=FilterExpressionList(expressions=exprs),
    )


def run_query_report(
    credentials: Credentials,
    property_id: str,
    metrics: list[str],
    dimensions: list[str] | None = None,
    days: int = 7,
    hours: int | None = None,
    limit: int = 0,
    order_by: str | None = None,
    filters: list[str] | None = None,
    realtime: bool = False,
) -> dict:
    """Run an arbitrary GA4 query (escape hatch)."""
    client = get_client(credentials)
    dimensions = dimensions or []

    dim_exprs: list[FilterExpression] = []
    met_exprs: list[FilterExpression] = []
    for f in filters or []:
        expr, is_metric = _parse_filter(f)
        (met_exprs if is_metric else dim_exprs).append(expr)

    order_bys = None
    if order_by:
        parts = order_by.rsplit(":", 1)
        field = parts[0]
        desc = parts[1].lower() != "asc" if len(parts) > 1 else True
        if field in metrics:
            order_bys = [{"metric": {"metric_name": field}, "desc": desc}]
        else:
            order_bys = [{"dimension": {"dimension_name": field}, "desc": desc}]

    if realtime:
        request = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            metrics=[Metric(name=m) for m in metrics],
            dimensions=[Dimension(name=d) for d in dimensions],
            dimension_filter=_combine_expressions(dim_exprs),
            metric_filter=_combine_expressions(met_exprs),
            limit=limit,
            order_bys=order_bys or [],
        )
        response = client.run_realtime_report(request)
    else:
        if hours is not None:
            start_date, hour_filter = _build_hour_filter(hours)
            dim_exprs.append(hour_filter)
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
            dimension_filter=_combine_expressions(dim_exprs),
            metric_filter=_combine_expressions(met_exprs),
            limit=limit,
            order_bys=order_bys or [],
        )
        response = client.run_report(request)

    return _parse_response(response, metrics, dimensions)
