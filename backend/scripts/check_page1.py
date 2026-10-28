import urllib.request
import json

login_data = json.dumps({'email': 'coordinator@paventra.local', 'password': 'Paventra2024!'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read().decode())['access_token']

req = urllib.request.Request('http://127.0.0.1:8000/api/v1/reports?page=1&page_size=20', headers={'Authorization': f'Bearer {token}'})
res = json.loads(urllib.request.urlopen(req).read().decode())
print(f"Total in view: {res['total']}")
print("Top 10 items on Page 1:")
for i, item in enumerate(res['items'][:10], 1):
    ref = item['public_ref']
    st = item['status']
    prio = str(item.get('priority_score'))
    asmt = str(item.get('assessment_status'))
    created = item['created_at'][:19]
    print(f" {i:2}. {ref} | {st:15} | prio={prio:6} | asmt={asmt:14} | {created}")

# Find index of PAV-VVQ380FX
req_all = urllib.request.Request('http://127.0.0.1:8000/api/v1/reports?page=1&page_size=100', headers={'Authorization': f'Bearer {token}'})
res_all = json.loads(urllib.request.urlopen(req_all).read().decode())
refs = [it['public_ref'] for it in res_all['items']]
if 'PAV-VVQ380FX' in refs:
    print(f"\nPAV-VVQ380FX is at index {refs.index('PAV-VVQ380FX') + 1} of 100")
else:
    print("\nPAV-VVQ380FX not in first 100")
