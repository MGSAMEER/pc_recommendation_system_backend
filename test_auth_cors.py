#!/usr/bin/env python3
"""
Test authentication CORS behavior for mobile browsers
"""
import requests
import json
from urllib.parse import urlparse

def test_cors_preflight():
    """Test CORS preflight OPTIONS request"""
    print("=== TESTING CORS PREFLIGHT (OPTIONS) ===")

    # Test URLs
    base_urls = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://192.168.0.105:8000"  # Network IP
    ]

    auth_endpoints = [
        "/api/v1/auth/login",
        "/api/v1/auth/signup"
    ]

    for base_url in base_urls:
        print(f"\nTesting {base_url}:")
        for endpoint in auth_endpoints:
            url = base_url + endpoint

            # Test OPTIONS request (preflight)
            try:
                headers = {
                    'Origin': 'http://192.168.0.105:3000',  # Simulate mobile frontend
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'authorization,content-type'
                }

                response = requests.options(url, headers=headers, timeout=5)

                print(f"  {endpoint}:")
                print(f"    Status: {response.status_code}")

                # Check CORS headers
                cors_headers = {
                    'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                    'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                    'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                    'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
                }

                for header, value in cors_headers.items():
                    status = "✅" if value else "❌"
                    print(f"    {header}: {value} {status}")

                # Validate critical headers
                if cors_headers['Access-Control-Allow-Origin'] == 'http://192.168.0.105:3000':
                    print("    ✅ Origin correctly allowed")
                elif cors_headers['Access-Control-Allow-Origin'] == '*':
                    print("    ⚠️  Wildcard origin (may work but less secure)")
                else:
                    print("    ❌ Origin not allowed")

                if 'POST' in str(cors_headers['Access-Control-Allow-Methods']):
                    print("    ✅ POST method allowed")
                else:
                    print("    ❌ POST method not allowed")

                if cors_headers['Access-Control-Allow-Headers'] and 'authorization' in cors_headers['Access-Control-Allow-Headers'].lower():
                    print("    ✅ Authorization header allowed")
                else:
                    print("    ❌ Authorization header not allowed")

                if cors_headers['Access-Control-Allow-Credentials'] == 'true':
                    print("    ✅ Credentials allowed")
                else:
                    print("    ❌ Credentials not allowed")

            except requests.exceptions.ConnectionError:
                print(f"  {endpoint}: ❌ CONNECTION FAILED")
            except Exception as e:
                print(f"  {endpoint}: ❌ ERROR - {e}")

def test_auth_request():
    """Test actual authentication request with CORS"""
    print("\n=== TESTING AUTHENTICATION REQUEST ===")

    # Test login request
    url = "http://192.168.0.105:8000/api/v1/auth/login"

    headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://192.168.0.105:3000',  # Mobile frontend origin
    }

    data = {
        'username': 'testuser',
        'password': 'testpass'
    }

    try:
        print(f"Testing POST {url}")
        print(f"Origin: {headers['Origin']}")
        print(f"Data: {data}")

        response = requests.post(url, json=data, headers=headers, timeout=10)

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")

        # Check CORS headers in response
        cors_origin = response.headers.get('Access-Control-Allow-Origin')
        cors_credentials = response.headers.get('Access-Control-Allow-Credentials')

        print(f"Access-Control-Allow-Origin: {cors_origin}")
        print(f"Access-Control-Allow-Credentials: {cors_credentials}")

        if cors_origin == headers['Origin']:
            print("✅ CORS origin matches request")
        else:
            print("❌ CORS origin mismatch")

        if cors_credentials == 'true':
            print("✅ Credentials enabled")
        else:
            print("❌ Credentials not enabled")

    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION FAILED - Backend not accessible")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_mobile_browser_simulation():
    """Simulate mobile browser request patterns"""
    print("\n=== MOBILE BROWSER SIMULATION ===")

    # Common mobile browser headers
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Origin': 'http://192.168.0.105:3000',
        'Referer': 'http://192.168.0.105:3000/login',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }

    url = "http://192.168.0.105:8000/api/v1/auth/login"
    data = {'username': 'mobiletest', 'password': 'mobilepass'}

    try:
        print("Simulating mobile browser login request...")
        response = requests.post(url, json=data, headers=mobile_headers, timeout=10)

        print(f"Status: {response.status_code}")

        # Check for CORS headers
        cors_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('access-control')}
        if cors_headers:
            print("CORS headers present:")
            for k, v in cors_headers.items():
                print(f"  {k}: {v}")
        else:
            print("❌ No CORS headers found")

        # Check if request was successful (even if auth fails)
        if response.status_code in [200, 401, 422]:
            print("✅ Request reached backend successfully")
        else:
            print(f"❌ Unexpected status: {response.status_code}")

    except Exception as e:
        print(f"❌ Mobile simulation failed: {e}")

def main():
    print("Authentication CORS Audit for Mobile Browsers")
    print("=" * 60)

    try:
        test_cors_preflight()
        test_auth_request()
        test_mobile_browser_simulation()

        print("\n" + "=" * 60)
        print("AUDIT COMPLETE")
        print("\nKey Findings:")
        print("- Check console output above for specific issues")
        print("- Ensure backend is running on the tested URLs")
        print("- Verify mobile device is on same network")

    except KeyboardInterrupt:
        print("\nAudit interrupted by user")
    except Exception as e:
        print(f"\nAudit failed with error: {e}")

if __name__ == "__main__":
    main()