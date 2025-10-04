#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

echo "Loading sample data..."
python3 manage.py load_sample_data

echo "Starting server..."
python3 manage.py runserver &
SERVER_PID=$!

# Give the server a moment to start
sleep 5

echo "Testing API endpoints..."
curl -s http://127.0.0.1:8000/api/recoveries/
echo ""
curl -s http://127.0.0.1:8000/api/workouts/runs/
echo ""
curl -s http://127.0.0.1:8000/api/workouts/tennis/
echo ""

echo "Stopping server..."
kill $SERVER_PID
