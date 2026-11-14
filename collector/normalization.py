"""Canonical normalization utilities for deduplicating songs across streaming and TikTok sources."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

NOISE_PATTERNS = [
    r"\((?:feat\.?|ft\.?|featuring|w/|with)\s+[^)]*\)",
    r"\[(?:feat\.?|ft\.?|featuring|w/|with)\s+[^\]]*\]",
    r"\((?:official\s*)?(?:music\s*)?(?:video|m/?v|audio|lyric\s*video|visualizer|live|sped\s*up|slowed(?:\s*\+\s*reverb)?|remix|remastered?|version)\)",
    r"\[(?:official\s*)?(?:music\s*)?(?:video|m/?v|audio|lyric\s*video|visualizer|live|hd|4k)\]",
    r"\s*[-–|]\s*(?:official\s*(?:music\s*)?(?:video|m/?v)|official\s*audio|audio|lyric\s*video|remastered.*|live.*)$",
    r"\s+(?:official\s+)?m/?v\b.*$",
    r"\s+(?:feat\.?|ft\.?|featuring)\s+[^(\[\-–]+$",
]

ORIGINAL_SOUND_PREFIXES = (
    "original sound",
    "sonido original",
    "som original",
    "suono originale",
    "son original",
    "originalton",
    "suara asli",
    "oryginalny dźwięk",
    "oryginalny dzwiek",
    "оригинальный звук",
    "nhạc nền",
    "เสียงต้นฉบับ",
    "オリジナル楽曲",
    "원본 사운드",
    "orijinal ses",
)


def strip_accents(text: str) -> str:
    """Fold Unicode accents to ASCII equivalents for deterministic matching."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def clean_track_title(raw_title: str) -> str:
    """Clean featured artist tags and video/edition suffixes from a song title."""
    title = (raw_title or "").strip()
    for pat in NOISE_PATTERNS:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)
    title = re.sub(r"[\(\[]\s*$", "", title)
    title = re.sub(r"\s+", " ", title).strip(" -–|\"'‘’“”~")
    return title or (raw_title or "").strip()


def clean_artist_name(raw_artist: str) -> str:
    """Normalize primary artist name by removing guest collaborators."""
    artist = (raw_artist or "").strip()
    artist = re.sub(r"\s+(?:feat\.?|ft\.?|featuring)\s+.*$", "", artist, flags=re.IGNORECASE)
    artist = re.sub(r"\s*[,&/x×]\s+.*$", "", artist, flags=re.IGNORECASE)
    artist = re.sub(r"\s+", " ", artist).strip(" -–|\"'“”~")
    return artist or (raw_artist or "").strip()


def make_song_key(title: str, artist: str) -> str:
    """Generate canonical slug key for matching songs across Spotify/YouTube/Apple/TikTok/Deezer."""
    t = strip_accents(clean_track_title(title)).lower()
    a = strip_accents(clean_artist_name(artist)).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    a = re.sub(r"[^a-z0-9]+", "-", a).strip("-")
    if not t and not a:
        return "unknown-track"
    return f"{a}__{t}" if a else t


def make_title_only_key(title: str) -> str:
    """Generate normalized title-only slug for secondary cross-source matching."""
    t = strip_accents(clean_track_title(title)).lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def is_original_sound(music_name: str, music_author: str = "", is_original_flag: Any = False) -> bool:
    """Return True if a TikTok sound looks like creator mic audio rather than a released song."""
    low = strip_accents((music_name or "").strip()).lower()
    if not low:
        return True
    if any(low.startswith(strip_accents(pref)) for pref in ORIGINAL_SOUND_PREFIXES):
        return True
    if bool(is_original_flag) and music_author:
        auth_low = strip_accents(music_author.strip()).lower()
        if auth_low and auth_low in low and len(low) <= len(auth_low) + 25:
            return True
    return False
