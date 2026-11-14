"""Deterministic unit tests for free source parsers and Apify TikTok normalizers."""

import asyncio
import json
from pathlib import Path

from collector.normalization import clean_artist_name, clean_track_title
from collector.scoring import merge_all_sources
from collector.sources_apify import (
    estimate_apify_weekly_cost,
    parse_explore_sounds_items,
    parse_history_insights_items,
    parse_instagram_reels_items,
    parse_shazam_charts_items,
    parse_spotify_scraper_items,
)
from collector.sources_free import (
    enrich_songs_metadata,
    parse_billboard_hot100_json,
    parse_deezer_chart_json,
    parse_itunes_rss_json,
    parse_kworb_apple_music_html,
    parse_kworb_radio_shazam_html,
    parse_kworb_spotify_daily_html,
    parse_kworb_spotify_weekly_html,
    parse_kworb_youtube_weekly_html,
)


def test_parse_kworb_spotify_weekly_html() -> None:
    html = """
    <table>
      <thead><tr><th>Pos</th><th>P+</th><th>Artist and Title</th><th>Wks</th><th>Pk</th><th>(x?)</th><th>Streams</th><th>Streams+</th><th>Total</th></tr></thead>
      <tbody>
        <tr>
          <td>1</td><td>+4</td>
          <td><a href="../artist/790.html">KAROL G</a> - <a href="../track/3h5T5JypYU7huFiVYhv1dr.html">BbY WOW (w/ Judeline , rusowsky )</a></td>
          <td>2</td><td>1</td><td>(x1)</td><td>33,199,682</td><td>+11,066,560</td><td>55,000,000</td>
        </tr>
      </tbody>
    </table>
    """
    rows = parse_kworb_spotify_weekly_html(html)
    assert len(rows) == 1
    r = rows[0]
    assert r["rank"] == 1
    assert r["rank_change"] == "+4"
    assert r["title"] == "BbY WOW"
    assert r["artist"] == "KAROL G"
    assert r["song_key"] == "karol-g__bby-wow"
    assert r["weekly_streams"] == 33_199_682
    assert r["weekly_delta"] == 11_066_560
    assert r["weekly_growth_pct"] == 50.0
    assert r["spotify_url"] == "https://open.spotify.com/track/3h5T5JypYU7huFiVYhv1dr"


def test_parse_kworb_spotify_daily_html() -> None:
    html = """
    <table id="spotifydaily">
      <tr>
        <td>2</td><td>NEW</td>
        <td><a href="../artist/6P5.html">Ashe</a> - <a href="../track/7MOO89Qv9AV7VZkt5mcqA8.html">Stop The Wedding!</a></td>
        <td>1</td><td>2</td><td></td><td>4,409,588</td><td>+72,262</td><td>29,137,725</td><td>+532,362</td><td>178,171,252</td>
      </tr>
    </table>
    """
    rows = parse_kworb_spotify_daily_html(html)
    assert len(rows) == 1
    assert rows[0]["daily_streams"] == 4_409_588
    assert rows[0]["seven_day_streams"] == 29_137_725
    assert rows[0]["rank_change"] == "NEW"


def test_parse_kworb_youtube_weekly_html() -> None:
    html = """
    <table>
      <tr>
        <td>1</td><td>NEW</td>
        <td><a href="../video/BPZkZpGMpXA.html">Bad Bunny - BAILE INoLVIDABLE (Official Video)</a></td>
        <td>1</td><td>1</td><td>(x1)</td><td>60,152,374</td><td></td>
      </tr>
      <tr>
        <td>2</td><td>+3</td>
        <td><a href="../video/4rPcOxl-cyM.html">KING: Tu Mil Jaaye | Shah Rukh Khan</a></td>
        <td>2</td><td>2</td><td>(x1)</td><td>30,000,000</td><td>+5,000,000</td>
      </tr>
    </table>
    """
    rows = parse_kworb_youtube_weekly_html(html)
    assert len(rows) == 2
    assert rows[0]["artist"] == "Bad Bunny"
    assert rows[0]["title"] == "BAILE INoLVIDABLE"
    assert rows[0]["youtube_video_id"] == "BPZkZpGMpXA"
    assert rows[1]["artist"] == "KING"
    assert rows[1]["weekly_growth_pct"] == 20.0


def test_parse_kworb_apple_and_radio_shazam() -> None:
    apple_html = "<table><tr><td>1</td><td>=</td><td>Tate McRae - Housewife</td><td>29</td><td>1</td><td>(x27)</td><td>15905</td><td>+410</td><td>0.481</td></tr></table>"
    apple = parse_kworb_apple_music_html(apple_html)
    assert len(apple) == 1
    assert apple[0]["points"] == 15905
    assert apple[0]["points_delta"] == 410

    radio_html = "<table><tr><td>6</td><td>+1</td><td>Taylor Swift - Patient Zero</td><td>47</td><td>6</td><td></td><td>40.44</td><td>+0.89</td><td>3</td><td>40.44</td><td>16</td><td>59</td><td>77</td><td>12</td></tr></table>"
    radio = parse_kworb_radio_shazam_html(radio_html)
    assert len(radio) == 1
    assert radio[0]["shazam_rank"] == 12
    assert radio[0]["radio_audience_m"] == 40.44
    assert radio[0]["radio_audience_delta"] == 0.89


def test_parse_itunes_deezer_billboard() -> None:
    itunes = parse_itunes_rss_json(
        {
            "feed": {
                "entry": [
                    {
                        "im:name": {"label": "Torn (feat. Dolly Parton)"},
                        "im:artist": {"label": "U2"},
                        "im:image": [{"label": "https://img/170x170bb.jpg"}],
                        "category": {"attributes": {"label": "Rock"}},
                        "link": [
                            {"attributes": {"rel": "alternate", "href": "https://music.apple.com/track"}},
                            {
                                "attributes": {
                                    "rel": "enclosure",
                                    "im:assetType": "preview",
                                    "href": "https://audio/preview.m4a",
                                }
                            },
                        ],
                    }
                ]
            }
        }
    )
    assert len(itunes) == 1
    assert itunes[0]["title"] == "Torn"
    assert itunes[0]["preview_url"] == "https://audio/preview.m4a"
    assert itunes[0]["cover_url"] == "https://img/500x500bb.jpg"
    assert itunes[0]["genre"] == "Rock"

    deezer = parse_deezer_chart_json(
        {
            "data": [
                {
                    "id": 99,
                    "title": "DTMF",
                    "rank": 980000,
                    "duration": 210,
                    "preview": "https://dz/p.mp3",
                    "link": "https://deezer.com/track/99",
                    "artist": {"name": "Bad Bunny"},
                    "album": {"cover_big": "https://dz/c.jpg"},
                }
            ]
        }
    )
    assert deezer[0]["preview_url"] == "https://dz/p.mp3"
    assert deezer[0]["deezer_rank"] == 980000

    bb = parse_billboard_hot100_json(
        {
            "data": [
                {
                    "song": "Choosin' Texas",
                    "artist": "Ella Langley",
                    "this_week": 1,
                    "last_week": 8,
                    "peak_position": 1,
                    "weeks_on_chart": 4,
                }
            ]
        }
    )
    assert bb[0]["rank"] == 1
    assert bb[0]["last_week"] == 8


def test_parse_apify_tiktok_actors_and_cost() -> None:
    history_raw = [
        {"record_type": "coverage_summary", "rows_written": 2},
        {
            "record_type": "sound_insight",
            "sound_id": "111",
            "title": "original sound - user99",
            "artist": "user99",
            "is_original_sound": True,
        },
        {
            "record_type": "sound_insight",
            "sound_id": "222",
            "title": "DtMF",
            "artist": "Bad Bunny",
            "chart_type": "viral",
            "rank": 3,
            "usage_count": 450000,
            "usage_change": 150000,
            "usage_growth_pct": 50.0,
            "rank_change": 12,
            "is_original_sound": False,
            "tiktok_url": "https://www.tiktok.com/music/DtMF-222",
            "spotify_url": "https://open.spotify.com/track/abc",
            "examples": [{"video_url": "https://tiktok.com/@c/video/1", "creator_handle": "c", "plays": 900000}],
        },
    ]
    parsed_h = parse_history_insights_items(history_raw)
    assert len(parsed_h) == 1
    assert parsed_h[0]["song_key"] == "bad-bunny__dtmf"
    assert parsed_h[0]["tiktok_7d_growth_pct"] == 50.0
    assert parsed_h[0]["tiktok_samples"][0]["plays"] == 900000

    explore_raw = [
        {"musicTitle": "sonido original - pepe", "musicAuthor": "pepe", "musicIsOriginal": True},
        {
            "musicTitle": "Abracadabra",
            "musicAuthor": "Lady Gaga",
            "musicId": "555",
            "position": 2,
            "previousPosition": 9,
            "videosInSample": 6,
            "samplePlays": 12_000_000,
            "musicIsOriginal": False,
            "isNew": False,
            "musicAudioUrl": "https://tt/audio.mp3",
        },
    ]
    parsed_e = parse_explore_sounds_items(explore_raw)
    assert len(parsed_e) == 1
    assert parsed_e[0]["tiktok_rank_change"] == 7
    assert parsed_e[0]["preview_url"] == "https://tt/audio.mp3"

    est = estimate_apify_weekly_cost()
    assert 0.80 <= est["estimated_usd"] <= 1.05
    assert 3.20 <= est["monthly_4_weeks_usd"] <= 4.20
    assert set(est["breakdown"].keys()) == {
        "tiktok_history_usd",
        "tiktok_explore_usd",
        "instagram_reels_usd",
        "shazam_charts_usd",
        "spotify_viral_plays_usd",
    }


def test_parse_reels_shazam_and_spotify_scraper() -> None:
    reels_raw = [
        {"title": "Original Audio", "artist": "user1", "kind": "original", "reel_count": 50},
        {
            "audio_id": "987",
            "audio_url": "https://www.instagram.com/reels/audio/987/",
            "title": "SI ANTES TE HUBIERA CONOCIDO",
            "artist": "KAROL G",
            "kind": "catalogue",
            "reel_count": 185000,
            "growth_1d": 4200,
            "growth_7d": 39000,
            "growth_7d_percent": 68.4,
            "native_rank": 1,
            "examples": [{"reel_url": "https://www.instagram.com/reel/abc/", "creator_handle": "bailar", "plays": 750000}],
        },
    ]
    reels = parse_instagram_reels_items(reels_raw)
    assert len(reels) == 1
    assert reels[0]["song_key"] == "karol-g__si-antes-te-hubiera-conocido"
    assert reels[0]["reels_7d_growth_pct"] == 68.4
    assert reels[0]["reels_samples"][0]["plays"] == 750000

    shazam_raw = [
        {
            "chartType": "top-200",
            "country": "world",
            "rank": 5,
            "trackTitle": "APT.",
            "artists": ["ROSÉ", "Bruno Mars"],
            "songUrl": "https://www.shazam.com/song/1/apt",
            "artworkUrl": "https://img/apt.jpg",
        },
        {
            "chartType": "viral",
            "country": "world",
            "rank": 2,
            "trackTitle": "APT.",
            "artists": ["ROSÉ"],
            "songUrl": "https://www.shazam.com/song/1/apt",
        },
    ]
    shazam = parse_shazam_charts_items(shazam_raw)
    assert len(shazam) == 1
    assert shazam[0]["shazam_global_rank"] == 5
    assert shazam[0]["shazam_viral_rank"] == 2
    assert shazam[0]["cover_url"] == "https://img/apt.jpg"

    spotify_raw = [
        {
            "type": "playlist",
            "tracks": [
                {
                    "name": "APT.",
                    "artists": ["ROSÉ", "Bruno Mars"],
                    "duration": 169000,
                    "url": "https://open.spotify.com/track/apt123",
                }
            ],
        },
        {
            "type": "track",
            "name": "APT.",
            "artists": [{"name": "ROSÉ"}],
            "playCount": 985000000,
            "releaseDate": "2024-10-18",
            "audioPreviewUrl": "https://p.scdn.co/mp3-preview/apt",
            "albumArt": "https://i.scdn.co/image/apt",
            "url": "https://open.spotify.com/track/apt123",
        },
    ]
    sp_extra = parse_spotify_scraper_items(spotify_raw)
    assert len(sp_extra) == 1
    assert sp_extra[0]["spotify_viral_rank"] == 1
    assert sp_extra[0]["spotify_total_plays"] == 985_000_000
    assert sp_extra[0]["release_date"] == "2024-10-18"
    assert sp_extra[0]["preview_url"] == "https://p.scdn.co/mp3-preview/apt"


def test_clean_track_title_mv_and_curly_quotes() -> None:
    assert clean_track_title("‘SHOCK’ M/V") == "SHOCK"
    assert clean_track_title("DESERVE' M/V") == "DESERVE"
    assert clean_track_title("ADDICTED (Official MV)") == "ADDICTED"
    assert clean_artist_name("RIIZE feat. Someone") == "RIIZE"


def test_merge_all_sources_preserves_itunes_preview_over_deezer() -> None:
    row = {
        "song_key": "karol-g__bby-wow",
        "title": "BbY WOW",
        "artist": "KAROL G",
        "rank": 1,
    }
    free_data = {
        "spotify_weekly": [{**row, "weekly_streams": 33_000_000}],
        "itunes_rss": [{**row, "preview_url": "https://audio-ssl.itunes.apple.com/bbywow.m4a", "cover_url": "https://it/cov.jpg"}],
        "deezer_chart": [{**row, "preview_url": "https://cdnt-preview.dzcdn.net/stream/c-abc.mp3?hdnea=exp=1700000000", "deezer_rank": 999999}],
    }
    merged = merge_all_sources(free_data, {}, "2026-11-14T00:00:00Z")
    assert len(merged) == 1
    assert merged[0]["preview_url"] == "https://audio-ssl.itunes.apple.com/bbywow.m4a"
    assert merged[0]["preview_source"] == "itunes"


def test_enrich_songs_metadata_upgrades_ephemeral_and_avoids_caching_dzcdn(
    tmp_path: Path, monkeypatch
) -> None:
    async def fake_itunes(client, title: str, artist: str) -> dict:
        if "BbY WOW" in title:
            return {
                "preview_url": "https://audio-ssl.itunes.apple.com/perm_bby.m4a",
                "preview_source": "itunes",
                "cover_url": "https://it/bby.jpg",
                "genre": "Latin",
                "duration_sec": 190,
                "apple_music_url": "https://music.apple.com/track/1",
            }
        return {}

    async def fake_deezer(client, title: str, artist: str, deezer_track_id: str = "") -> dict:
        return {
            "preview_url": "https://cdnt-preview.dzcdn.net/stream/c-xyz.mp3?hdnea=exp=9999999999",
            "preview_source": "deezer",
            "cover_url": "https://dz/rare.jpg",
            "bpm": 124.0,
            "deezer_url": "https://www.deezer.com/track/42",
        }

    monkeypatch.setattr("collector.sources_free._lookup_itunes_meta", fake_itunes)
    monkeypatch.setattr("collector.sources_free._lookup_deezer_meta", fake_deezer)

    cache_file = tmp_path / "track_meta_cache.json"
    songs = [
        {
            "song_key": "karol-g__bby-wow",
            "title": "BbY WOW",
            "artist": "KAROL G",
            "preview_url": "https://cdnt-preview.dzcdn.net/old_expired.mp3?hdnea=exp=100",
            "preview_source": "deezer_chart",
            "cover_url": "https://dz/old.jpg",
            "genres": [],
        },
        {
            "song_key": "rare__exclusive",
            "title": "Exclusive Track",
            "artist": "Indie Artist",
            "preview_url": "",
            "preview_source": "",
            "cover_url": "",
            "genres": [],
        },
    ]

    asyncio.run(enrich_songs_metadata(songs, max_enrich=10, cache_path=cache_file))

    # Song 1 upgraded from ephemeral dzcdn.net to permanent iTunes
    assert songs[0]["preview_url"] == "https://audio-ssl.itunes.apple.com/perm_bby.m4a"
    assert songs[0]["preview_source"] == "itunes"
    # Song 2 receives live Deezer preview on snapshot object, but cache must NOT store ephemeral dzcdn URL
    assert "dzcdn.net" in songs[1]["preview_url"]
    assert songs[1]["bpm"] == 124.0

    saved_cache = json.loads(cache_file.read_text(encoding="utf-8"))
    assert saved_cache["karol-g__bby-wow"]["preview_url"] == "https://audio-ssl.itunes.apple.com/perm_bby.m4a"
    assert saved_cache["rare__exclusive"]["preview_url"] == ""
    assert saved_cache["rare__exclusive"]["cover_url"] == "https://dz/rare.jpg"


def test_parse_eduair94_spotify_viral_and_track_rows() -> None:
    eduair_raw = [
        {
            "category": "chart_viral_tracks",
            "mode": "chart",
            "ok": True,
            "name": "STORM II",
            "artists": ["GENER8ION", "Yung Lean"],
            "rank": 1,
            "playCount": 97_326_139,
            "releaseDate": "2026-04-24",
            "imageUrl": "https://i.scdn.co/image/storm2",
            "url": "https://open.spotify.com/track/0FZd4IaxB12sUTKSUUGwWq",
        },
        {
            "category": "chart_viral_tracks",
            "mode": "chart",
            "ok": True,
            "name": "BbY WOW",
            "artists": ["KAROL G", "Judeline"],
            "rank": 7,
            "playCount": 470_000_000,
            "releaseDate": "2026-08-07",
            "imageUrl": "https://i.scdn.co/image/bby",
            "url": "https://open.spotify.com/track/3h5T5JypYU7huFiVYhv1dr",
        },
        {
            "category": "track",
            "mode": "get",
            "ok": True,
            "name": "BbY WOW",
            "artists": ["KAROL G"],
            "durationMs": 225834,
            "playCount": 474_751_786,
            "releaseDate": "2026-08-07",
            "imageUrl": "https://i.scdn.co/image/bby_hd",
            "previewUrl": "https://p.scdn.co/mp3-preview/bbywow",
            "url": "https://open.spotify.com/track/3h5T5JypYU7huFiVYhv1dr",
        },
        {
            "category": "track",
            "mode": "get",
            "ok": False,
            "name": "Bad Row",
            "artists": ["Someone"],
        },
    ]
    parsed = parse_spotify_scraper_items(eduair_raw)
    assert len(parsed) == 2

    by_key = {row["song_key"]: row for row in parsed}
    storm = by_key["gener8ion__storm-ii"]
    assert storm["spotify_viral_rank"] == 1
    assert storm["spotify_total_plays"] == 97_326_139
    assert storm["cover_url"] == "https://i.scdn.co/image/storm2"

    bby = by_key["karol-g__bby-wow"]
    assert bby["spotify_viral_rank"] == 7
    assert bby["spotify_total_plays"] == 474_751_786
    assert bby["duration_sec"] == 225
    assert bby["preview_url"] == "https://p.scdn.co/mp3-preview/bbywow"
