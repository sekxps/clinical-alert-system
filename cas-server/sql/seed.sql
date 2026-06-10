-- ---------------------------------------------------------
-- Initial Seed Data
-- ---------------------------------------------------------

INSERT IGNORE INTO
    criteria (
        name,
        description,
        category,
        query,
        severity,
        cooldown_min
    )
VALUES (
        'MI Risk Screen (EKG Required)',
        'คัดกรองผู้ป่วยเสี่ยง MI: เมื่อพบ CC เจ็บหน้าอกร่วมกับปัจจัยเสี่ยง ให้รีบตามทำ EKG เพื่อ R/O MI ทันที',
        'cardiac',
        'SELECT
    visit_id,
    hn,
    patient_name,
    vsttime,
    department_name,
    is_alert,
    IF(is_alert = 1, detail, NULL) AS detail
FROM (
    SELECT
        VS.vn AS visit_id,
        VS.hn AS hn,
        CONCAT(PT.pname, PT.fname, '' '', PT.lname) AS patient_name,
        OV.vsttime AS vsttime,
        SP.name AS department_name,
        IF(
            (
                ((VS.sex = ''1'' AND VS.age_y > 45) OR (VS.sex = ''2'' AND VS.age_y > 55))
                OR EXISTS (SELECT 1 FROM opdscreen WHERE vn = VS.vn AND bmi > 25)
                OR EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 LIKE ''E1%'')
                OR EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 LIKE ''I1%'')
                OR EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 LIKE ''E78%'')
                OR EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 REGEXP ''^I2[0-5]'')
                OR EXISTS (SELECT 1 FROM opdscreen WHERE vn = VS.vn AND smoking_type_id IN (2, 3))
                OR EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 REGEXP ''^F1[1-9]'')
            )
            AND EXISTS (
                SELECT 1 FROM opdscreen
                WHERE vn = VS.vn
                AND cc REGEXP ''เจ็บหน้าอก|จุกแน่นใต้ลิ้นปี่|หน้ามืด|เป็นลม|หมดสติ|ใจสั่นเหงื่อแตก|เหนื่อยง่าย''
            ),
        1, 0) AS is_alert,
        TRIM(BOTH '' | '' FROM CONCAT_WS('' | '',
            IF((VS.sex = ''1'' AND VS.age_y > 45) OR (VS.sex = ''2'' AND VS.age_y > 55),
                CONCAT(''อายุ/เพศเสี่ยง ('', IF(VS.sex=''1'',''ชาย'',''หญิง''), '' อายุ '', VS.age_y, '' ปี)''), NULL),
            IF(EXISTS (SELECT 1 FROM opdscreen WHERE vn = VS.vn AND bmi > 25),
                ''BMI > 25 (น้ำหนักเกิน)'', NULL),
            IF(EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 LIKE ''E1%''),
                ''เบาหวาน (E1x)'', NULL),
            IF(EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 LIKE ''I1%''),
                ''ความดันโลหิตสูง (I1x)'', NULL),
            IF(EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 LIKE ''E78%''),
                ''ไขมันในเลือดผิดปกติ (E78x)'', NULL),
            IF(EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 REGEXP ''^I2[0-5]''),
                ''โรคหัวใจ/หลอดเลือด (I20-I25)'', NULL),
            IF(EXISTS (SELECT 1 FROM opdscreen WHERE vn = VS.vn AND smoking_type_id IN (2, 3)),
                ''สูบบุหรี่ (smoking_type_id 2,3)'', NULL),
            IF(EXISTS (SELECT 1 FROM ovstdiag WHERE hn = VS.hn AND icd10 REGEXP ''^F1[1-9]''),
                ''สารเสพติด (F11-F19)'', NULL),
            (SELECT TRIM(BOTH '', '' FROM CONCAT_WS('', '',
                IF(cc LIKE ''%เจ็บหน้าอก%'',        ''เจ็บหน้าอก'', NULL),
                IF(cc LIKE ''%จุกแน่นใต้ลิ้นปี่%'', ''จุกแน่นใต้ลิ้นปี่'', NULL),
                IF(cc LIKE ''%หน้ามืด%'',            ''หน้ามืด'', NULL),
                IF(cc LIKE ''%เป็นลม%'',             ''เป็นลม'', NULL),
                IF(cc LIKE ''%หมดสติ%'',             ''หมดสติ'', NULL),
                IF(cc LIKE ''%ใจสั่นเหงื่อแตก%'',   ''ใจสั่นเหงื่อแตก'', NULL),
                IF(cc LIKE ''%เหนื่อยง่าย%'',        ''เหนื่อยง่าย'', NULL)
            )) FROM opdscreen WHERE vn = VS.vn LIMIT 1)
        )) AS detail
    FROM vn_stat VS
    LEFT JOIN patient PT ON PT.hn = VS.hn
    LEFT JOIN ovst OV ON OV.vn = VS.vn
    LEFT JOIN spclty SP ON SP.spclty = VS.spclty
    WHERE VS.vstdate = CURDATE()
      AND EXISTS (SELECT 1 FROM opdscreen WHERE vn = VS.vn AND cc IS NOT NULL AND cc != '''')
) t',
        'critical',
        0
    );