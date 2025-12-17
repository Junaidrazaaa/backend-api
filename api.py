from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import re
import shutil
from datetime import datetime

app = Flask(__name__)
# CORS Fix for all origins
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

# Render par hamesha '/tmp' folder use karna chahiye files save karne ke liye
DOWNLOAD_DIR = '/tmp/downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def sanitize_filename(filename):
    safe_filename = re.sub(r'[\\/:*?"<>|]', '', filename)
    safe_filename = re.sub(r'[^\w\s-]', '', safe_filename).strip()
    return safe_filename or "video_file"

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
        # Step 1: Options for Extraction & Download
        # Humne Extraction aur Download ko ek hi step mein kar diya hai stability ke liye
        temp_folder_name = f"dir_{datetime.now().strftime('%H%M%S')}"
        temp_dir = os.path.join(DOWNLOAD_DIR, temp_folder_name)
        os.makedirs(temp_dir, exist_ok=True)

        ydl_opts = {
            # Sab se asaan format jo bina FFmpeg ke chale
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(temp_dir, '%(title).200s.%(ext)s'),
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Mobile client use karna taake YouTube block na kare
            'extractor_args': {'youtube': {'player_client': ['android']}},
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            # Seedha download shuru karein
            ydl.download([video_url])
            
        # Check karein ke file kahan hai
        files = os.listdir(temp_dir)
        if not files:
            raise Exception("Server could not save the video. IP might be blocked.")
            
        full_path = os.path.join(temp_dir, files[0])

        # Step 2: File bhejien
        return send_file(
            full_path, 
            as_attachment=True, 
            download_name=files[0]
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

    finally:
        # Note: 'finally' mein cleanup thora risk hota hai, 
        # isliye cleanup handle karne ka behtar tareeqa bad mein dekhenge
        pass

if __name__ == '__main__':
    pass
