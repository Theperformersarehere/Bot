import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# Initialize Supabase client
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    """
    Since we're using Supabase, tables must be created manually via the Supabase SQL Editor.
    This function just ensures the default settings exist.
    """
    try:
        # Check if menu_text exists
        res = supabase.table("settings").select("*").eq("key", "menu_text").execute()
        if not res.data:
            supabase.table("settings").insert({
                "key": "menu_text",
                "value": "👋 *Welcome!*\n\nJoin our channels below, then tap *✅ I've Joined — Verify*."
            }).execute()

        # Check if menu_photo_file_id exists
        res = supabase.table("settings").select("*").eq("key", "menu_photo_file_id").execute()
        if not res.data:
            supabase.table("settings").insert({
                "key": "menu_photo_file_id",
                "value": ""
            }).execute()

        # Check if join_channel_link exists
        res = supabase.table("settings").select("*").eq("key", "join_channel_link").execute()
        if not res.data:
            supabase.table("settings").insert({
                "key": "join_channel_link",
                "value": "https://t.me/yourchannel"
            }).execute()
            
        logger.info("Supabase connected and default settings verified.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase DB: {e}")
        logger.error("Make sure you have created the 'settings', 'buttons', and 'channels' tables in your Supabase project!")


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str) -> str:
    res = supabase.table("settings").select("value").eq("key", key).execute()
    if res.data:
        return res.data[0].get("value", "")
    return ""


def set_setting(key: str, value: str):
    # Upsert requires the primary key to be included in the object
    supabase.table("settings").upsert({"key": key, "value": value}).execute()


# ── Channels ──────────────────────────────────────────────────────────────────

def get_channels():
    res = supabase.table("channels").select("*").execute()
    return res.data


def add_channel(channel_id: str, channel_username: str, invite_link: str):
    # Check if exists first to avoid duplicate errors (or we can just let it fail silently)
    existing = supabase.table("channels").select("id").eq("channel_id", channel_id).execute()
    if not existing.data:
        supabase.table("channels").insert({
            "channel_id": channel_id,
            "channel_username": channel_username,
            "invite_link": invite_link
        }).execute()


def delete_channel(ch_id: int):
    supabase.table("channels").delete().eq("id", ch_id).execute()


# ── Videos ────────────────────────────────────────────────────────────────────

def get_videos():
    res = supabase.table("videos").select("*").order("id").execute()
    return res.data


def add_video(file_id: str):
    supabase.table("videos").insert({
        "file_id": file_id
    }).execute()


def delete_video(video_id: int):
    supabase.table("videos").delete().eq("id", video_id).execute()
