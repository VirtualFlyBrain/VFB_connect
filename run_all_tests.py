#!/usr/bin/env python3
"""
Unified test runner for VFB_connect that shares VFB connection across all test modules.
This optimizes CI/CD performance by avoiding multiple VFB connection setups.
"""

import unittest
import sys
import os
import time
from pathlib import Path

# Add src to path so we can import modules
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main test runner - simplified approach"""
    print("VFB_connect Unified Test Runner")
    print("=" * 60)
    
    total_start_time = time.time()
    
    # Set up shared VFB connection once
    print("Setting up shared VFB connection...")
    connection_start = time.time()
    
    from vfb_connect import vfb
    vfb._load_limit = 10  # Limit results for faster testing
    
    connection_time = time.time() - connection_start
    print(f"VFB connection established in {connection_time:.2f} seconds")
    
    # Import all test modules (this triggers the optimized setUpClass methods we created)
    test_modules = [
        'vfb_connect.owl.test.query_tools_test',
        'vfb_connect.test.cross_server_tools_test', 
        'vfb_connect.neo.test.neo_tools_test',
        'vfb_connect.schema.test.vfb_term_test'
    ]
    
    print(f"\nImporting {len(test_modules)} test modules...")
    for module_name in test_modules:
        try:
            __import__(module_name)
            print(f"✅ Imported {module_name}")
        except Exception as e:
            print(f"❌ Failed to import {module_name}: {e}")
            return 1
    
    # Discover and run all tests
    print(f"\nDiscovering and running tests...")
    loader = unittest.TestLoader()
    start_dir = str(src_path)
    
    # Discover all tests
    suite = unittest.TestSuite()
    for module_name in test_modules:
        module = sys.modules[module_name]
        module_suite = loader.loadTestsFromModule(module)
        suite.addTest(module_suite)
    
    # Run all tests
    runner = unittest.TextTestRunner(
        verbosity=2, 
        stream=sys.stdout, 
        buffer=False,
        failfast=False
    )
    
    print(f"Running tests...")
    test_start = time.time()
    result = runner.run(suite)
    test_duration = time.time() - test_start
    
    # Summary
    total_duration = time.time() - total_start_time
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Connection setup time: {connection_time:.2f} seconds")
    print(f"Test execution time: {test_duration:.2f} seconds") 
    print(f"Total execution time: {total_duration:.2f} seconds")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split(chr(10))[-2] if traceback else 'Unknown'}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split(chr(10))[-2] if traceback else 'Unknown'}")
    
    # Exit with appropriate code
    if result.failures or result.errors:
        print("❌ Some tests failed")
        return 1
    else:
        print("🎉 All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
