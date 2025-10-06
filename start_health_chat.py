#!/usr/bin/env python3
"""
Health Data Chat Launcher

Starts both the FastAPI data server and Gradio chat interface.
"""

import subprocess
import sys
import time
import signal
import os
from multiprocessing import Process
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()

def check_api_server():
    """Check if the API server is running."""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_api_server():
    """Start the FastAPI server."""
    console.print("🌐 Starting FastAPI Health Data Server...")
    
    # Check if already running
    if check_api_server():
        console.print("✅ API server already running on http://localhost:8000")
        return None
    
    # Start the API server
    process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "app:app", 
        "--host", "0.0.0.0", 
        "--port", "8000",
        "--reload"
    ], cwd=os.getcwd())
    
    # Wait for server to start
    console.print("⏳ Waiting for API server to start...")
    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        if check_api_server():
            console.print("✅ API server started on http://localhost:8000")
            return process
        console.print(f"   Checking... ({i+1}/30)")
    
    console.print("❌ API server failed to start")
    return process

def start_chat_interface():
    """Start the Gradio chat interface."""
    console.print("💬 Starting Chat Interface...")
    
    process = subprocess.Popen([
        sys.executable, "chat_app.py"
    ], cwd=os.getcwd())
    
    console.print("✅ Chat interface starting on http://localhost:7860")
    return process

def main():
    """Launch both services."""
    console.print(Panel.fit(
        "🏥 Health Data Chat System\n"
        "Starting API Server + Chat Interface",
        title="🚀 Launcher"
    ))
    
    processes = []
    
    try:
        # Start API server first
        api_process = start_api_server()
        if api_process:
            processes.append(api_process)
        
        # Wait a bit for API to stabilize
        time.sleep(2)
        
        # Start chat interface
        chat_process = start_chat_interface()
        processes.append(chat_process)
        
        # Show status
        console.print(Panel(
            "🎉 Services Running!\n\n"
            "• API Server: http://localhost:8000\n"
            "• API Docs: http://localhost:8000/docs\n"
            "• Chat Interface: http://localhost:7860\n\n"
            "Press Ctrl+C to stop all services",
            title="✅ Ready"
        ))
        
        # Wait for interrupt
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        console.print("\n🛑 Shutting down services...")
        
        # Kill all processes
        for process in processes:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
        
        console.print("✅ All services stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()