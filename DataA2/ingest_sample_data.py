import csv
from pymongo import MongoClient
from datetime import datetime

# MongoDB Atlas connection string (replace <password> and <dbname>)
client = MongoClient("mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<dbname>?retryWrites=true&w=majority")
db = client.event_platform

def ingest_csv_to_collection(file_path, collection_name):
    collection = db[collection_name]
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert timestamp string to datetime if exists
            if 'timestamp' in row:
                row['timestamp'] = datetime.fromisoformat(row['timestamp'])
            if 'rating' in row:
                row['rating'] = int(row['rating'])
            collection.insert_one(row)
    print(f"Ingested {file_path} into {collection_name}")

if __name__ == "__main__":
    ingest_csv_to_collection('ticket_scans.csv', 'ticket_scans')
    ingest_csv_to_collection('rfid_movements.csv', 'rfid_movements')
    ingest_csv_to_collection('feedback.csv', 'feedback')
