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
CORS(app) 

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def sanitize_filename(filename):
    safe_filename = re.sub(r'[\\/:*?"<>|]', '', filename)
    safe_filename = re.sub(r'[^\w\s-]', '', safe_filename).strip()
    return safe_filename

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')

    if not video_url:
        return jsonify({"success": False, "message": "Link faraham nahi kiya gaya hai."}), 400

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
        
        temp_folder_name = f'temp_{clean_title[:20]}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        temp_dir = os.path.join(DOWNLOAD_DIR, temp_folder_name)
        
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Step 2: Download Options (STRICT NON-FFMPEG MODE)
        ydl_opts_download = {
            # FIX: Sirf wahi format download hoga jisme audio+video pehle se ek saath ho
            # Is se FFmpeg ki zaroorat nahi paregi
            'format': 'best[ext=mp4]/best', 
            'outtmpl': os.path.join(temp_dir, f"{clean_title}.%(ext)s"),
            'nocheckcertificate': True,
            'quiet': True,
            'ignoreerrors': True,
            'noplaylist': True,
            'postprocessors': [], # No merging/post-processing
        }
        
        # Step 3: Download
        with YoutubeDL(ydl_opts_download) as ydl_download:
            ydl_download.download([video_url])
            
        downloaded_files = [f for f in os.listdir(temp_dir) if f.startswith(clean_title)]
        
        if not downloaded_files:
            raise Exception("File download fail ho gayi. Link shayad private hai ya supported nahi.")
            
        final_filename_with_ext = downloaded_files[0]
        full_path = os.path.join(temp_dir, final_filename_with_ext)

        # Step 4: Send File
        response = send_file(full_path, 
                             as_attachment=True, 
                             download_name=final_filename_with_ext)

        @response.call_on_close
        def cleanup():
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        
        return response

    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        return jsonify({
            "success": False, 
            "message": f"Download Error: {str(e)[:50]}"
        }), 400 

if __name__ == '__main__':
    # Local testing ke liye
    port = int(os.environ.get('PORT', 5000))
    # app.run(debug=True, port=port)
    pass
