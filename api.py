from flask import Flask, request, jsonify, send_file
from flask_cors import CORS 
from yt_dlp import YoutubeDL
import os
import re
import shutil
from datetime import datetime

app = Flask(__name__)
# CORS ko React ke local host (http://localhost:3000) ke liye enable kar dein
CORS(app) 
PORT = 5000

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# File name se illegal characters hatane ka function
def sanitize_filename(filename):
    # Illegal characters ko hata kar sirf alphanumeric aur spaces rehne de
    safe_filename = re.sub(r'[\\/:*?"<>|]', '', filename)
    safe_filename = re.sub(r'[^\w\s-]', '', safe_filename).strip()
    return safe_filename

# API Endpoint: /api/download
@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')

    if not video_url:
        return jsonify({"success": False, "message": "Link faraham nahi kiya gaya hai."}), 400

    temp_dir = None 
    try:
        # Step 1: Video ki information extract karna
        ydl_opts_info = {
            'quiet': True,
            'nocheckcertificate': True,
            'skip_download': True,
        }
        with YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
        
        raw_title = info_dict.get('title', 'media_file')
        clean_title = sanitize_filename(raw_title)
        
        # Temporary folder banana
        temp_folder_name = f'temp_{clean_title[:20]}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        temp_dir = os.path.join(DOWNLOAD_DIR, temp_folder_name)
        
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Step 2: Download Options set karna (NO MERGING REQUIRED)
        ydl_opts_download = {
            # FIX: Simple 'best' format use karen taake merging ki zaroorat na pare (No FFmpeg)
            'format': 'best', 
            'outtmpl': os.path.join(temp_dir, f"{clean_title}.%(ext)s"),
            'nocheckcertificate': True,
            'quiet': True,
            # Reddit specific fix: Agar format available nahi hai, toh error na de
            'ignoreerrors': True,
        }
        
        # Step 3: Video download karna
        with YoutubeDL(ydl_opts_download) as ydl_download:
            ydl_download.download([video_url])
            
        # Downloaded file ka poora naam dhundhna
        downloaded_files = [f for f in os.listdir(temp_dir) if f.startswith(clean_title)]
        
        # Agar koi file nahi mili toh exception throw karen
        if not downloaded_files:
            raise Exception("File download hone ke baad mili nahi ya link supported nahi.")
            
        final_filename_with_ext = downloaded_files[0]
        full_path = os.path.join(temp_dir, final_filename_with_ext)


        # Step 4: Downloaded file ko browser par send karna
        response = send_file(full_path, 
                              as_attachment=True, 
                              download_name=final_filename_with_ext)

        # Download transfer hone ke baad temp folder ko delete karna
        @response.call_on_close
        def cleanup():
            try:
                shutil.rmtree(temp_dir)
                print(f"Temporary folder deleted: {temp_dir}")
            except Exception as e:
                print(f"Cleanup Error: {e}")
        
        return response

    except Exception as e:
        error_message = f"Download Error: {e}"
        print(error_message)
        
        # Cleanup agar error ho
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        # Error hone par 400 status code aur JSON data bhej rahe hain
        return jsonify({
            "success": False, 
            "message": "Error: Link invalid, private video, ya aapke device par is format ki video download nahi ho saki."
        }), 400 

if __name__ == '__main__':
    print(f"Flask API is starting on http://127.0.0.1:{PORT}")
    app.run(debug=True, port=PORT)