#!/usr/bin/env python3
"""
ParcelFlow Frontend Server
Run this file to start the Flask server
"""
import os
import sys

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

if __name__ == "__main__":
    # Development server
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
