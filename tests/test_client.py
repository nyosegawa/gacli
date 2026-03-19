"""Tests for client.py — pure function tests for response parsing and request building."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gacli.client import (
    _build_hour_filter,
    _parse_response,
    run_pages_report,
    run_report,
    run_realtime_report,
)


def _make_row(dim_values: list[str], met_values: list[str]):
    return SimpleNamespace(
        dimension_values=[SimpleNamespace(value=v) for v in dim_values],
        metric_values=[SimpleNamespace(value=v) for v in met_values],
    )


class TestParseResponse:
    def test_empty_response(self):
        response = SimpleNamespace(rows=[], row_count=0)
        result = _parse_response(response, ["activeUsers"], ["country"])
        assert result == {
            "dimensions": ["country"],
            "metrics": ["activeUsers"],
            "rows": [],
            "row_count": 0,
        }

    def test_single_row(self):
        response = SimpleNamespace(
            rows=[_make_row(["Japan"], ["42"])],
            row_count=1,
        )
        result = _parse_response(response, ["activeUsers"], ["country"])
        assert result["rows"] == [{"country": "Japan", "activeUsers": "42"}]
        assert result["row_count"] == 1

    def test_multiple_rows_and_metrics(self):
        response = SimpleNamespace(
            rows=[
                _make_row(["20260319"], ["100", "50", "60"]),
                _make_row(["20260320"], ["200", "80", "90"]),
            ],
            row_count=2,
        )
        metrics = ["screenPageViews", "activeUsers", "sessions"]
        result = _parse_response(response, metrics, ["date"])
        assert len(result["rows"]) == 2
        assert result["rows"][0] == {
            "date": "20260319",
            "screenPageViews": "100",
            "activeUsers": "50",
            "sessions": "60",
        }

    def test_no_dimensions(self):
        response = SimpleNamespace(
            rows=[_make_row([], ["10"])],
            row_count=1,
        )
        result = _parse_response(response, ["activeUsers"], [])
        assert result["rows"] == [{"activeUsers": "10"}]


class TestRunReport:
    def test_default_metrics_and_dimensions(self):
        mock_creds = MagicMock()
        mock_client = MagicMock()
        mock_client.run_report.return_value = SimpleNamespace(
            rows=[_make_row(["20260319"], ["10", "5", "6"])],
            row_count=1,
        )

        with patch("gacli.client.get_client", return_value=mock_client):
            result = run_report(mock_creds, "123456")

        call_args = mock_client.run_report.call_args[0][0]
        assert call_args.property == "properties/123456"
        assert len(call_args.metrics) == 3
        assert call_args.metrics[0].name == "screenPageViews"
        assert call_args.dimensions[0].name == "date"
        assert result["row_count"] == 1

    def test_custom_days(self):
        mock_creds = MagicMock()
        mock_client = MagicMock()
        mock_client.run_report.return_value = SimpleNamespace(rows=[], row_count=0)

        with patch("gacli.client.get_client", return_value=mock_client):
            run_report(mock_creds, "123456", days=30)

        call_args = mock_client.run_report.call_args[0][0]
        date_range = call_args.date_ranges[0]
        # 30 days span
        from datetime import date, timedelta
        expected_start = (date.today() - timedelta(days=29)).isoformat()
        expected_end = date.today().isoformat()
        assert date_range.start_date == expected_start
        assert date_range.end_date == expected_end


class TestRunRealtimeReport:
    def test_default_metrics(self):
        mock_creds = MagicMock()
        mock_client = MagicMock()
        mock_client.run_realtime_report.return_value = SimpleNamespace(
            rows=[_make_row(["Japan"], ["42"])],
            row_count=1,
        )

        with patch("gacli.client.get_client", return_value=mock_client):
            result = run_realtime_report(mock_creds, "123456", dimensions=["country"])

        call_args = mock_client.run_realtime_report.call_args[0][0]
        assert call_args.property == "properties/123456"
        assert call_args.metrics[0].name == "activeUsers"
        assert result["rows"][0]["country"] == "Japan"


class TestBuildHourFilter:
    def test_returns_correct_number_of_hours(self):
        start_date, dim_filter = _build_hour_filter(3)
        values = dim_filter.filter.in_list_filter.values
        assert len(values) == 3

    def test_hour_values_format(self):
        _start_date, dim_filter = _build_hour_filter(1)
        values = dim_filter.filter.in_list_filter.values
        # dateHour format: YYYYMMDDHH (10 chars)
        assert len(values[0]) == 10

    def test_field_name_is_dateHour(self):
        _start_date, dim_filter = _build_hour_filter(1)
        assert dim_filter.filter.field_name == "dateHour"


class TestRunReportHourly:
    def test_hours_uses_dateHour_dimension(self):
        mock_creds = MagicMock()
        mock_client = MagicMock()
        mock_client.run_report.return_value = SimpleNamespace(
            rows=[_make_row(["2026031918"], ["10", "5", "6"])],
            row_count=1,
        )

        with patch("gacli.client.get_client", return_value=mock_client):
            result = run_report(mock_creds, "123456", hours=3)

        call_args = mock_client.run_report.call_args[0][0]
        assert call_args.dimensions[0].name == "dateHour"
        assert call_args.dimension_filter is not None
        assert result["dimensions"] == ["dateHour"]

    def test_hours_none_uses_date_dimension(self):
        mock_creds = MagicMock()
        mock_client = MagicMock()
        mock_client.run_report.return_value = SimpleNamespace(
            rows=[_make_row(["20260319"], ["10", "5", "6"])],
            row_count=1,
        )

        with patch("gacli.client.get_client", return_value=mock_client):
            result = run_report(mock_creds, "123456")

        call_args = mock_client.run_report.call_args[0][0]
        assert call_args.dimensions[0].name == "date"
        assert not call_args.dimension_filter


class TestRunPagesReportHourly:
    def test_hours_adds_dimension_filter(self):
        mock_creds = MagicMock()
        mock_client = MagicMock()
        mock_client.run_report.return_value = SimpleNamespace(
            rows=[_make_row(["/posts/hello/"], ["50", "30"])],
            row_count=1,
        )

        with patch("gacli.client.get_client", return_value=mock_client):
            run_pages_report(mock_creds, "123456", hours=3)

        call_args = mock_client.run_report.call_args[0][0]
        assert call_args.dimensions[0].name == "pagePath"
        assert call_args.dimension_filter is not None


class TestRunPagesReport:
    def test_limit_and_ordering(self):
        mock_creds = MagicMock()
        mock_client = MagicMock()
        mock_client.run_report.return_value = SimpleNamespace(
            rows=[_make_row(["/posts/hello/"], ["50", "30"])],
            row_count=1,
        )

        with patch("gacli.client.get_client", return_value=mock_client):
            result = run_pages_report(mock_creds, "123456", days=7, limit=5)

        call_args = mock_client.run_report.call_args[0][0]
        assert call_args.limit == 5
        assert call_args.dimensions[0].name == "pagePath"
        assert result["rows"][0]["pagePath"] == "/posts/hello/"
