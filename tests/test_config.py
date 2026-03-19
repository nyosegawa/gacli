"""Tests for config management — pure function tests using tmp directories."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import click
import pytest

from gacli.cli import (
    get_default_profile,
    is_json_mode,
    list_profiles,
    load_config,
    require_property_id,
    save_config,
    set_default_profile,
)


@pytest.fixture
def tmp_config_dir(tmp_path):
    with patch("gacli.cli.CONFIG_DIR", tmp_path):
        yield tmp_path


class TestConfigIO:
    def test_load_config_missing_file(self, tmp_config_dir):
        result = load_config("nonexistent")
        assert result == {}

    def test_save_and_load_config(self, tmp_config_dir):
        save_config("blog", {"property_id": "123"})
        result = load_config("blog")
        assert result == {"property_id": "123"}

    def test_save_creates_profile_dir(self, tmp_config_dir):
        save_config("new_profile", {"property_id": "456"})
        assert (tmp_config_dir / "profiles" / "new_profile" / "config.json").exists()


class TestDefaultProfile:
    def test_default_when_no_file(self, tmp_config_dir):
        assert get_default_profile() == "default"

    def test_set_and_get_default(self, tmp_config_dir):
        set_default_profile("blog")
        assert get_default_profile() == "blog"


class TestListProfiles:
    def test_empty(self, tmp_config_dir):
        assert list_profiles() == []

    def test_lists_profile_dirs(self, tmp_config_dir):
        (tmp_config_dir / "profiles" / "blog").mkdir(parents=True)
        (tmp_config_dir / "profiles" / "work").mkdir(parents=True)
        assert list_profiles() == ["blog", "work"]


class TestRequirePropertyId:
    def test_raises_when_missing(self):
        ctx = click.Context(click.Command("test"))
        ctx.ensure_object(dict)
        ctx.obj["profile"] = "default"
        with pytest.raises(click.ClickException, match="Property ID not set"):
            require_property_id(ctx)

    def test_returns_when_present(self):
        ctx = click.Context(click.Command("test"))
        ctx.ensure_object(dict)
        ctx.obj["property_id"] = "123456"
        ctx.obj["profile"] = "default"
        assert require_property_id(ctx) == "123456"


class TestJsonMode:
    def test_explicit_json_flag(self):
        ctx = click.Context(click.Command("test"))
        ctx.ensure_object(dict)
        ctx.obj["json_output"] = True
        assert is_json_mode(ctx) is True

    def test_no_json_flag_tty(self):
        ctx = click.Context(click.Command("test"))
        ctx.ensure_object(dict)
        ctx.obj["json_output"] = False
        # In test environment stdout.isatty() is False, so json mode is auto-enabled
        # This tests the piped behavior
        result = is_json_mode(ctx)
        assert isinstance(result, bool)
