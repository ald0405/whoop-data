# Testing Guide for WHOOP Data Platform

## Quick Verification Checklist

### ✅ 1. Test ETL Pipeline (Data Loading)

**Option A: Full Pipeline with Server**
```bash
python run_app.py
# Choose option 1: Run complete pipeline
# Watch for success messages showing data loaded
```

**Option B: ETL Only**
```bash
python run_app.py
# Choose option 3: Only run data pipeline
```

**Expected Output:**
- ✅ Database tables created
- ✅ WHOOP authentication successful (browser popup)
- ✅ Withings authentication successful (browser popup)
- ✅ Data loaded: recovery, workouts, sleep, weight records
- 📈 Shows count of loaded records
- ❌ Shows count of any errors

**Quick Database Check:**
```bash
python -c "
from whoopdata.database.database import SessionLocal
from whoopdata.models.models import Recovery, Workout, Sleep, WithingsWeight

db = SessionLocal()
print(f'Recovery records: {db.query(Recovery).count()}')
print(f'Workout records: {db.query(Workout).count()}')
print(f'Sleep records: {db.query(Sleep).count()}')
print(f'Weight records: {db.query(WithingsWeight).count()}')
db.close()
"
```

---

### ✅ 2. Test API Server

**Start the Server:**
```bash
# If not already running from step 1
python run_app.py
# Choose option 2: Skip data loading and just start server
```

**Test Endpoints:**

```bash
# Test WHOOP endpoints
curl http://localhost:8000/recovery/latest
curl http://localhost:8000/workout/latest
curl http://localhost:8000/sleep/latest

# Test Withings endpoints
curl http://localhost:8000/withings/weight/latest
curl http://localhost:8000/withings/heart-rate/latest

# Check API docs
open http://localhost:8000/docs  # macOS
```

**Expected Results:**
- ✅ Each endpoint returns JSON data
- ✅ No 500 errors
- ✅ Data contains expected fields (recovery_score, strain, weight, etc.)
- ✅ API docs page loads with all endpoints listed

---

### ✅ 3. Test Chat Interface

**Start the Chat:**
```bash
# Requires API server running on port 8000
python chat_app.py
```

**Or start both together:**
```bash
python start_health_chat.py
```

**Test Questions:**

1. **Recovery data:**
   ```
   Get my latest recovery data
   ```
   Expected: Returns recovery score, HRV, RHR, sleep quality

2. **Tennis workouts:**
   ```
   Show me my tennis workouts from 2025
   ```
   Expected: List of tennis sessions with dates, strain, duration

3. **Weight trends:**
   ```
   What's my weight trend over the last 30 days?
   ```
   Expected: Weight measurements with dates and trend analysis

4. **Sleep analysis:**
   ```
   How has my sleep been this week?
   ```
   Expected: Sleep scores, efficiency, duration analysis

5. **Running data:**
   ```
   Show me my running performance with TRIMP scores
   ```
   Expected: Running workouts with TRIMP calculations

**Expected Chat Behavior:**
- ✅ Agent responds within 5-10 seconds
- ✅ Responses are concise and analytical (Hannah Fry + David Goggins style)
- ✅ Agent doesn't loop infinitely (max 3 iterations)
- ✅ Agent asks at most 1 follow-up question
- ✅ No crashes or error messages
- ❌ Charts won't display (known limitation, but shouldn't crash)

---

## Withings Health Check (Quick)

- Force re-auth and validate token:
  ```bash
  uv run whoop-withings-auth
  ```
- Verify API is reachable and data is recent:
  ```bash
  curl http://localhost:8000/auth/withings/status
  ```

## Detailed Testing

### Test 1: Virtual Environment Check

```bash
# Verify you're in the correct venv
which python
# Should show: /Users/asiflaldin/Documents/Projects/whoop-data/venv/bin/python

# Check dependencies
pip list | grep -E "fastapi|gradio|langchain|openai"
```

**Expected:**
- fastapi >= 0.104.0
- gradio >= 4.0.0
- langchain-openai
- openai

---

### Test 2: Environment Variables

```bash
# Check .env file exists and has required keys
cat .env | grep -E "WHOOP|WITHINGS|OPENAI"
```

**Must have:**
- WHOOP_CLIENT_ID
- WHOOP_CLIENT_SECRET
- WITHINGS_CLIENT_ID
- WITHINGS_CLIENT_SECRET
- OPENAI_API_KEY

---

### Test 3: Database Integrity

```bash
python -c "
from whoopdata.database.database import SessionLocal
from whoopdata.models.models import Recovery, Workout, Sleep
from datetime import datetime

db = SessionLocal()

# Check for 2025 data
workouts_2025 = db.query(Workout).filter(
    Workout.created_at >= datetime(2025, 1, 1)
).count()

recoveries_2025 = db.query(Recovery).filter(
    Recovery.created_at >= datetime(2025, 1, 1)
).count()

print(f'2025 Workouts: {workouts_2025}')
print(f'2025 Recoveries: {recoveries_2025}')

# Should have data
assert workouts_2025 > 0, 'No 2025 workout data!'
assert recoveries_2025 > 0, 'No 2025 recovery data!'

print('✅ 2025 data verified')
db.close()
"
```

---

### Test 4: Agent Tools

```bash
python -c "
import asyncio
from whoopdata.agent.graph import run_agent

async def test():
    result = await run_agent('Get my latest workout', thread_id='test_thread')
    messages = result.get('messages', [])
    print(f'Messages: {len(messages)}')
    if messages:
        print(f'Last response: {messages[-1].content[:200]}...')
    return len(messages) > 0

success = asyncio.run(test())
print(f'Agent test: {'✅ PASS' if success else '❌ FAIL'}')
"
```

---

## Troubleshooting

### Issue: "Module not found" errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### Issue: Database errors
```bash
# Recreate database
rm -rf db/whoop.db
python run_app.py  # Choose option 1
```

### Issue: API server won't start
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill existing process if needed
kill -9 <PID>
```

### Issue: Chat interface errors
```bash
# Verify API server is running
curl http://localhost:8000/recovery/latest

# Check agent imports
python -c "from whoopdata.agent.graph import run_agent; print('✅ Agent imports OK')"
```

### Issue: Authentication failures
```bash
# Remove old tokens and re-authenticate
rm .whoop_tokens.json .withings_tokens.json
python run_app.py  # Will trigger new OAuth flow
```

---

## Success Criteria

✅ **ETL Working:**
- Database created at `db/whoop.db`
- Multiple records in recovery, workout, sleep tables
- 2025 data present
- No critical errors during load

✅ **API Working:**
- Server starts on port 8000
- All endpoints return valid JSON
- Latest endpoints return most recent records
- API docs accessible

✅ **Chat Working:**
- Interface loads on port 7860
- Agent responds to queries
- No infinite loops (stops after 3 iterations)
- Responses match personality (concise, analytical, tough love)
- Tool calls execute successfully

---

## Quick Test Script

Run this to test everything at once:

```bash
# Save as test_all.sh
#!/bin/bash

echo "🧪 Testing WHOOP Data Platform"
echo "================================"

# 1. Check environment
echo "✓ Checking virtual environment..."
source venv/bin/activate || { echo "❌ No venv found"; exit 1; }

# 2. Check dependencies
echo "✓ Checking dependencies..."
pip show fastapi gradio langchain-openai > /dev/null || { echo "❌ Missing dependencies"; exit 1; }

# 3. Check database
echo "✓ Checking database..."
python -c "from whoopdata.database.database import engine; print('✅ DB OK')" || { echo "❌ DB error"; exit 1; }

# 4. Check agent
echo "✓ Checking agent..."
python -c "from whoopdata.agent.graph import run_agent; print('✅ Agent OK')" || { echo "❌ Agent error"; exit 1; }

echo ""
echo "✅ All checks passed!"
echo ""
echo "Next steps:"
echo "1. Run ETL: python run_app.py (choose option 1)"
echo "2. Test API: curl http://localhost:8000/recovery/latest"
echo "3. Test Chat: python chat_app.py"
```

Make it executable:
```bash
chmod +x test_all.sh
./test_all.sh
```
