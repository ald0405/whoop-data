"""Transport status service using TfL (Transport for London) API."""

from typing import Dict, Any, List
import requests

from whoopdata.agent import settings as _settings


# Complete static list of TfL lines with their API IDs and display names.
# Used as a fallback when the TfL API is unreachable during setup.
TFL_LINE_CATALOGUE: List[Dict[str, str]] = [
    # ── London Underground ──────────────────────────────────────────────────
    {"id": "bakerloo",          "name": "Bakerloo",            "mode": "tube"},
    {"id": "central",           "name": "Central",             "mode": "tube"},
    {"id": "circle",            "name": "Circle",              "mode": "tube"},
    {"id": "district",          "name": "District",            "mode": "tube"},
    {"id": "hammersmith-city",  "name": "Hammersmith & City",  "mode": "tube"},
    {"id": "jubilee",           "name": "Jubilee",             "mode": "tube"},
    {"id": "metropolitan",      "name": "Metropolitan",        "mode": "tube"},
    {"id": "northern",          "name": "Northern",            "mode": "tube"},
    {"id": "piccadilly",        "name": "Piccadilly",          "mode": "tube"},
    {"id": "victoria",          "name": "Victoria",            "mode": "tube"},
    {"id": "waterloo-city",     "name": "Waterloo & City",     "mode": "tube"},
    # ── Other rail modes ────────────────────────────────────────────────────
    {"id": "elizabeth",         "name": "Elizabeth line",      "mode": "elizabeth-line"},
    {"id": "dlr",               "name": "DLR",                 "mode": "dlr"},
    {"id": "london-overground", "name": "London Overground",   "mode": "overground"},
    {"id": "tram",              "name": "Tram",                "mode": "tram"},
    {"id": "cable-car",         "name": "Emirates Air Line",   "mode": "cable-car"},
]


class TravelAPI:
    """Client for TfL API providing London transport line and station data."""

    def __init__(self):
        """Initialize TravelAPI client.

        Lines and stations are read from settings so they can be configured
        via environment variables (TFL_KEY_LINES, TFL_KEY_STATIONS).
        """
        self.base_url = "https://api.tfl.gov.uk"

        # Lines to include in status reports — driven by TFL_KEY_LINES env var
        self.key_lines = list(_settings.TFL_KEY_LINES)

        # Stations for real-time arrival boards — driven by TFL_KEY_STATIONS env var.
        # Format stored in env: "Label:NaptanID,Label:NaptanID,..."
        # Falls back to the original Canary Wharf defaults when not configured.
        self.key_stations: Dict[str, str] = _settings.TFL_KEY_STATIONS or {
            "DLR South Quay":         "940GZZDLSOQ",
            "Canary Wharf (Jubilee)": "940GZZLUCYF",
            "Canary Wharf (Elizabeth line)": "910GCANWHRF",
        }

    # ── discovery helpers (used by setup wizard) ─────────────────────────────

    def list_available_lines(self) -> List[Dict[str, str]]:
        """Return all TfL lines fetchable from the API.

        Queries the TfL line-status endpoint for every rail mode so the caller
        gets the live canonical list (including any newly added lines).
        Falls back to TFL_LINE_CATALOGUE on network errors.

        Returns:
            List of dicts with keys: id, name, mode.
        """
        try:
            url = f"{self.base_url}/line/mode/tube,overground,dlr,elizabeth-line,tram,cable-car"
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            lines = []
            for item in response.json():
                lines.append({
                    "id":   item.get("id", ""),
                    "name": item.get("name", ""),
                    "mode": item.get("modeName", ""),
                })
            if lines:
                return sorted(lines, key=lambda x: x["name"])
        except Exception:
            pass
        return list(TFL_LINE_CATALOGUE)

    def search_stations(
        self,
        query: str,
        modes: str = "tube,dlr,elizabeth-line,overground,tram",
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """Search TfL StopPoint by station name.

        Args:
            query: Station name fragment (e.g. "King's Cross", "Canary Wharf")
            modes: Comma-separated TfL modes to filter by
            limit: Maximum number of results to return

        Returns:
            List of dicts with keys: id (NaptanId), name, lines (list of line names).
            Returns an empty list on network errors or no results.
        """
        try:
            url = f"{self.base_url}/StopPoint/Search/{requests.utils.quote(query)}"
            response = requests.get(
                url,
                params={"modes": modes, "maxResults": limit},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for match in data.get("matches", [])[:limit]:
                lines = sorted({
                    ln.get("name", ln.get("id", ""))
                    for ln in match.get("lines", [])
                })
                results.append({
                    "id":    match.get("id", ""),
                    "name":  match.get("name", ""),
                    "lines": lines,
                })
            return results
        except Exception:
            return []

    # ── runtime methods ───────────────────────────────────────────────────────

    def get_line_status(self) -> Dict[str, Dict[str, str]]:
        """Fetch current status of the configured TfL lines.

        Returns:
            Dict mapping line display-names to their status and description.
        """
        url = f"{self.base_url}/line/mode/tube,overground,dlr,elizabeth-line,tram/status"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch TfL line status: {str(e)}")

        data = response.json()
        all_lines: Dict[str, Dict[str, str]] = {}

        for line in data:
            try:
                line_name = line["name"]
                statuses = [s["statusSeverityDescription"] for s in line["lineStatuses"]]
                state = " + ".join(sorted(set(statuses)))

                if state == "Good Service":
                    reason = "Nothing to report"
                else:
                    reasons = [
                        s.get("reason", "")
                        for s in line["lineStatuses"]
                        if s.get("reason")
                    ]
                    reason = " *** ".join(reasons) if reasons else "Service disruption"

                all_lines[line_name] = {"status": state, "description": reason}

            except (KeyError, IndexError) as e:
                all_lines[line.get("name", "Unknown")] = {
                    "status": "Unknown",
                    "description": f"Error parsing API data: {str(e)}",
                }

        return {k: all_lines[k] for k in self.key_lines if k in all_lines}

    def get_station_arrivals(self, limit: int = 5) -> Dict[str, Any]:
        """Fetch real-time train arrivals for the configured stations.

        Args:
            limit: Maximum number of arrivals to return across all stations.

        Returns:
            Dict with arrivals list (sorted by time), total found, and stations queried.
        """
        all_arrivals = []

        for station_label, station_id in self.key_stations.items():
            try:
                url = f"{self.base_url}/StopPoint/{station_id}/Arrivals"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                for arrival in response.json():
                    all_arrivals.append({
                        "line":                    arrival["lineName"],
                        "destination":             arrival["destinationName"],
                        "platform":                arrival["platformName"],
                        "time_to_station_seconds": arrival["timeToStation"],
                        "time_to_station_minutes": arrival["timeToStation"] // 60,
                        "station_name":            arrival["stationName"],
                    })

            except requests.RequestException as e:
                print(f"Warning: Failed to fetch arrivals for {station_label}: {str(e)}")
                continue

        all_arrivals.sort(key=lambda x: x["time_to_station_seconds"])

        return {
            "arrivals":         all_arrivals[:limit],
            "total_found":      len(all_arrivals),
            "stations_queried": list(self.key_stations.keys()),
        }
