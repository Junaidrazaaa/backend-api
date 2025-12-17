from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import re
import shutil
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

DOWNLOAD_DIR = '/tmp/downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/api/download', methods=['POST', 'OPTIONS'])
def download_video():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"success": False, "message": "Link missing"}), 400
        
    video_url = data.get('url')
    temp_dir = None 

    try:
        temp_folder_name = f"dir_{datetime.now().strftime('%H%M%S')}"
        temp_dir = os.path.join(DOWNLOAD_DIR, temp_folder_name)
        os.makedirs(temp_dir, exist_ok=True)

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            # FIX: Title ko 50 characters tak limit kar diya hai taake 'File name too long' error na aaye
            'outtmpl': os.path.join(temp_dir, '%(title).50s.%(ext)s'),
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {'youtube': {'player_client': ['android']}},
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        files = os.listdir(temp_dir)
        if not files:
            raise Exception("Download failed - No file saved.")
            
        full_path = os.path.join(temp_dir, files[0])

        return send_file(
            full_path, 
            as_attachment=True, 
            download_name=files[0]
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

if __name__ == '__main__':
    pass
