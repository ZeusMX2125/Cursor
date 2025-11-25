#!/usr/bin/env python3
"""Quick diagnostic script to check if backend is running and CORS is configured."""

import sys
import asyncio
import aiohttp
from datetime import datetime

async def check_backend():
    """Check if backend is running and responding correctly."""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("Backend Diagnostic Check")
    print("=" * 60)
    print(f"Checking: {base_url}")
    print()
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        all_checks_passed = True
        # Test 1: Root endpoint
        print("1. Testing root endpoint (/)...")
        try:
            async with session.get(f"{base_url}/") as resp:
                print(f"   Status: {resp.status}")
                data = await resp.json()
                print(f"   Response: {data}")
                cors_header = resp.headers.get("Access-Control-Allow-Origin")
                print(f"   CORS Header: {cors_header or 'MISSING'}")
        except aiohttp.ClientConnectorError as e:
            print(f"   [X] ERROR: Backend is not running! ({e})")
            print("   Start it with: cd backend && uvicorn app:app --reload")
            return False
        except aiohttp.ServerDisconnectedError as e:
            print(f"   [X] ERROR: Server disconnected - backend may have crashed! ({e})")
            print("   Check backend logs for errors")
            return False
        except Exception as e:
            print(f"   [X] ERROR: {type(e).__name__}: {e}")
            return False
        
        print()
        
        # Test 2: CORS test endpoint
        print("2. Testing CORS endpoint (/api/test/cors)...")
        try:
            async with session.get(f"{base_url}/api/test/cors") as resp:
                print(f"   Status: {resp.status}")
                data = await resp.json()
                print(f"   Response: {data}")
                cors_header = resp.headers.get("Access-Control-Allow-Origin")
                print(f"   CORS Header: {cors_header or 'MISSING'}")
                if cors_header:
                    print("   [OK] CORS is configured")
                else:
                    print("   [X] CORS header missing!")
                    all_checks_passed = False
        except Exception as e:
            print(f"   [X] ERROR: {e}")
            all_checks_passed = False
        
        print()
        
        # Test 3: Contracts endpoint
        print("3. Testing contracts endpoint (/api/market/contracts)...")
        try:
            async with session.get(
                f"{base_url}/api/market/contracts?live=true",
                headers={"Origin": "http://localhost:3000"}
            ) as resp:
                print(f"   Status: {resp.status}")
                cors_header = resp.headers.get("Access-Control-Allow-Origin")
                print(f"   CORS Header: {cors_header or 'MISSING'}")
                if not cors_header:
                    print("   [X] Missing CORS header on contracts response!")
                    all_checks_passed = False
                if resp.status == 200:
                    data = await resp.json()
                    contract_count = len(data.get("contracts", []))
                    print(f"   [OK] Success! Found {contract_count} contracts")
                elif resp.status >= 500:
                    text = await resp.text()
                    print(f"   [X] Backend error: {text[:200]}")
                    all_checks_passed = False
                else:
                    text = await resp.text()
                    print(f"   [WARN] Non-200 response (expected during startup): {text[:200]}")
        except Exception as e:
            print(f"   [X] ERROR: {e}")
            all_checks_passed = False
        
        print()
        
        # Test 4: Health endpoint
        print("4. Testing health endpoint (/health)...")
        try:
            async with session.get(f"{base_url}/health") as resp:
                print(f"   Status: {resp.status}")
                data = await resp.json()
                print(f"   Auth Status: {data.get('auth', {}).get('status', 'unknown')}")
                if data.get('auth', {}).get('error'):
                    print(f"   [WARN] Auth Error: {data['auth']['error']}")
        except Exception as e:
            print(f"   [X] ERROR: {e}")
        
        print()
        print("=" * 60)
        print("Diagnostic complete!")
        print("=" * 60)
    
    return all_checks_passed

if __name__ == "__main__":
    try:
        result = asyncio.run(check_backend())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)

