import requests, time

readings = [
    {"voltage":3.9,"current":2.1,"temperature":31,"battery_percentage":82,"humidity":45,"cycle":120,"capacity":0.91},
    {"voltage":3.7,"current":3.5,"temperature":42,"battery_percentage":60,"humidity":55,"cycle":200,"capacity":0.82},
    {"voltage":3.4,"current":4.2,"temperature":55,"battery_percentage":35,"humidity":70,"cycle":350,"capacity":0.65},
]

print("=== Testing ESP32 Pipeline ===")
for i, r in enumerate(readings):
    resp = requests.post("http://127.0.0.1:8000/telemetry", json=r)
    d = resp.json()
    print(f"  Send {i+1}: SOH={d['soh_prediction']}%, Deg={d['degradation_percentage']}%, Cond={d['battery_condition']}")
    time.sleep(0.3)

latest = requests.get("http://127.0.0.1:8000/latest").json()
print(f"\n/latest endpoint: SOH={latest['soh_prediction']}%, Temp={latest['temperature']}C")

hist = requests.get("http://127.0.0.1:8000/history").json()
print(f"/history endpoint: {hist['count']} entries stored")
print(f"ESP32 connected: {hist['esp32_connected']}")
print("\n=== Pipeline Test Complete ===")
