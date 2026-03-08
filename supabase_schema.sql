-- Run this exact block of code in the Supabase SQL Editor
-- to create all required tables for the Telegram bot.

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS buttons (
    id       SERIAL PRIMARY KEY,
    label    TEXT NOT NULL,
    url      TEXT NOT NULL,
    position INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS channels (
    id               SERIAL PRIMARY KEY,
    channel_id       TEXT NOT NULL UNIQUE,
    channel_username TEXT NOT NULL,
    invite_link      TEXT NOT NULL
);

-- Insert defaults for settings
INSERT INTO settings (key, value) 
VALUES ('menu_text', '👋 *Welcome!*\n\nJoin our channels below, then tap *✅ I''ve Joined — Verify*.')
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value) 
VALUES ('menu_photo_file_id', '')
ON CONFLICT (key) DO NOTHING;
