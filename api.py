from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import re
import shutil
from datetime import datetime

# Render Stability Settings
os.environ['YDL_NO_CACHE_DIR'] = 'true'
os.environ['YDL_OPTS'] = '--no-check-certificates --geo-bypass'

app = Flask(__name__)

# >>>>> CORS FIX FOR HOSTINGER <<<<<
# Is se Hostinger ki website ko backend use karne ki permission mil jayegi
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def sanitize_filename(filename):
    safe_filename = re.sub(r'[\\/:*?"<>|]', '', filename)
    safe_filename = re.sub(r'[^\w\s-]', '', safe_filename).strip()
    return safe_filename

@app.route('/api/download', methods=['POST', 'OPTIONS'])
def download_video():
    # OPTIONS request handle karne ke liye (Browser pre-flight check)
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"success": False, "message": "Link missing"}), 400
        
    video_url = data.get('url')
    temp_dir = None 

    try:
        # Step 1: Info Extraction
        ydl_opts_info = {
            'quiet': True,
            'nocheckcertificate': True,
            'skip_download': True,
        }
        with YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
        
        raw_title = info_dict.get('title', 'media_file')
        clean_title = sanitize_filename(raw_title)
        
        temp_folder_name = f'temp_{clean_title[:15]}_{datetime.now().strftime("%H%M%S")}'
        temp_dir = os.path.join(DOWNLOAD_DIR, temp_folder_name)
        
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Step 2: Download Options (Strict Non-FFmpeg)
        ydl_opts_download = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(temp_dir, f"{clean_title}.%(ext)s"),
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        # Step 3: Download
        with YoutubeDL(ydl_opts_download) as ydl_download:
            ydl_download.download([video_url])
            
        downloaded_files = os.listdir(temp_dir)
        if not downloaded_files:
            raise Exception("No file downloaded")
            
        full_path = os.path.join(temp_dir, downloaded_files[0])

        # Step 4: Send File
        response = send_file(full_path, as_attachment=True)
        
        # CORS Headers manually add karna (Extra Safety)
        response.headers.add("Access-Control-Allow-Origin", "*")

        @response.call_on_close
        def cleanup():
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        return response

    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return jsonify({"success": False, "message": str(e)}), 400

if __name__ == '__main__':
    app.run()
