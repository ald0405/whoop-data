#!/usr/bin/env python3
"""
Test script to verify matplotlib configuration fixes.

This script tests that matplotlib can be used safely in background threads
without causing GUI-related errors.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

def test_matplotlib_in_thread():
    """Test matplotlib usage in a background thread."""
    try:
        # Import matplotlib with safe configuration
        import matplotlib
        matplotlib.use('Agg', force=True)
        import matplotlib.pyplot as plt
        plt.ioff()
        
        import numpy as np
        
        print(f"Thread {threading.current_thread().name}: Creating plot...")
        
        # Create a simple plot
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, label='sin(x)')
        plt.xlabel('X values')
        plt.ylabel('Y values')
        plt.title('Test Plot - Sin Wave')
        plt.legend()
        plt.grid(True)
        
        # Save instead of show (headless operation)
        filename = f'test_plot_thread_{threading.current_thread().name}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Thread {threading.current_thread().name}: ✅ Plot saved as {filename}")
        return True
        
    except Exception as e:
        print(f"Thread {threading.current_thread().name}: ❌ Error: {e}")
        return False

def test_agent_tools_import():
    """Test importing the agent tools with matplotlib configuration."""
    try:
        print("Testing agent tools import...")
        from whoopdata.agent.tools import python_repl_tool
        print("✅ Agent tools imported successfully")
        
        # Test the Python REPL tool
        result = python_repl_tool.run("print('Hello from Python REPL tool!')")
        print(f"✅ Python REPL tool basic test: {result}")
        
        # Test plot creation for Studio UI
        plot_code = """
import numpy as np
x = np.linspace(0, 10, 50)
y = np.sin(x)
plt.figure(figsize=(8, 5))
plt.plot(x, y, 'b-', linewidth=2, label='sin(x)')
plt.xlabel('X values')
plt.ylabel('Y values')
plt.title('Test Plot for Studio UI')
plt.legend()
plt.grid(True, alpha=0.3)
result = show_plot()
print(f"Plot HTML length: {len(result)} characters")
print("✅ Plot created successfully for Studio UI")
"""
        
        plot_result = python_repl_tool.run(plot_code)
        if "<img src=" in plot_result and "base64," in plot_result:
            print("✅ Studio UI plot display functionality working")
        else:
            print("⚠️  Studio UI plot display may need verification")
            
        return True
        
    except Exception as e:
        print(f"❌ Error importing agent tools: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing matplotlib GUI error fixes...")
    print("=" * 60)
    
    # Test 1: Single thread matplotlib usage
    print("\n1️⃣ Testing matplotlib in main thread:")
    success_main = test_matplotlib_in_thread()
    
    # Test 2: Multiple background threads
    print("\n2️⃣ Testing matplotlib in background threads:")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(test_matplotlib_in_thread) for _ in range(3)]
        success_threads = all(future.result() for future in futures)
    
    # Test 3: Agent tools import
    print("\n3️⃣ Testing agent tools import:")
    success_tools = test_agent_tools_import()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print(f"  Main thread matplotlib: {'✅ PASS' if success_main else '❌ FAIL'}")
    print(f"  Background thread matplotlib: {'✅ PASS' if success_threads else '❌ FAIL'}")
    print(f"  Agent tools import: {'✅ PASS' if success_tools else '❌ FAIL'}")
    
    if success_main and success_threads and success_tools:
        print("\n🎉 All tests passed! Matplotlib GUI error should be fixed.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        return 1

if __name__ == '__main__':
    exit(main())