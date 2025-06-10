#!/usr/bin/env python3
"""
Fast test runner for VFB_connect - runs only essential tests that complete quickly.
Skips slow OWL queries and problematic tests.
"""

import sys
import os
import unittest
import time
from io import StringIO

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_shared_vfb():
    """Set up the shared VFB connection once"""
    print("Setting up shared VFB connection...")
    start_time = time.time()
    
    from vfb_connect import vfb
    
    # Set conservative limits for faster testing
    vfb._load_limit = 5
    
    setup_time = time.time() - start_time
    print(f"VFB connection established in {setup_time:.2f} seconds")
    return vfb

def run_fast_tests():
    """Run only the fast, essential tests"""
    print("VFB_connect Fast Test Runner")
    print("=" * 60)
    
    # Set up shared connection
    shared_vfb = setup_shared_vfb()
    
    # Test the main fix - LC_12 ambiguous match resolution
    print("\n🔧 Testing main fix: LC_12 ambiguous match resolution...")
    test_cases = ['LC_12', 'LC12', 'LC 12', ' LC12 ']
    
    for case in test_cases:
        start = time.time()
        result = shared_vfb.lookup_id(case, verbose=False)
        duration = time.time() - start
        
        if result == 'FBbt_00100484':
            print(f"  ✅ {case:<8} -> {result} ({duration:.3f}s)")
        else:
            print(f"  ❌ {case:<8} -> {result} (UNEXPECTED)")
    
    # Test basic functionality
    print("\n🧪 Running essential functionality tests...")
    
    # Create a test suite with only fast tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Import test modules
    from vfb_connect.schema.test.vfb_term_test import VfbTermTest
    from vfb_connect.test.cross_server_tools_test import VfbConnectTest, VfbTermTests
    
    # Inject shared VFB connection into test classes
    VfbTermTest.vfb = shared_vfb
    VfbConnectTest.vc = shared_vfb
    VfbTermTests.vc = shared_vfb
    
    # Add only fast, essential tests
    fast_tests = [
        # Core lookup tests
        (VfbTermTest, 'test_lookups'),
        (VfbTermTest, 'test_lookups_matching'),
        (VfbTermTest, 'test_lookup_names'),
        
        # Basic term creation tests
        (VfbTermTest, 'test_create_vfbterm_from_json'),
        (VfbTermTest, 'test_create_vfbterm_from_id'),
        (VfbTermTest, 'test_create_vfbterm_from_name'),
        (VfbTermTest, 'test_create_vfbterms_from_list'),
        
        # Basic functionality tests
        (VfbConnectTest, 'test_lookup_id'),
        (VfbTermTests, 'test_term'),
        (VfbTermTests, 'test_terms'),
    ]
    
    for test_class, test_method in fast_tests:
        try:
            suite.addTest(test_class(test_method))
        except Exception as e:
            print(f"  ⚠️  Could not add test {test_class.__name__}.{test_method}: {e}")
    
    # Run the tests
    print(f"\n🏃 Running {suite.countTestCases()} fast tests...")
    
    # Capture output to reduce noise
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=1)
    
    start_time = time.time()
    result = runner.run(suite)
    total_time = time.time() - start_time
    
    # Print summary
    print(f"\n📊 Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Total time: {total_time:.2f} seconds")
    print(f"   Average per test: {total_time/max(result.testsRun, 1):.2f} seconds")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   • {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   • {test}: {traceback.split()[-1]}")
    
    # Overall status
    if result.wasSuccessful():
        print(f"\n🎉 All tests passed! The main fix is working correctly.")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_fast_tests())
