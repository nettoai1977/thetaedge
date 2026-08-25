"""Fetch a YouTube transcript to text. Usage: fetch_yt.py VIDEO_ID [OUTFILE]"""
import sys
from youtube_transcript_api import YouTubeTranscriptApi

vid = sys.argv[1]
outfile = sys.argv[2] if len(sys.argv) > 2 else None

api = YouTubeTranscriptApi()
tlist = api.list(vid)
# Prefer English, else first available
try:
    t = tlist.find_transcript(['en'])
except Exception:
    t = next(iter(tlist))
data = t.fetch()
text = ' '.join(seg.text.replace('\n', ' ') for seg in data)

if outfile:
    with open(outfile, 'w') as f:
        f.write(text)
    print(f'saved {len(text)} chars -> {outfile}')
else:
    print(text)
