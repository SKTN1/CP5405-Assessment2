## Section 3 – Design Justification (README)

### Overview
The EventManagement database uses a **hybrid schema strategy** combining embedding,
referencing, and denormalization. Each design choice is justified below against
MongoDB best practices and academic references.

---

### 1. Embedding — Bucket Pattern (`attendee_master_final`)

All ticket history, zone movements, and feedback for each attendee are embedded
as arrays inside a single document. This follows the **Bucket Pattern** described
in MongoDB's official data modeling documentation (MongoDB Inc., 2023).

**Justification:**
- Attendee data is always accessed together embedding avoids expensive `$lookup`
  joins at query time, improving read performance significantly.
- MongoDB's document model is optimized for co-locating related data. Forcing a
  relational (normalized) structure into MongoDB loses this core advantage
  (Chodorow, *MongoDB: The Definitive Guide*, 2019).
- The 16MB document size limit is not a concern here even the largest attendee
  document (with ~7 movements and ~2 feedback records) is well within limits.

**Trade-off:** Updates to individual embedded records require rewriting the full
array. For a read-heavy analytics platform like DataFest, this is acceptable.

---

### 2. Extended Reference Pattern (`movement_security_audit`)

The security audit collection stores one document per ticket scan, enriched with
the attendee's last known RFID location pulled from `attendee_master_final`.

**Justification:**
- The **Extended Reference Pattern** (MongoDB Inc., 2023) avoids repeated joins
  by denormalizing only the most frequently accessed fields (`location_id`,
  `rfid_time`) directly into the audit document.
- Security queries ("find all attendees scanned at Gate G1 who were last seen in
  HALL_C") are answered with a single collection scan no join needed.
- This is aligned with the principle: *"data that is accessed together should be
  stored together"* (Bradshaw et al., *MongoDB: The Definitive Guide*, 3rd ed.).

---

### 3. Denormalization via `$lookup` + `$merge` (`attendee_analytics_view`)

A flat analytical collection is built using an aggregation pipeline that joins
`movement_security_audit` with `attendee_master_final` and writes results via
`$merge`.

**Justification:**
- Denormalization pre-computes cross-collection joins, supporting near-real-time
  analytics without query-time overhead (Fowler, *NoSQL Distilled*, 2012).
- `$merge` is the recommended approach for materialized views in MongoDB — it
  supports incremental updates (`whenMatched: replace`) meaning the view can be
  refreshed as new event data arrives without a full rebuild.
- This directly addresses the DataFest requirement for scalable, near-real-time
  analytics across multiple live data streams.

---

### 4. Schema Versioning Pattern

A `schema_version: 1` field is added to every document in `attendee_master_final`.

**Justification:**
- The **Schema Versioning Pattern** (MongoDB Inc., 2023) is a best practice for
  production systems where the data model will evolve over time.
- For DataFest, future data sources (e.g., social media feeds, sponsor check-ins)
  can be added as `schema_version: 2` documents without breaking existing queries
  on version 1 documents.
- Application code can branch on `schema_version` to handle both old and new
  document shapes gracefully during migration periods.

---

### 5. Subset Pattern

The `total_movements` field in `attendee_master_final` is a pre-computed integer
storing the count of zone movement records for each attendee.

**Justification:**
- The **Subset Pattern** avoids loading the full `zone_movements` array just to
  get a count a common analytics query.
- Pre-computing frequently read aggregations reduces CPU and I/O overhead at query
  time, which is critical for a near-real-time dashboard (MongoDB Inc., 2023).

---

### 6. Polymorphic Pattern (Future-Proofing)

The embedded arrays (`ticket_history`, `zone_movements`, `feedback_given`) can
hold documents of varying shapes without schema changes. For example, a future
`biometric_scan` event type could be added to `zone_movements` alongside existing
RFID records — MongoDB's flexible document model accommodates this natively.

This follows the **Polymorphic Pattern** (MongoDB Inc., 2023), which is recommended
when objects share a common identity (attendee_id) but have varying attributes
depending on their source or type.

---

### References
- MongoDB Inc. (2023). *Building with Patterns: A Summary*. MongoDB Documentation.
  https://www.mongodb.com/blog/post/building-with-patterns-a-summary
- Bradshaw, S., Brazil, E., & Chodorow, K. (2019). *MongoDB: The Definitive Guide*
  (3rd ed.). O'Reilly Media.
- Fowler, M., & Sadalage, P. (2012). *NoSQL Distilled: A Brief Guide to the
  Emerging World of Polyglot Persistence*. Addison-Wesley.
