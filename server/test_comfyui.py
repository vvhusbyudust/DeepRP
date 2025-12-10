import asyncio
import httpx
import socket

async def test():
    urls_to_try = [
        "http://127.0.0.1:8055",
        "http://localhost:8055",
        "http://0.0.0.0:8055",
    ]
    
    print("=" * 50)
    print("ComfyUI Connection Test (Port 8055)")
    print("=" * 50)
    
    # First check if port is open
    print("\n[1] Checking if port 8055 is open...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("127.0.0.1", 8055))
    sock.close()
    if result == 0:
        print("  ✓ Port 8055 is OPEN")
    else:
        print(f"  ✗ Port 8055 is CLOSED (error code: {result})")
        
    # Try different URLs
    print("\n[2] Testing HTTP connections...")
    for url in urls_to_try:
        print(f"\n  Testing {url}...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/system_stats", timeout=5.0)
                print(f"    Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"    ✓ ComfyUI connected!")
                    print(f"    VRAM: {data.get('system', {}).get('vram', {})}")
                    return url
        except httpx.ConnectError as e:
            print(f"    ✗ Connect failed: {e}")
        except httpx.ReadTimeout:
            print(f"    ✗ Read timeout")
        except Exception as e:
            print(f"    ✗ Error: {type(e).__name__}: {e}")
    
    print("\n[3] No connection worked. Checking with simple HTTP request...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:8055/", timeout=5.0)
            print(f"  Root URL status: {response.status_code}")
            print(f"  Content type: {response.headers.get('content-type')}")
            print(f"  First 200 chars: {response.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    
    return None

working_url = asyncio.run(test())
if working_url:
    print(f"\n\n✓ Working URL: {working_url}")
else:
    print("\n\n✗ Could not connect to ComfyUI")
