from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import yt_dlp, os, socket, logging
import requests as req

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, origins="*")
logging.getLogger('werkzeug').setLevel(logging.ERROR)

COOKIES_FILE = 'yt_cookies.txt'

# Clean invalid cookies on startup
if os.path.exists(COOKIES_FILE):
    try:
        with open(COOKIES_FILE, 'r') as f: c = f.read().strip()
        if not c.startswith('# Netscape HTTP Cookie File'):
            os.remove(COOKIES_FILE)
    except:
        try: os.remove(COOKIES_FILE)
        except: pass

def ydl_opts(extra={}):
    o = {"quiet": True, "no_warnings": True, "skip_download": True}
    if os.path.exists(COOKIES_FILE):
        o["cookiefile"] = COOKIES_FILE
    o.update(extra)
    return o

def card(e):
    vid = e.get('id', '')
    return {
        "id": vid,
        "title": e.get("title") or "Unknown",
        "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        "duration": e.get("duration"),
        "view_count": e.get("view_count"),
        "uploader": e.get("uploader") or e.get("channel") or ""
    }

# ── STATIC FILES ──
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/json')

@app.route('/icon.png')
def icon():
    if os.path.exists('icon.png'):
        return send_from_directory('.', 'icon.png', mimetype='image/png')
    return '', 404

@app.route('/status')
def status():
    return jsonify({"ok": True, "version": "3.0"})

# ── API ──
@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    if not q: return jsonify({"results": []})
    try:
        with yt_dlp.YoutubeDL(ydl_opts({"extract_flat": "in_playlist"})) as ydl:
            res = ydl.extract_info(f"ytsearch24:{q}", download=False)
            return jsonify({"results": [card(e) for e in (res.get('entries') or []) if e and e.get('id')]})
    except Exception as ex:
        return jsonify({"results": [], "error": str(ex)})

@app.route('/api/trending')
def trending():
    try:
        with yt_dlp.YoutubeDL(ydl_opts({"extract_flat": "in_playlist", "playlistend": 24})) as ydl:
            res = ydl.extract_info("https://www.youtube.com/feed/trending", download=False)
            results = [card(e) for e in (res.get('entries') or []) if e and e.get('id')]
            if results: return jsonify({"results": results})
    except: pass
    try:
        with yt_dlp.YoutubeDL(ydl_opts({"extract_flat": "in_playlist"})) as ydl:
            res = ydl.extract_info("ytsearch24:trending india 2025", download=False)
            return jsonify({"results": [card(e) for e in (res.get('entries') or []) if e and e.get('id')]})
    except Exception as ex:
        return jsonify({"results": [], "error": str(ex)})

@app.route('/api/shorts')
def shorts():
    try:
        with yt_dlp.YoutubeDL(ydl_opts({"extract_flat": "in_playlist", "playlistend": 20})) as ydl:
            res = ydl.extract_info("https://www.youtube.com/shorts", download=False)
            results = [card(e) for e in (res.get('entries') or []) if e and e.get('id')]
            if results: return jsonify({"results": results})
    except: pass
    try:
        with yt_dlp.YoutubeDL(ydl_opts({"extract_flat": "in_playlist"})) as ydl:
            res = ydl.extract_info("ytsearch20:#shorts trending india", download=False)
            return jsonify({"results": [card(e) for e in (res.get('entries') or []) if e and e.get('id')]})
    except Exception as ex:
        return jsonify({"results": [], "error": str(ex)})

@app.route('/api/video')
def video():
    vid = request.args.get('id', '').strip()
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        with yt_dlp.YoutubeDL(ydl_opts({"format": "best/bestvideo+bestaudio", "noplaylist": True})) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            best = None
            fmts = info.get('formats', [])
            for f in reversed(fmts):
                if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none' and f.get('url'):
                    best = f['url']; break
            if not best:
                for f in reversed(fmts):
                    if f.get('acodec') != 'none' and f.get('vcodec') != 'none' and f.get('url'):
                        best = f['url']; break
            if not best and info.get('url'):
                best = info['url']
            if not best:
                for f in fmts:
                    if f.get('url'): best = f['url']; break
            return jsonify({
                "id": info.get("id"),
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "uploader": info.get("uploader"),
                "channel_id": info.get("channel_id"),
                "subscriber_count": info.get("channel_follower_count"),
                "description": (info.get("description") or "")[:800],
                "upload_date": info.get("upload_date"),
                "stream_url": best,
            })
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

@app.route('/api/comments')
def comments():
    vid = request.args.get('id', '').strip()
    if not vid: return jsonify({"comments": []})
    try:
        opts = ydl_opts({"getcomments": True, "extractor_args": {"youtube": {"max_comments": ["20"]}}})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            raw = info.get('comments') or []
            return jsonify({"comments": [{"author": c.get("author",""), "text": c.get("text",""), "likes": c.get("like_count",0)} for c in raw[:20]]})
    except Exception as ex:
        return jsonify({"comments": [], "error": str(ex)})

@app.route('/api/proxy')
def proxy():
    url = request.args.get('url', '')
    if not url: return jsonify({"error": "url required"}), 400
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36',
            'Referer': 'https://www.youtube.com/'
        }
        rng = request.headers.get('Range')
        if rng: headers['Range'] = rng
        r = req.get(url, headers=headers, stream=True, timeout=15)
        def gen():
            for chunk in r.iter_content(8192): yield chunk
        rh = {'Accept-Ranges': 'bytes', 'Content-Type': r.headers.get('Content-Type', 'video/mp4')}
        if 'Content-Length' in r.headers: rh['Content-Length'] = r.headers['Content-Length']
        if 'Content-Range' in r.headers: rh['Content-Range'] = r.headers['Content-Range']
        return Response(gen(), status=r.status_code, headers=rh)
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

@app.route('/api/extract-cookies')
def extract_cookies():
    try:
        import subprocess
        result = subprocess.run(
            ['yt-dlp', '--cookies-from-browser', 'firefox',
             '--skip-download', '--cookies', COOKIES_FILE, 'https://www.youtube.com'],
            capture_output=True, text=True, timeout=30
        )
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'r') as f: c = f.read().strip()
            if c.startswith('# Netscape HTTP Cookie File'):
                return jsonify({"ok": True, "msg": "Cookies extracted!"})
        return jsonify({"ok": False, "msg": result.stderr[:300] or "Failed"})
    except Exception as ex:
        return jsonify({"ok": False, "msg": str(ex)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except:
        ip = '127.0.0.1'
    os.system('clear')
    print("\n")
    print("\033[91m" + "  ██╗      █████╗ ██████╗ ██╗   ██╗███╗   ██╗ ██████╗███████╗██████╗ " + "\033[0m")
    print("\033[94m" + "  ██║     ██╔══██╗██╔══██╗╚██╗ ██╔╝████╗  ██║██╔════╝██╔════╝██╔══██╗" + "\033[0m")
    print("\033[91m" + "  ██║     ███████║██████╔╝ ╚████╔╝ ██╔██╗ ██║██║     █████╗  ██║  ██║" + "\033[0m")
    print("\033[94m" + "  ██║     ██╔══██║██╔══██╗  ╚██╔╝  ██║╚██╗██║██║     ██╔══╝  ██║  ██║" + "\033[0m")
    print("\033[91m" + "  ███████╗██║  ██║██║  ██║   ██║   ██║ ╚████║╚██████╗███████╗██████╔╝" + "\033[0m")
    print("\033[94m" + "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═════╝" + "\033[0m")
    print("\n")
    print("\033[92m" + "  ✦  LARYNCED v3.0  ✦" + "\033[0m")
    print("\033[37m" + f"  http://{ip}:{port}\n" + "\033[0m")
    app.run(host='0.0.0.0', port=port, debug=False)
