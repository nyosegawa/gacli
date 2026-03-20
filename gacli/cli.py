from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from gacli.client import run_pages_report, run_query_report, run_realtime_report, run_report
from gacli.oauth import authenticate, credentials_path, load_credentials

console = Console()

CONFIG_DIR = Path.home() / ".config" / "gacli"


def profile_dir(profile: str) -> Path:
    return CONFIG_DIR / "profiles" / profile


def config_path(profile: str) -> Path:
    return profile_dir(profile) / "config.json"


def default_profile_path() -> Path:
    return CONFIG_DIR / "default_profile"


def get_default_profile() -> str:
    p = default_profile_path()
    if p.exists():
        return p.read_text().strip()
    return "default"


def set_default_profile(name: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    default_profile_path().write_text(name)


def load_config(profile: str) -> dict:
    p = config_path(profile)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def save_config(profile: str, config: dict) -> None:
    d = profile_dir(profile)
    d.mkdir(parents=True, exist_ok=True)
    config_path(profile).write_text(json.dumps(config, indent=2) + "\n")


def require_property_id(ctx: click.Context) -> str:
    pid = ctx.obj.get("property_id")
    if not pid:
        profile = ctx.obj.get("profile", "default")
        raise click.ClickException(
            f"Property ID not set.\n"
            f"  Why: No property ID configured for profile '{profile}'.\n"
            f"  Fix: gacli config -p <PROPERTY_ID> --profile {profile}\n"
            f"  Find your property ID at: Google Analytics > Admin > Property Settings"
        )
    return pid


def require_credentials(profile: str):
    try:
        return load_credentials(profile)
    except FileNotFoundError:
        raise click.ClickException(
            f"Not authenticated.\n"
            f"  Why: No credentials found for profile '{profile}'.\n"
            f"  Fix: gacli auth --profile {profile}"
        )


def list_profiles() -> list[str]:
    profiles_dir = CONFIG_DIR / "profiles"
    if not profiles_dir.exists():
        return []
    return sorted(d.name for d in profiles_dir.iterdir() if d.is_dir())


def output_json(data: dict) -> None:
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))


def is_json_mode(ctx: click.Context) -> bool:
    return ctx.obj.get("json_output", False) or not sys.stdout.isatty()


@click.group()
@click.option(
    "--profile",
    default=None,
    help="Profile name (default: saved default profile)",
)
@click.option(
    "--property-id", "-p",
    default=None,
    help="GA4 property ID (overrides saved config)",
)
@click.option(
    "--json", "json_output",
    is_flag=True,
    default=False,
    help="Output as JSON (auto-enabled when piped)",
)
@click.pass_context
def main(ctx: click.Context, profile: str | None, property_id: str | None, json_output: bool) -> None:
    """Simple Google Analytics 4 CLI."""
    resolved_profile = profile or get_default_profile()
    config = load_config(resolved_profile)

    ctx.ensure_object(dict)
    ctx.obj["profile"] = resolved_profile
    ctx.obj["property_id"] = property_id or config.get("property_id")
    ctx.obj["json_output"] = json_output


@main.command()
@click.option("--profile", default=None, help="Profile name to authenticate")
def auth(profile: str | None) -> None:
    """Authenticate with Google via browser (no gcloud required)."""
    resolved_profile = profile or get_default_profile()
    console.print(f"Authenticating profile [cyan]{resolved_profile}[/cyan]...")

    try:
        authenticate(resolved_profile)
    except FileNotFoundError:
        raise click.ClickException(
            f"Client secret not found.\n"
            f"  Why: ~/.config/gacli/client_secret.json does not exist.\n"
            f"  Fix: Download OAuth client ID JSON from GCP Console and save it as:\n"
            f"       ~/.config/gacli/client_secret.json\n"
            f"  See: https://console.cloud.google.com/auth/clients/create"
        )

    console.print(f"[bold green]Done![/bold green] Profile [cyan]{resolved_profile}[/cyan] authenticated.")


@main.command("config")
@click.option("--profile", default=None, help="Profile name")
@click.option("--property-id", "-p", default=None, help="GA4 property ID to save")
@click.option("--set-default", is_flag=True, help="Set this profile as default")
def config_cmd(profile: str | None, property_id: str | None, set_default: bool) -> None:
    """Show or update saved configuration."""
    resolved_profile = profile or get_default_profile()
    config = load_config(resolved_profile)

    if property_id:
        config["property_id"] = property_id
        save_config(resolved_profile, config)
        console.print(f"[cyan]{resolved_profile}[/cyan] property_id: {property_id}")

    if set_default:
        set_default_profile(resolved_profile)
        console.print(f"Default profile set to [cyan]{resolved_profile}[/cyan]")

    if not property_id and not set_default:
        console.print(f"Profile: [cyan]{resolved_profile}[/cyan]")
        if not config:
            console.print("  (no config)")
        for key, value in config.items():
            console.print(f"  {key}: {value}")
        has_creds = credentials_path(resolved_profile).exists()
        console.print(f"  authenticated: {'yes' if has_creds else 'no'}")


@main.command()
def profiles() -> None:
    """List all profiles."""
    profs = list_profiles()
    default = get_default_profile()

    if not profs:
        console.print("No profiles. Run [cyan]gacli auth --profile <name>[/cyan] to create one.")
        return

    table = Table(title="Profiles")
    table.add_column("Profile", style="cyan")
    table.add_column("Property ID", style="green")
    table.add_column("Auth", justify="center")
    table.add_column("Default", justify="center")

    for name in profs:
        config = load_config(name)
        has_creds = credentials_path(name).exists()
        table.add_row(
            name,
            config.get("property_id", "-"),
            "yes" if has_creds else "no",
            "*" if name == default else "",
        )

    console.print(table)


@main.command()
@click.pass_context
def realtime(ctx: click.Context) -> None:
    """Show realtime active users."""
    pid = require_property_id(ctx)
    creds = require_credentials(ctx.obj["profile"])
    data = run_realtime_report(creds, pid, dimensions=["country"])

    if is_json_mode(ctx):
        output_json(data)
        return

    table = Table(title="Realtime Active Users")
    table.add_column("Country", style="cyan")
    table.add_column("Active Users", style="green", justify="right")

    for row in data["rows"]:
        table.add_row(row.get("country", "-"), row["activeUsers"])

    console.print(table)

    total = sum(int(r["activeUsers"]) for r in data["rows"])
    console.print(f"\nTotal: [bold green]{total}[/bold green] active users")


@main.command()
@click.option("--days", "-d", default=7, help="Number of days (default: 7)")
@click.option("--hours", default=None, type=int, help="Last N hours (overrides --days)")
@click.pass_context
def summary(ctx: click.Context, days: int, hours: int | None) -> None:
    """Show daily summary (PV, users, sessions)."""
    pid = require_property_id(ctx)
    creds = require_credentials(ctx.obj["profile"])
    data = run_report(creds, pid, days=days, hours=hours)

    if is_json_mode(ctx):
        output_json(data)
        return

    if hours is not None:
        title = f"Summary (last {hours} hours)"
        time_dim = "dateHour"
    else:
        title = f"Summary (last {days} days)"
        time_dim = "date"

    table = Table(title=title)
    table.add_column("Hour" if hours else "Date", style="cyan")
    table.add_column("Page Views", style="green", justify="right")
    table.add_column("Users", style="yellow", justify="right")
    table.add_column("Sessions", style="magenta", justify="right")

    rows = sorted(data["rows"], key=lambda r: r[time_dim])
    for row in rows:
        d = row[time_dim]
        if hours:
            formatted = f"{d[:4]}-{d[4:6]}-{d[6:8]} {d[8:]}:00"
        else:
            formatted = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        table.add_row(
            formatted,
            row["screenPageViews"],
            row["activeUsers"],
            row["sessions"],
        )

    console.print(table)

    total_pv = sum(int(r["screenPageViews"]) for r in data["rows"])
    total_users = sum(int(r["activeUsers"]) for r in data["rows"])
    console.print(f"\nTotal: [green]{total_pv}[/green] PV, [yellow]{total_users}[/yellow] users")


@main.command()
@click.option("--days", "-d", default=7, help="Number of days (default: 7)")
@click.option("--hours", default=None, type=int, help="Last N hours (overrides --days)")
@click.option("--limit", "-n", default=10, help="Number of pages (default: 10)")
@click.pass_context
def pages(ctx: click.Context, days: int, hours: int | None, limit: int) -> None:
    """Show top pages by page views."""
    pid = require_property_id(ctx)
    creds = require_credentials(ctx.obj["profile"])
    data = run_pages_report(creds, pid, days=days, limit=limit, hours=hours)

    if is_json_mode(ctx):
        output_json(data)
        return

    if hours is not None:
        title = f"Top {limit} Pages (last {hours} hours)"
    else:
        title = f"Top {limit} Pages (last {days} days)"

    table = Table(title=title)
    table.add_column("#", style="dim", justify="right")
    table.add_column("Page", style="cyan")
    table.add_column("Page Views", style="green", justify="right")
    table.add_column("Users", style="yellow", justify="right")

    for i, row in enumerate(data["rows"], 1):
        table.add_row(
            str(i),
            row["pagePath"],
            row["screenPageViews"],
            row["activeUsers"],
        )

    console.print(table)


@main.command()
@click.option("--metric", "-m", multiple=True, required=True, help="Metric name(s)")
@click.option("--dimension", "-d", "dims", multiple=True, help="Dimension name(s)")
@click.option("--days", default=7, help="Number of days (default: 7)")
@click.option("--hours", default=None, type=int, help="Last N hours (overrides --days)")
@click.option("--limit", "-n", default=0, help="Max rows (0 = all)")
@click.option("--sort", default=None, help="Sort: field:desc or field:asc")
@click.option("--filter", "-f", "filters", multiple=True, help="Filter: 'field op value'")
@click.option("--realtime", is_flag=True, help="Use realtime API")
@click.pass_context
def query(
    ctx: click.Context,
    metric: tuple[str, ...],
    dims: tuple[str, ...],
    days: int,
    hours: int | None,
    limit: int,
    sort: str | None,
    filters: tuple[str, ...],
    realtime: bool,
) -> None:
    """Run a custom GA4 query (escape hatch)."""
    pid = require_property_id(ctx)
    creds = require_credentials(ctx.obj["profile"])
    data = run_query_report(
        creds,
        pid,
        metrics=list(metric),
        dimensions=list(dims),
        days=days,
        hours=hours,
        limit=limit,
        order_by=sort,
        filters=list(filters) if filters else None,
        realtime=realtime,
    )
    output_json(data)
