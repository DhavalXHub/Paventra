import sqlite3
conn = sqlite3.connect(r'd:/Paventra/backend/paventra.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('''
    SELECT public_ref, status, severity, priority_score, assessment_status, created_at,
    CASE WHEN status IN ('RESOLVED', 'REJECTED') THEN 1 ELSE 0 END as is_non_actionable
    FROM reports
    ORDER BY is_non_actionable ASC, priority_score DESC, created_at DESC
    LIMIT 25
''')

print("TOP 25 by list sort order (priority_score DESC NULLS LAST, created_at DESC):")
for i, r in enumerate(c.fetchall(), 1):
    pr = r['priority_score']
    print(f'{i:2}. {r["public_ref"]} | {r["status"]:20} | prio={str(pr):6} | asmt={str(r["assessment_status"]):15} | {r["created_at"][:16]}')

print()
# Find where PAV-VBNRRWHU lands
c.execute('''
    SELECT COUNT(*) + 1 as position
    FROM reports
    WHERE (
      CASE WHEN status IN ('RESOLVED','REJECTED') THEN 1 ELSE 0 END < 
      CASE WHEN (SELECT status FROM reports WHERE public_ref='PAV-VBNRRWHU') IN ('RESOLVED','REJECTED') THEN 1 ELSE 0 END
    )
    OR (
      CASE WHEN status IN ('RESOLVED','REJECTED') THEN 1 ELSE 0 END = 
      CASE WHEN (SELECT status FROM reports WHERE public_ref='PAV-VBNRRWHU') IN ('RESOLVED','REJECTED') THEN 1 ELSE 0 END
      AND priority_score > (SELECT COALESCE(priority_score, -999) FROM reports WHERE public_ref='PAV-VBNRRWHU')
    )
    OR (
      priority_score IS NOT NULL AND (SELECT priority_score FROM reports WHERE public_ref='PAV-VBNRRWHU') IS NULL
      AND status NOT IN ('RESOLVED','REJECTED')
    )
''')
row = c.fetchone()
if row:
    print(f"PAV-VBNRRWHU approximate position: {row[0]}")

# Find most recently created reports position on list
c.execute('''
    SELECT public_ref, submitter_email, created_at FROM reports
    WHERE submitter_email LIKE '%dhaval%'
    ORDER BY created_at DESC
    LIMIT 10
''')
print()
print("Your genuine reports:")
for r in c.fetchall():
    print(f"  {r['public_ref']} | {r['submitter_email']} | {r['created_at'][:16]}")

# Check conftest.py
import os
if os.path.exists(r'd:/Paventra/backend/tests/conftest.py'):
    with open(r'd:/Paventra/backend/tests/conftest.py', 'r') as f:
        print("\nconftest.py:\n" + f.read())
else:
    print("\nNo conftest.py found in tests/")
