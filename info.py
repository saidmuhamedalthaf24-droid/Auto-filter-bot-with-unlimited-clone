import os
from dotenv import load_dotenv
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URI = os.getenv("DB_URI")           # Main MongoDB
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Filter channel
CLONE_DB_URI = os.getenv("CLONE_DB_URI")  # Clone database  
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))  # Log channel
OWNER_ID = int(os.getenv("OWNER_ID"))
