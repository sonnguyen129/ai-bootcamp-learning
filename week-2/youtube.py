from youtube_transcript_api import YouTubeTranscriptApi
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    """Convert seconds to H:MM:SS if > 1 hour, else M:SS"""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02}:{secs:02}"
    else:
        return f"{minutes}:{secs:02}"


def make_subtitles(transcript) -> str:
    lines = []

    for entry in transcript:
        ts = format_timestamp(entry.start)
        text = entry.text.replace('\n', ' ')
        lines.append(ts + ' ' + text)

    return '\n'.join(lines)


def fetch_transcript_raw(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)
    return transcript


def fetch_transcript_text(video_id):
    transcript = fetch_transcript_raw(video_id)
    subtitles = make_subtitles(transcript)
    return subtitles


def fetch_transcript_cached(video_id):
    cache_dir = Path("./data_cache/youtube_videos")
    cache_file = cache_dir / f"{video_id}.txt"

    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    subtitles = fetch_transcript_text(video_id)
    cache_file.write_text(subtitles, encoding="utf-8")

    return subtitles