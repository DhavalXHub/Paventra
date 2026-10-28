import urllib.request
import urllib.parse
import json
import mimetypes
import uuid
from pathlib import Path

# Load an actual real distress photo
photo_path = Path("d:/Paventra/backend/uploads/reports/078faa2024166e3c3b5445e8f218b937.jpg")
assert photo_path.exists(), "Photo must exist"

# Read bytes
with open(photo_path, "rb") as f:
    img_bytes = f.read()

# Build multipart/form-data
boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
body = []

def add_field(name, val):
    body.append(f"--{boundary}".encode())
    body.append(f'Content-Disposition: form-data; name="{name}"\r\n'.encode())
    body.append(f"{val}\r\n".encode())

add_field("description", "Pothole detected near Ghatlodiya crossroad")
add_field("damage_type", "pothole")
add_field("latitude", "23.0945")
add_field("longitude", "72.5615")
add_field("location_source", "manual")
add_field("address_hint", "Arterial Ring Road, Ghatlodiya")
add_field("submitter_email", "cyclops141g@gmail.com")

body.append(f"--{boundary}".encode())
body.append(b'Content-Disposition: form-data; name="image"; filename="verified_pothole.jpg"\r\nContent-Type: image/jpeg\r\n\r\n')
body.append(img_bytes)
body.append(b"\r\n")
body.append(f"--{boundary}--\r\n".encode())

payload = b"".join(body)

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/reports",
    data=payload,
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(payload)),
    },
)

res = json.loads(urllib.request.urlopen(req).read().decode())
print("Submission Successful!")
print(f"Public Ref: {res['public_ref']}")
print(f"Status: {res['status']}")
print("AI Assessment Result:")
print(json.dumps(res['ai_assessment'], indent=2))

# Verify it appears in /reports/recent
login_data = json.dumps({'email': 'coordinator@paventra.local', 'password': 'Paventra2024!'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read().decode())['access_token']

req = urllib.request.Request('http://127.0.0.1:8000/api/v1/reports/recent?limit=5', headers={'Authorization': f'Bearer {token}'})
recent = json.loads(urllib.request.urlopen(req).read().decode())
print("\nRecent Submissions at Coordinator Portal:")
for i, r in enumerate(recent[:3], 1):
    print(f"  {i}. {r['public_ref']} | prio={r['priority_score']} | asmt={r['assessment_status']} | type={r['damage_type']}")

assert recent[0]['public_ref'] == res['public_ref'], "New submission MUST be rank #1 in recent submissions!"
print("\nSUCCESS: Newly submitted report is immediately rank #1 in recent submissions!")
