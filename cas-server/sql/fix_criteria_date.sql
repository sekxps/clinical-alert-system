-- อัปเดต SQL query ของ criteria ในฐานข้อมูล
-- เปลี่ยน hardcode date "2026-06-09" → CURDATE()
-- รัน script นี้บน cas_db ครั้งเดียวครับ

UPDATE criteria
SET
    query =
REPLACE (
        query,
        '"2026-06-09"',
        'CURDATE()'
    )
WHERE
    active = 1
    AND query LIKE '%"2026-06-09"%';

-- ตรวจสอบผลลัพธ์
SELECT id, name, IF(
        query LIKE '%CURDATE()%', 'OK ✅', 'ยังมีวันที่ hardcode ⚠️'
    ) AS status
FROM criteria
WHERE
    active = 1;