import subprocess
import os
import re
import asyncio
from datetime import datetime
from pytubefix import YouTube

# Define the target directory
VIDEO_DIR = "videos/"

# Ensure the directory exists
os.makedirs(VIDEO_DIR, exist_ok=True)

def get_video_quality_options(video_url: str):
    yt = YouTube(video_url)
    streams = yt.streams.filter(file_extension='mp4', adaptive=True).order_by('resolution').desc()
    
    quality_options = []
    for stream in streams:
        quality_options.append({
            "resolution": stream.resolution,
            "fps": stream.fps,
            "mime_type": stream.mime_type,
            "video_codec": stream.video_codec,
            "itag": stream.itag
        })
    
    return quality_options

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|#]', "_", filename)

async def combine_audio_video(video_path: str, audio_path: str, output_path: str) -> str:
    """ Merge video and audio using ffmpeg inside the 'videos/' folder """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{output_path}_{timestamp}_NSD.mp4"
    output_path = os.path.join(VIDEO_DIR, output_filename)

    command = [
        'ffmpeg', '-i', video_path, '-i', audio_path, '-c', 'copy', output_path
    ]
    process = await asyncio.create_subprocess_exec(*command)
    await process.communicate()

    return output_path

async def download_youtube_video(video_url: str, resolution: str, is_audio: bool):
    yt = YouTube(video_url, use_oauth=True, allow_oauth_cache=True)
    
    sanitized_title = sanitize_filename(yt.title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not is_audio:
        video_stream = yt.streams.filter(res=resolution, adaptive=True, file_extension='mp4').first()
        if video_stream is None:
            raise ValueError("No adaptive video stream found.")
        
        video_filename = f"{sanitized_title}_video_{timestamp}.mp4"
        video_path = os.path.join(VIDEO_DIR, video_filename)
        await asyncio.to_thread(video_stream.download, output_path=VIDEO_DIR, filename=video_filename)

        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
        if audio_stream is None:
            raise ValueError("No audio stream found.")
        
        audio_filename = f"{sanitized_title}_audio_{timestamp}.mp3"
        audio_path = os.path.join(VIDEO_DIR, audio_filename)
        await asyncio.to_thread(audio_stream.download, output_path=VIDEO_DIR, filename=audio_filename)

        return video_path, audio_path
    
    else:
        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
        if audio_stream is None:
            raise ValueError("No audio stream found.")
        
        audio_filename = f"{sanitized_title}_audio_{timestamp}.mp3"
        audio_path = os.path.join(VIDEO_DIR, audio_filename)
        await asyncio.to_thread(audio_stream.download, output_path=VIDEO_DIR, filename=audio_filename)
        
        return audio_path

async def clean_up_files(*file_paths):
    """ Delete files from the 'videos/' folder """
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted: {file_path}")
