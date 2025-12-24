"""Transport status service using TfL (Transport for London) API."""

from typing import Dict, Any
import requests


class TravelAPI:
    """Client for TfL API providing London transport line status."""
    
    def __init__(self):
        """Initialize TravelAPI client.
        
        TfL API is open and doesn't require authentication for basic line status queries.
        """
        self.base_url = "https://api.tfl.gov.uk"
        # Lines relevant for South Quay / Canary Wharf area
        self.key_lines = ["Jubilee", "DLR", "Elizabeth line"]
        # Key stations for arrivals
        self.key_stations = {
            "dlr_south_quay": "940GZZDLSOQ",
            "jubilee_canary_wharf": "940GZZLUCYF",
            "elizabeth_canary_wharf": "910GCANWHRF"
        }
    
    def get_line_status(self) -> Dict[str, Dict[str, str]]:
        """Fetch current status of key TfL lines.
        
        Returns:
            Dict mapping line names to their status and description.
            Status is either "Good Service" or describes the disruption.
            
        Raises:
            Exception: If API request fails
        """
        # Fetch status for Tube, DLR, Elizabeth line, and Overground
        url = f"{self.base_url}/line/mode/tube,overground,dlr,elizabeth-line,tram/status"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch TfL line status: {str(e)}")
        
        data = response.json()
        all_lines = {}
        
        # Parse status for all lines
        for line in data:
            try:
                line_name = line["name"]
                
                # Extract status descriptions
                statuses = [
                    status["statusSeverityDescription"]
                    for status in line["lineStatuses"]
                ]
                
                # Combine multiple statuses if present
                state = " + ".join(sorted(set(statuses)))
                
                # Get disruption reason if not good service
                if state == "Good Service":
                    reason = "Nothing to report"
                else:
                    # Extract reasons from all statuses that have them
                    reasons = [
                        status.get("reason", "")
                        for status in line["lineStatuses"]
                        if status.get("reason")
                    ]
                    reason = " *** ".join(reasons) if reasons else "Service disruption"
                
                all_lines[line_name] = {
                    "status": state,
                    "description": reason
                }
                
            except (KeyError, IndexError) as e:
                # Handle parsing errors gracefully
                all_lines[line.get("name", "Unknown")] = {
                    "status": "Unknown",
                    "description": f"Error parsing API data: {str(e)}"
                }
        
        # Filter to only return key lines relevant to user
        selected_lines = {
            key: all_lines[key]
            for key in self.key_lines
            if key in all_lines
        }
        
        return selected_lines
    
    def get_station_arrivals(self, limit: int = 5) -> Dict[str, Any]:
        """Fetch real-time train arrivals for key stations.
        
        Fetches arrivals from DLR South Quay, Jubilee Line Canary Wharf, 
        and Elizabeth Line Canary Wharf. Merges and sorts by arrival time.
        
        Args:
            limit: Maximum number of arrivals to return (default: 5)
            
        Returns:
            Dict with list of upcoming arrivals sorted by time.
            Each arrival contains: line, destination, platform, minutes, seconds.
            
        Raises:
            Exception: If API request fails
        """
        all_arrivals = []
        
        # Fetch arrivals from each station
        for station_name, station_id in self.key_stations.items():
            try:
                url = f"{self.base_url}/StopPoint/{station_id}/Arrivals"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                station_data = response.json()
                
                # Parse each arrival
                for arrival in station_data:
                    all_arrivals.append({
                        "line": arrival["lineName"],
                        "destination": arrival["destinationName"],
                        "platform": arrival["platformName"],
                        "time_to_station_seconds": arrival["timeToStation"],
                        "time_to_station_minutes": arrival["timeToStation"] // 60,
                        "station_name": arrival["stationName"]
                    })
                    
            except requests.RequestException as e:
                # Log error but continue with other stations
                print(f"Warning: Failed to fetch arrivals for {station_name}: {str(e)}")
                continue
        
        # Sort by arrival time and limit results
        all_arrivals.sort(key=lambda x: x["time_to_station_seconds"])
        
        return {
            "arrivals": all_arrivals[:limit],
            "total_found": len(all_arrivals),
            "stations_queried": list(self.key_stations.keys())
        }
