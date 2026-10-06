"""Pytest configuration to ensure assignment modules are on sys.path."""

import os
import sys

# Add scraping_assignment project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
