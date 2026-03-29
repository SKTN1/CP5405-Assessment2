# Assessment 2 – DataFlow Analytics Starter Pack

## Overview
This starter pack includes:
- Sample CSV data for three event data streams.
- A Python ingestion script to insert data into MongoDB Atlas.
- Basic setup instructions.

## Setup
1. Create a **free-tier MongoDB Atlas** cluster.
2. Create a database named `event_platform`.
3. Download `ticket_scans.csv`, `rfid_movements.csv`, and `feedback.csv` to your working directory.
4. Update the `MongoClient` connection string in `ingest_sample_data.py` with your Atlas credentials.
5. Run:
   ```bash
   python ingest_sample_data.py
