# Manual

## Project Overview
This repository provides a complete Extract-Transform-Load (ETL) pipeline for WHOOP data. You can:
- Authenticate and fetch data (recovery, sleep, workouts) from the WHOOP API.
- Transform raw JSON records into structured formats.
- Load data into a local SQLite database using SQLAlchemy ORM.
- Perform further analysis with provided sample scripts.

## Prerequisites
- Python 3.9 or higher
- pip (Python package installer)
- SQLite (bundled with Python)

## Installation
1. Clone the repository:
   ```bash
   git clone <repo_url>
   cd <repo_directory>
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows: venv\Scripts\activate
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
1. Create a file named `.env` in the project root:
   ```text
   USERNAME=your_whoop_username
   PASSWORD=your_whoop_password
   ```
2. Ensure that sensitive files like `.env` are listed in `.gitignore` (create one if needed):
   ```gitignore
   .env
   ```

## Database Setup
Run the database setup script to create tables in a SQLite database:
```bash
python db_setup.py
```
- This creates `db/whoop.db` and tables: `cycles`, `sleep`, `recovery`, `workout`.
- **Warning**: Re-running this script will drop and recreate tables, erasing existing data.

## Data Extraction & Loading
Use the provided script to fetch data from the WHOOP API and load it into your database:
```bash
python load_recovery.py
```
- Authenticates using credentials in `.env`.
- Fetches all recovery, sleep, and workout records.
- Transforms each record to match the ORM model.
- Inserts data into the SQLite database.

## Project Structure
```
├── data/                     # Sample CSV files
├── db/                       # SQLite database file (`whoop.db`)
├── models/                   # SQLAlchemy ORM model definitions
│   └── init_models.py
├── services/                 # WHOOP API client module
│   └── whoop_api.py
├── utils/                    # Helper modules for transformation & loading
│   ├── model_transformation.py
│   └── load_into_database.py
├── analysis/                 # Example data extraction & analysis scripts
├── custom_gpt/               # ChatGPT function definitions (YAML/JSON)
├── db_setup.py               # Script to create database tables
├── load_recovery.py          # ETL script: fetch & load WHOOP data
├── crud.py                   # Example CRUD helper functions
├── requirements.txt          # Python dependencies
└── manual.md                 # This manual file
```

## Usage Examples

### Fetching Data via the WHOOP API Client
```python
from services.whoop_api import Whoop

api = Whoop()
api.authenticate()
records = api.make_paginated_request(api.get_endpoint_url('recovery'))
print(records)
```

### Querying the SQLite Database
```python
import sqlite3

conn = sqlite3.connect('db/whoop.db')
cursor = conn.cursor()
cursor.execute('SELECT user_id, recovery_score, created_at FROM recovery LIMIT 5;')
for row in cursor.fetchall():
    print(row)
conn.close()
```

## Extending the Project
- Add or modify CRUD operations in `crud.py` for other models.
- Enhance data transformations in `utils/model_transformation.py`.
- Develop custom analysis scripts in the `analysis/` folder.
- Integrate additional WHOOP API endpoints by updating `services/whoop_api.py`.

## License
This project is licensed under the MIT License. See `LICENSE` for details.