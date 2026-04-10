#!/usr/bin/env python3
"""
WHOOP Data Platform - First-time setup wizard.

Guides new users through creating their .env file, validating credentials,
and initialising the database so they can run their first ETL in minutes.
"""

import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table

console = Console()

ENV_PATH = Path(".env")

# ── credential definitions ────────────────────────────────────────────────────

REQUIRED_CREDENTIALS = [
    {
        "key": "WHOOP_CLIENT_ID",
        "label": "WHOOP Client ID",
        "secret": False,
        "hint": "From https://developer.whoop.com/ → Applications → your app → Client ID",
    },
    {
        "key": "WHOOP_CLIENT_SECRET",
        "label": "WHOOP Client Secret",
        "secret": True,
        "hint": "From the same WHOOP developer dashboard (keep this private)",
    },
    {
        "key": "WITHINGS_CLIENT_ID",
        "label": "Withings Client ID",
        "secret": False,
        "hint": "From https://account.withings.com/partner/dashboard_oauth2",
    },
    {
        "key": "WITHINGS_CLIENT_SECRET",
        "label": "Withings Client Secret",
        "secret": True,
        "hint": "From the same Withings partner dashboard (keep this private)",
    },
    {
        "key": "OPENAI_API_KEY",
        "label": "OpenAI API Key",
        "secret": True,
        "hint": "From https://platform.openai.com/api-keys",
    },
]

OPTIONAL_CREDENTIALS = [
    {
        "key": "OPENWEATHER_API_KEY",
        "label": "OpenWeatherMap API Key (optional)",
        "secret": True,
        "hint": "From https://openweathermap.org/api — enables weather context in coaching",
    },
    {
        "key": "TELEGRAM_BOT_TOKEN",
        "label": "Telegram Bot Token (optional)",
        "secret": True,
        "hint": "Create a bot via @BotFather on Telegram and paste the token here",
    },
]

FIXED_VALUES = {
    "WITHINGS_CALLBACK_URL": "http://localhost:8766/callback",
}

# Thames Environment Agency tide stations — used as a fallback when the EA API
# is not reachable during setup.  The live list is fetched via _fetch_tide_stations().
_TIDE_STATIONS_FALLBACK: dict[str, str] = {
    "0001": "Silvertown",
    "0003": "Charlton",
    "0007": "Tower Pier",
}

# Country inputs we recognise as UK for London-feature prompts
_UK_IDENTIFIERS = {"gb", "uk", "united kingdom", "england", "great britain", "britain"}


def _fetch_tide_stations() -> dict[str, str]:
    """Return {station_id: name} by querying the EA Flood Monitoring API.

    Falls back to _TIDE_STATIONS_FALLBACK if the network is unreachable or the
    API returns no usable data (e.g. during offline setup).
    """
    try:
        from whoopdata.services.tide_service import TideService

        service = TideService(timeout=6)
        raw = asyncio.run(service.list_thames_tidal_stations())
        if raw:
            return {s["id"]: s["name"] for s in raw}
    except Exception:
        pass
    return dict(_TIDE_STATIONS_FALLBACK)


def _fetch_tfl_lines() -> list[dict[str, str]]:
    """Return available TfL lines from the live API (or the static catalogue).

    Each entry is {"id": ..., "name": ..., "mode": ...}.
    """
    try:
        from whoopdata.services.transport_service import TravelAPI
        api = TravelAPI()
        lines = api.list_available_lines()
        if lines:
            return lines
    except Exception:
        pass
    # Static fallback — mirrors TFL_LINE_CATALOGUE in transport_service.py
    from whoopdata.services.transport_service import TFL_LINE_CATALOGUE
    return list(TFL_LINE_CATALOGUE)


def _prompt_tfl_lines(existing_lines: str) -> str:
    """Numbered multi-select for TfL lines. Returns comma-separated line names."""
    console.print("\n  [dim]Fetching available TfL lines...[/dim]")
    lines = _fetch_tfl_lines()

    # Show numbered table
    t = Table(box=None, show_header=True, header_style="dim", padding=(0, 2))
    t.add_column("#",    style="bold cyan", no_wrap=True, justify="right")
    t.add_column("Line", no_wrap=True)
    t.add_column("Mode", style="dim")
    for i, line in enumerate(lines, 1):
        t.add_row(str(i), line["name"], line["mode"])
    console.print(t)

    # Pre-select numbers that match the existing configured lines
    existing_set = {ln.strip().lower() for ln in existing_lines.split(",") if ln.strip()}
    preselected = [
        str(i) for i, ln in enumerate(lines, 1)
        if ln["name"].lower() in existing_set
    ]
    default_str = ",".join(preselected) if preselected else "8,3,12"  # Jubilee, DLR, Elizabeth

    raw = Prompt.ask(
        "  [bold]Select lines to monitor[/bold] "
        "[dim](enter numbers, comma-separated, e.g. 3,8,12)[/dim]",
        default=default_str,
    ).strip()

    chosen_names: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(lines):
                chosen_names.append(lines[idx]["name"])
        else:
            # Allow typing a name directly as a fallback
            chosen_names.append(token)

    return ",".join(chosen_names) if chosen_names else existing_lines


def _prompt_tfl_stations(existing_stations_env: str) -> str:
    """Interactive station search. Returns pipe-separated 'Label:NaptanID' pairs."""
    console.print()
    console.print(
        "  [bold]Station arrival monitoring[/bold] [dim](optional)[/dim]\n"
        "  [dim]Shows real-time departures for up to 5 stations.\n"
        "  Search by name — the TfL StopPoint API has ~500 stations.[/dim]"
    )

    # Decode any existing stations for display
    existing_stations: dict[str, str] = {}
    for pair in existing_stations_env.split("|"):
        pair = pair.strip()
        if ":" in pair:
            label, _, naptan = pair.partition(":")
            existing_stations[label.strip()] = naptan.strip()

    if existing_stations:
        console.print("\n  [dim]Currently configured stations:[/dim]")
        for label, naptan in existing_stations.items():
            console.print(f"    [cyan]{label}[/cyan]  ({naptan})")

    want_arrivals = Confirm.ask(
        "\n  Configure station arrival monitoring?",
        default=bool(existing_stations),
    )
    if not want_arrivals:
        return existing_stations_env  # keep unchanged

    try:
        from whoopdata.services.transport_service import TravelAPI
        api = TravelAPI()
    except Exception:
        console.print("  [yellow]Could not initialise TfL client — skipping station setup.[/yellow]")
        return existing_stations_env

    selected: dict[str, str] = dict(existing_stations)  # start from existing

    while True:
        query = Prompt.ask(
            "\n  [bold]Search station name[/bold] "
            "[dim](e.g. 'King's Cross', 'Canary Wharf', or blank to finish)[/dim]",
            default="",
        ).strip()
        if not query:
            break

        console.print("  [dim]Searching...[/dim]")
        results = api.search_stations(query)

        if not results:
            console.print("  [yellow]No results found. Try a different name.[/yellow]")
            continue

        # Show numbered results
        rt = Table(box=None, show_header=True, header_style="dim", padding=(0, 2))
        rt.add_column("#",       style="bold cyan", no_wrap=True, justify="right")
        rt.add_column("Station", no_wrap=True)
        rt.add_column("Lines",   style="dim")
        for i, r in enumerate(results, 1):
            rt.add_row(str(i), r["name"], ", ".join(r["lines"]))
        console.print(rt)

        pick = Prompt.ask(
            "  Pick a number to add (or blank to skip)",
            default="",
        ).strip()
        if pick.isdigit():
            idx = int(pick) - 1
            if 0 <= idx < len(results):
                station = results[idx]
                label = Prompt.ask(
                    f"  Label for [bold]{station['name']}[/bold]",
                    default=station["name"],
                ).strip()
                selected[label] = station["id"]
                console.print(f"  ✅ Added [cyan]{label}[/cyan] ({station['id']})")

        # Show running list
        if selected:
            console.print("\n  [dim]Stations so far:[/dim]")
            for lbl, nid in selected.items():
                console.print(f"    [cyan]{lbl}[/cyan]  ({nid})")

        another = Confirm.ask("  Add another station?", default=False)
        if not another:
            break

    if not selected:
        return ""
    return "|".join(f"{lbl}:{nid}" for lbl, nid in selected.items())


# ── helpers ───────────────────────────────────────────────────────────────────


def _load_existing_env() -> dict[str, str]:
    """Return key→value pairs from the existing .env (if present)."""
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    with open(ENV_PATH) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()
    return values


def _prompt_credential(cred: dict, existing: str = "") -> str:
    """Interactively prompt the user for a single credential."""
    console.print(f"\n[bold cyan]{cred['label']}[/bold cyan]")
    console.print(f"[dim]{cred['hint']}[/dim]")

    placeholder = ""
    if existing:
        if cred["secret"]:
            placeholder = existing[:4] + "****" + existing[-4:] if len(existing) > 8 else "****"
        else:
            placeholder = existing

    prompt_text = f"  Enter value{f' [{placeholder}]' if placeholder else ''}"

    if cred["secret"]:
        value = Prompt.ask(prompt_text, password=True, default=existing)
    else:
        value = Prompt.ask(prompt_text, default=existing)

    return value.strip()


def _is_uk(country: str) -> bool:
    """Return True if the country string looks like a UK entry."""
    return country.strip().lower() in _UK_IDENTIFIERS


def _prompt_location(existing: dict[str, str]) -> dict[str, str]:
    """Prompt for city/country and London-specific features.

    Returns a dict of env var keys → values to merge into the main values dict.
    """
    result: dict[str, str] = {}

    console.print()
    console.print(Rule("[bold cyan]Location & regional features[/bold cyan]"))
    console.print(
        "[dim]Your location is used for weather forecasts and day-of coaching context.\n"
        "TfL line monitoring and Thames tidal data are London-specific features.[/dim]"
    )

    # ── city ──────────────────────────────────────────────────────────────
    current_city = existing.get("DEFAULT_LOCATION", "")
    city = Prompt.ask(
        "\n[bold]City or area name[/bold] [dim](used for weather queries)[/dim]",
        default=current_city or "Canary Wharf",
    ).strip()
    result["DEFAULT_LOCATION"] = city or "Canary Wharf"

    # ── country ───────────────────────────────────────────────────────────
    console.print(
        "[dim]  Country code is used to disambiguate geocoding "
        "(e.g. GB, US, DE, FR, AU).[/dim]"
    )
    current_country = existing.get("DEFAULT_COUNTRY", "")
    country = Prompt.ask(
        "[bold]Country code[/bold] [dim](ISO 3166-1 alpha-2, e.g. GB)[/dim]",
        default=current_country or "GB",
    ).strip().upper()
    result["DEFAULT_COUNTRY"] = country or "GB"

    # ── London-specific features ──────────────────────────────────────────
    is_uk = _is_uk(country)

    if not is_uk:
        # Non-UK users: disable London services silently with a brief note
        console.print(
            f"\n[dim]Country [bold]{country}[/bold] — "
            "TfL and Thames tidal features are London-specific and will be disabled.[/dim]"
        )
        result["ENABLE_TFL"] = "false"
        result["ENABLE_THAMES_TIDES"] = "false"
        return result

    # UK user — offer London-specific features
    console.print(f"\n🇬🇧 [bold]United Kingdom[/bold] detected.")

    in_london = Confirm.ask(
        "  Are you in the [bold]Greater London area[/bold]? "
        "[dim](enables TfL + Thames tidal data)[/dim]",
        default=existing.get("ENABLE_TFL", "false").lower() == "true",
    )

    if not in_london:
        result["ENABLE_TFL"] = "false"
        result["ENABLE_THAMES_TIDES"] = "false"
        console.print("[dim]  TfL and Thames tidal features disabled.[/dim]")
        return result

    # ── TfL configuration ─────────────────────────────────────────────────
    console.print()
    enable_tfl = Confirm.ask(
        "  Enable [bold]TfL line monitoring[/bold]?",
        default=True,
    )
    result["ENABLE_TFL"] = "true" if enable_tfl else "false"

    if enable_tfl:
        current_lines = existing.get("TFL_KEY_LINES", "Jubilee,DLR,Elizabeth line")
        result["TFL_KEY_LINES"] = _prompt_tfl_lines(current_lines)

        current_stations_env = existing.get("TFL_KEY_STATIONS", "")
        stations_env = _prompt_tfl_stations(current_stations_env)
        if stations_env:
            result["TFL_KEY_STATIONS"] = stations_env

    # ── Thames tides configuration ─────────────────────────────────────────
    console.print()
    enable_tides = Confirm.ask(
        "  Enable [bold]Thames tidal data[/bold]?",
        default=True,
    )
    result["ENABLE_THAMES_TIDES"] = "true" if enable_tides else "false"

    if enable_tides:
        # Try to fetch the live station list from the EA API; fall back to known 3
        console.print("\n  [dim]Fetching available stations from Environment Agency API...[/dim]")
        tide_stations = _fetch_tide_stations()

        # Build and display a table of available stations
        station_table = Table(box=None, show_header=True, header_style="dim")
        station_table.add_column("ID", style="bold cyan", no_wrap=True)
        station_table.add_column("Name")
        for sid, sname in tide_stations.items():
            station_table.add_row(sid, sname)
        console.print(station_table)

        current_station = existing.get("DEFAULT_TIDE_STATION_ID", "0001")
        station_id = Prompt.ask(
            "  [bold]Default tide station ID[/bold]",
            default=current_station,
        ).strip()

        if station_id not in tide_stations:
            console.print(
                f"  [yellow]Station '{station_id}' not in the fetched list — "
                "it may still be valid (the EA has many stations). "
                "Keeping your entry as-is.[/yellow]"
            )
            station_name = station_id  # Use ID as name if unknown
        else:
            station_name = tide_stations[station_id]

        result["DEFAULT_TIDE_STATION_ID"] = station_id
        result["DEFAULT_TIDE_STATION_NAME"] = station_name

    return result


def _write_env(values: dict[str, str]) -> None:
    """Write all collected values to .env with a consistent section structure."""
    sections = [
        ("# WHOOP API Configuration", ["WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET"]),
        (
            "# Withings API Configuration",
            ["WITHINGS_CLIENT_ID", "WITHINGS_CLIENT_SECRET", "WITHINGS_CALLBACK_URL"],
        ),
        ("# OpenAI API Configuration", ["OPENAI_API_KEY"]),
        (
            "# Location Configuration\n"
            "# DEFAULT_LOCATION: city/area name used for weather queries\n"
            "# DEFAULT_COUNTRY: ISO 3166-1 alpha-2 country code for geocoding disambiguation",
            ["DEFAULT_LOCATION", "DEFAULT_COUNTRY"],
        ),
        (
            "# Weather API Configuration (optional)",
            ["OPENWEATHER_API_KEY"],
        ),
        (
            "# London Regional Features\n"
            "# ENABLE_TFL: set true for Transport for London line monitoring (London only)\n"
            "# ENABLE_THAMES_TIDES: set true for Thames tidal data (London only)\n"
            "# TFL_KEY_LINES: comma-separated TfL line names to monitor\n"
            "# TFL_KEY_STATIONS: pipe-separated 'Label:NaptanID' pairs for arrival boards\n"
            "# DEFAULT_TIDE_STATION_ID: EA station ID — query /api/v1/data/tides/stations for full list",
            [
                "ENABLE_TFL",
                "ENABLE_THAMES_TIDES",
                "TFL_KEY_LINES",
                "TFL_KEY_STATIONS",
                "DEFAULT_TIDE_STATION_ID",
                "DEFAULT_TIDE_STATION_NAME",
            ],
        ),
        ("# Telegram Bot Configuration (optional)", ["TELEGRAM_BOT_TOKEN"]),
    ]

    lines = ["# WHOOP Data Platform — generated by whoop-setup", ""]
    for comment, keys in sections:
        lines.append(comment)
        for key in keys:
            val = values.get(key, "")
            if val:
                lines.append(f"{key}={val}")
        lines.append("")

    # Append any keys from the original file not covered by the sections above
    covered = {k for _, keys in sections for k in keys}
    extras = {k: v for k, v in values.items() if k not in covered}
    if extras:
        lines.append("# Additional settings")
        for k, v in extras.items():
            lines.append(f"{k}={v}")
        lines.append("")

    ENV_PATH.write_text("\n".join(lines))
    console.print(f"\n✅ [bold green].env written to {ENV_PATH.resolve()}[/bold green]")


def _setup_database() -> bool:
    """Create SQLite database tables."""
    console.print("\n[bold]Initialising database tables...[/bold]")
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)

        from whoopdata.database.database import engine
        from whoopdata.models.models import Base

        Base.metadata.create_all(bind=engine)
        console.print("✅ [bold green]Database tables ready[/bold green]")
        return True
    except Exception as exc:
        console.print(f"❌ [bold red]Database setup failed:[/bold red] {exc}")
        console.print("[dim]You can retry later with: make etl[/dim]")
        return False


def _show_next_steps(tfl_enabled: bool, tides_enabled: bool) -> None:
    """Print a summary of recommended next actions."""
    console.print()
    console.print(Rule("[bold magenta]You're all set![/bold magenta]"))

    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Step", style="bold cyan", no_wrap=True)
    table.add_column("Command", style="green")
    table.add_column("What it does")

    table.add_row("1", "make etl", "Fetch data from WHOOP and Withings (incremental)")
    table.add_row("2", "make server", "Start the FastAPI server at http://localhost:8000")
    table.add_row("3", "make chat", "Open the chat UI at http://localhost:7860 (optional)")
    table.add_row("4", "make analytics", "Train ML models and materialise insights (optional)")
    table.add_row("5", "make verify", "Run a full system health check at any time")

    console.print(table)

    notes: list[str] = [
        "WHOOP uses OAuth 2.0. The first time you run [bold]make etl[/bold] you will "
        "be redirected to your browser to complete the authorisation flow."
    ]
    if tfl_enabled:
        notes.append(
            "TfL integration is [bold green]enabled[/bold green]. "
            "Line status will appear in the agent's day-of briefing."
        )
    if tides_enabled:
        notes.append(
            "Thames tidal data is [bold green]enabled[/bold green]. "
            "The agent can recommend optimal riverside walk times."
        )

    console.print()
    for note in notes:
        console.print(
            Panel.fit(f"[dim]{note}[/dim]", title="[bold yellow]Note[/bold yellow]")
        )
        console.print()


# ── main entry point ──────────────────────────────────────────────────────────


def main() -> int:
    """Interactive first-time setup wizard for the WHOOP Data Platform."""
    console.print(
        Panel.fit(
            "[bold]WHOOP Data Platform — Setup Wizard[/bold]\n\n"
            "[dim]This wizard will create your [bold].env[/bold] file with API credentials,\n"
            "configure your location and regional features, and initialise the local database\n"
            "so you are ready to ingest data.[/dim]",
            style="bold magenta",
        )
    )

    # ── check for an existing .env ─────────────────────────────────────────
    existing = _load_existing_env()
    if existing:
        console.print(
            f"\n[bold yellow]A .env file already exists[/bold yellow] at {ENV_PATH.resolve()}"
        )
        if not Confirm.ask("  Re-run setup and update credentials?", default=False):
            console.print("[dim]Setup cancelled — your existing .env was not modified.[/dim]")
            return 0

    values: dict[str, str] = dict(existing)

    # ── fixed values ───────────────────────────────────────────────────────
    for key, val in FIXED_VALUES.items():
        values[key] = val

    # ── required credentials ───────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold cyan]Required credentials[/bold cyan]"))

    for cred in REQUIRED_CREDENTIALS:
        value = _prompt_credential(cred, existing=existing.get(cred["key"], ""))
        if not value:
            console.print(
                f"[bold red]  ✗ {cred['label']} is required — setup aborted.[/bold red]"
            )
            return 1
        values[cred["key"]] = value

    # ── optional credentials ───────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold cyan]Optional credentials[/bold cyan]"))
    console.print("[dim]Press Enter to skip any optional credential.[/dim]")

    for cred in OPTIONAL_CREDENTIALS:
        current = existing.get(cred["key"], "")
        if cred["secret"]:
            value = Prompt.ask(
                f"\n[bold]{cred['label']}[/bold]\n  [dim]{cred['hint']}[/dim]\n  Value",
                password=True,
                default=current,
            )
        else:
            value = Prompt.ask(
                f"\n[bold]{cred['label']}[/bold]\n  [dim]{cred['hint']}[/dim]\n  Value",
                default=current,
            )
        if value.strip():
            values[cred["key"]] = value.strip()

    # ── location & regional features ───────────────────────────────────────
    location_values = _prompt_location(existing)
    values.update(location_values)

    # ── write .env ─────────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold cyan]Writing configuration[/bold cyan]"))
    _write_env(values)

    # ── database init ──────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold cyan]Database initialisation[/bold cyan]"))
    _setup_database()

    # ── next steps ─────────────────────────────────────────────────────────
    _show_next_steps(
        tfl_enabled=values.get("ENABLE_TFL") == "true",
        tides_enabled=values.get("ENABLE_THAMES_TIDES") == "true",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
