import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN         = os.getenv("BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY      = os.getenv("SUPABASE_KEY", "")
