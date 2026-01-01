"""Sport ID to name mapping for WHOOP workouts.

WHOOP uses numeric sport IDs that need to be mapped to human-readable names.
This module provides utilities for translating sport_id values to descriptive names.
"""

# WHOOP Sport ID Mapping
# Based on WHOOP API documentation and common sport IDs
SPORT_ID_MAP = {
    0: "Running",
    1: "Cycling",
    16: "Baseball",
    17: "Basketball",
    18: "Rowing",
    19: "Fencing",
    20: "Field Hockey",
    21: "Football",
    22: "Golf",
    24: "Ice Hockey",
    25: "Lacrosse",
    27: "Rugby",
    28: "Sailing",
    29: "Skiing",
    30: "Soccer",
    31: "Softball",
    32: "Squash",
    33: "Swimming",
    34: "Tennis",
    35: "Track & Field",
    36: "Volleyball",
    37: "Water Polo",
    38: "Wrestling",
    39: "Boxing",
    42: "Dance",
    43: "Pilates",
    44: "Yoga",
    45: "Weightlifting",
    47: "Cross Country Skiing",
    48: "Functional Fitness",
    49: "Duathlon",
    51: "Gymnastics",
    52: "Hiking/Rucking",
    53: "Horseback Riding",
    55: "Kayaking",
    56: "Martial Arts",
    57: "Mountain Biking",
    59: "Powerlifting",
    60: "Rock Climbing",
    61: "Paddleboarding",
    62: "Triathlon",
    63: "Walking",
    64: "Surfing",
    65: "Elliptical",
    66: "Stairmaster",
    70: "Meditation",
    71: "Other",
    73: "Diving",
    74: "Operations - Tactical",
    75: "Operations - Medical",
    76: "Operations - Flying",
    77: "Operations - Water",
    82: "Ultimate",
    83: "Climber",
    84: "Jumping Rope",
    85: "Australian Football",
    86: "Skateboarding",
    87: "Coaching",
    88: "Ice Bath",
    89: "Commuting",
    90: "Gaming",
    91: "Snowboarding",
    92: "Motocross",
    93: "Caddying",
    94: "Obstacle Course Racing",
    95: "Motor Racing",
    96: "HIIT",
    97: "Spin",
    98: "Jiu Jitsu",
    99: "Manual Labor",
    100: "Cricket",
    101: "Pickleball",
    102: "Inline Skating",
    103: "Box Fitness",
    104: "Spikeball",
    105: "Wheelchair Pushing",
    106: "Paddle Tennis",
    107: "Barre",
    108: "Stage Performance",
    109: "High Stress Work",
    110: "Parkour",
    111: "Gaelic Football",
    112: "Hurling/Camogie",
    121: "Circus Arts",
    125: "Massage Therapy",
    126: "Watching Sports",
    230: "Breathwork",
    231: "Stretching",
    232: "Strength Trainer",
    233: "Physical Therapy",
}


def get_sport_name(sport_id: int) -> str:
    """Get human-readable sport name from WHOOP sport ID.
    
    Args:
        sport_id: Integer sport ID from WHOOP API
        
    Returns:
        Human-readable sport name, or "Unknown Sport ({sport_id})" if not found
        
    Examples:
        >>> get_sport_name(0)
        'Running'
        >>> get_sport_name(34)
        'Tennis'
        >>> get_sport_name(9999)
        'Unknown Sport (9999)'
    """
    if sport_id is None:
        return "No Sport"
    return SPORT_ID_MAP.get(sport_id, f"Unknown Sport ({sport_id})")


def get_sport_id(sport_name: str) -> int | None:
    """Get WHOOP sport ID from sport name (case-insensitive).
    
    Args:
        sport_name: Human-readable sport name
        
    Returns:
        Integer sport ID, or None if not found
        
    Examples:
        >>> get_sport_id("Running")
        0
        >>> get_sport_id("tennis")
        34
        >>> get_sport_id("unknown")
        None
    """
    # Create reverse mapping (lowercase for case-insensitive matching)
    reverse_map = {name.lower(): sid for sid, name in SPORT_ID_MAP.items()}
    return reverse_map.get(sport_name.lower())


def get_all_sports() -> dict[int, str]:
    """Get complete mapping of all sport IDs to names.
    
    Returns:
        Dictionary mapping sport IDs to sport names
    """
    return SPORT_ID_MAP.copy()


def is_cardio_sport(sport_id: int) -> bool:
    """Check if a sport is primarily cardio-based.
    
    Args:
        sport_id: Integer sport ID from WHOOP API
        
    Returns:
        True if sport is cardio-focused, False otherwise
    """
    cardio_sports = {0, 1, 18, 29, 30, 33, 47, 52, 57, 63, 62, 49, 94}  # Running, Cycling, Rowing, etc.
    return sport_id in cardio_sports


def is_strength_sport(sport_id: int) -> bool:
    """Check if a sport is primarily strength-based.
    
    Args:
        sport_id: Integer sport ID from WHOOP API
        
    Returns:
        True if sport is strength-focused, False otherwise
    """
    strength_sports = {45, 59, 232}  # Weightlifting, Powerlifting, Strength Trainer
    return sport_id in strength_sports


def get_sport_category(sport_id: int) -> str:
    """Get general category for a sport.
    
    Args:
        sport_id: Integer sport ID from WHOOP API
        
    Returns:
        Category name: "Cardio", "Strength", "Team Sport", "Racquet Sport", 
        "Mind-Body", "Recovery", or "Other"
    """
    if sport_id is None:
        return "Unknown"
        
    if is_cardio_sport(sport_id):
        return "Cardio"
    if is_strength_sport(sport_id):
        return "Strength"
    
    # Team sports
    if sport_id in {17, 21, 23, 25, 27, 30, 31, 36, 37, 85, 100, 111, 112}:
        return "Team Sport"
    
    # Racquet sports
    if sport_id in {32, 34, 101, 106}:
        return "Racquet Sport"
    
    # Mind-body
    if sport_id in {43, 44, 70, 230, 231}:
        return "Mind-Body"
    
    # Recovery activities
    if sport_id in {88, 125, 233}:
        return "Recovery"
    
    return "Other"
