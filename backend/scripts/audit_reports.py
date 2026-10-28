import sqlite3
import json

conn = sqlite3.connect(r'd:/Paventra/backend/paventra.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM reports')
total = c.fetchone()[0]
print(f"Total reports: {total}")

c.execute('SELECT status, count(*) FROM reports GROUP BY status')
print("Status breakdown:", dict(c.fetchall()))

c.execute('''
    SELECT 
        CASE 
            WHEN description IS NULL THEN '[NULL]'
            ELSE substr(description, 1, 50)
        END as desc_sample,
        count(*) as cnt
    FROM reports
    GROUP BY desc_sample
    ORDER BY cnt DESC
    LIMIT 20
''')
print("\nDescription breakdown:")
for r in c.fetchall():
    print(f"  {r['cnt']}x: {r['desc_sample']}")

c.execute('''
    SELECT 
        source,
        count(*) as cnt
    FROM (
        SELECT 
            CASE 
                WHEN description IS NULL THEN 'NO_DESC'
                WHEN description LIKE '%Large pothole near city center%' THEN 'TEST_POTHOLE_CITY_CENTER'
                WHEN description LIKE '%Guest reported crater%' THEN 'TEST_GUEST_CRATER'
                WHEN description LIKE '%Report by Citizen%' THEN 'TEST_CITIZEN_A_B'
                WHEN description LIKE '%Rate limit test%' THEN 'TEST_RATE_LIMIT'
                WHEN description LIKE '%Test description%' THEN 'TEST_GENERIC_TEST'
                WHEN description LIKE '%Automated inspection%' THEN 'METHOD_B_INSPECTION'
                ELSE 'OTHER_USER_SUBMITTED'
            END as source
        FROM reports
    )
    GROUP BY source
''')
print("\nCategorized sources:")
for r in c.fetchall():
    print(f"  {r['source']}: {r['cnt']}")

c.execute('''
    SELECT 
        count(distinct r.id) as with_media,
        count(distinct CASE WHEN m.file_path IS NOT NULL THEN r.id END) as with_valid_media_file
    FROM reports r
    JOIN media_assets m ON m.report_id = r.id
''')
row = c.fetchone()
print(f"\nReports with media assets: {row['with_media']}")

# Let's inspect priority scores distribution
c.execute('''
    SELECT 
        CASE 
            WHEN priority_score IS NULL THEN 'NULL'
            WHEN priority_score >= 80 THEN 'CRITICAL (>=80)'
            WHEN priority_score >= 60 THEN 'HIGH (60-79)'
            WHEN priority_score >= 40 THEN 'MEDIUM (40-59)'
            ELSE 'LOW (<40)'
        END as prio_bracket,
        count(*) as cnt
    FROM reports
    GROUP BY prio_bracket
    ORDER BY cnt DESC
''')
print("\nPriority brackets:")
for r in c.fetchall():
    print(f"  {r['prio_bracket']}: {r['cnt']}")

# Let's inspect damage_type distribution
c.execute('''
    SELECT coalesce(damage_type, '[NULL]') as dt, count(*) as cnt
    FROM reports
    GROUP BY dt
    ORDER BY cnt DESC
''')
print("\nDamage types:")
for r in c.fetchall():
    print(f"  {r['dt']}: {r['cnt']}")

# Let's inspect severity distribution
c.execute('''
    SELECT coalesce(severity, '[NULL]') as sev, count(*) as cnt
    FROM reports
    GROUP BY sev
    ORDER BY cnt DESC
''')
print("\nSeverities:")
for r in c.fetchall():
    print(f"  {r['sev']}: {r['cnt']}")

# Let's inspect assessment_status
c.execute('''
    SELECT coalesce(assessment_status, '[NULL]') as ast, count(*) as cnt
    FROM reports
    GROUP BY ast
    ORDER BY cnt DESC
''')
print("\nAssessment statuses:")
for r in c.fetchall():
    print(f"  {r['ast']}: {r['cnt']}")

# Check distinct dates/timestamps
c.execute('''
    SELECT substr(created_at, 1, 16) as time_min, count(*) as cnt
    FROM reports
    GROUP BY time_min
    HAVING count(*) > 3
    ORDER BY cnt DESC
    LIMIT 15
''')
print("\nTimestamp clustering (bursts > 3 in same minute):")
for r in c.fetchall():
    print(f"  {r['time_min']}: {r['cnt']} reports")

# Reopen connection for extended analysis
conn = sqlite3.connect(r'd:/Paventra/backend/paventra.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Extended Media & Submitter Analysis
print("\n--- MEDIA ASSETS AUDIT ---")
c.execute('SELECT count(*) FROM media_assets')
print('Total media assets:', c.fetchone()[0])

c.execute('SELECT asset_type, count(*) FROM media_assets GROUP BY asset_type')
print('Media by asset_type:', dict(c.fetchall()))

import os
c.execute('SELECT file_path, file_name FROM media_assets')
rows = c.fetchall()
exists_count = 0
missing_count = 0
for r in rows:
    p = r['file_path']
    fn = r['file_name']
    if p and (os.path.exists(p) or os.path.exists(os.path.join(r'd:/Paventra/backend/uploads/reports', fn or ''))):
        exists_count += 1
    else:
        missing_count += 1
print(f'Media files on disk: {exists_count} exist, {missing_count} missing')

print("\n--- SUBMITTER EMAILS AUDIT ---")
c.execute('''
    SELECT 
        CASE 
            WHEN submitter_email IS NULL THEN '[NULL/ANON]'
            ELSE submitter_email
        END as em,
        count(*) as cnt
    FROM reports
    GROUP BY em
    ORDER BY cnt DESC
    LIMIT 10
''')
for r in c.fetchall():
    print(f"  {r['cnt']}x: {r['em']}")

print("\n--- AUDIT EVENTS ---")
c.execute('SELECT action, count(*) FROM audit_events GROUP BY action')
for r in c.fetchall():
    print(f"  {r['action']}: {r['count(*)']}")
