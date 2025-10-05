"""
Utilities package for whoop_data.

This package contains utility modules for configuration and helper functions.
"""

from .matplotlib_config import configure_matplotlib_headless, get_safe_matplotlib_imports

__all__ = ['configure_matplotlib_headless', 'get_safe_matplotlib_imports']