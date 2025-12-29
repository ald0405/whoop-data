"""
Matplotlib configuration utility for headless operation.

This module ensures matplotlib uses a non-GUI backend to prevent
GUI-related errors when running in background threads or headless environments.
"""

import matplotlib
import os


def configure_matplotlib_headless():
    """
    Configure matplotlib to use a non-GUI backend for headless operation.

    This prevents the "NSWindow should only be instantiated on the main thread!"
    error on macOS and similar GUI-related errors on other platforms.
    """
    # Force matplotlib to use non-interactive Agg backend
    matplotlib.use("Agg", force=True)

    # Ensure we don't try to display plots
    import matplotlib.pyplot as plt

    plt.ioff()  # Turn off interactive mode

    # Suppress GUI warnings
    os.environ["MPLBACKEND"] = "Agg"


def get_safe_matplotlib_imports():
    """
    Return a string containing safe matplotlib imports for PythonREPL.

    Returns:
        str: Python code to safely import and configure matplotlib
    """
    return """
import matplotlib
matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
plt.ioff()  # Turn off interactive mode

# Now safe to import other plotting libraries
import seaborn as sns
"""


# Auto-configure matplotlib when this module is imported
configure_matplotlib_headless()
