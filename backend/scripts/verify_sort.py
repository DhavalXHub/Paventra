import sqlite3
conn = sqlite3.connect(r'd:/Paventra/backend/paventra.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print('=== NEW SORT ORDER SIMULATION (after cleanup) ===')
c.execute('''
    SELECT public_ref, status, severity, priority_score, assessment_status, submitter_email, created_at,
    CASE 
        WHEN status IN ('RESOLVED', 'REJECTED') THEN 2
        WHEN priority_score IS NOT NULL THEN 0
        ELSE 1
    END as bucket
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
    LIMIT 25
''')
for i, r in enumerate(c.fetchall(), 1):
    em = r['submitter_email'] or ''
    genuine = '[GENUINE]' if 'dhaval' in em else ''
    bucket = r['bucket']
    print(f"{i:2}. B{bucket} | {r['public_ref']} | {r['status'][:18]:18} | prio={str(r['priority_score'])[:6]:6} | {r['created_at'][:16]} {genuine}")

print()
print('Total reports in DB:', end=' ')
c.execute("SELECT COUNT(*) FROM reports")
print(c.fetchone()[0])
print()
c.execute("SELECT COUNT(*) FROM reports WHERE assessment_status = 'AUTOMATED_TEST_ARTIFACT'")
print('Test artifact records (score cleared):', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM reports WHERE submitter_email LIKE '%dhaval%'")
print('Genuine citizen submissions:', c.fetchone()[0])
