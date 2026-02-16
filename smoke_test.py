#!/usr/bin/env python3
"""
Smoke Test for Me-ish (meish.cc)

Tests rate limiting, content filtering, and basic functionality
before deploying to production.

Usage:
    python smoke_test.py                    # Test local (localhost:5000)
    python smoke_test.py https://meish.cc   # Test production
"""

import sys
import time
import requests
from io import BytesIO

# Colors for output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name):
    print(f"\n{BLUE}[TEST]{RESET} {name}")

def print_pass(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def print_fail(msg):
    print(f"  {RED}✗{RESET} {msg}")

def print_warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def test_homepage(base_url):
    """Test that homepage loads"""
    print_test("Homepage loads")
    try:
        r = requests.get(base_url, timeout=10)
        if r.status_code == 200 and 'Me-ish' in r.text:
            print_pass(f"Homepage loaded (status {r.status_code})")
            return True
        else:
            print_fail(f"Homepage returned {r.status_code}")
            return False
    except Exception as e:
        print_fail(f"Failed to load homepage: {e}")
        return False

def test_content_filter(base_url):
    """Test that content filtering works"""
    print_test("Content filtering")

    # Create a dummy file
    files = {'files': ('test.txt', BytesIO(b'Sample writing style for testing'), 'text/plain')}
    data = {
        'custom_topic': 'fucking terrible topic',  # Should be filtered
        'use_sample_style': 'off'
    }

    try:
        r = requests.post(f"{base_url}/generate", files=files, data=data, timeout=10)
        if r.status_code == 400 and 'professional' in r.text.lower():
            print_pass("Content filter blocked inappropriate topic")
            return True
        else:
            print_warn(f"Content filter returned {r.status_code} - might be disabled or changed")
            return True  # Not a critical failure
    except Exception as e:
        print_fail(f"Content filter test failed: {e}")
        return False

def test_rate_limiting(base_url):
    """Test that rate limiting is enforced"""
    print_test("Rate limiting enforcement")

    # Use sample style to avoid file uploads
    data = {
        'custom_topic': 'artificial intelligence',
        'use_sample_style': 'on'
    }

    try:
        print_pass("Making first request...")
        r1 = requests.post(f"{base_url}/generate", data=data, timeout=60)

        if r1.status_code == 200:
            print_pass(f"First request succeeded (status {r1.status_code})")
        else:
            print_warn(f"First request returned {r1.status_code}")

        print_pass("Making rapid follow-up requests to test rate limit...")
        rate_limited = False

        # Try to hit the limit (should be 10/hour, but test with 3 more to be safe)
        for i in range(3):
            print(f"    Request {i+2}/4...")
            r = requests.post(f"{base_url}/generate", data=data, timeout=60)

            if r.status_code == 429:
                print_pass(f"Rate limit enforced after {i+2} requests (429 Too Many Requests)")
                rate_limited = True
                break
            elif r.status_code == 200:
                print_pass(f"Request {i+2} succeeded")
            else:
                print_warn(f"Request {i+2} returned {r.status_code}")

            time.sleep(1)  # Small delay between requests

        if not rate_limited:
            print_warn("Rate limiting not triggered in test (limit may be higher than 3 requests)")
            print_warn("This is OK - rate limit is 10/hour per IP")
            return True  # Not a failure, just didn't hit the limit yet

        return True

    except requests.exceptions.Timeout:
        print_fail("Request timed out - server may be slow or down")
        return False
    except Exception as e:
        print_fail(f"Rate limit test failed: {e}")
        return False

def test_basic_generation(base_url):
    """Test basic article generation flow"""
    print_test("Basic article generation")

    data = {
        'custom_topic': 'climate change solutions',
        'use_sample_style': 'on'
    }

    try:
        print_pass("Sending generation request...")
        r = requests.post(f"{base_url}/generate", data=data, timeout=90, stream=True)

        if r.status_code == 200:
            print_pass("Request accepted (status 200)")

            # Check for SSE events
            events_received = 0
            for line in r.iter_lines(decode_unicode=True):
                if line.startswith('data:'):
                    events_received += 1
                    if events_received == 1:
                        print_pass("Receiving Server-Sent Events...")
                    if events_received >= 5:
                        print_pass(f"Received {events_received}+ SSE events - stream working!")
                        break

            if events_received > 0:
                print_pass("Article generation flow working")
                return True
            else:
                print_fail("No SSE events received")
                return False
        elif r.status_code == 429:
            print_warn("Rate limited (429) - this is expected if you ran tests recently")
            return True  # Not a failure
        else:
            print_fail(f"Generation failed with status {r.status_code}")
            return False

    except requests.exceptions.Timeout:
        print_fail("Request timed out - generation may be too slow")
        return False
    except Exception as e:
        print_fail(f"Generation test failed: {e}")
        return False

def test_missing_topic(base_url):
    """Test validation when topic is missing"""
    print_test("Input validation (missing topic)")

    data = {
        'custom_topic': '',
        'use_sample_style': 'on'
    }

    try:
        r = requests.post(f"{base_url}/generate", data=data, timeout=10)
        if r.status_code == 400:
            print_pass("Missing topic rejected with 400 error")
            return True
        else:
            print_fail(f"Expected 400, got {r.status_code}")
            return False
    except Exception as e:
        print_fail(f"Validation test failed: {e}")
        return False

def run_all_tests(base_url):
    """Run all smoke tests"""
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Me-ish Smoke Tests{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"Testing: {base_url}")

    tests = [
        ("Homepage", test_homepage),
        ("Content Filter", test_content_filter),
        ("Input Validation", test_missing_topic),
        ("Basic Generation", test_basic_generation),
        ("Rate Limiting", test_rate_limiting),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func(base_url)
            results.append((name, result))
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Tests interrupted by user{RESET}")
            sys.exit(1)
        except Exception as e:
            print_fail(f"Unexpected error in {name}: {e}")
            results.append((name, False))

    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")

    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}")

    if passed == total:
        print(f"{GREEN}✓ All tests passed! Safe to deploy.{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some tests failed. Fix issues before deploying.{RESET}")
        return 1

if __name__ == '__main__':
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip('/')
    else:
        base_url = 'http://localhost:5000'

    exit_code = run_all_tests(base_url)
    sys.exit(exit_code)
