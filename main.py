from flask import Flask, request, jsonify, send_from_directory
import os
import yt
from dotenv import load_dotenv
import asyncio
from pytubefix import YouTube
import socket
import urllib.parse

app = Flask(__name__)

# Define the path for video storage
VIDEO_DIR = "videos/"
# Load API Key from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")


def get_server_ip():
    """ Get the local IP address of the server """
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)


def is_authorized():
    """ Verify API key from headers """
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header.split(" ")[1] != API_KEY:
        return False
    return True

@app.route('/info', methods=['POST'])
def fetch_video_info():
    
    if not is_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({"error": "No URL provided"}), 400

        video_info = yt.get_video_quality_options(url)
        return jsonify(video_info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/download', methods=['POST'])
def download_video():
    
    if not is_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        url = request.json.get('data').get('url')
        resolution = request.json.get('data').get('resolution')
        is_audio = request.json.get('data').get('is_audio')
        if not url:
            return jsonify({"error": "No URL provided"}), 400

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if is_audio:
            
            audio_path = loop.run_until_complete(yt.download_youtube_video(url, resolution, is_audio))
            
            server_ip = get_server_ip()
            encoded_filename = urllib.parse.quote(audio_path)
            file_url = f"http://{server_ip}:5000/{encoded_filename}"
            return jsonify({"output_path": file_url})

        else:
            
            video_path, audio_path = loop.run_until_complete(yt.download_youtube_video(url, resolution, is_audio))
            output_path = f"{yt.sanitize_filename(YouTube(url).title)}"

            final_output = loop.run_until_complete(yt.combine_audio_video(video_path, audio_path, output_path))
            loop.run_until_complete(yt.clean_up_files(video_path, audio_path))
            
            # Get server IP and encode filename for URL compatibility
            server_ip = get_server_ip()
            encoded_filename = urllib.parse.quote(final_output)
            
            file_url = f"http://{server_ip}:5000/{encoded_filename}"

            return jsonify({"output_path": file_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to serve video files
@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)

if __name__ == '__main__':
    server_ip = get_server_ip()
    print(f"Server running on: http://{server_ip}:5000")
    app.run(debug=True, host='0.0.0.0')
