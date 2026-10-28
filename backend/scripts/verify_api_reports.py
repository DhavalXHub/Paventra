import urllib.request
import json

# 1. Login coordinator
login_data = json.dumps({'email': 'coordinator@paventra.local', 'password': 'Paventra2024!'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read().decode())['access_token']

# 2. Get reports page 1
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/reports?page=1&page_size=20', headers={'Authorization': f'Bearer {token}'})
res = json.loads(urllib.request.urlopen(req).read().decode())
print(f"Total reports returned: {res['total']}")
print(f"Page size: {res['page_size']}, Pages: {res['pages']}")
print("\nPAGE 1 ITEMS (Real API response):")
for i, item in enumerate(res['items'], 1):
    prio = f"{item['priority_score']:.1f}" if item['priority_score'] is not None else 'None'
    asmt = item.get('assessment_status') or 'None'
    print(f"{i:2}. {item['public_ref']} | {item['status']:18} | prio={prio:6} | asmt={asmt:15} | {item['created_at'][:16]}")

# 3. Test Backfill dry run
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/reports/backfill-assessments?dry_run=true', data=b'', headers={'Authorization': f'Bearer {token}'})
backfill_res = json.loads(urllib.request.urlopen(req).read().decode())
print("\nBACKFILL DRY RUN RESPONSE:")
print(backfill_res)
