#!/usr/bin/env python3
"""Debug session issues"""
import requests
import urllib3
urllib3.disable_warnings()

print("Debugging Session Flow")
print("=" * 50)

# Create a session to maintain cookies
session = requests.Session()

# Step 1: Start from Flask app
print("\n1. Accessing Flask app...")
r1 = session.get("http://localhost:5000/", allow_redirects=True)
print(f"   Status: {r1.status_code}")
print(f"   Session cookies: {dict(session.cookies)}")

# Step 2: Follow login redirect
print("\n2. Following login redirect...")
r2 = session.get("http://localhost:5000/login", allow_redirects=False)
print(f"   Status: {r2.status_code}")
if 'Location' in r2.headers:
    redirect_url = r2.headers['Location']
    print(f"   Redirects to: {redirect_url}")
    
    # Step 3: Follow to auth service
    print("\n3. Following to auth service...")
    r3 = session.get(redirect_url, verify=False, allow_redirects=False)
    print(f"   Status: {r3.status_code}")
    print(f"   Session cookies after auth redirect: {dict(session.cookies)}")
    if 'Set-Cookie' in r3.headers:
        print(f"   New cookie: {r3.headers['Set-Cookie']}")
    if 'Location' in r3.headers:
        print(f"   Azure AD redirect: {r3.headers['Location'][:100]}...")

print("\n4. Session Analysis:")
print(f"   Total cookies: {len(session.cookies)}")
for cookie in session.cookies:
    print(f"   - {cookie.name}: domain={cookie.domain}, path={cookie.path}, secure={cookie.secure}")

print("\n5. The issue:")
print("   When you access via 10.1.5.58 in browser but Flask redirects to 'localhost:8000',")
print("   cookies set for one domain won't be sent to the other.")
print("\n   Solution: Access everything via the same domain/IP:")
print("   - Either use http://localhost:5000 and https://localhost:8000")
print("   - Or use http://10.1.5.58:5000 and https://10.1.5.58:8000")