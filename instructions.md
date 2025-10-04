 # Instructions

 ## Rationale
 This project provides a complete pipeline to extract, transform, and load data from the WHOOP API, store it in a local SQLite database, and expose it via a FastAPI server for easy querying and analysis. It streamlines how WHOOP recovery, sleep, and workout data can be programmatically accessed, stored, and consumed.

 ## Project Structure
 - **services/**: WHOOP API client (`whoop_api.py`) for authentication and data fetching.
 - **utils/**: Transformation (`model_transformation.py`) and loading (`load_into_database.py`) helpers.
 - **models/**: SQLAlchemy ORM definitions (`Cycle`, `Sleep`, `Recovery`, `Workout`).
 - **db_setup.py**: Creates the SQLite database (`db/whoop.db`) and tables.
 - **load_recovery.py**, **extract_transform_load_all.py**: ETL scripts to fetch and insert WHOOP data.
 - **api/**: FastAPI routers for recovery and workout endpoints.
 - **schemas/**: Pydantic models for request/response validation.
 - **crud/**: Database query functions for recoveries and workouts.
 - **analysis/**: Example scripts for ad-hoc data analysis.
 - **custom_gpt/**: ChatGPT function definitions for integration.
 - **main.py**: FastAPI application entry point.
 - **requirements.txt**: Python dependencies.
 - **LICENSE**: MIT license terms.

 ## Prerequisites
 - Python 3.9 or higher
 - pip (Python package installer)
 - SQLite (bundled with Python)
 - WHOOP account credentials

 ## Setup & Installation
 1. **Clone the repository**
    ```bash
    git clone <repo_url>
    cd <repo_directory>
    ```
 2. **(Optional) Create a virtual environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate    # On Windows: venv\Scripts\activate
    ```
 3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
 4. **Configure WHOOP credentials**
    Create a `.env` file in the project root:
    ```text
    USERNAME=your_whoop_username
    PASSWORD=your_whoop_password
    ```
    Ensure `.env` is listed in `.gitignore`.

 ## Database Initialization
 Run the database setup script:
 ```bash
 python db_setup.py
 ```
 This creates `db/whoop.db` and tables: `cycles`, `sleep`, `recovery`, `workout`.
 **Warning**: Re-running will reset existing data.

 ## Loading Data (ETL)
 - **Recovery Only**
   ```bash
   python load_recovery.py
   ```
 - **All Workouts**
   ```bash
   python extract_transform_load_all.py
   ```
 These scripts will: authenticate with WHOOP, fetch records, transform them, and insert into the database.

 ## Running the API Server
 Launch the FastAPI application using Uvicorn:
 ```bash
 uvicorn main:app --reload
 ```
 By default, the server runs at `http://127.0.0.1:8000`.

 ## API Endpoints
 **Recovery**
 - `GET /recoveries/` — List recoveries (`skip`, `limit` query parameters)
 - `GET /recoveries/top` — Top N recoveries (`limit`)
 - `GET /recoveries/avg_recoveries/` — Weekly average recovery and RHR (`week`)
 
 **Workouts**
 - `GET /workouts/` — List workouts (`skip`, `limit`)
 - `GET /workouts/get_runs` — List run workouts (`skip`, `limit`)
 - `GET /workouts/get_tennis` — List tennis workouts (`skip`, `limit`)

 ## Analytical Scripts
 Explore and analyze your data with example scripts in the `analysis/` folder:
 - `analysis/sleep_scoring.py` — Sleep performance analysis
 - `analysis/stats_utils.py` — Summary statistics helpers
 - `analysis/whoop_data_extraction.py` — ETL preview utilities

 ## Extending the Project
 - Modify or add transformations in `utils/model_transformation.py`.
 - Extend CRUD operations in `crud/` or add new FastAPI routes in `api/`.
 - Integrate additional WHOOP endpoints via `services/whoop_api.py`.
 - Use `custom_gpt/` definitions to automate tasks with ChatGPT.

 ## License
 This project is licensed under the MIT License. See `LICENSE` for details.