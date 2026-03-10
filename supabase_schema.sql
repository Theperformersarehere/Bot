-- Run this exact block of code in the Supabase SQL Editor
-- to create all required tables for the Telegram bot.

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS channels (
    id               SERIAL PRIMARY KEY,
    channel_id       TEXT NOT NULL UNIQUE,
    channel_username TEXT NOT NULL,
    invite_link      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    id       SERIAL PRIMARY KEY,
    file_id  TEXT NOT NULL
);

-- Insert defaults for settings
INSERT INTO settings (key, value) 
VALUES ('menu_text', '*Hey {first_name} {username}*\n\n*Please Join All My Update Channels To Use Me!*')
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value) 
VALUES ('menu_photo_file_id', '')
ON CONFLICT (key) DO NOTHING;

INSERT INTO settings (key, value)
VALUES ('join_channel_link', 'https://t.me/yourchannel')
ON CONFLICT (key) DO NOTHING;
