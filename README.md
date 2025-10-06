# WHOOP Health Data Platform

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive health data integration platform for WHOOP and Withings devices with FastAPI backend.

## Project Structure

```
whoop-data/
├── whoop_data/               # Main package directory
│   ├── __init__.py
│   ├── start.py              # Main application launcher
│   ├── etl.py                # ETL pipeline logic
│   ├── database.py           # Database setup utilities  
│   ├── utils.py              # Database loading utilities
│   ├── model_transformation.py # Data transformation functions
│   ├── api/                  # FastAPI routes
│   │   ├── __init__.py
│   │   ├── recovery_routes.py
│   │   ├── sleep_routes.py
│   │   ├── workout_routes.py
│   │   └── withings_routes.py
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   └── models.py
│   ├── clients/              # API clients for WHOOP and Withings
│   │   ├── __init__.py
│   │   ├── whoop_client.py
│   │   └── withings_client.py
│   ├── schemas/              # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── recovery.py
│   │   ├── sleep.py
│   │   └── workout.py
│   ├── crud/                 # Database CRUD operations
│   │   ├── __init__.py
│   │   ├── recovery.py
│   │   ├── sleep.py
│   │   └── workout.py
│   ├── tests/                # Test files
│   │   ├── __init__.py
│   │   └── test_withings.py
│   └── analysis/             # Analysis scripts and notebooks
│       ├── __init__.py
│       └── ...
├── scripts/                  # Helper scripts
│   ├── create_tables.py      # Database table creation
│   └── run_etl.py           # Standalone ETL runner
├── django_whoop/             # Django project (optional)
├── main.py                   # FastAPI application entry point
├── run_app.py               # Simple application runner
├── setup.py                 # Package configuration
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md

```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Environment Variables

Create a `.env` file with your credentials:

```bash
# WHOOP credentials
USERNAME=your_whoop_email@example.com
PASSWORD=your_whoop_password

# Withings OAuth credentials
WITHINGS_CLIENT_ID=your_withings_client_id
WITHINGS_CLIENT_SECRET=your_withings_client_secret
WITHINGS_REDIRECT_URI=http://localhost:8080/callback
```

### 3. Run the Application

**Option 1: Using the simple runner**
```bash
./run_app.py
```

**Option 2: Using the package directly**
```bash
python -m whoop_data.start
```

**Option 3: After installing the package**
```bash
pip install -e .
whoop-start
```

### 4. Access the API

Once running, the FastAPI server will be available at:
- **Main API**: http://localhost:8000
- **Interactive Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## API Endpoints

### WHOOP Data
- `GET /recovery` - Recovery scores and metrics
- `GET /recovery/latest` - Most recent recovery
- `GET /workout` - Workout data and strain
- `GET /workout/latest` - Most recent workout
- `GET /sleep` - Sleep performance data  
- `GET /sleep/latest` - Most recent sleep

### Withings Data
- `GET /withings/weight` - Weight and body composition
- `GET /withings/weight/latest` - Most recent weight
- `GET /withings/weight/stats` - Weight statistics
- `GET /withings/heart-rate` - Heart rate and blood pressure
- `GET /withings/heart-rate/latest` - Most recent heart rate
- `GET /withings/summary` - Withings data summary

## Development

### Testing Withings Integration

```bash
python whoop_data/tests/test_withings.py
```

### Running ETL Pipeline Only

```bash
python scripts/run_etl.py
```

### Creating Database Tables

```bash
python scripts/create_tables.py
```

## WHOOP Data Summary

### Physiological Cycles
- Activity is referenced in the context of a Physiological Cycle (Cycle for short).
- **Current Cycle:** Only has a Start Time. Past Cycles have both start and end times.
- A physiological day on WHOOP begins when you fall asleep one night and ends when you fall asleep the following night.

### Recovery
- Daily measure of body preparedness to perform.
- **Recovery score:** Percentage between 0 - 100% calculated in the morning.
- Calculated using previous day's data including RHR, HRV, respiratory rate, sleep quality, etc.
- **GREEN** (67-100%): Well recovered and primed to perform.
- **YELLOW** (34-66%): Maintaining and ready for moderate strain.
- **RED** (0-33%): Indicates the need for rest.

### Sleep Tracking
- Tracks sleep duration and stages: Light, REM, and Deep sleep.
- Calculates sleep need based on Sleep Debt and previous day's activity.

### Strain
- Measurement of stress on the body, scored on a 0 to 21 scale.
- Based on [Strain Borg Scale of Perceived Exertion](https://www.cdc.gov/physicalactivity/basics/measuring/exertion.htm).
- Strain scores tracked continuously throughout the day and during workouts.

### Workout Tracking
- WHOOP tracks workouts and measures accumulated Strain over each workout.

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/README.md) directory:

- **[Technical Documentation](docs/technical/)** - Development logs, API changes, and troubleshooting
- **[Features Documentation](docs/features/)** - Feature specifications and configurations

For API documentation, visit http://localhost:8000/docs after starting the application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
