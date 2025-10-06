# Matplotlib GUI Error Fix

## Problem
The LangGraph agent was experiencing crashes on macOS due to matplotlib trying to create GUI windows in background threads. The error was:

```
NSInternalInconsistencyException: 'NSWindow should only be instantiated on the main thread!'
```

This occurred because:
1. The agent runs Python code through `PythonREPLTool` in background threads
2. Matplotlib was trying to use a GUI backend (like TkAgg or Qt) 
3. macOS doesn't allow GUI window creation outside the main thread

## Solution
We implemented a comprehensive fix with multiple layers of protection:

### 1. Global matplotlib configuration
- Set matplotlib to use the 'Agg' backend (non-GUI) before any imports
- Added configuration in `whoop_data/agent/__init__.py`
- Created utility module `whoop_data/utils/matplotlib_config.py`

### 2. Updated analysis modules
- Fixed imports in `whoop_data/analysis/stats_utils.py`
- Fixed imports in `whoop_data/analysis/sleep_scoring.py`
- Configured matplotlib for headless operation before pyplot import

### 3. Custom Python REPL tool
- Created `SafeMatplotlibPythonREPL` class
- Automatically configures matplotlib on startup
- Pre-loads common data science libraries
- Provides clear instructions for plot saving

### 4. Environment setup
- Created `setup_env.py` for environment configuration
- Sets `MPLBACKEND=Agg` environment variable
- Provides verification of configuration

## Key Changes

### Before (problematic):
```python
import matplotlib.pyplot as plt
plt.show()  # Tries to create GUI window
```

### After (safe):
```python
import matplotlib
matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
plt.ioff()  # Turn off interactive mode
plt.savefig('plot.png')  # Save to file instead
```

## Usage Notes

1. **For plotting**: Use `plt.savefig('filename.png')` instead of `plt.show()`
2. **The agent will automatically**: Configure matplotlib safely in the background
3. **Environment setup**: Run `python setup_env.py` to verify configuration
4. **Testing**: Run `python test_matplotlib_fix.py` to verify the fix works

## Files Modified

- `whoop_data/agent/__init__.py` - Global matplotlib configuration
- `whoop_data/agent/tools.py` - Custom Python REPL with safe matplotlib
- `whoop_data/analysis/stats_utils.py` - Fixed matplotlib imports
- `whoop_data/analysis/sleep_scoring.py` - Fixed matplotlib imports
- `whoop_data/utils/matplotlib_config.py` - New utility module
- `setup_env.py` - Environment setup script
- `test_matplotlib_fix.py` - Verification tests

## Verification

The fix has been tested and verified to:
✅ Work in main thread
✅ Work in background threads  
✅ Work with the LangGraph agent
✅ Allow plot creation and saving
✅ Prevent GUI-related crashes

The agent should now run without matplotlib-related crashes on macOS.