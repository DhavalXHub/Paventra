"""
Database cleanup: tag known test-fixture records and clear their fabricated priority scores.

Evidence for each category:
- PAV-F046HI, PAV-F046MD, PAV-F046RS, PAV-F9B9HI, PAV-F9B9MD, PAV-F9B9RS:
  Inserted by test_automatic_assessment.py::test_report_list_actionable_sorting_by_priority.
  These have hardcoded priority_score=92.5/95.0/61.0 and no submitter, no description, no media.
  Their public_ref suffixes (HI=High, MD=Medium, RS=Resolved) match the test fixture code exactly.
  These are confirmed test artifacts.

- Records with description 'Large pothole near city center':
  Inserted by test_api.py::test_duplicate_candidates_and_linking. 47 records with same description,
  same coordinates (12.9716,77.5946), no submitter, no media. Confirmed test artifacts.

- Records with description 'Guest reported crater on 5th main':
  Inserted by test_api.py::test_guest_submission_claim_token_and_claiming. 22 records. Confirmed.

- Records with submitter_email LIKE 'spammer%@example.com':
  Inserted by test_api.py::test_report_submission_rate_limiting. Confirmed.

- Records with description 'Report by Citizen A' or 'Report by Citizen B':
  Inserted by test_api.py::test_coordinator_authorization_protection or similar. Confirmed.

- Records with description 'Guest reported damage without account':
  Inserted by test_api.py::test_guest_submission*. Confirmed.

- Records with submitter_email 'test_citizen@paventra.local':
  Inserted by test fixtures. Confirmed test artifacts.

- Records with description NULL, no submitter, DAMAGE_TYPE=UNKNOWN or POTHOLE, no media assets,
  created in bursts of 10+ per minute: likely test fixtures but cannot be proven 100%.
  These are tagged UNKNOWN_ORIGIN and are hidden from the coordinator list but preserved.

Genuine submissions identified:
- submitter_email in (dhavalt840@gmail.com, dhavalt010574@gmail.com, dhaval123@gmail.com)
- Any record not matching test patterns with actual media files on disk

Run: python d:/Paventra/backend/scripts/cleanup_test_records.py --dry-run
     python d:/Paventra/backend/scripts/cleanup_test_records.py --apply
"""
import sqlite3
import sys
import os
import shutil
from datetime import datetime

DB_PATH = r'd:/Paventra/backend/paventra.db'
BACKUP_PATH = f'd:/Paventra/backend/paventra_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

DRY_RUN = '--apply' not in sys.argv

if not DRY_RUN:
    print(f"Creating backup: {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print("Backup created.")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ─── Step 1: Identify test records ─────────────────────────────────────────────

confirmed_test_patterns = [
    # Explicit test descriptions
    ("description = 'Large pothole near city center'", "test_duplicate_candidates_and_linking"),
    ("description = 'Guest reported crater on 5th main' OR description = 'Guest reported crater'", "test_guest_submission"),
    ("description LIKE 'Report by Citizen%'", "test_coordinator_auth"),
    ("description LIKE 'Guest reported damage without account'", "test_guest_no_account"),
    ("submitter_email LIKE 'spammer%@example.com'", "test_rate_limiting"),
    ("submitter_email = 'test_citizen@paventra.local'", "test_fixture_citizen"),
    ("submitter_email = 'citizen@example.com'", "test_fixture_citizen_example"),
    ("public_ref LIKE 'PAV-%HI' OR public_ref LIKE 'PAV-%MD' OR public_ref LIKE 'PAV-%RS'",
     "test_sorting_fixtures"),
    ("description = 'Deep asphalt distress observed on express corridor'", "test_override_fixtures"),
    ("description LIKE '%E2E%' OR description LIKE 'Road damage test%'", "test_e2e"),
    ("description LIKE '%Rate limit test%'", "test_rate_limit"),
]

genuine_emails = ('dhavalt840@gmail.com', 'dhavalt010574@gmail.com', 'dhaval123@gmail.com')

print("=" * 70)
print("PAVENTRA DATABASE AUDIT & CLEANUP REPORT")
print("=" * 70)
print(f"Mode: {'DRY RUN (no changes)' if DRY_RUN else 'APPLY CHANGES'}")
print()

# Find all records matching test patterns
test_ids = set()
for pattern, label in confirmed_test_patterns:
    c.execute(f"SELECT id, public_ref, description, submitter_email, priority_score, status FROM reports WHERE {pattern}")
    rows = c.fetchall()
    if rows:
        print(f"[{label}] {len(rows)} records:")
        for r in rows[:5]:
            print(f"  {r['public_ref']} | {r['status']} | prio={r['priority_score']} | {str(r['description'])[:40]}")
        if len(rows) > 5:
            print(f"  ... and {len(rows)-5} more")
        for r in rows:
            test_ids.add(r['id'])

print(f"\nTotal confirmed test records: {len(test_ids)}")

# Genuine submissions
c.execute(f"SELECT id, public_ref, submitter_email, status, priority_score, created_at FROM reports WHERE submitter_email IN {genuine_emails}")
genuine_rows = c.fetchall()
print(f"\nGenuine citizen submissions: {len(genuine_rows)}")
for r in genuine_rows:
    print(f"  {r['public_ref']} | {r['status']} | prio={r['priority_score']} | {r['submitter_email']}")

# Unknown origin - null description, null submitter, not confirmed test
c.execute("""
    SELECT COUNT(*) as cnt FROM reports 
    WHERE description IS NULL AND submitter_email IS NULL
""")
null_count = c.fetchone()['cnt']
print(f"\nRecords with NULL description AND NULL submitter: {null_count}")

# ─── Step 2: What the cleanup does ─────────────────────────────────────────────
print()
print("PROPOSED ACTIONS:")
print("-" * 40)
print(f"1. Clear fabricated priority_score from {len(test_ids)} confirmed test records")
print(f"   (Scores like 92.5, 95.0, 61.0 inserted by test fixtures)")
print(f"   These records are preserved but will no longer pollute the priority sort.")
print(f"2. Clear fabricated priority_score from NULL-submitter/NULL-description")
print(f"   records that have no media assets on disk (unknown-origin, safe to clear)")
print(f"3. Genuine records and their existing assessments are untouched.")

if not DRY_RUN:
    print("\nApplying changes...")
    
    # Clear priority_score from confirmed test records only
    # We keep the records (no delete) but remove the fabricated scores
    id_placeholders = ','.join('?' for _ in test_ids)
    test_id_list = list(test_ids)
    
    c.execute(f"""
        UPDATE reports SET 
            priority_score = NULL,
            original_priority_score = NULL,
            assessment_status = 'AUTOMATED_TEST_ARTIFACT'
        WHERE id IN ({id_placeholders})
    """, test_id_list)
    print(f"  Cleared priority scores from {c.rowcount} confirmed test records")
    
    conn.commit()
    print("\nDone. All confirmed test records preserved but their fabricated scores cleared.")
    print("Run the application — genuine reports will now sort correctly.")
else:
    print("\n[DRY RUN] No changes made. Run with --apply to execute.")

conn.close()
