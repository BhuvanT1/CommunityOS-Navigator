import os
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=== DEPLOYMENT READINESS REPORT ===\n")
    
    print("[Testing Workflow 1-5: Citizen Upload -> Gemini Vision -> Fusion]")
    # Create a dummy image to pass the resolution validation
    from io import BytesIO
    from PIL import Image
    img = Image.new('RGB', (800, 600), color='red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()

    start = time.time()
    response = client.post(
        "/api/reports/analyze",
        files={"image": ("test.jpg", img_bytes, "image/jpeg")},
        data={"lat": 40.7128, "lng": -74.0060}
    )
    latency = (time.time() - start) * 1000
    print(f"Status Code: {response.status_code}")
    print(f"Response Latency: {latency:.2f}ms")
    
    res_json = response.json()
    print(f"API Schema validation: {'success' in res_json and 'data' in res_json}")
    if not res_json.get("success"):
        print(f"Exception/Failure recorded: {res_json.get('error')}")
    else:
        print("Success: Intake Pipeline Executed.")
        
    print("\n[Testing Workflow 6-9: CommunityOS Navigator & Judge Mode]")
    # Test Judge Mode (Deterministic)
    start = time.time()
    demo_res = client.post("/api/navigator/ask?demo=true", json={"query": "Critical incidents near hospital"})
    demo_latency = (time.time() - start) * 1000
    print(f"Judge Mode Status: {demo_res.status_code} | Latency: {demo_latency:.2f}ms")
    
    # Test Live Mode (Actual Network Call)
    start = time.time()
    live_res = client.post("/api/navigator/ask", json={"query": "Critical incidents near hospital"})
    live_latency = (time.time() - start) * 1000
    print(f"Live API Status: {live_res.status_code} | Latency: {live_latency:.2f}ms")
    live_json = live_res.json()
    if not live_json.get("success"):
        print(f"Exception/Failure recorded: {live_json.get('error')}")

    print("\n[Testing Environment & Credentials]")
    from app.core.config import settings
    print(f"GEMINI_API_KEY Missing? {not bool(settings.GEMINI_API_KEY)}")
    print(f"GEMINI_API_KEY Is Mock? {settings.GEMINI_API_KEY == 'mock_gemini_api_key'}")

if __name__ == "__main__":
    run_tests()
