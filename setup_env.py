#!/usr/bin/env python3
"""
Environment setup script for WHOOP Health Data Agent.

This script configures the environment for headless operation,
particularly ensuring matplotlib works correctly in background threads.
"""

import os
import sys

def setup_matplotlib_environment():
    """Set environment variables for matplotlib headless operation."""
    # Force matplotlib to use non-GUI backend
    os.environ['MPLBACKEND'] = 'Agg'
    
    # Prevent matplotlib from trying to access the display
    os.environ['DISPLAY'] = ''
    
    # For macOS, prevent NSWindow creation outside main thread
    os.environ['PYTHONPATH'] = os.pathsep.join([
        os.environ.get('PYTHONPATH', ''),
        os.path.dirname(os.path.abspath(__file__))
    ]).strip(os.pathsep)

def setup_python_environment():
    """Configure Python environment for the agent."""
    # Disable Python buffering for better logging
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Set warnings to be less verbose
    os.environ['PYTHONWARNINGS'] = 'ignore'

def main():
    """Main setup function."""
    print("Setting up environment for WHOOP Health Data Agent...")
    
    setup_matplotlib_environment()
    setup_python_environment()
    
    print("✅ Matplotlib configured for headless operation")
    print("✅ Python environment configured")
    print("✅ Environment setup complete!")
    
    # Verify matplotlib configuration
    try:
        import matplotlib
        backend = matplotlib.get_backend()
        print(f"✅ Matplotlib backend: {backend}")
        if backend.lower() == 'agg':
            print("✅ Safe non-GUI backend confirmed")
        else:
            print(f"⚠️  Warning: Backend '{backend}' may cause GUI issues")
    except ImportError:
        print("⚠️  Warning: matplotlib not installed")

if __name__ == '__main__':
    main()