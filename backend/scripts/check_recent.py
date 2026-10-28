import urllib.request
import json

login_data = json.dumps({'email': 'coordinator@paventra.local', 'password': 'Paventra2024!'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read().decode())['access_token']

req = urllib.request.Request('http://127.0.0.1:8000/api/v1/reports/recent?limit=5', headers={'Authorization': f'Bearer {token}'})
recent = json.loads(urllib.request.urlopen(req).read().decode())
print(f"Recent reports count: {len(recent)}")
for i, r in enumerate(recent, 1):
    ref = r['public_ref']
    st = r['status']
    dt = r['damage_type']
    asmt = r.get('assessment_status')
    dt_str = r['created_at'][:19]
    print(f" {i:2}. {ref} | {st:15} | {dt:10} | asmt={asmt:15} | {dt_str}")
