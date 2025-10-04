<!-- tutorial.md: Step-by-step guide to set up, load, and run the Whoop Data FastAPI project -->
# Tutorial

This tutorial explains how to set up the project, configure the database, load WHOOP data, and run the FastAPI server.

## 1. Prerequisites
- Python 3.9 or higher
- pip (Python package installer)
- SQLite (bundled with Python)
- WHOOP account credentials

## 2. Clone the Repository
```bash
git clone <repo_url>
cd <repo_directory>
```  

## 3. (Optional) Create & Activate a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```  

## 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```  

## 5. Configure WHOOP Credentials
Create a file named `.env` in the project root with:
```text
USERNAME=your_whoop_username
PASSWORD=your_whoop_password
```
Ensure `.env` is listed in `.gitignore` to avoid committing sensitive data.

## 6. Database Setup

### 6.1 Drop Existing Database (if any)
Since upsert functionality is not available, drop the existing database before re-population:
```bash
rm -rf db/whoop.db
```  

### 6.2 Initialize Database
Run the setup script to create a fresh SQLite database and tables:
```bash
python db_setup.py
```  
This creates `db/whoop.db` and the tables: `cycles`, `sleep`, `recovery`, `workout`.

## 7. Load WHOOP Data

### 7.1 Load Recovery Data Only
```bash
python load_recovery.py
```  

### 7.2 Load All Data (Recovery, Workout, Sleep)
```bash
python extract_transform_load_all.py
```  
These scripts will:
- Authenticate with the WHOOP API using `.env` credentials.
- Fetch paginated records for each data type.
- Transform raw JSON into ORM-friendly dicts.
- Insert records into the SQLite database.

## 8. Run the FastAPI Server
Start the server with Uvicorn:
```bash
uvicorn main:app --reload
```  
The API will be available at `http://127.0.0.1:8000`.

## 9. API Endpoints
- **Recoveries**
  - `GET /recoveries/` — List recoveries (`skip` & `limit` query parameters)
  - `GET /recoveries/top` — Top N recoveries (`limit`)
  - `GET /recoveries/avg_recoveries/` — Weekly average recovery (`week`)
- **Workouts**
  - `GET /workouts/` — List all workouts (`skip`, `limit`)
  - `GET /workouts/get_runs` — List running workouts (`skip`, `limit`)
  - `GET /workouts/get_run_trimp` — Runs with TRIMP score (`skip`, `limit`)
  - `GET /workouts/get_tennis` — List tennis workouts (`skip`, `limit`)
- **Sleep**
  - `GET /sleep/` — List sleep records (`skip`, `limit`)

## 10. Next Steps
- Implement upsert functionality to avoid dropping and rebuilding the database each run.
- Extend or customize CRUD operations in the `crud/` directory.
- Add or modify API routes under the `api/` directory.
- Enhance data transformations in `utils/model_transformation.py`.
- Add automated tests or CI pipelines as needed.