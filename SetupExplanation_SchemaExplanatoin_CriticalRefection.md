# CP5405 Assessment 2 — DataFest Analytics System
**Unit:** CP5405 Scalable Database Systems  
**Student:** Sai Kham Thura Nyunt  
**Database:** MongoDB Atlas  
**Platform:** Google Colab  

---

## Overview

This project implements a MongoDB-based analytics system for DataFest — a large-scale
international conference. The system ingests multiple live data streams (ticket scans,
RFID movements, feedback forms), stores them in an optimised schema, and delivers
near-real-time analytics with measurable performance optimisations.

---

## Repository Structure
```
CP5405-Assessment2/
├── Assignment_2.ipynb          # Main notebook — all code for Parts A, B, C
├── ticket_scans.csv            # 1,000 rows of entry/exit scan data
├── rfid_movements.csv          # 2,000 rows of attendee RFID movement data
├── feedback.csv                # 500 rows of attendee feedback
├── README.md                   # This file
└── sample_outputs/
    ├── index_performance_comparison.png   # Part C performance chart
    └── screenshots/                       # Output screenshots per section
```

---

## Setup Instructions

### 1. MongoDB Atlas
- Create a free-tier cluster at https://www.mongodb.com/atlas
- Create a database named `EventManagement`
- Whitelist your IP address under Network Access
- Create a database user and copy your connection string

### 2. Google Drive
Upload the three CSV files to your Google Drive:
```
ticket_scans.csv
rfid_movements.csv
feedback.csv
```

### 3. Google Colab
- Open `Assignment_2.ipynb` in Google Colab
- Update the file paths in Cell 4 to match your Google Drive location:
```python
path_to_data1 = "/content/drive/MyDrive/YOUR_FOLDER/ticket_scans.csv"
path_to_data2 = "/content/drive/MyDrive/YOUR_FOLDER/rfid_movements.csv"
path_to_data3 = "/content/drive/MyDrive/YOUR_FOLDER/feedback.csv"
```
- Update the MongoDB connection string in Cell 5:
```python
client = MongoClient("mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CLUSTER_URL/")
```

### 4. Run the Notebook
Run cells **in order from top to bottom**. Each section depends on the previous one.

---

## Schema Design

### Collections

| Collection | Pattern | Documents | Purpose |
|---|---|---|---|
| `attendee_master_final` | Embedding / Bucket | 287 | Attendee-centric master record |
| `movement_security_audit` | Extended Reference | 1,000 | Gate scan + last known location |
| `attendee_analytics_view` | Denormalized ($merge) | 1,000 | Flat analytical view |
| `session_logs` | TTL Index | Auto-expiring | Temporary session tracking |

### Design Patterns Applied

**Bucket Pattern** — `attendee_master_final` embeds all ticket history, zone movements,
and feedback as arrays inside a single attendee document. All related data is accessed
together — embedding avoids expensive joins at query time.

**Extended Reference Pattern** — `movement_security_audit` stores ticket scan records
enriched with the attendee's last known RFID location, pulled directly from the RFID
data. Security queries are answered with a single collection scan — no join needed.

**Denormalization via `$lookup` + `$merge`** — `attendee_analytics_view` is built
using an aggregation pipeline that joins across collections and writes results via
`$merge`. The view can be refreshed incrementally as new event data arrives.

**Schema Versioning Pattern** — A `schema_version: 1` field is added to every document
in `attendee_master_final`. Future data sources can be introduced as version 2 documents
without breaking existing queries.

**Subset Pattern** — The `total_movements` field pre-computes the movement count per
attendee, avoiding full array scans for a common analytics query.

**Polymorphic Pattern** — Embedded arrays can hold documents of varying shapes,
accommodating future event types (e.g. biometric scans) without schema migration.

---

## Optimisation Notes

### Indexes Implemented

| Index | Collection | Type | Purpose |
|---|---|---|---|
| `attendee_id_1_scan_time_1` | `movement_security_audit` | Compound | Attendee + time queries |
| `unique_attendee_gate` | `movement_security_audit` | Unique | Prevent duplicate scan records |
| `partial_high_ratings` | `attendee_master_final` | Partial | High-rating feedback queries only |
| `compound_engagement_rating` | `attendee_master_final` | Compound | Engagement score + rating queries |
| `ttl_session_expiry` | `session_logs` | TTL | Auto-delete expired session docs |

### Index Strategy Comparison (Part C)

Four index strategies were tested against the same query on `movement_security_audit`:

- **Single (attendee_id)** — narrows by attendee but still scans all gate values
- **Single (location_id)** — irrelevant to the query predicate, falls back to COLLSCAN
- **Compound (attendee_id + gate_id)** — covers both query fields, minimal docs examined
- **Compound (attendee_id + scan_time + gate_id)** — covers query + time-based sorts

The compound index on `attendee_id + gate_id` performed best for point queries.
At 100x scale (100,000 documents), a COLLSCAN examines every document on every query
while the compound index examines only the qualifying subset regardless of collection size.

### Bulk API
`initialize_ordered_bulk_op` is used to compute and write engagement scores for all
287 attendees in a single batched operation. At 100x scale this reduces 28,700
individual network round-trips to one batched operation.

### ESR Rule
Compound indexes follow MongoDB's ESR rule (Equality → Sort → Range) for field
ordering — maximising index selectivity at each stage of the B-tree traversal.

---

## Aggregation Pipelines (Part B)

### Pipeline 1 — Gate Busiest Hour Analysis
Unwinds the embedded `ticket_history` array, extracts the hour from each scan
timestamp, and groups by gate + hour to identify peak traffic periods.
Stages: `$unwind` → `$addFields` → `$group` → `$project` → `$sort` → `$limit`

### Pipeline 2 — Zone vs Feedback Sentiment (Multi-collection Join)
Joins `movement_security_audit` with `attendee_master_final` via `$lookup`,
then correlates each attendee's last known zone with their average feedback rating.
Stages: `$lookup` → `$unwind` → `$unwind` → `$group` → `$addFields` → `$project` → `$sort`

### Pipeline 3 — Movement Frequency vs Engagement (Open-ended)
Segments attendees into mobility tiers using `$bucket`, then measures average
feedback volume and rating per tier  identifying non-obvious engagement patterns.
Stages: `$project` → `$bucket` → `$project`

---

## Critical Reflection

### Complexity
The DataFest scenario is inherently complex  three live data streams, multiple
access patterns, and an undefined set of future data sources. A purely normalised
relational approach would require multiple joins for every query. The hybrid embedding
+ denormalization strategy reduces this complexity by co-locating data according to
how it is actually accessed, not how it is theoretically structured.

### Scalability
Every design decision was evaluated against a 100x scaling scenario (287 → 28,700
attendees, 1,000 → 100,000 ticket scans). Key scalability choices:
- Compound indexes maintain O(log n) query performance as collections grow
- The `$merge` pipeline for `attendee_analytics_view` supports incremental refresh
- TTL indexes eliminate manual cleanup overhead at scale
- Bulk API reduces write amplification for batch operations

At 1,000x scale (millions of documents), the partial index on high-rated feedback
becomes critical  a full index on a low-selectivity field wastes memory and slows
writes, while the partial index covers only the qualifying subset.

### Professional Practice
Design choices reference MongoDB's official Building with Patterns documentation and
academic sources including Bradshaw et al. (2019) and Fowler & Sadalage (2012).
The ESR rule is applied consistently for compound index field ordering. Schema
versioning is implemented to support production-grade schema evolution without
downtime or migration scripts.

### Limitations
- The dataset (287 attendees) is small enough that COLLSCAN vs IXSCAN timing
  differences are minimal in milliseconds the structural improvement in
  `totalDocsExamined` is the meaningful metric at this scale.
- MongoDB Atlas free-tier TTL monitor runs every 60 seconds, so TTL expiry
  is not instantaneous in the demo environment.

---

## References
- MongoDB Inc. (2023). *Building with Patterns: A Summary*. https://www.mongodb.com/blog/post/building-with-patterns-a-summary
- Bradshaw, S., Brazil, E., & Chodorow, K. (2019). *MongoDB: The Definitive Guide* (3rd ed.). O'Reilly Media.
- Fowler, M., & Sadalage, P. (2012). *NoSQL Distilled*. Addison-Wesley.
