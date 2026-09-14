import sys
import pandas as pd
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

print("--- Testing GET /api/assets/ENG-001/timeseries ---")
resp = client.get("/api/assets/ENG-001/timeseries")
print("Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("Items:", len(data))
    if len(data) > 0:
        print("First item keys:", data[0].keys())
else:
    print("Error:", resp.text)

print("\n--- Testing POST /api/assess with 20-cycle CSV ---")
with open('unseen_asset_test_20_cycles.csv', 'rb') as f:
    resp = client.post("/api/assess", files={"file": ("unseen_asset_test_20_cycles.csv", f, "text/csv") })
print("Status:", resp.status_code)
print("Response:", resp.json() if resp.status_code == 200 else resp.text)

print("\n--- Testing POST /api/assess with 1-cycle CSV ---")
df = pd.read_csv('unseen_asset_test_20_cycles.csv')
df.head(1).to_csv('1_cycle.csv', index=False)
with open('1_cycle.csv', 'rb') as f:
    resp = client.post("/api/assess", files={"file": ("1_cycle.csv", f, "text/csv") })
print("Status:", resp.status_code)
print("Response:", resp.json() if resp.status_code == 200 else resp.text)

print("\n--- Testing POST /api/assess with RUL column CSV ---")
df['rul'] = 50
df.to_csv('with_rul.csv', index=False)
with open('with_rul.csv', 'rb') as f:
    resp = client.post("/api/assess", files={"file": ("with_rul.csv", f, "text/csv") })
print("Status:", resp.status_code)
print("Response:", resp.json() if resp.status_code == 200 else resp.text)
