import requests

MBTA_API_KEY = "6426e442cb644cae82e86def2e03ecb3"
BASE_URL = "https://api-v3.mbta.com"

static_endpoints = {
    "alerts": f"/alerts?filter[activity]=ALL&api_key={MBTA_API_KEY}",
    "routes": f"/routes?api_key={MBTA_API_KEY}",
    "stops": f"/stops?api_key={MBTA_API_KEY}",
    "vehicles": f"/vehicles?api_key={MBTA_API_KEY}",
    "lines": f"/lines?api_key={MBTA_API_KEY}",
    "facilities": f"/facilities?api_key={MBTA_API_KEY}"
}

for name, endpoint in static_endpoints.items():
    try:
        url = BASE_URL + endpoint
        print(f"🔍 Testing: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        count = len(data.get("data", []))
        print(f"✅ {name}: {count} records returned\n")
    except Exception as e:
        print(f"❌ {name} failed: {e}\n")
