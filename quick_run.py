#!/usr/bin/env python3
"""
Quick run script for WHOOP Data project.

This script drops the existing database, initialises it, loads WHOOP data
(recovery, workout, sleep), and starts the FastAPI server.

Usage:
    python quick_run.py
"""
import os
import sys
import subprocess

def run_command(cmd, **kwargs):
    """
    Execute a shell command and exit on failure.

    This function runs the given command via subprocess.run() and
    terminates the script if the command returns a non-zero exit code.

    Args:
        cmd (list[str]): Command and arguments to execute.
        **kwargs: Additional keyword arguments passed to subprocess.run().

    Raises:
        SystemExit: If the command exits with a non-zero status.
    """
    print(f"\n>>> Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)

    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

def main():
    """
    Execute the quick run pipeline.

    This function performs the following steps in order:
    1. Remove the existing SQLite database file, if present.
    2. Initialise the database and create tables.
    3. Load WHOOP data (recovery, workout, sleep) into the database.
    4. Launch the FastAPI server via Uvicorn.

    Raises:
        SystemExit: On failure to remove the database file or subprocess error.
    """
    # Step 6.1: Drop existing database
    db_path = os.path.join('db', 'whoop.db')
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        try:
            os.remove(db_path)
        except OSError as e:
            print(f"Error removing database file: {e}")
            sys.exit(1)

    # Step 6.2: Initialise database (create tables)
    run_command([sys.executable, 'db_setup.py'])

    # Step 7: Load WHOOP data (recovery, workout, sleep)
    run_command([sys.executable, 'extract_transform_load_all.py'])

    # Step 8: Start FastAPI server with Uvicorn
    print("\n>>> Starting FastAPI server at http://127.0.0.1:8000")
    # Replace current process with Uvicorn
    os.execvp(
        sys.executable,
        [
            sys.executable,
            '-m',
            'uvicorn',
            'main:app',
            '--reload',
        ],
    )

if __name__ == '__main__':
    main()