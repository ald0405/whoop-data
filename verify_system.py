#!/usr/bin/env python3
"""
Quick System Verification Script
Tests that ETL, API, and Agent components are working correctly
"""

import sys
import subprocess
from pathlib import Path


def check_mark(passed):
    return "✅" if passed else "❌"


def test_imports():
    """Test that all critical imports work"""
    print("\n" + "=" * 60)
    print("📦 Testing Python Imports")
    print("=" * 60)

    tests = []

    # Test database imports
    try:
        from whoopdata.database.database import SessionLocal, engine

        print(f"{check_mark(True)} Database imports OK")
        tests.append(True)
    except Exception as e:
        print(f"{check_mark(False)} Database imports failed: {e}")
        tests.append(False)

    # Test model imports
    try:
        from whoopdata.models.models import Recovery, Workout, Sleep, WithingsWeight

        print(f"{check_mark(True)} Model imports OK")
        tests.append(True)
    except Exception as e:
        print(f"{check_mark(False)} Model imports failed: {e}")
        tests.append(False)

    # Test ETL imports
    try:
        from whoopdata.etl import run_complete_etl

        print(f"{check_mark(True)} ETL imports OK")
        tests.append(True)
    except Exception as e:
        print(f"{check_mark(False)} ETL imports failed: {e}")
        tests.append(False)

    # Test agent imports
    try:
        from whoopdata.agent.graph import run_agent
        from whoopdata.agent.tools import AVAILABLE_TOOLS

        print(f"{check_mark(True)} Agent imports OK")
        print(f"    Available tools: {len(AVAILABLE_TOOLS)}")
        tests.append(True)
    except Exception as e:
        print(f"{check_mark(False)} Agent imports failed: {e}")
        tests.append(False)

    # Test API imports
    try:
        from main import app

        print(f"{check_mark(True)} FastAPI app imports OK")
        tests.append(True)
    except Exception as e:
        print(f"{check_mark(False)} FastAPI imports failed: {e}")
        tests.append(False)

    # Test chat imports
    try:
        import gradio as gr

        print(f"{check_mark(True)} Gradio imports OK")
        tests.append(True)
    except Exception as e:
        print(f"{check_mark(False)} Gradio imports failed: {e}")
        tests.append(False)

    return all(tests)


def test_database():
    """Test database connection and check for data"""
    print("\n" + "=" * 60)
    print("🗄️  Testing Database")
    print("=" * 60)

    try:
        from whoopdata.database.database import SessionLocal
        from whoopdata.models.models import Recovery, Workout, Sleep, WithingsWeight
        from datetime import datetime

        db = SessionLocal()

        # Count records
        recovery_count = db.query(Recovery).count()
        workout_count = db.query(Workout).count()
        sleep_count = db.query(Sleep).count()
        weight_count = db.query(WithingsWeight).count()

        print(f"{check_mark(True)} Database connection successful")
        print(f"    Recovery records: {recovery_count}")
        print(f"    Workout records: {workout_count}")
        print(f"    Sleep records: {sleep_count}")
        print(f"    Weight records: {weight_count}")

        # Check for 2025 data
        workouts_2025 = db.query(Workout).filter(Workout.created_at >= datetime(2025, 1, 1)).count()

        recoveries_2025 = (
            db.query(Recovery).filter(Recovery.created_at >= datetime(2025, 1, 1)).count()
        )

        print(f"\n    2025 Workouts: {workouts_2025}")
        print(f"    2025 Recoveries: {recoveries_2025}")

        db.close()

        has_data = recovery_count > 0 or workout_count > 0 or sleep_count > 0 or weight_count > 0

        if not has_data:
            print(f"\n{check_mark(False)} Database is empty - run ETL to load data")
            print("    Run: python run_app.py (choose option 1 or 3)")
            return False

        return True

    except Exception as e:
        print(f"{check_mark(False)} Database test failed: {e}")
        return False


def test_environment():
    """Test environment variables"""
    print("\n" + "=" * 60)
    print("🔐 Testing Environment Variables")
    print("=" * 60)

    import os
    from pathlib import Path

    env_file = Path(".env")

    if not env_file.exists():
        print(f"{check_mark(False)} .env file not found")
        print("    Create .env with API credentials (see .env.example)")
        return False

    print(f"{check_mark(True)} .env file exists")

    required_vars = [
        "WHOOP_CLIENT_ID",
        "WHOOP_CLIENT_SECRET",
        "WITHINGS_CLIENT_ID",
        "WITHINGS_CLIENT_SECRET",
        "OPENAI_API_KEY",
    ]

    # Load .env
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        # Try reading manually if dotenv not installed
        with open(".env") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    missing = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing.append(var)
            print(f"{check_mark(False)} {var} not set")
        else:
            print(f"{check_mark(True)} {var} is set")

    if missing:
        print(f"\n{check_mark(False)} Missing environment variables")
        return False

    return True


def test_agent():
    """Test agent with a simple query"""
    print("\n" + "=" * 60)
    print("🤖 Testing Agent")
    print("=" * 60)

    try:
        import asyncio
        from whoopdata.agent.graph import run_agent

        async def run_test():
            print("    Running test query: 'test'")
            result = await run_agent("test", thread_id="verify_test")
            messages = result.get("messages", [])
            return len(messages) > 0

        success = asyncio.run(run_test())

        if success:
            print(f"{check_mark(True)} Agent executed successfully")
            return True
        else:
            print(f"{check_mark(False)} Agent returned no messages")
            return False

    except Exception as e:
        print(f"{check_mark(False)} Agent test failed: {e}")
        return False


def test_api_routes():
    """Test that API routes are defined"""
    print("\n" + "=" * 60)
    print("🌐 Testing API Routes")
    print("=" * 60)

    try:
        from main import app

        routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                routes.append((route.path, list(route.methods)))

        print(f"{check_mark(True)} Found {len(routes)} API routes")

        # Check for critical routes
        critical_paths = ["/recovery/latest", "/workout/latest", "/withings/weight/latest"]
        for path in critical_paths:
            exists = any(path in route[0] for route in routes)
            print(f"    {check_mark(exists)} {path}")

        return True

    except Exception as e:
        print(f"{check_mark(False)} API route test failed: {e}")
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    total = len(results)
    passed = sum(results.values())

    for test_name, result in results.items():
        print(f"{check_mark(result)} {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All systems operational!")
        print("\nNext steps:")
        print("  1. ETL: python run_app.py (choose option 1)")
        print("  2. Chat: python chat_app.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. See above for details.")
        return 1


def main():
    """Run all verification tests"""
    print("🏥 WHOOP Data Platform - System Verification")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "Environment": test_environment(),
        "Database": test_database(),
        "API Routes": test_api_routes(),
        "Agent": test_agent(),
    }

    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
