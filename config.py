import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv('MONGODB_URI')
JWT_SECRET = os.getenv('JWT_SECRET')