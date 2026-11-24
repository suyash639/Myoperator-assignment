-- Independent verification of Phase 2 headline numbers.
-- Reads data/raw/*.json directly with DuckDB. Shares no code with src/metrics.py or src/audit.py.
-- {RAW} is replaced with the raw directory path by src/verify_sql.py.
-- Each row: check_id, numerator, denominator. These are compared against the Python outputs (src/metrics.py, src/audit.py).
-- Extended in Phase 2.2 (DEC-023/DEC-024): attribution variants, new DQ checks, department funnel, completed cohort.

CREATE OR REPLACE MACRO recs(f) AS TABLE
  SELECT unnest(records) AS r FROM read_json(f, format = 'array', maximum_object_size = 104857600);

CREATE OR REPLACE TABLE apps AS
SELECT r.id AS id, r.fields."Stage" AS stage, r.fields."Status" AS status,
       r.fields."Candidate"[1] AS cand, r.fields."Opening"[1] AS opening,
       r.fields."Screened On" AS screened_on, r.fields."Applied On" AS applied_on,
       r.fields."Closed On" AS closed_on,
       coalesce(len(r.fields."Interviews"), 0) AS n_int, coalesce(len(r.fields."Offers"), 0) AS n_off,
       r.fields."Offers"[1] AS offer_id, r.fields."Offered On" AS app_offered_on,
       r.fields."First Interview On" AS first_int_on, r.fields."Final Interview On" AS final_int_on,
       r.fields."Referred By"[1] AS referred_by, r.fields."Application ID" AS app_bk
FROM recs('{RAW}/applications.json');

CREATE OR REPLACE TABLE cands AS
SELECT r.id AS id, r.fields."Source" AS source, lower(trim(r.fields."Full Name")) AS nm,
       replace(r.fields."Phone", ' ', '') AS ph, r.fields."Created On" AS created_on,
       r.fields."Expected CTC" AS expected_ctc
FROM recs('{RAW}/candidates.json');

-- first-touch Source per (name, phone) person: earliest Created On, ties broken by record id
CREATE OR REPLACE TABLE first_touch AS
SELECT c.id, f.source AS ft_source
FROM cands c
JOIN (SELECT nm, ph, arg_min(source, created_on || id) AS source FROM cands GROUP BY nm, ph) f
  ON f.nm = c.nm AND f.ph = c.ph;

CREATE OR REPLACE TABLE offers AS
SELECT r.id AS id, r.fields."Status" AS status, r.fields."Application"[1] AS app,
       r.fields."Offered On" AS offered_on, r.fields."Decision On" AS decision_on,
       r.fields."Base CTC" AS base_ctc
FROM recs('{RAW}/offers.json');

CREATE OR REPLACE TABLE ints AS
SELECT r.id AS id, r.fields."Application"[1] AS app, r.fields."Scheduled On" AS sched, r.fields."Completed On" AS completed_on
FROM recs('{RAW}/interviews.json');

CREATE OR REPLACE TABLE offers2 AS
SELECT r.id AS id, r.fields."Proposed Start Date" AS start_on FROM recs('{RAW}/offers.json');

CREATE OR REPLACE TABLE jobs AS
SELECT r.id AS id, r.fields."Opened On" AS opened_on, r.fields."Department"[1] AS dept FROM recs('{RAW}/job_openings.json');

CREATE OR REPLACE TABLE depts AS
SELECT r.id AS id, r.fields."Name" AS name FROM recs('{RAW}/departments.json');

-- first touch by earliest application date per (name, phone) person
CREATE OR REPLACE TABLE first_touch_applied AS
SELECT c.id, f.source AS fa_source
FROM cands c
JOIN (SELECT c2.nm, c2.ph, arg_min(c2.source, m.min_applied || c2.id) AS source
      FROM cands c2 JOIN (SELECT cand, min(applied_on) AS min_applied FROM apps GROUP BY cand) m ON m.cand = c2.id
      GROUP BY c2.nm, c2.ph) f
  ON f.nm = c.nm AND f.ph = c.ph;

-- latest recorded activity per application (applied, screened, interviews, offer, decision)
CREATE OR REPLACE TABLE last_act AS
SELECT apps.id, greatest(apps.applied_on, coalesce(apps.screened_on, apps.applied_on),
                         coalesce(i.m, apps.applied_on), coalesce(o.offered_on, apps.applied_on),
                         coalesce(o.decision_on, apps.applied_on)) AS last_on
FROM apps
LEFT JOIN (SELECT app, max(sched) AS m FROM ints GROUP BY app) i ON i.app = apps.id
LEFT JOIN offers o ON o.id = apps.offer_id;

-- offers to candidates already hired via another application
CREATE OR REPLACE TABLE prior_hire AS
SELECT o.id, o.status, EXISTS (
         SELECT 1 FROM apps h JOIN offers ho ON ho.id = h.offer_id
         WHERE h.cand = ap.cand AND h.id <> ap.id AND h.stage = 'Hired' AND ho.decision_on < o.offered_on) AS ph
FROM offers o JOIN apps ap ON ap.id = o.app;

CREATE OR REPLACE TABLE a AS
SELECT apps.*, cands.source,
       CASE WHEN referred_by IS NOT NULL THEN 'Referral' ELSE cands.source END AS chan_ref
FROM apps JOIN cands ON apps.cand = cands.id;

CREATE OR REPLACE TABLE results AS
-- hire definitions agree
SELECT 'M-H0' AS check_id,
       (SELECT count(*) FROM a JOIN offers o ON o.app = a.id WHERE a.stage = 'Hired' AND o.status = 'Accepted') AS num,
       (SELECT count(*) FROM (SELECT id FROM a WHERE stage = 'Hired' UNION SELECT app FROM offers WHERE status = 'Accepted')) AS den
UNION ALL SELECT 'M-F0', count(*), count(*) FROM a
UNION ALL SELECT 'M-F1', count(*) FILTER (WHERE screened_on IS NOT NULL), count(*) FROM a
UNION ALL SELECT 'M-F2', count(*) FILTER (WHERE n_int > 0), count(*) FROM a
UNION ALL SELECT 'M-F3', count(*) FILTER (WHERE n_off > 0), count(*) FROM a
UNION ALL SELECT 'M-F4', count(*) FILTER (WHERE stage = 'Hired'), count(*) FROM a
UNION ALL SELECT 'M-FC-interviewed', count(*) FILTER (WHERE n_int > 0 AND screened_on IS NOT NULL), count(*) FILTER (WHERE screened_on IS NOT NULL) FROM a
UNION ALL SELECT 'M-FC-offered', count(*) FILTER (WHERE n_off > 0 AND n_int > 0), count(*) FILTER (WHERE n_int > 0) FROM a
UNION ALL SELECT 'M-FC-hired', count(*) FILTER (WHERE stage = 'Hired' AND n_off > 0), count(*) FILTER (WHERE n_off > 0) FROM a
-- Claim A
UNION ALL SELECT 'M-A0', count(*) FILTER (WHERE source = 'Job Board'), count(*) FROM a WHERE stage = 'Hired'
UNION ALL SELECT 'M-A0r', count(*) FILTER (WHERE source = 'Referral'), count(*) FROM a WHERE stage = 'Hired'
UNION ALL SELECT 'M-A1', count(DISTINCT cand) FILTER (WHERE source = 'Job Board'), count(DISTINCT cand) FROM a WHERE stage = 'Hired'
UNION ALL SELECT 'M-A2', count(*) FILTER (WHERE chan_ref = 'Job Board'), count(*) FROM a WHERE stage = 'Hired'
UNION ALL SELECT 'M-A8', count(*) FILTER (WHERE ft.ft_source = 'Job Board'), count(*) FROM a JOIN first_touch ft ON ft.id = a.cand WHERE a.stage = 'Hired'
UNION ALL SELECT 'M-A5', count(*) FILTER (WHERE source = 'Job Board'), count(*) FROM a
UNION ALL SELECT 'M-A6', count(*) FILTER (WHERE source = 'Job Board'), count(*) FROM cands
UNION ALL SELECT 'M-A7-Job Board', count(*) FILTER (WHERE stage = 'Hired'), count(*) FROM a WHERE source = 'Job Board'
UNION ALL SELECT 'M-A7-Referral', count(*) FILTER (WHERE stage = 'Hired'), count(*) FROM a WHERE source = 'Referral'
UNION ALL SELECT 'M-A7r-Job Board', count(*) FILTER (WHERE stage = 'Hired'), count(*) FROM a WHERE chan_ref = 'Job Board'
UNION ALL SELECT 'M-A7r-Referral', count(*) FILTER (WHERE stage = 'Hired'), count(*) FROM a WHERE chan_ref = 'Referral'
-- Claim B
UNION ALL SELECT 'M-B0', count(*) FILTER (WHERE status = 'Accepted'), count(*) FROM offers
UNION ALL SELECT 'M-B1', count(*) FILTER (WHERE status = 'Accepted'), count(*) FILTER (WHERE status IN ('Accepted', 'Declined')) FROM offers
UNION ALL SELECT 'M-B2', count(*) FILTER (WHERE status IN ('Accepted', 'Pending')), count(*) FROM offers
UNION ALL SELECT 'M-B3', count(*) FILTER (WHERE status = 'Accepted'),
       count(*) FILTER (WHERE status IN ('Accepted', 'Declined') OR (status = 'Pending' AND date_diff('day', offered_on::DATE, DATE '2026-08-27') > 30)) FROM offers
UNION ALL SELECT 'M-B4', count(*) FILTER (WHERE has_acc), count(*) FILTER (WHERE has_acc OR has_dec)
  FROM (SELECT a.cand, bool_or(o.status = 'Accepted') AS has_acc, bool_or(o.status = 'Declined') AS has_dec
        FROM offers o JOIN a ON a.id = o.app GROUP BY a.cand)
-- Data-quality counts
UNION ALL SELECT 'DQ-01',
       (SELECT count(*) FROM a WHERE (referred_by IS NOT NULL AND source <> 'Referral') OR (referred_by IS NULL AND source = 'Referral')),
       (SELECT count(*) FROM a)
UNION ALL SELECT 'DQ-02', (SELECT coalesce(sum(n), 0) FROM (SELECT count(*) AS n FROM cands GROUP BY nm, ph HAVING count(*) > 1)), (SELECT count(*) FROM cands)
UNION ALL SELECT 'DQ-03', (SELECT coalesce(sum(n), 0) FROM (SELECT count(*) AS n FROM a GROUP BY app_bk HAVING count(*) > 1)), (SELECT count(*) FROM a)
UNION ALL SELECT 'DQ-04', (SELECT coalesce(sum(n), 0) FROM (SELECT count(*) AS n FROM a WHERE stage = 'Hired' GROUP BY cand HAVING count(*) > 1)),
       (SELECT count(*) FROM a WHERE stage = 'Hired')
UNION ALL SELECT 'DQ-06', count(*) FILTER (WHERE decision_on IS NOT NULL), count(*) FROM offers WHERE status = 'Pending'
UNION ALL SELECT 'DQ-07', count(*) FILTER (WHERE date_diff('day', offered_on::DATE, DATE '2026-08-27') > 30), count(*) FROM offers WHERE status = 'Pending'
UNION ALL SELECT 'DQ-15',
       (SELECT count(*) FROM (
          SELECT a.id FROM a JOIN offers o ON o.id = a.offer_id WHERE a.app_offered_on IS DISTINCT FROM o.offered_on
          UNION
          SELECT a.id FROM a JOIN (SELECT app, min(sched) AS m FROM ints GROUP BY app) i ON i.app = a.id WHERE a.first_int_on IS DISTINCT FROM i.m)),
       (SELECT count(*) FROM a WHERE n_int > 0 OR n_off > 0)
UNION ALL SELECT 'DQ-16',
       (SELECT count(*) FROM a JOIN (SELECT app, max(sched) AS m FROM ints GROUP BY app) i ON i.app = a.id WHERE a.final_int_on > i.m),
       (SELECT count(*) FROM a WHERE final_int_on IS NOT NULL AND n_int > 0)
UNION ALL SELECT 'DQ-18',
       (SELECT count(*) FROM a JOIN offers o ON o.id = a.offer_id WHERE a.stage = 'Hired' AND a.closed_on < o.decision_on),
       (SELECT count(*) FROM a WHERE stage = 'Hired')
UNION ALL SELECT 'DQ-25',
       (SELECT count(*) FROM offers o JOIN apps ON apps.id = o.app JOIN cands c ON c.id = apps.cand
        WHERE o.base_ctc::DOUBLE / c.expected_ctc < 0.67 OR o.base_ctc::DOUBLE / c.expected_ctc > 1.5),
       (SELECT count(*) FROM offers)
-- Phase 2.2 additions: attribution variants
UNION ALL SELECT 'M-A9', count(*) FILTER (WHERE referred_by IS NULL AND source = 'Job Board'), count(*) FROM a WHERE stage = 'Hired'
UNION ALL SELECT 'M-A9n', count(*) FILTER (WHERE referred_by IS NULL), count(*) FROM a WHERE stage = 'Hired' AND source = 'Referral'
UNION ALL SELECT 'M-A10', count(*) FILTER (WHERE f.fa_source = 'Job Board'), count(*) FROM a JOIN first_touch_applied f ON f.id = a.cand WHERE a.stage = 'Hired'
UNION ALL SELECT 'M-A7s-Job Board', count(*) FILTER (WHERE stage = 'Hired'), count(*) FROM a WHERE referred_by IS NULL AND source = 'Job Board'
UNION ALL SELECT 'M-A7m-Job Board', count(*) FILTER (WHERE a.stage = 'Hired'), count(*) FROM a JOIN first_touch ft ON ft.id = a.cand WHERE ft.ft_source = 'Job Board'
-- offer variants
UNION ALL SELECT 'M-B3-2026-11-24', count(*) FILTER (WHERE status = 'Accepted'),
       count(*) FILTER (WHERE status IN ('Accepted', 'Declined') OR (status = 'Pending' AND date_diff('day', offered_on::DATE, DATE '2026-11-24') > 30)) FROM offers
UNION ALL SELECT 'M-B9', count(*) FILTER (WHERE ph), count(*) FROM prior_hire WHERE status IN ('Accepted', 'Declined')
UNION ALL SELECT 'M-B10', count(*) FILTER (WHERE status = 'Accepted'), count(*) FROM prior_hire WHERE status IN ('Accepted', 'Declined') AND NOT ph
-- new and rebuilt DQ checks
UNION ALL SELECT 'DQ-13', (SELECT count(DISTINCT id) FROM (
          SELECT a.id FROM a JOIN jobs j ON j.id = a.opening WHERE a.applied_on < j.opened_on
          UNION ALL SELECT i.id FROM ints i JOIN apps ap ON ap.id = i.app WHERE i.sched < ap.applied_on OR i.sched < ap.screened_on
          UNION ALL SELECT id FROM ints WHERE completed_on < sched
          UNION ALL SELECT ap.id FROM apps ap JOIN offers o ON o.id = ap.offer_id JOIN (SELECT app, max(sched) AS m FROM ints GROUP BY app) i ON i.app = ap.id WHERE i.m > o.offered_on
          UNION ALL SELECT o.id FROM offers o JOIN offers2 o2 ON o2.id = o.id WHERE o.offered_on > o.decision_on OR o.offered_on > o2.start_on OR o.decision_on > o2.start_on
          UNION ALL SELECT id FROM apps WHERE applied_on > first_int_on OR screened_on > first_int_on OR first_int_on > final_int_on OR final_int_on > app_offered_on
          UNION ALL SELECT id FROM cands WHERE created_on > '2026-08-27')),
       (SELECT count(*) FROM apps) + (SELECT count(*) FROM ints) + (SELECT count(*) FROM offers) + (SELECT count(*) FROM cands)
UNION ALL SELECT 'DQ-26', count(*) FILTER (WHERE a.closed_on < o.decision_on), count(*) FROM a JOIN offers o ON o.id = a.offer_id WHERE o.status = 'Declined'
UNION ALL SELECT 'DQ-27', count(*) FILTER (WHERE i.m > a.closed_on), count(*)
  FROM a JOIN (SELECT app, max(sched) AS m FROM ints GROUP BY app) i ON i.app = a.id
  WHERE a.stage IN ('Rejected', 'Withdrawn') AND a.closed_on IS NOT NULL
UNION ALL SELECT 'DQ-28', count(*) FILTER (WHERE date_diff('day', l.last_on::DATE, DATE '2026-08-27') > 90), count(*)
  FROM a JOIN last_act l ON l.id = a.id WHERE a.status = 'Active'
UNION ALL SELECT 'DQ-29', count(*) FILTER (WHERE ph), count(*) FROM prior_hire
-- department funnel (Engineering)
UNION ALL SELECT 'M-DF-Engineering-hired', count(*) FILTER (WHERE a.stage = 'Hired'), count(*)
  FROM a JOIN jobs j ON j.id = a.opening JOIN depts d ON d.id = j.dept WHERE d.name = 'Engineering'
UNION ALL SELECT 'M-DF-Engineering-interviewed', count(*) FILTER (WHERE a.n_int > 0), count(*)
  FROM a JOIN jobs j ON j.id = a.opening JOIN depts d ON d.id = j.dept WHERE d.name = 'Engineering'
-- completed cohort
UNION ALL SELECT 'M-K-eligible',
       count(*) FILTER (WHERE a.status = 'Closed' OR date_diff('day', l.last_on::DATE, DATE '2026-08-27') > 90), count(*)
  FROM a JOIN last_act l ON l.id = a.id WHERE a.applied_on BETWEEN '2025-07-01' AND '2026-03-31'
UNION ALL SELECT 'M-KF3', count(*) FILTER (WHERE a.n_off > 0), count(*)
  FROM a JOIN last_act l ON l.id = a.id WHERE a.applied_on BETWEEN '2025-07-01' AND '2026-03-31'
   AND (a.status = 'Closed' OR date_diff('day', l.last_on::DATE, DATE '2026-08-27') > 90)
UNION ALL SELECT 'M-KF4', count(*) FILTER (WHERE a.stage = 'Hired'), count(*)
  FROM a JOIN last_act l ON l.id = a.id WHERE a.applied_on BETWEEN '2025-07-01' AND '2026-03-31'
   AND (a.status = 'Closed' OR date_diff('day', l.last_on::DATE, DATE '2026-08-27') > 90)
-- referential integrity: forward links to records missing from the snapshot
UNION ALL SELECT 'REL-orphans',
       (SELECT count(*) FROM apps WHERE cand NOT IN (SELECT id FROM cands))
     + (SELECT count(*) FROM offers WHERE app NOT IN (SELECT id FROM apps))
     + (SELECT count(*) FROM ints WHERE app NOT IN (SELECT id FROM apps)),
       (SELECT count(*) FROM apps) + (SELECT count(*) FROM offers) + (SELECT count(*) FROM ints);

SELECT * FROM results ORDER BY check_id;
