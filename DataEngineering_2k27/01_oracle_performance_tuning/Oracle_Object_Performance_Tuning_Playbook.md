# Oracle Object Performance Tuning Playbook

## Purpose and operating principles

This playbook is a repeatable, evidence-led workflow for diagnosing Oracle object and SQL performance. It covers the common production object families requested here; it is not a claim that one setting or index strategy is optimal for every workload or Oracle release.

**Important:** The 50 case patterns in Section 14 are anonymized, representative production archetypes with explicitly illustrative measurements. They are not claims about a particular customer's database, and their numbers are not performance guarantees. Replace them with measurements from the target system.

### Safety, licensing, and version notes

- Confirm Oracle version, edition, CDB/PDB, RAC, workload, business SLA, maintenance window, and rollback path before changing anything. Syntax and available columns vary by release.
- AWR, ASH, ADDM, SQL Tuning Advisor, and Real-Time SQL Monitoring are subject to Oracle Diagnostics Pack and/or Tuning Pack licensing terms. Verify entitlements for the exact release and deployment before using these features. Do not query `DBA_HIST_*` or ASH simply because access is technically available.
- The examples use conventional `V$`, `DBA_`, and `ALL_` views. Substitute `GV$` for RAC-wide investigation and include `INST_ID`; use `CDB_*` views and `CON_ID` when authorized and diagnosing across containers. Access may require catalog privileges.
- Bind values and object names below are examples. Use approved bind handling, least privilege, and change-management controls. Avoid exposing bind values that may contain personal, financial, or secret data.
- Do not tune from a single ratio, `EXPLAIN PLAN`, object size, or “fragmentation” score. Compare the same SQL, bind/selectivity class, concurrency, and representative workload before and after.
- Capture a baseline and a rollback plan before each change. Prefer one controlled change at a time; make online/online-redefinition claims only after checking release, edition, object features, and operational constraints.

## 1. Universal performance-tuning workflow

### Step 1 — Collect evidence

**Activities:** Record incident window, affected service and SQL, elapsed-time distribution, throughput, concurrency, bind/selectivity classes, recent deployments, batch overlap, and business impact. Capture the exact SQL text and child cursor/plan information.

**Queries (current workload):**

```sql
-- Top statements by cumulative elapsed time since instance startup.
-- Use deltas over a bounded interval for incident analysis; totals can be misleading.
SELECT sql_id, child_number, plan_hash_value, executions,
       ROUND(elapsed_time / 1e6, 2) elapsed_s,
       ROUND(cpu_time / 1e6, 2) cpu_s,
       buffer_gets, disk_reads, rows_processed,
       SUBSTR(sql_text, 1, 120) sql_text
FROM   v$sql
WHERE  executions > 0
ORDER  BY elapsed_time DESC
FETCH FIRST 30 ROWS ONLY;

-- Active sessions and blockers. Use GV$SESSION for RAC.
SELECT sid, serial#, username, sql_id, event, wait_class,
       state, seconds_in_wait, blocking_session,
       row_wait_obj#, row_wait_file#, row_wait_block#, row_wait_row#
FROM   v$session
WHERE  type = 'USER'
AND    status = 'ACTIVE';

-- Instance event totals are cumulative, not incident-window deltas.
SELECT event, wait_class, total_waits,
       ROUND(time_waited_micro / 1e6, 2) waited_s
FROM   v$system_event
WHERE  wait_class <> 'Idle'
ORDER  BY time_waited_micro DESC
FETCH FIRST 30 ROWS ONLY;
```

**Tools:** `V$SESSION`, `V$SQL`, `V$SQLSTATS`, `V$SQL_PLAN`, SQL trace/TKPROF where approved, application telemetry, OS/storage/cluster metrics, and (licensed) AWR/ASH/ADDM or SQL Monitor.

**Decision points:** Is the issue still active? Is DB time mainly on CPU, I/O, locks, cluster waits, or parse? Is one SQL dominant, or is the system saturated across many statements? Is it an execution-time problem or a queueing/capacity problem?

**Expected result:** A timestamped baseline tied to SQL_ID, plan hash, object(s), service/module/action, and an observed user impact.

**Common mistakes:** Treating cumulative counters as interval measurements; looking only at average latency; overlooking application connection queues; comparing unlike binds; querying AWR without licensing; using a shared pool dump as a first step.

### Step 2 — Identify the bottleneck

**Activities:** Separate database time from end-to-end time. Decompose CPU, user I/O, concurrency, cluster, commit, and parse; find the dominant SQL, wait, plan line, and object.

**Queries:** Review `V$SQLSTATS` deltas; active wait distribution and blocker chain in `V$SESSION`; plan row-source statistics with `DBMS_XPLAN.DISPLAY_CURSOR`. If licensed, use AWR Load Profile, Top Timed Events, SQL ordered by elapsed/CPU/gets/reads, SQL Statistics, and ASH Top SQL/Top Events/Top Objects/Blocking Sessions. ADDM findings are leads to validate, not instructions to apply blindly.

```sql
-- Actual row-source plan stats are available only if collected (e.g. GATHER_PLAN_STATISTICS
-- or an appropriate statistics_level). Use the exact SQL_ID and child number.
SELECT *
FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(:sql_id, :child_no,
                                     'ALLSTATS LAST +PEEKED_BINDS'));
```

Use `ALLSTATS LAST` to compare estimated rows (`E-Rows`) and actual rows (`A-Rows`), starts, buffer gets, and elapsed time by operation. `PEEKED_BINDS` can expose sensitive values; omit it when unsuitable.

**Expected result:** A ranked bottleneck with a measurable contribution to DB time or SLA.

**Common mistakes:** Fixing the loudest wait name without tracing its cause; optimizing a query that is not material to the workload; treating `EXPLAIN PLAN` as the executed plan; tuning memory before identifying actual pressure.

### Step 3 — Determine root cause

**Activities:** Walk from symptom to mechanism: plan shape and actual row counts, predicates and data distribution, object layout/statistics, concurrency and transaction design, memory/temp/I/O, and recent changes.

**Queries/tools:** Actual cursor plan; `V$SQL_PLAN_STATISTICS_ALL`; `DBA_TAB_STATISTICS`, `DBA_IND_STATISTICS`, `DBA_TAB_COL_STATISTICS`, `DBA_TAB_MODIFICATIONS`; `DBA_SEGMENTS`; `V$TEMPSEG_USAGE`; `V$SESSION`; lock views; `V$ACTIVE_SESSION_HISTORY` only when licensed; SQL trace/TKPROF for call-level evidence. Compare representative bind values and child cursors.

**Decision points:** Is there a cardinality error, avoidable work, missing access path, skew/histogram problem, contention, resource ceiling, or data-model mismatch? Does the evidence establish causality?

**Expected result:** One testable root-cause statement, such as “the date predicate is non-sargable, so all monthly partitions are visited,” with evidence.

**Common mistakes:** “Add an index” before checking selectivity and table access cost; rebuilding objects without proving benefit; interpreting a full scan as automatically wrong; applying hints that mask stale stats or bad SQL.

### Step 4 — Verify object impact

**Activities:** Map plan operations and ASH samples to owner/object, partition, data object ID, and workload. Check write overhead, constraints, dependent SQL, ETL, and other consumers.

**Queries:**

```sql
SELECT owner, object_name, subobject_name, object_type, object_id,
       data_object_id
FROM   dba_objects
WHERE  owner = UPPER(:owner)
AND    object_name = UPPER(:object_name);

SELECT owner, segment_name, partition_name, segment_type,
       ROUND(bytes / 1024 / 1024, 1) mb, blocks, extents
FROM   dba_segments
WHERE  owner = UPPER(:owner)
AND    segment_name = UPPER(:object_name)
ORDER  BY partition_name;
```

**Expected result:** Confirmed object/partition relationship and impact to its consumers, including DML and maintenance operations.

**Common mistakes:** Confusing `OBJECT_ID` with `DATA_OBJECT_ID`; assuming the sampled current object is the sole cause; missing index, LOB, or partition subobjects.

### Step 5 — Implement a controlled fix

**Activities:** State hypothesis, change, expected metric, exposure, approver, timing, rollback, and stop conditions. Use a test/staging workload or production canary where possible. Prefer reversible changes and plan baselines for a known plan regression.

**Tools:** Change management; SQL Plan Management where appropriate; online index/DDL options only after compatibility review; `DBMS_STATS` with pending stats or restore points as suitable; DDL scripts saved and reviewed.

**Decision points:** Does it preserve results and semantics? Can it be rolled back within the SLA? Is there a lock, space, redo, replication, or failover consequence?

**Expected result:** One isolated change with a captured pre-change state.

**Common mistakes:** Multiple simultaneous changes; silently changing isolation or query results; rebuilding an index during peak hours; relying on rollback for DDL (Oracle DDL commits implicitly).

### Step 6 — Validate improvement

**Activities:** Execute equivalent workload and binds. Compare elapsed percentiles, CPU, buffer gets, physical reads, rows, plan hash and actual row-source stats, throughput, concurrency, errors, and downstream impacts. Check write costs after index or MV changes.

**Expected result:** Statistically and operationally meaningful improvement without regressions or result changes. A lower elapsed time with a materially different workload is not proof.

**Common mistakes:** Comparing one lucky run; ignoring warm cache or concurrency; interpreting lower reads as a success when latency worsens; failing to verify correctness.

### Step 7 — Monitor and document

**Activities:** Observe after deployment and through representative peak/batch periods; alert on plan changes, regressions, blocking, growth, refresh lag, errors, and SLA percentiles. Save before/after evidence and rollback outcome.

**Expected result:** Improvement persists across the relevant workload cycle and the operational owner knows the new behavior.

**Common mistakes:** Ending monitoring after a smoke test; forgetting partition rollover or statistics jobs; leaving temporary diagnostic instrumentation enabled.

## 2. Table performance tuning

### 2.1 Architecture and workload classes

Heap tables store rows in heap-organized blocks; rowids locate rows. A segment may have multiple extents and, for partitioned tables, separate partition segments. IOTs store rows in a primary-key B-tree. Temporary tables have session- or transaction-scoped row semantics. External tables read files through access drivers and do not store ordinary table data segments. Big Table Cache is a buffer-cache feature for eligible scan-heavy segments, not a table type or substitute for SQL tuning.

Start with workload: OLTP point lookups and updates, reporting scans, bulk loads, transient work, file ingestion, or a hot lookup table. Compare rows, bytes, block visits, DML rate, concurrency, and SLA.

### 2.2 Symptom-to-diagnosis patterns

| Problem | Symptoms and evidence | Likely causes / first checks |
|---|---|---|
| Full table scan | `TABLE ACCESS FULL`, high physical reads/gets, elapsed time | May be correct for large result sets. Check predicates, rows, partition pruning, table size, cache and parallelism. |
| High logical reads | High buffer gets per execution; CPU-heavy SQL | Repeated probes, inefficient joins, poor selectivity, nested loops with too many starts, repeated PL/SQL SQL calls. |
| High physical reads | Read waits / physical read bytes / direct reads | Broad scans, cold cache, storage latency, temp spill, concurrent I/O. Distinguish single-block from multiblock and direct-path I/O. |
| Hot blocks / block contention | `buffer busy waits`, `read by other session`, `gc buffer busy` (RAC); ASH block samples | Concurrent access to same data or index block, right-edge insert, ITL pressure, poor transaction pattern. |
| Row chaining/migration | Extra block visits; high `table fetch continued row`; chained-row analysis | Rows span blocks due to row growth, small block/large rows, wide rows, or PCTFREE/updates. A high count is not by itself proof of a performance incident. |
| Segment growth | Rapid `DBA_SEGMENTS` growth, tablespace pressure, partition imbalance | Data retention, LOB growth, excessive extents are not automatically fragmentation; inspect row/LOB volume and space use. |
| Skewed data | Cardinality estimates diverge for values; plan varies by bind | Data skew, correlated columns, stale/missing stats, bind peeking/adaptive cursor sharing. |
| Temporary table pressure | Temp spills, `direct path write temp/read temp` | Large sorts/hash operations, PGA pressure, high concurrency, unnecessary intermediate results. |

### 2.3 Detection queries

```sql
-- Object touches in cached cursor plans (not a complete historical workload inventory).
SELECT p.object_owner, p.object_name, p.object_type, p.operation, p.options,
       COUNT(DISTINCT p.sql_id) sql_count
FROM   v$sql_plan p
WHERE  p.object_owner = UPPER(:owner)
AND    p.object_name = UPPER(:table_name)
GROUP  BY p.object_owner, p.object_name, p.object_type, p.operation, p.options
ORDER  BY sql_count DESC;

-- Full scans of the specified table in cached plans. A scan is evidence to inspect,
-- not proof of a problem; evaluate actual rows, bytes, gets, and elapsed time.
SELECT p.sql_id, p.child_number, s.plan_hash_value, s.executions,
       s.buffer_gets, s.disk_reads, s.rows_processed, s.last_active_time,
       p.operation, p.options, p.object_owner, p.object_name
FROM   v$sql_plan p
JOIN   v$sql s
  ON   s.sql_id = p.sql_id
 AND   s.child_number = p.child_number
WHERE  p.object_owner = UPPER(:owner)
AND    p.object_name = UPPER(:table_name)
AND    p.operation = 'TABLE ACCESS'
AND    p.options = 'FULL'
ORDER  BY s.last_active_time DESC;

-- Physical and logical read counters are cumulative since instance start.
SELECT owner, object_name, subobject_name, object_type, value
FROM   v$segment_statistics
WHERE  owner = UPPER(:owner)
AND    object_name = UPPER(:table_name)
AND    statistic_name IN ('logical reads', 'physical reads',
                          'buffer busy waits', 'ITL waits')
ORDER  BY statistic_name, subobject_name;

-- Table stats / estimated row count and last analyzed timestamp.
SELECT owner, table_name, num_rows, blocks, avg_row_len, chain_cnt,
       stale_stats, last_analyzed, partitioned, temporary
FROM   dba_tab_statistics
WHERE  owner = UPPER(:owner)
AND    table_name = UPPER(:table_name)
AND    partition_name IS NULL;

-- Recent DML monitoring counts (best effort, not exact real-time counters).
SELECT table_owner, table_name, inserts, updates, deletes, timestamp
FROM   dba_tab_modifications
WHERE  table_owner = UPPER(:owner)
AND    table_name = UPPER(:table_name);

-- Row chaining/migration: create an appropriately privileged target table once
-- using the Oracle-provided UTLCHN1.SQL script (or equivalent documented definition).
-- Then:
-- ANALYZE TABLE owner.table_name LIST CHAINED ROWS INTO owner.chained_rows;
-- SELECT head_rowid FROM owner.chained_rows WHERE table_name = UPPER(:table_name);
-- ANALYZE ... is for this diagnostic only; use DBMS_STATS for optimizer statistics.
```

`V$SEGMENT_STATISTICS` values are cumulative; sample twice and calculate deltas. For block-level evidence, correlate ASH `CURRENT_OBJ#`, `CURRENT_FILE#`, and `CURRENT_BLOCK#` (licensed) with `DBA_OBJECTS`/`DBA_EXTENTS`; ASH rows are sampled, not an exact event log:

```sql
-- Licensed ASH example; restrict to the incident window and relevant SQL/service.
SELECT current_obj#, current_file#, current_block#, event,
       COUNT(*) samples
FROM   v$active_session_history
WHERE  sample_time >= :start_time
AND    sample_time <  :end_time
AND    current_obj# > 0
GROUP  BY current_obj#, current_file#, current_block#, event
ORDER  BY samples DESC
FETCH FIRST 30 ROWS ONLY;
```

### 2.4 Diagnostic workflow and fixes

1. Identify SQL_ID and actual plan; determine whether the scan is by design. A full scan can be optimal for a large fraction of rows.
2. Check actual rows versus estimates at filters and joins; inspect predicate section, implicit conversions, partition start/stop, and projection width.
3. Check current table/column stats, histograms, data skew, DML since stats, compression, block size, and segment/partition size.
4. For contention, identify hot object/block and concurrent SQL/transactions. Inspect `V$SESSION`, blockers, ITL waits, index right-edge inserts, and RAC `gc` waits.
5. For chaining, verify material impact and row growth. Consider a table move/redefinition only when justified; preserve grants, constraints, indexes, triggers, policies, LOB attributes, and availability requirements.
6. Apply the smallest effective fix: query rewrite; correct stats; targeted index; partitioning for lifecycle/pruning; schema/data-type correction; bulk DML; concurrency redesign; storage/capacity change.
7. Gather/restore stats deliberately, and validate both query and DML workload.

**Before/after scorecard (fill with actual values):**

| Measure | Before | After | Acceptance |
|---|---:|---:|---|
| p95/p99 elapsed per execution | measured | measured | Meets SLA over comparable workload |
| CPU and buffer gets per execution | measured | measured | Work reduction, not merely shifted waiting |
| Physical reads / read latency | measured | measured | No storage regression |
| Rows returned / plan hash / actual rows | measured | measured | Same result and explainable plan |
| DML latency / redo / concurrency | measured | measured | No unacceptable write cost |

### 2.5 Table subtype-specific guidance

- **Partitioned:** Confirm partition pruning in the executed plan (`PSTART`/`PSTOP`); use predicates on partition keys with compatible types; inspect partition-level stats and skew. Partitioning helps manageability and elimination, not automatically every query.
- **Temporary:** Validate GTT transaction/session semantics and stats behavior; account for temp segment allocation, temp tablespace, PGA, and concurrency. Avoid repeated populate/read/drop patterns when a set-based query works.
- **External:** Measure file format parsing, remote/local storage, directory access, parallelism and reject limits. Push predicates where the access driver supports it. External data has no ordinary table segment/index; stage into a managed table if repeated indexed access is required.
- **IOT:** Best for primary-key access and index-organized clustering. Check overflow segment, secondary-index rowid cost, key width and update costs. Avoid wide/volatile primary keys when they bloat all secondary indexes.
- **Big Table Cache:** Evaluate only for scan-heavy workloads and supported configuration; it may protect the conventional cache from large scans. Confirm scan behavior and cache impact; do not blindly force caching.
- **Small lookup tables:** Full scans may be cheapest. Check cardinality, buffer residency, join order, and concurrent updates before adding indexes or parallelism.

**Slow vs improved example:** Avoid assuming a scan needs an index.

```sql
-- Broad scan of a large table; may be expensive for a selective date range.
SELECT *
FROM   sales
WHERE  TRUNC(order_date) = DATE '2025-01-15';

-- Sargable, narrow projection; may enable range scan and partition pruning.
SELECT order_id, customer_id, amount
FROM   sales
WHERE  order_date >= DATE '2025-01-15'
AND    order_date <  DATE '2025-01-16';
```

If most rows on that day are needed, a table/partition scan may remain the correct plan. An alternative function-based index must be justified against all consumers and DML.

## 3. Index performance tuning

### 3.1 Architecture and selection

B-tree indexes are balanced search trees; a leaf contains key values and rowids. Bitmap indexes encode value-to-row sets and are useful in low-concurrency analytic workloads. Local partitioned indexes align with table partitions; global indexes span partitions. Composite column order matters. Function-based indexes store expressions. Reverse-key indexes reverse key bytes to spread monotonically increasing inserts but lose ordinary range-scan behavior. Descending indexes support descending key order/use cases. Invisible indexes are maintained but ignored by the optimizer unless enabled for a session.

### 3.2 When to use / avoid

| Type | Consider when | Avoid / caution |
|---|---|---|
| B-tree | Selective equality/range predicates, joins, ordering, uniqueness | Low-selectivity scans may be cheaper; every index adds DML, storage, cache and maintenance cost. |
| Bitmap | Read-mostly warehouse dimensions; combining predicates | High-concurrency OLTP DML on indexed rows can serialize and create contention. |
| Function-based | Predicate repeatedly uses same deterministic expression | Expression mismatch, NLS/dependency issues, changed semantics; add stats on expression as needed. |
| Reverse key | Right-edge insert contention on monotonically increasing key | Range predicates/order by the original key, where key order is needed. |
| Composite | Frequently used predicate prefix / join and order pattern | Excess width, wrong leading column, redundant overlapping indexes. |
| Local partitioned | Partition-aligned access/maintenance; partition pruning | Queries without partition key may visit many local index partitions. |
| Global partitioned/nonpartitioned | Cross-partition lookup or unique key not containing partition key | Partition maintenance can invalidate/maintain global indexes; operational cost. |
| Invisible | Safely test a candidate index plan for a session | Does not eliminate DML/storage cost; not a substitute for controlled testing. |
| Descending | Descending access or mixed ordering where plan can use it | Do not create based on `ORDER BY` alone; test plan and workload. |

### 3.3 Detection and analysis queries

```sql
-- Index structure, visibility, status and partition type.
SELECT i.owner, i.index_name, i.table_name, i.index_type, i.uniqueness,
       i.status, i.visibility, i.blevel, i.leaf_blocks, i.distinct_keys,
       i.clustering_factor, i.last_analyzed, i.partitioned
FROM   dba_indexes i
WHERE  i.owner = UPPER(:owner)
AND    i.table_name = UPPER(:table_name)
ORDER  BY i.index_name;

-- Key order and column stats.
SELECT index_name, column_position, column_name, descend
FROM   dba_ind_columns
WHERE  index_owner = UPPER(:owner)
AND    table_name = UPPER(:table_name)
ORDER  BY index_name, column_position;

-- Index segment size (include partitions/subpartitions).
SELECT owner, segment_name, partition_name, segment_type,
       ROUND(bytes / 1024 / 1024, 1) mb
FROM   dba_segments
WHERE  owner = UPPER(:owner)
AND    segment_name IN
       (SELECT index_name FROM dba_indexes
        WHERE owner = UPPER(:owner) AND table_name = UPPER(:table_name))
ORDER  BY segment_name, partition_name;

-- Plans using a table's indexes, currently cached.
SELECT p.sql_id, p.child_number, p.operation, p.options, p.object_name,
       p.cardinality, p.cost, s.last_active_time
FROM   v$sql_plan p
JOIN   v$sql s
  ON   s.sql_id = p.sql_id
 AND   s.child_number = p.child_number
WHERE  p.object_owner = UPPER(:owner)
AND    p.object_name IN
       (SELECT index_name FROM dba_indexes
        WHERE owner = UPPER(:owner) AND table_name = UPPER(:table_name))
ORDER  BY s.last_active_time DESC;

-- Index usage monitoring is limited evidence. Start a measured monitoring window:
-- ALTER INDEX owner.index_name MONITORING USAGE;
-- Later inspect DBA_OBJECT_USAGE, then stop:
-- ALTER INDEX owner.index_name NOMONITORING USAGE;
```

**Unused index caution:** `DBA_OBJECT_USAGE` only covers monitored periods and has limitations (scope/operations vary by release). A quiet period does not prove an index is unused: rare month-end, failover, reporting, constraints, foreign keys, and application paths matter. Check SQL plans/AWR (licensed), dependencies, constraints, index uniqueness, and workload calendar before removal. An index can enforce a business rule even when the optimizer does not select it.

**Missing index:** There is no reliable universal “missing index” query. Use actual SQL predicates, plan row counts/gets, workload frequency, selectivity, clustering factor, and write rate. Validate a candidate using invisible index/session testing and representative binds. Do not infer a missing index from a full scan alone.

**Fragmentation/inefficiency:** BLEVEL, leaf blocks, deleted leaf rows, and clustering factor are clues, not rebuild criteria. Rebuild only with demonstrated benefit (e.g., unusable index, required space recovery/maintenance or measured physical inefficiency) and a plan for locks, space, redo, online restrictions, and rollback. `ANALYZE INDEX ... VALIDATE STRUCTURE` can be intrusive and creates diagnostic data; do not run casually on a large production index.

### 3.4 Slow SQL example, plan review, and fix

```sql
SELECT order_id, order_date, status
FROM   orders
WHERE  TRUNC(order_date) = DATE '2025-02-01'
AND    customer_id = :customer_id;
```

Review the executed plan for `Predicate Information`, actual `A-Rows`, `Starts`, buffer gets, and whether a filter is applied after reading many rows. A function over `order_date` may prevent use of a plain date index. Candidate fix:

```sql
SELECT order_id, order_date, status
FROM   orders
WHERE  order_date >= DATE '2025-02-01'
AND    order_date <  DATE '2025-02-02'
AND    customer_id = :customer_id;

-- A candidate composite index, only after validating selectivity and DML impact:
CREATE INDEX orders_cust_date_ix ON orders(customer_id, order_date);
```

Index leading column and column order must match workload. Do not force index use with a hint unless measured evidence and plan governance require it.

**Post-tuning:** Compare plan hash, actual rows, buffer gets, physical reads, elapsed percentiles and inserts/updates/deletes. Rollback by dropping a newly created index (after checking dependencies); for a new index invisible first then visible is a controlled option, but creation still incurs resource costs. Restore prior stats/plan only through a planned procedure.

## 4. Partitioning tuning

### Strategy choice

- **Range:** Ordered time/numeric values; lifecycle, archival, pruning. Define boundary convention (`VALUES LESS THAN`) carefully.
- **Interval:** Auto-creates range partitions beyond a transition point; useful for regularly arriving time data. Monitor default/interval partition creation and tablespace placement.
- **List:** Discrete categories such as region or tenant with known values; manage new/default values.
- **Hash:** Distributes rows evenly for concurrency or partition-wise access; does not provide time-based purge or natural range pruning.
- **Composite:** E.g., range-hash or range-list; use when lifecycle dimension plus within-range distribution is needed. More segments, stats, and maintenance complexity.

Select a partition key and granularity from the actual predicate/lifecycle pattern, not table size alone. Evaluate skew, number/size of partitions, pruning opportunity, indexes, join compatibility, exchange/load process, and maintenance overhead.

### Detect pruning failures and hotspots

1. Inspect executed cursor plan partition start/stop (`PSTART`/`PSTOP`), `PARTITION RANGE ALL`, actual rows and I/O by partition.
2. Check datatype/implicit conversion, function/wrapping on key, predicate boundaries, bind type, and query transformations.
3. Inspect `DBA_TAB_PARTITIONS`/`DBA_TAB_SUBPARTITIONS` row counts, stats and segments; compare workload samples by partition.
4. For hotspots, correlate ASH object/data-object and block samples (licensed) or segment-stat deltas with partition; distinguish skewed data from skewed access.
5. For partition-wise joins, compare compatible partitioning keys, join predicates, partition alignment and plan operations (`PARTITION HASH/RANGE`, `PX ...` where parallel). Parallel partition-wise joins can increase resource use and are not automatically faster.

```sql
SELECT table_owner, table_name, partition_name, num_rows, blocks,
       last_analyzed, global_stats, user_stats
FROM   dba_tab_partitions
WHERE  table_owner = UPPER(:owner)
AND    table_name = UPPER(:table_name)
ORDER  BY partition_position;

SELECT owner, segment_name, partition_name, segment_type,
       ROUND(bytes / 1024 / 1024, 1) mb
FROM   dba_segments
WHERE  owner = UPPER(:owner)
AND    segment_name = UPPER(:table_name)
ORDER  BY bytes DESC;
```

**Example:** For monthly range partitioned `SALES(order_date)`, use half-open ranges:

```sql
SELECT SUM(amount)
FROM   sales
WHERE  order_date >= DATE '2025-01-01'
AND    order_date <  DATE '2025-02-01';
```

Avoid `TRUNC(order_date)` unless a matching function-based design is intentional. Check plan `PSTART`/`PSTOP` and actual visited partitions.

**Maintenance:** Use partition exchange/drop/truncate only with verified constraints, indexes, statistics, referential integrity, replication, and retention policy. Local indexes simplify partition maintenance but do not eliminate all costs. Global indexes can become unusable depending on DDL and release/options; verify status immediately. Test `UPDATE GLOBAL INDEXES`/asynchronous maintenance behavior for the target version and operation. Maintain partition and global stats intentionally; do not gather all stats after every partition operation without a reason.

**Rollback:** Partition DDL may be irreversible or auto-commit. Preserve exchanged data in a staging table, validate boundaries and index status, and use an approved backup/restore or reverse exchange plan. Do not promise transactional rollback for DDL.

## 5. Materialized view tuning

### Design, refresh, rewrite

A materialized view (MV) stores query results. Query rewrite lets the optimizer substitute a compatible MV when `QUERY_REWRITE_ENABLED` and integrity settings permit. Fast refresh uses change logs/metadata when the defining query and changes meet restrictions; complete refresh recomputes results. “Incremental refresh” generally refers to fast refresh or release-specific mechanisms and is not universally supported by every query shape.

1. Identify expensive repeated SQL and candidate common aggregation/join.
2. Check MV capabilities (`DBMS_MVIEW.EXPLAIN_MVIEW`; install the release-provided capability table script as required), rewrite eligibility (`DBMS_MVIEW.EXPLAIN_REWRITE`), freshness and refresh logs.
3. Test refresh cost, base-table DML overhead, staleness window, and query equivalence.
4. Select `ON COMMIT` only if synchronous commit cost is acceptable; otherwise schedule `ON DEMAND`.

```sql
SELECT owner, mview_name, refresh_mode, refresh_method, staleness,
       compile_state, last_refresh_type, last_refresh_date
FROM   dba_mviews
WHERE  owner = UPPER(:owner);

-- Diagnose capabilities with DBMS_MVIEW.EXPLAIN_MVIEW after creating the
-- release-appropriate MV_CAPABILITIES_TABLE using Oracle's supplied script.
-- Query the table for capability_name, possible, related_text, msgtxt.
```

**Slow refresh:** Check refresh method, refresh duration and row volume, MV log size/overhead, base-table DML, indexes/constraints on MV, temp/undo/redo, locks and refresh concurrency. Compare fast vs complete refresh eligibility; check explain plan of defining SQL.

**Failures:** Capture exact error stack, `DBA_MVIEW_REFRESH_TIMES` if available, scheduler/job logs, `DBA_MVIEW_LOGS`, refresh dependencies, privileges and invalid objects. Never swallow refresh errors or publish stale data as fresh.

**Rewrite failure/stale data:** Verify rewrite settings in the executing session/system, cost-based eligibility, query text equivalence, constraints, freshness/integrity mode, and capabilities. Check `DBA_MVIEWS.STALENESS`; do not force `STALE_TOLERATED` unless the business explicitly accepts stale results.

**Example:**

```sql
CREATE MATERIALIZED VIEW sales_by_day
BUILD IMMEDIATE
REFRESH FAST ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT TRUNC(sale_ts) sale_day, product_id, SUM(amount) amount_sum,
       COUNT(*) row_count
FROM   sales
GROUP  BY TRUNC(sale_ts), product_id;
```

This shape may require a materialized view log and additional count expressions for fast refresh; verify with `EXPLAIN_MVIEW`, not assumption. Example refresh:

```sql
BEGIN
  DBMS_MVIEW.REFRESH(list => 'SALES_BY_DAY', method => 'F');
END;
/
```

Rollback: disable rewrite/drop only after routing consumers back to base SQL and confirming SLA; coordinate MV log changes with other MVs. Recreating an MV or logs can be expensive.

## 6. View performance tuning

Ordinary views store SQL text, not rows; the optimizer usually merges/inlines them, but aggregation, `DISTINCT`, set operators, analytics, security barriers, outer joins, or hints can constrain transformations. A view is not inherently slow; its expanded SQL, predicates, joins and base objects determine cost.

**Method:** Get caller SQL and actual cursor plan; expand view definition (`DBA_VIEWS.TEXT`/`DBMS_METADATA.GET_DDL`); identify nested view layers, joins, filters, aggregation and predicates; compare estimated/actual rows and predicate placement. Check view merging and predicate pushdown; do not assume alias rearrangement changes join order.

```sql
SELECT owner, view_name, text
FROM   dba_views
WHERE  owner = UPPER(:owner)
AND    view_name = UPPER(:view_name);

SELECT referenced_owner, referenced_name, referenced_type
FROM   dba_dependencies
WHERE  owner = UPPER(:owner)
AND    name = UPPER(:view_name)
ORDER  BY referenced_type, referenced_name;
```

**Symptoms:** Hidden full scan, repeated correlated subquery, duplicated joins, late filter, cardinality explosion, unnecessary `DISTINCT`/sort, view-on-view expansion, or predicate blocked by non-mergeable constructs.

**Fixes:** Narrow projected columns; remove redundant layers/joins only after validating semantics; push safe predicates into the view/caller; index/filter base tables appropriately; rewrite repeated work; use an MV only for repeated expensive results with acceptable freshness. Avoid hints that change outer-join or security semantics.

**Example:** Replace `SELECT *` from a broad multi-join view with a projection and selective predicates, then validate actual rows and plan. A view's full scan may be optimal when the caller needs most rows.

**Rollback:** Preserve prior view DDL and dependent object validity; `CREATE OR REPLACE VIEW` can invalidate dependents and change grants/result shape. Test applications before rollout.

## 7. Sequence tuning

Sequences are independent number generators, not gap-free counters. `CACHE` reduces dictionary/redo-related overhead and sequence allocation pressure; cache loss on failure/restart can create gaps. In RAC, `NOORDER` generally avoids enforcing global order; `ORDER` can add coordination and should only be used when ordering semantics require it. Scalable sequences (available in newer releases) trade a simple contiguous-looking value pattern for reduced hot-block pressure; validate key format and application assumptions.

```sql
SELECT sequence_owner, sequence_name, min_value, max_value, increment_by,
       cycle_flag, order_flag, cache_size, scale_flag, extend_flag
FROM   dba_sequences
WHERE  sequence_owner = UPPER(:owner)
AND    sequence_name = UPPER(:sequence_name);

SELECT event, total_waits, time_waited_micro
FROM   v$system_event
WHERE  event LIKE '%sequence%'
OR     event LIKE 'enq: SV%';
```

Investigate actual waits in `V$SESSION`/`GV$SESSION`, ASH when licensed, and sequence cache/order settings; correlate with insert index hot blocks and RAC global cache waits. Sequence generation itself is rarely the only bottleneck—right-edge index blocks may be the real issue.

**Fix:** Increase cache after confirming gap acceptance and operational policy; consider `NOORDER` if business requirements allow; consider scalable sequences for supported releases/high concurrency; evaluate reverse-key or hash partitioning only when query semantics permit. Never use `MAX(id)+1` for concurrent allocation.

**Rollback:** Alter cache/order back using reviewed DDL; note DDL and consumed sequence values cannot be undone. Ensure downstream consumers do not rely on gap-free or chronological IDs.

## 8. LOB performance tuning

LOBs use a locator in the base row and separate LOB storage (depending on type/storage attributes). BasicFiles is legacy; SecureFiles (availability/options depend on release and licensing) adds capabilities such as deduplication, compression, and encryption. BLOB/CLOB/NCLOB, in-row/out-of-row storage, chunk size and LOB index affect access patterns.

**Symptoms:** Large read/write latency, excess I/O, segment growth, redo, LOB index contention, round trips from piecewise access, unexpected cache pollution, long retention of old versions, or expensive LOB transformations.

```sql
SELECT owner, table_name, column_name, segment_name, index_name,
       securefile, in_row, chunk, cache, logging, compression, deduplication
FROM   dba_lobs
WHERE  owner = UPPER(:owner)
AND    table_name = UPPER(:table_name);

SELECT owner, segment_name, segment_type, ROUND(bytes/1024/1024,1) mb
FROM   dba_segments
WHERE  owner = UPPER(:owner)
AND    segment_name IN
       (SELECT segment_name FROM dba_lobs
        WHERE owner = UPPER(:owner) AND table_name = UPPER(:table_name));
```

**Workflow/fixes:** Measure payload size and access pattern; retrieve only needed columns/LOB portions; batch locator operations; reduce network round trips; tune application streaming and chunking; check LOB retention/versioning and reclaim policy. Use `CACHE` only for repeated access where cache impact is understood; `NOCACHE` can suit large streaming access. `LOGGING`/`NOLOGGING` has recovery implications; do not tune for speed by compromising recoverability.

Compression/deduplication can save space but consume CPU and may have licensing/edition implications. Benchmark representative data and write/read ratio. `DBMS_LOB.SUBSTR` returns a limited portion and does not mean all application-side LOB access is optimized. LOB shrink/move/redefinition can be resource-intensive; determine reclaimable space first and ensure backup/standby behavior.

**Validation/rollback:** Compare bytes read/written, p95 latency, CPU, redo, storage, cache and correctness. DDL storage changes are not a simple transaction; retain a tested restore/redefinition plan.

## 9. PL/SQL object tuning

### Diagnosis and tools

Instrument module/action/client identifier; identify slow SQL inside the procedure before blaming PL/SQL. Use SQL trace/TKPROF for SQL/call counts; `DBMS_PROFILER` for line-level PL/SQL profiling; `DBMS_HPROF` for hierarchical call profiling. Profiler tables and grants may require Oracle-supplied scripts. Profiling adds overhead; use controlled windows.

Review `V$SQL` by module/action, `V$SESSION`, `DBA_PROCEDURES`, `DBA_SOURCE`, and compiler warnings. AWR/ASH and SQL Monitor are license-gated as noted above.

### Optimization hierarchy

1. Replace row-by-row database work with set-based SQL.
2. If procedural work is required, use bounded `BULK COLLECT ... LIMIT` and `FORALL`, with exception handling and transaction semantics preserved.
3. Avoid repeated SQL parsing/execute and unnecessary context switches; bind dynamic SQL and validate injection safety.
4. Consider deterministic/result-cache only for genuinely repeatable results with correct invalidation; do not cache session-dependent or volatile outputs.
5. Native compilation may help CPU-heavy PL/SQL after measurement, but will not fix SQL, I/O, or waits; verify platform/deployment and compilation requirements.
6. Review trigger work; row triggers multiply cost per affected row and can recurse or serialize. Preserve business rules/audit guarantees.

**Slow vs set-based example:**

```sql
-- Slow: repeated context switches and update statements.
BEGIN
  FOR r IN (SELECT employee_id FROM employees WHERE department_id = :dept) LOOP
    UPDATE employees SET salary = salary * 1.03 WHERE employee_id = r.employee_id;
  END LOOP;
END;
/

-- Faster and simpler when semantics match:
UPDATE employees
SET    salary = salary * 1.03
WHERE  department_id = :dept;
```

**Bulk example when per-row logic is necessary:**

```sql
DECLARE
  CURSOR c IS SELECT employee_id, salary
              FROM employees WHERE department_id = :dept;
  TYPE t_rows IS TABLE OF c%ROWTYPE;
  l_rows t_rows;
BEGIN
  OPEN c;
  LOOP
    FETCH c BULK COLLECT INTO l_rows LIMIT 500;
    EXIT WHEN l_rows.COUNT = 0;
    FORALL i IN 1 .. l_rows.COUNT
      UPDATE employees
      SET salary = l_rows(i).salary * 1.03
      WHERE employee_id = l_rows(i).employee_id;
  END LOOP;
  CLOSE c;
END;
/
```

This exact example should not be used when the set-based update suffices; `FORALL` is not a substitute for set SQL. Ensure cursor closure on exceptions, and decide how `SAVE EXCEPTIONS`, partial success and commits affect correctness.

**Validation:** Compare procedure elapsed/CPU, SQL calls/executions, context switches, rows and commits, plus lock duration and redo. Keep source/DDL and prior grants for rollback; compilation does not undo changed behavior.

## 10. Cursor and shared-pool performance

Hard parse performs optimization/authorization and allocates cursor structures; soft parse reuses a compatible cursor but still incurs parse-call overhead. Bind variables help reuse but can introduce selectivity sensitivity; adaptive cursor sharing may create multiple child cursors. `CURSOR_SHARING=FORCE` is not a universal fix and may change semantics/plan quality.

```sql
SELECT name, value
FROM   v$sysstat
WHERE  name IN ('parse count (total)', 'parse count (hard)',
                'execute count', 'session cursor cache hits');

SELECT sql_id, version_count, executions, parse_calls, loads, invalidations,
       sharable_mem, SUBSTR(sql_text,1,100) sql_text
FROM   v$sqlarea
WHERE  version_count > 20
ORDER  BY version_count DESC
FETCH FIRST 30 ROWS ONLY;

SELECT sql_id, child_number, plan_hash_value, is_bind_sensitive,
       is_bind_aware, executions, parse_calls, buffer_gets
FROM   v$sql
WHERE  sql_id = :sql_id
ORDER  BY child_number;
```

Check `V$SQL_SHARED_CURSOR` reason flags for child cursor proliferation; examine `V$LIBRARYCACHE` reloads/invalidations and relevant waits (`library cache: mutex X`, `cursor: pin S wait on X`). System counters are cumulative; compare deltas. High parse calls can result from client behavior even if hard parses are modest.

**Fix:** Reuse prepared statements in the client; bind appropriate data types; avoid SQL text literal variation and implicit conversions; size session cursor cache/shared pool only after identifying pressure; reduce invalidation churn from DDL/stats changes; fix child-cursor mismatch. Keep distinct statements when semantics or optimizer selectivity require them.

**Rollback:** Revert application cursor behavior or session/database parameter change using prior value and change control. Do not flush shared pool as a routine remediation; it can cause a parse storm.

## 11. Statistics tuning

Optimizer statistics describe table/column/index distribution and support cardinality/cost estimates. Histograms model skew; extended stats model correlated columns/expressions. Stats are estimates, not runtime truth.

**Identify:** stale/missing table/partition stats, bad `E-Rows` vs `A-Rows`, skewed binds, implicit conversions, correlation, stats locks, sampling, incremental stats, and child plans. Inspect `DBA_TAB_STATISTICS`, `DBA_TAB_COL_STATISTICS`, `DBA_IND_STATISTICS`, `DBA_OPTSTAT_OPERATIONS`, and `DBA_TAB_MODIFICATIONS`.

```sql
SELECT owner, table_name, partition_name, num_rows, blocks,
       stale_stats, last_analyzed, global_stats, stattype_locked
FROM   dba_tab_statistics
WHERE  owner = UPPER(:owner)
AND    table_name = UPPER(:table_name);

SELECT column_name, num_distinct, density, num_nulls, histogram,
       num_buckets, last_analyzed
FROM   dba_tab_col_statistics
WHERE  owner = UPPER(:owner)
AND    table_name = UPPER(:table_name);
```

**Fix workflow:** Prove mismatch; identify relevant columns/expressions and bind values; gather appropriate stats using `DBMS_STATS` (not `ANALYZE TABLE ... COMPUTE STATISTICS`); test pending stats where supported; consider histogram only for relevant skew and predicate usage; create extended stats for proven correlation; consider incremental stats for partitioned tables. Use restore stats API/window and plan baselines as rollback tools when appropriate.

```sql
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(
    ownname          => UPPER(:owner),
    tabname          => UPPER(:table_name),
    estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
    method_opt       => 'FOR ALL COLUMNS SIZE AUTO',
    cascade          => DBMS_STATS.AUTO_CASCADE,
    no_invalidate    => DBMS_STATS.AUTO_INVALIDATE
  );
END;
/
```

Do not run a broad stats gather in peak production without estimating resource, lock, plan-change, and duration impact. `SIZE AUTO` does not guarantee a histogram on every needed column. Avoid forcing histograms, deleting stats, or repeatedly gathering stats to chase transient plans.

**Validation:** Compare estimates vs actual rows, plan hash, cursor children and representative binds; evaluate whole workload and DML. Restore prior stats if regression is proven, and ensure the restore timestamp/history is within retention.

## 12. Execution-plan analysis framework

### Reading a plan

1. Use the actual cursor plan and actual row-source stats, not only `EXPLAIN PLAN`.
2. Read from leaf operations upward; parent operations consume child rows. In parallel plans, account for PX operations and data redistribution.
3. Compare `E-Rows` and `A-Rows`, `Starts`, buffers, reads, and elapsed by operation. Multiplying rows per start can explain repeated work.
4. Read `Predicate Information`, access vs filter predicates, partition boundaries, projections, outline/hints, adaptive branches and plan notes.
5. Find the first major estimate divergence and the operation doing most work; then inspect SQL and object stats.

| Operation | Meaning | Risk / tuning questions |
|---|---|---|
| `TABLE ACCESS FULL` | Reads table blocks | Correct for broad retrieval; for selective query check filter, partition pruning, stats, parallelism, physical I/O. |
| `INDEX RANGE SCAN` | Reads a key range | Check range selectivity, leaf visits, starts, clustering factor and table rowid visits. |
| `INDEX UNIQUE SCAN` | Finds unique key entry | Usually narrow; subsequent table access, contention, wrong datatype or excessive calls may dominate. |
| `HASH JOIN` | Builds hash table and probes another rowset | Large input can use PGA/TEMP; inspect build size, spill, estimates, parallel redistribution and join filters. |
| `MERGE JOIN` | Joins ordered inputs | May require expensive sorts; can be good when inputs are already ordered or range conditions apply. |
| `NESTED LOOPS` | For each outer row, probes inner | Excellent for small outer set and indexed lookup; disastrous with huge starts/outer cardinality. |
| `SORT` | Orders/deduplicates/groups | Check rows/width, PGA/TEMP spill, unnecessary ORDER BY/DISTINCT, index ordering possibility. |
| `FILTER` | Applies predicate/subquery condition | May execute correlated work repeatedly; inspect Starts and actual rows; sometimes transformed to semi/anti join. |

Other useful lines include `PARTITION RANGE`, `INLIST ITERATOR`, `BITMAP CONVERSION`, `VIEW`, `WINDOW SORT`, `REMOTE`, `PX SEND/RECEIVE`, and `TABLE ACCESS BY INDEX ROWID`. A plan operation name alone is not a diagnosis.

**Example diagnosis:** If `NESTED LOOPS` outer `A-Rows` is 900,000, inner index lookup has `Starts` near 900,000 and high buffers, the issue may be an inaccurate outer estimate or inappropriate join strategy. Confirm correct stats, predicates and rowset; a hash join may be better, but only measured actual plan evidence should drive a change.

## 13. Object-wise troubleshooting playbooks

Use this loop for any object: **symptoms → interval evidence → actual SQL plan → object mapping → root cause → controlled change → result and workload validation → rollback/monitor.**

| Object/problem | Investigation | Fix and validation | Rollback |
|---|---|---|---|
| Table scan/reads | `V$SQL`, `DBMS_XPLAN`, `V$SEGMENT_STATISTICS`, table/column/partition stats | Sargable predicate, projection reduction, justified index/partition/stats; compare gets/reads/elapsed | Revert SQL/index/stats/plan under change plan |
| Table hot block | Active wait/blocker, ASH block samples if licensed, segment-stat deltas, `DBA_EXTENTS`, index type | Reduce serialization, adjust key/index/transaction pattern, evaluate ITL/storage; verify hot-block samples and throughput | Revert index/DDL or application change; preserve data |
| Table chaining/migration | `CHAIN_CNT`, chained-row sample, `table fetch continued row`, row width/growth | Fix row growth/schema or rebuild/move only if materially beneficial; verify row fetch work | DDL restore/redefinition plan; preserve object metadata |
| Index inefficiency | Actual access path, key order, clustering factor, usage window, DML overhead | Candidate index/rewrite, visible/invisible test, compare read and write costs | Drop new index or restore prior definition |
| Partition pruning/hotspot | PSTART/PSTOP, partition stats/segments, ASH/object samples if licensed | Predicate/type correction, partition strategy or maintenance change | Preplanned reverse exchange/restore; DDL not transactional |
| LOB slowness/growth | `DBA_LOBS`, LOB segments, payload size, waits/I/O/redo | Stream/project appropriately; storage attributes after benchmark | Restore/redefinition plan; keep old data until verified |
| MV slow/stale/failed | `DBA_MVIEWS`, refresh/job logs, capability/rewrite analysis, base SQL plan | Correct logs/refresh method/SQL/schedule; verify freshness and results | Route back to base query; preserve logs/dependencies |
| PL/SQL slow | Trace/TKPROF, profiler/HPROF, SQL by module/action | Set SQL/bulk bounded processing, remove redundant calls; measure end-to-end and locks | Re-deploy prior source and compile/validate dependents |
| Statistics/plan regression | `DBA_*STATISTICS`, actual plan, bind-aware children, stats history | Targeted stats/extended stats/pending stats; validate bind classes | Restore previous stats or plan baseline |
| Cursor/shared pool | parse deltas, `V$SQLAREA`, child mismatch, library cache and client metrics | Statement reuse/binds/type consistency; prevent invalidation churn | Revert client/parameter change; avoid shared-pool flush |
| Sequence contention | cache/order, session waits, RAC `SV`/GC waits and hot index blocks | Cache/order/scalable sequence or index design as requirements permit | Alter settings back; values/gaps already consumed |
| View regression | Expanded SQL, dependencies, actual plan and predicates | Simplify view or rewrite consumer while preserving semantics | Restore view DDL and revalidate dependent objects |

### AWR/ASH/ADDM review checklist (licensed features only)

- **AWR:** report interval, DB time and load profile, Top Timed Foreground Events, SQL ordered by elapsed/CPU/gets/reads, SQL plan changes, instance activity, IO/statistics, segments by physical/logical reads, and RAC/global cache sections where relevant. Normalize per execution/transaction, not just totals.
- **ASH:** filter exact incident window, service/module/action, SQL_ID and session type; review Top SQL, Top Events, Top Objects, blocking sessions, wait class and plan line. ASH samples are statistical snapshots.
- **ADDM:** review findings, impact estimate, rationale and recommendations. Verify with live query/object evidence and operational constraints before action.
- Correlate with application request IDs, deployment times, OS/ASM/storage telemetry, job schedules and business metrics.

## 14. Fifty representative production scenario patterns

These are **illustrative production archetypes**, not authenticated case histories. Before/after numbers are example measurements chosen to show the kind of evidence to record; use actual values from a licensed/authorized target environment. AWR/ASH wording below assumes entitlement.

### Tables and access paths

| # | Business problem / symptom | AWR-style clue and root cause | Object / fix | Illustrative before → after | Lesson |
|---:|---|---|---|---|---|
| 1 | Daily order lookup misses SLA | SQL by gets; full scan caused by `TRUNC(date)` | Heap table; half-open date predicate | 12s, 2.1M gets → 90ms, 8K gets | Make predicates sargable; validate broad-date binds. |
| 2 | Dashboard scans years of sales | High physical reads; no partition elimination | Range partition; predicate datatype mismatch | 18 min, 96 partitions → 42s, 1 partition | Check executed PSTART/PSTOP. |
| 3 | Small reference table appears in top SQL | High executions but tiny segment and low elapsed | Lookup table; scan is cheaper than index | 3ms/exec → unchanged | Do not optimize operation names in isolation. |
| 4 | Customer search CPU spike for popular values | Estimate mismatch; skew not represented | Table column stats/histogram tested | p95 7s → 0.8s for selective values | Validate all bind selectivity classes. |
| 5 | Update-heavy table grows rapidly | Segment bytes rise; row length and retention increased | Heap table; correct retention and row design | 1.8TB → stable monthly growth | Segment growth is not automatically fragmentation. |
| 6 | Row reads do extra I/O after updates | Continued-row fetches and chained samples | Heap rows migrate after expansion | 2.5K continued fetches/s → 300/s after redesign | Diagnose representative rows before move. |
| 7 | Insert storm stalls on same block | `buffer busy waits`/RAC `gc buffer busy`; right-edge block | Table/index key concurrency; redesign allocation/key distribution | 40% DB time on hot block → <5% | Identify exact block and object before changing key. |
| 8 | Monthly purge blocks production | DML delete generates undo/redo and locks | Range-partitioned history; partition lifecycle | 90 min delete → 4 min partition operation | DDL recovery/replication constraints first. |
| 9 | Temp table report spills heavily | Temp I/O; hash/sort input much larger than estimated | Query/table stats and projection width | 110GB temp → 14GB | Reduce rows/width and fix estimates; don't only enlarge TEMP. |
| 10 | File ingestion slowed by parse overhead | CPU and direct path reads; external CSV parsing repeated | External table; stage once for repeated indexed lookups | 20 min repeated queries → 3 min staged load + reads | External tables lack ordinary indexes. |

### Indexes and partitioning

| # | Business problem / symptom | AWR-style clue and root cause | Object / fix | Illustrative before → after | Lesson |
|---:|---|---|---|---|---|
| 11 | Account query scans too many rows | High gets; index key order does not match filters | Composite B-tree `(tenant_id, account_id)` | 3.2s → 120ms | Validate selectivity and write cost. |
| 12 | Monotonic key insert contention | Hot rightmost leaf and buffer busy waits | Reverse-key candidate tested | 28% wait time → 4% | Range scans on key may be lost. |
| 13 | OLTP bitmap index stalls DML | TX/bitmap contention under concurrent updates | Bitmap replaced with B-tree/design alternative | 6x batch duration → baseline | Bitmap is generally read-mostly analytics tool. |
| 14 | Function predicate ignores plain index | Table scan and high logical reads | Function-based index or sargable rewrite | 9s → 250ms | Match exact expression and NLS semantics. |
| 15 | “Unused” index removal breaks month-end | Rare report absent from short monitoring window | Index retained after full workload review | Report 14min → 20s with index | Usage monitoring window is not proof. |
| 16 | Index rebuild causes outage | DDL blocks/space pressure; “fragmentation” assumed | Rebuild cancelled; evidence-based maintenance policy | 35min lock → zero incident | BLEVEL alone is not a rebuild trigger. |
| 17 | Cross-partition lookup slow | Local indexes probe many partitions | Global index candidate | 11s → 0.6s | Global index maintenance affects partition ops. |
| 18 | Partitioned unique index unusable after maintenance | Global index status / DDL behavior overlooked | Adopted tested maintenance clause/runbook | Load recovery 2h → 12min | Verify index state after partition DDL. |
| 19 | Query visits all monthly partitions | `PARTITION RANGE ALL`; bind datatype mismatch | SQL binds aligned to key type | 2.4M blocks → 24K | Check implicit conversions and bind metadata. |
| 20 | Hot tenant dominates one partition | Segment and ASH activity skewed to one list value | Composite list/hash strategy after evaluation | p99 4.8s → 0.9s | Partitioning cannot erase workload skew alone. |

### Joins, views, and materialized views

| # | Business problem / symptom | AWR-style clue and root cause | Object / fix | Illustrative before → after | Lesson |
|---:|---|---|---|---|---|
| 21 | Nested loop runs millions of inner probes | Actual outer rows far exceed estimates | Stats/query; enable appropriate join plan through correct estimates | 70M gets → 4M | Fix rowset/estimate; don't blindly force hash join. |
| 22 | Reporting query sorts huge rowset | `direct path write temp`; unnecessary `DISTINCT` | SQL/view rewrite reduces duplication | 90GB temp → 5GB | Prove duplicate semantics before removal. |
| 23 | Nested views hide duplicated joins | Plan repeats base table access | View definitions simplified, projection narrowed | 28s → 4s | Views are expanded SQL, not cached results. |
| 24 | View filter applied after broad aggregation | Late filter and high A-Rows | Predicate pushdown-compatible rewrite | 7.5M rows processed → 110K | Preserve outer-join and null semantics. |
| 25 | Regional dashboard repeats aggregation | Same group-by SQL dominates elapsed time | MV with tested rewrite/refresh policy | 38s → 1.2s | Include refresh cost and staleness SLA. |
| 26 | Fast refresh silently unavailable | Capability analysis shows unsupported query form | MV/query/log redesigned or complete refresh scheduled | 2h refresh → 18min fast refresh | Verify with `EXPLAIN_MVIEW`. |
| 27 | MV is stale after job failures | Scheduler errors and stale status; app serves old summary | Job error handling, alert and freshness gate | 9h stale → <10min lag | Never label stale data as fresh. |
| 28 | ON COMMIT MV slows checkout | Commit latency rises from refresh maintenance | Change to on-demand refresh and explicit staleness | p95 commit 80ms → 12ms | Synchronous freshness has transaction cost. |
| 29 | Query rewrite does not choose MV | Rewrite disabled/ineligible or cost higher | Correct settings/capability/cost validation | 22s → 1.4s | An MV can exist without being rewrite eligible. |
| 30 | Fast refresh logs consume storage | MV logs grow with high base DML | Refresh cadence and log retention tuned | 600GB logs → 90GB | MV logs add write/storage overhead. |

### LOBs, PL/SQL, sequences, cursors, and stats

| # | Business problem / symptom | AWR-style clue and root cause | Object / fix | Illustrative before → after | Lesson |
|---:|---|---|---|---|---|
| 31 | Document list reads full BLOBs | High bytes, network and I/O for metadata screen | LOB table; defer payload fetch | 5MB/request → 12KB | Avoid selecting LOB when not needed. |
| 32 | CLOB writes consume storage | Large repeated content, no dedup/compression evaluation | SecureFiles option benchmarked/approved | 3.0TB → 1.7TB | Benchmark CPU/license and write impact. |
| 33 | LOB segment fails to shrink after deletes | Segment footprint persists after purge | LOB reclaim/redefinition plan after measurement | 900GB → 510GB | Reclaim operations need space and recovery planning. |
| 34 | PL/SQL batch takes hours | Trace shows per-row SQL and context switches | Set-based update replaces loop | 4h → 6min | First choice is SQL, not bulk syntax. |
| 35 | Procedural validation requires row logic | Profiler points to repeated DML/context switches | Bounded bulk collect + FORALL | 52min → 8min | Bound memory and preserve error semantics. |
| 36 | Trigger increases bulk insert time | Per-row trigger performs redundant lookup | Trigger logic simplified while retaining audit/validation | 45min → 13min | Never disable business controls without approval. |
| 37 | Package CPU-heavy math limits throughput | HPROF isolates pure PL/SQL CPU | Algorithm optimized; native compile only after test | 1,200 calls/s → 2,100 | Native compilation is not an I/O fix. |
| 38 | Sequence allocation waits in RAC | `enq: SV - contention`; ORDER + tiny cache | Cache/order adjusted to business contract | 18% DB time → 1% | Sequence gaps are normal; ordering has a cost. |
| 39 | High parse rate from web tier | Parse calls near executes; literal variation | Client statement reuse + binds | 55K hard parses/min → 900 | Bind types and skew still matter. |
| 40 | Child cursor explosion | Many children and mismatch reasons | Consistent bind datatypes/session settings | 240 children → 12 | Read mismatch evidence, not just version count. |

### Statistics, concurrency, and operational scenarios

| # | Business problem / symptom | AWR-style clue and root cause | Object / fix | Illustrative before → after | Lesson |
|---:|---|---|---|---|---|
| 41 | Plan regresses after bulk load | Table stats predate large data change | Targeted stats gathered/tested | 44min → 3.5min | Coordinate stats with load completion. |
| 42 | Correlated filters misestimate | Combined predicates have far fewer rows than independent estimates | Extended column group stats | 1.8M gets → 90K | Use only for demonstrated correlation. |
| 43 | Skewed state code selects wrong plan | Popular and rare values share unsuitable child plan | Histogram/ACS validated by bind class | Rare bind 18s → 0.4s | Histogram is workload-specific tradeoff. |
| 44 | Stats job causes unexpected plan flips | Concurrent gather and invalidation during peak | Job window/pending stats/plan controls | 14% p99 regression → none | Stats changes are production changes. |
| 45 | Blocker stalls order writes | `enq: TX - row lock contention`; long transaction | Transaction scope shortened, lock order corrected | 19min queue → <2s | Indexes do not solve row-lock design. |
| 46 | Commit wait dominates response | `log file sync`; commits per row | Batch transaction boundary after durability review | 3,000 commits/s → 120 | Batching changes durability/recovery semantics. |
| 47 | RAC remote block traffic high | `gc cr/current block 2-way` on hot object | Access locality and key distribution improved | 31% cluster waits → 8% | Confirm with cluster-wide, not single-node views. |
| 48 | Parallel query overloads OLTP | PX waits/CPU saturation during batch overlap | Degree/scheduling/resource plan adjusted | OLTP p95 2.6s → 0.7s | More parallelism can reduce total throughput. |
| 49 | “Slow DB” is actually connection queueing | DB execution fast; app pool wait dominates end-to-end | Pool size/timeout and service telemetry corrected | p95 12s → 1.1s end-to-end | Separate database time from user latency. |
| 50 | Query tuned but regresses next release | Plan hash changes after deployment/stats/DDL | SQL regression monitoring and tested plan control | 3s recurring → 0.3s stable | Treat plan governance as lifecycle, not incident-only. |

### Case-study evidence template

For each real incident, replace the illustrative row with:

1. Business impact and exact interval/timezone.
2. Oracle release/edition, topology, service, workload and licensing status.
3. AWR/ASH/ADDM excerpts only where licensed and approved; redact sensitive SQL/binds.
4. SQL_ID, child number, plan hash, actual plan and representative bind/selectivity class.
5. Object/partition/index/LOB segment and relevant wait/blocker evidence.
6. Root cause, rejected hypotheses, change ticket and rollback plan.
7. Same-workload before/after p50/p95/p99, CPU, gets, reads, rows, throughput, DML/redo and errors.
8. Monitoring period, side effects, rollback decision and lessons.

## 15. Production controls, rollback, and review questions

### Change / rollback checklist

- Preserve original SQL/object DDL, grants, dependencies, stats and current plan evidence.
- Confirm backup/standby/replication, free space, undo/temp/redo, locks, downtime, and recovery window.
- For DDL, remember implicit commits and that rollback is not generally transactional. Prepare a reverse DDL, restore, exchange, or application-routing strategy.
- Set stop conditions: latency, errors, lock time, redo, replication lag, space, CPU, or regression threshold.
- Validate result correctness and every critical consumer—not merely the target statement.
- Remove diagnostic instrumentation and temporary objects after capturing evidence.

### Architect-level review questions

1. What is the user's SLA and the affected request path?
2. What is the dominant measured resource per execution and per business transaction?
3. Which actual plan line first diverges from estimated cardinality?
4. Which binds, tenants, partitions, and concurrency classes are representative?
5. Does the proposed fix lower total work or only shift cost to DML, temp, redo, storage, or other users?
6. What result, consistency, ordering, uniqueness, audit, and recovery semantics must remain invariant?
7. Can the change be isolated, observed, and reversed within the incident SLA?
8. What will alert the team if the plan, partition, refresh, or workload changes later?

## References to consult for the target release

Use the licensed Oracle Database Performance Tuning Guide, SQL Tuning Guide, VLDB and Partitioning Guide, PL/SQL Language Reference, SecureFiles and Large Objects Developer's Guide, Database Reference (dynamic performance views), and Licensing Information User Manual for the exact version and edition. Confirm syntax, feature availability, and licensing with the documentation and contract applicable to the target environment.
