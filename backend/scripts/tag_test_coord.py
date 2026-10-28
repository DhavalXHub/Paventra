import sqlite3
import sys
import shutil
from datetime import datetime

DB_PATH = r'd:/Paventra/backend/paventra.db'
APPLY = '--apply' in sys.argv

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Find test_coord / test_api records
c.execute('''
    SELECT distinct r.id, r.public_ref, r.submitter_email, r.priority_score, r.status
    FROM reports r
    LEFT JOIN report_status_history h ON h.report_id = r.id
    WHERE h.notes = 'Confirmed large crater'
       OR h.changed_by_email = 'test_coord@paventra.local'
       OR r.override_reason LIKE '%deep sub-base hollow%'
''')
test_rows = c.fetchall()
print(f"Identified {len(test_rows)} test_api.py / test_coord records with hard evidence.")

test_ids = [r['id'] for r in test_rows]

if APPLY:
    backup_path = f'd:/Paventra/backend/paventra_backup_coord_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    shutil.copy2(DB_PATH, backup_path)
    print(f"Created backup: {backup_path}")

    placeholders = ','.join('?' for _ in test_ids)
    c.execute(f'''
        UPDATE reports 
        SET priority_score = NULL,
            original_priority_score = NULL,
            assessment_status = 'AUTOMATED_TEST_ARTIFACT'
        WHERE id IN ({placeholders})
    ''', test_ids)
    conn.commit()
    print(f"Updated {c.rowcount} records: set priority_score=NULL and assessment_status='AUTOMATED_TEST_ARTIFACT'")

# Preview top 15 on list
c.execute('''
    SELECT public_ref, status, severity, priority_score, assessment_status, submitter_email, created_at
    FROM reports
    WHERE assessment_status != 'AUTOMATED_TEST_ARTIFACT'
       OR assessment_status IS NULL
    ORDER BY 
        CASE 
            WHEN status IN ('RESOLVED', 'REJECTED') THEN 2
            WHEN priority_score IS NOT NULL THEN 0
            ELSE 1
        END ASC,
        priority_score DESC,
        created_at DESC
    LIMIT 15
''')

print("\n--- PREVIEW: TOP 15 COORDINATOR LIST ---")
for i, r in enumerate(c.fetchall(), 1):
    em = r['submitter_email'] or '(no email)'
    prio = f"{r['priority_score']:.1f}" if r['priority_score'] is not None else 'None'
    asmt = r['assessment_status'] or 'None'
    print(f"{i:2}. {r['public_ref']} | {r['status']:18} | prio={prio:6} | asmt={asmt:14} | {r['created_at'][:16]} | {em}")

conn.close()
