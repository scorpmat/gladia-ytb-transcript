# services/stream_capture.py
import subprocess

def get_audio_stream(url):
    command = [
        "yt-dlp", "-f", "bestaudio", "-o", "-",
        "--no-playlist", "--live-from-start", url,
        "|", "ffmpeg", "-i", "-", "-ac", "1", "-ar", "16000", "-f", "wav", "-"
    ]
    process = subprocess.Popen(" ".join(command), shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return process.stdout