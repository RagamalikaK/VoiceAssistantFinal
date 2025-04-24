import requests

MBTA_API_KEY = "6426e442cb644cae82e86def2e03ecb3"
BASE_URL = "https://api-v3.mbta.com"

def test_route_endpoints(route_id):
    endpoints = {
        "predictions": f"/predictions?filter[route]={route_id}&include=stop,trip,vehicle&api_key={MBTA_API_KEY}",
        "schedules": f"/schedules?filter[route]={route_id}&api_key={MBTA_API_KEY}"
    }

    for name, endpoint in endpoints.items():
        try:
            url = BASE_URL + endpoint
            print(f"🔍 Testing {name} for route: {route_id}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            count = len(data.get("data", []))
            print(f"✅ {name}: {count} records\n")
        except Exception as e:
            print(f"❌ {name} failed: {e}\n")

# Try for one known route like 'Red'
test_route_endpoints("Red")
