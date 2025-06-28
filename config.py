from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://mongo:27017/')
DB_NAME = os.getenv('DB_NAME', 'expTracker')
PORT = int(os.getenv('PORT', 5003))

_mongo_client = MongoClient(MONGODB_URI)
db = _mongo_client[DB_NAME]

try:
    _mongo_client.admin.command('ping')
    print(f"MongoDB connection successful to database '{DB_NAME}'.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

JWT_SECRET = os.getenv('JWT_SECRET', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YW55cmFuZG9tc3RyaW5n.c2VjcmV0X2tleV9nZW5lcmF0ZWRfZm9yX3lvdQ')