#!/usr/bin/env python3
"""
Simple entry point to run the WHOOP Health Data application

This script provides a convenient way to start the application
after the package restructuring.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from whoopdata.cli import main

    main()
