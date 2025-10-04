# Whoop Data Django Project

This project is a Django-based API for Whoop data. It provides endpoints for recoveries, workouts, and sleep data.

## Setup

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Apply database migrations**:
    ```bash
    python3 manage.py migrate
    ```

## Running the application

To start the development server, run the following command:

```bash
./run.sh
```

The server will be available at `http://127.0.0.1:8000`.

## API Documentation

The API is documented using OpenAPI. You can access the documentation at the following URLs:

*   **Swagger UI**: `http://127.0.0.1:8000/api/schema/swagger-ui/`
*   **ReDoc**: `http://127.0.0.1:8000/api/schema/redoc/`
*   **OpenAPI Schema**: `http://127.0.0.1:8000/api/schema/`

## Testing

To test the API, you can run the following script:

```bash
./test_api.sh
```

This script will:

1.  Load sample data into the database.
2.  Start the development server.
3.  Make requests to the API endpoints to ensure they are working.
4.  Stop the development server.
