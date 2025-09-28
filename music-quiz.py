# --------------------
# music-quiz13.1
# Improved Error Page: Get available device algorithm
# Improved Login Page: Logo integration (cut left-align)
# Minor UI size changes
# --------------------


import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template_string, redirect, url_for, request, session, jsonify
import re
import os
import time
from dotenv import load_dotenv
import json

# Angepasste Importe für die schlanke Farbanalyse
import requests
from io import BytesIO
import colorsys
from PIL import Image # Pillow wird jetzt direkt genutzt

load_dotenv()

# 1. FLASK-ANWENDUNG INITIALISIEREN
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

class FlaskSessionCacheHandler(spotipy.cache_handler.CacheHandler):
    def __init__(self, session_obj):
        self.session = session_obj

    def get_cached_token(self):
        return self.session.get('spotify_token_info')

    def save_token_to_cache(self, token_info):
        self.session['spotify_token_info'] = token_info

scope = "user-read-currently-playing user-modify-playback-state user-read-playback-state"

# --- FARBPALETTEN ---
PALETTES = {
    'album': {
        'name': 'Album-Cover',
        'highlight_color': '#C06EF3',
        'button_hover_color': '#9F47D6',
        'button_text_color': '#FFFFFF'
    },
    'default': {
        'name': 'Lavendel (Standard)',
        'highlight_color': '#C06EF3',
        'button_hover_color': '#9F47D6',
        'button_text_color': '#FFFFFF'
    },
    'emerald_green': {
        'name': 'Smaragd Grün',
        'highlight_color': '#1DB954',
        'button_hover_color': '#1AA34A',
        'button_text_color': '#FFFFFF'
    },
    'ocean_blue': {
        'name': 'Ozeanblau',
        'highlight_color': '#2D8BBA',
        'button_hover_color': '#246D92',
        'button_text_color': '#FFFFFF'
    },
    'butter_yellow': {
        'name': 'Buttergelb',
        'highlight_color': '#f2d34c',
        'button_hover_color': '#efc23b',
        'button_text_color': '#1a1a1a'
    },
    'sunset_orange': {
        'name': 'Sonnenuntergang',
        'highlight_color': '#F56E28',
        'button_hover_color': '#C45820',
        'button_text_color': '#FFFFFF'
    },
    'white': {
        'name': 'Weiß',
        'highlight_color': "#FFFFFF",
        'button_hover_color': "#E6E6E6",
        'button_text_color': '#1a1a1a'
    }
}
# --- ENDE DER FARBPALETTE ---

# --- STATISCHE EINSTELLUNGEN ---
wave_animation_speed = 60
polling_interval_seconds = 3
arrow_size = "60px"
arrow_thickness = 4.5
progress_bar_thickness = 11
album_art_hover_scale = 1.05
arrow_hover_scale = 1.2
button_hover_scale = 1.07
progress_bar_hover_increase_px = 5
icon_svg = 'icon2.svg'
icon_svg_sq = 'icon2-sq.svg'
icon_png = 'icon2.png'
# --- ENDE DER EINSTELLUNGEN ---

TOKEN_INFO_KEY = 'spotify_token_info'

# --- FUNKTIONEN FÜR DIE FARBANALYSE ---

def darken_color(hex_color, amount=0.85):
    try:
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darker_rgb = tuple(int(c * amount) for c in rgb)
        return "#%02x%02x%02x" % darker_rgb
    except:
        return hex_color

def get_text_color_for_bg(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        return '#1a1a1a' if luminance > 150 else '#FFFFFF'
    except:
        return '#FFFFFF'

def analyze_album_art(image_url):
    """
    Analysiert ein Album-Cover mit einer mehrstufigen Logik, 
    um eine ästhetisch ansprechende Akzentfarbe zu finden.
    """
    # 1. Strengere Filter definieren
    MIN_SATURATION = 0.25  # Anforderung für eine "ideale" Akzentfarbe
    MIN_VALUE = 0.5

    MIN_SAT_FALLBACK = 0.2

    
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        with Image.open(BytesIO(response.content)) as img:
            # 1. Bild extrem verkleinern für massive Performance-Steigerung
            img.thumbnail((64, 64))

            # 2. Schnelle Extraktion einer kleinen Farbpalette (8 Farben)
            paletted_img = img.convert("RGB").quantize(colors=64)
            palette = paletted_img.getpalette()

            # Die Palette ist eine flache Liste [R1,G1,B1, R2,G2,B2, ...], wir gruppieren sie
            raw_colors_rgb = [tuple(palette[i:i+3]) for i in range(0, len(palette), 3)]

        candidate_colors = []

        for r, g, b in raw_colors_rgb:

            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)

            # "Ideale" Kandidaten mit strengen Kriterien sammeln
            if s >= MIN_SATURATION and v >= MIN_VALUE:
                score = (s * 1) * (v * 1)
                candidate_colors.append({'rgb': (r, g, b), 'score': score})

        highlight_color = None

        if candidate_colors:
            best_candidate = sorted(candidate_colors, key=lambda x: x['score'], reverse=True)[0]
            r, g, b = best_candidate['rgb']
            highlight_color = f"#{r:02x}{g:02x}{b:02x}"
        elif raw_colors_rgb:
            brightest_color = max(raw_colors_rgb, key=lambda c: (0.299*c[0] + 0.587*c[1] + 0.114*c[2]))
            r, g, b = brightest_color
            highlight_color = f"#{r:02x}{g:02x}{b:02x}"

        if not highlight_color:
            return PALETTES['default']

        return {
            'name': 'Album-Cover',
            'highlight_color': highlight_color,
            'button_hover_color': darken_color(highlight_color),
            'button_text_color': get_text_color_for_bg(highlight_color)
        }

    except Exception as e:
        print(f"Fehler bei der Farbanalyse: {e}")
        return PALETTES['default']

### 🧠 HELFER-FUNKTIONEN FÜR DIE AUTHENTIFIZIERUNG ###

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.environ.get('CLIENT_ID'),
        client_secret=os.environ.get('CLIENT_SECRET'),
        redirect_uri=os.environ.get('REDIRECT_URI'),
        scope=scope,
        cache_handler=FlaskSessionCacheHandler(session)
    )

def get_token():
    token_info = session.get(TOKEN_INFO_KEY, None)
    if not token_info:
        return None

    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session[TOKEN_INFO_KEY] = token_info

    return token_info

def get_spotify_client():
    token_info = get_token()
    if not token_info:
        return None
    return spotipy.Spotify(auth=token_info['access_token'])


### 🚀 ROUTEN ###

@app.route("/login")
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/logout")
def logout():
    session.pop(TOKEN_INFO_KEY, None)
    session.pop('quiz_state', None)
    session.pop('player_mode', None)
    return redirect(url_for('home'))

@app.route("/callback")
def callback():
    sp_oauth = create_spotify_oauth()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)

    session[TOKEN_INFO_KEY] = token_info
    return redirect(url_for('home'))

@app.route("/")
def home():
    sp = get_spotify_client()

    theme_name = session.get('theme', 'default')
    colors = PALETTES.get(theme_name, PALETTES['default']).copy()

    if not sp:
        login_html = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
            <title>Login - Song Quiz</title>
            <style>
                * {{ box-sizing: border-box; }}
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
                    background-color: #121212; 
                    color: #B3B3B3; 
                    display: flex; 
                    flex-direction: column; 
                    align-items: center; 
                    justify-content: flex-start; 
                    min-height: 100vh; 
                    margin: 0; 
                    padding-top: 5vh; 
                    padding-bottom: 5vh;
                }}
                .container {{ 
                    width: calc(100% - 2rem); 
                    max-width: 600px; 
                    padding: 2rem; 
                    border-radius: 12px; 
                    background-color: #1a1a1a; 
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
                    /* --- NEU: Container ist linksbündig --- */
                    text-align: left;
                }}
                .login-icon {{
                    /* Das SVG wird so hoch wie von dir vorgegeben */
                    width: 100%;
                    height: auto;
                    max-height: 150px; /* Begrenzt die Höhe auf großen Bildschirmen */
                    /* Negativer unterer Rand, um den Text näher heranzuholen */
                    margin-bottom: -1rem;
                    margin-top: -1rem;
                    /* Korrigiert die Positionierung für die linksbündige Ausrichtung */
                    margin-left: -2rem; /* Zieht das SVG an den Rand des Containers */
                }}
                h1 {{ 
                    color: #FFFFFF; 
                    font-size: clamp(2rem, 6vw, 2.8rem); /* Etwas grösser für mehr Wirkung */
                    margin-bottom: 1rem; 
                }}
                h2 {{ 
                    color: #B3B3B3; 
                    font-size: clamp(1rem, 3vw, 1.2rem); 
                    margin: 0.5rem 0 2.5rem;
                    font-weight: 400;
                }}
                .center-wrapper {{
                    text-align: center;
                }}
                .button {{ 
                    padding: 12px 24px; 
                    background-color: {colors['highlight_color']}; 
                    color: {colors['button_text_color']}; 
                    text-decoration: none; 
                    border-radius: 50px; 
                    font-weight: bold; 
                    transition: background-color 0.3s, transform 0.3s; 
                    display: inline-block; 
                }}
                .button:hover {{ 
                    background-color: {colors['button_hover_color']}; 
                    transform: scale({button_hover_scale}); 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <img class="login-icon" src="{{{{ url_for('static', filename='icon2-sq-extended-cut.svg') }}}}" alt="Song Quiz Logo">
                <div class="center-wrapper">
                    <h1>Willkommen beim<br>Song Quiz</h1>
                    <h2>Bitte melde dich mit deinem Spotify Konto an,<br>um fortzufahren.</h2>
                    <a href="/login" class="button">Anmelden</a>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(login_html)

    try:
        is_player_mode = session.get('player_mode', False)
        current_track = sp.currently_playing()
        if not current_track or not current_track.get('item'):
            raise ValueError("Kein abspielbarer Song gefunden.")

        album_image_url = "https://via.placeholder.com/300/1a1a1a?text=Error"
        if current_track["item"]["album"]["images"]:
            album_image_url = current_track["item"]["album"]["images"][0]["url"]

        if theme_name == 'album':
            dynamic_palette = analyze_album_art(album_image_url)
            colors.update(dynamic_palette)

        current_track_id = current_track['item']['id']
        quiz_state = session.get('quiz_state', {})

        if current_track_id != quiz_state.get('track_id'):
            quiz_state = {'track_id': current_track_id, 'is_solved': False}
            session['quiz_state'] = quiz_state

        show_solution = is_player_mode or quiz_state.get('is_solved', False)
        progress_ms = current_track.get('progress_ms', 0)
        duration_ms = current_track['item'].get('duration_ms', 0)
        is_playing = current_track.get('is_playing', False)

        display_title = "Welcher Song ist das?"
        display_artist = "Wer ist der Interpret?"
        year_question_html = f'<h3 class="year-question">Aus welchem Jahr?</h3>'
        info_section_html = ""
        button_text = "Auflösen"
        button_link = "/solve"
        player_mode_checked = 'checked' if is_player_mode else ''

        image_html = f"""
        <div class="placeholder-quiz">
            <svg class="quiz-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
        </div>
        """

        track_name_raw = current_track["item"]["name"]
        artists_string = ", ".join([artist["name"] for artist in current_track["item"]["artists"]])
        album_name = current_track["item"]["album"]["name"]
        initial_release_year = int(current_track["item"]["album"]["release_date"].split('-')[0])

        if show_solution:
            display_title = track_name_raw
            display_artist = artists_string
            year_question_html = ""
            button_text = "Nächstes Lied"
            button_link = "/next"
            image_html = f'<img class="album-art" src="{album_image_url}" alt="Album Cover">'

            original_release_year = initial_release_year
            original_album_name = album_name

            terms_to_remove = [
                r"\s*-\s*\d{4}\s*Remastered.*", r"\s*-\s*Remastered.*",
                r"\s*-\s*\d{4}\s*Remaster.*", r"\s*-\s*Remaster.*",
                r"\(Remastered\)", r"\[Remastered\]",
                r"\(Remaster\)", r"\[Remaster\]",
                r"\s+-\s*Live.*", r"\(Live\)", r"\[Live\]",
                r"\s*-\s*Edit.*", r"\(Edit\)",
                r"\s*-\s*Single.*",  r"\(Single Version\)",
                r"\s*-\s*Mono.*", r"\(Mono Version\)",
                r"\s*-\s*Stereo.*", r"\(Stereo Version\)",
                r"\s*-\s*Original.*", r"\(Original Version\)", r"\(Original\)",
                r"\s*-\s*Radio.*", r"\(Radio Version\)", r"\(Radio\)"
            ]

            cleaned_track_name = track_name_raw
            for pattern in terms_to_remove:
                cleaned_track_name = re.sub(pattern, "", cleaned_track_name, flags=re.IGNORECASE).strip()

            original_artist_names = [artist["name"].lower() for artist in current_track["item"]["artists"]]

            results = sp.search(q=f"track:{cleaned_track_name} artist:{artists_string}", type="track", limit=50)
            for result in results['tracks']['items']:
                try:
                    result_track_name_raw = result['name']
                    cleaned_result_track_name = result_track_name_raw
                    for pattern in terms_to_remove:
                        cleaned_result_track_name = re.sub(pattern, "", cleaned_result_track_name, flags=re.IGNORECASE).strip()

                    if cleaned_track_name.lower() == cleaned_result_track_name.lower():
                        result_artist_names = [artist["name"].lower() for artist in result["artists"]]
                        if any(artist_name in result_artist_names for artist_name in original_artist_names):
                            result_year = int(result['album']['release_date'].split('-')[0])
                            if result_year < original_release_year:
                                original_release_year = result_year
                                original_album_name = result['album']['name']
                except (KeyError, ValueError):
                    continue

            initial_year_html = ""
            original_info_html = ""
            prominent_year_html = f'<p class="prominent-year">{initial_release_year}</p>'
            if original_release_year < initial_release_year:
                prominent_year_html = f'<p class="prominent-year">{original_release_year}</p>'
                initial_year_html = f'<p><strong>Veröffentlichungsjahr:</strong> {initial_release_year}</p>'
                original_info_html = f"""<div class="info-box"><h3>Originalversion</h3><p><strong>Original-Titel für Suche:</strong> {cleaned_track_name}</p><p><strong>Original-Album:</strong> {original_album_name}</p></div>"""

            info_section_html = f"""
            <div class="info-section">
                <hr class="info-divider">
                <div class="info-box">
                    <p><strong>Album:</strong> {album_name}</p>
                    {initial_year_html}
                </div>
                {original_info_html}
                {prominent_year_html}
            </div>
            """

        temp_palettes = PALETTES.copy()
        if theme_name == 'album':
            temp_palettes['album'] = colors

        options_html = ""
        album_theme_active_class = "album-theme-active" if theme_name == 'album' else ""
        main_dot_style = f"background-color: {colors['highlight_color']};" if theme_name != 'album' else ""

        for key, palette in temp_palettes.items():
            album_dot_class = "album-theme-active" if key == 'album' else ""
            dot_style = f'background-color: {palette["highlight_color"]};' if key != 'album' else ''
            options_html += f'<a href="/set-theme/{key}" class="theme-dot {album_dot_class}" style="{dot_style}" title="{palette["name"]}"></a>'

        theme_selector_html = f"""
        <div class="theme-picker">
            <div id="theme-picker-toggle" class="theme-dot main-dot {album_theme_active_class}" style="{main_dot_style}" title="Farbe ändern"></div>
            <div id="theme-options" class="theme-options-container">
                {options_html}
            </div>
        </div>
        """

        html_content = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">

        <link rel="icon" href="{{{{ url_for('static', filename='{icon_svg}') }}}}" type="image/svg+xml">
        <link rel="apple-touch-icon" href="{{{{ url_for('static', filename='{icon_png}') }}}}">

        <title>Song Quiz</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #121212; color: #B3B3B3; display: flex; flex-direction: column; align-items: center;justify-content: flex-start;min-height: 100vh; margin: 0; text-align: center;padding-top: 5vh;padding-bottom: 5vh;}}
            .container {{ width: calc(100% - 2rem); max-width: 600px; padding: 2rem; border-radius: 12px; background-color: #1a1a1a; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); }}
            .album-art-container {{ display: flex; align-items: center; justify-content: center; gap: 20px; width: 100%; max-width: 450px; margin: 0 auto 1.5rem; }}
            .album-art-link {{ flex: 1 1 0; min-width: 0; display: flex; justify-content: center; transition: transform 0.3s ease; }}
            .album-art-link:hover {{ transform: scale({album_art_hover_scale}); }}
            .album-art, .placeholder-quiz {{ width: 100%; max-width: 300px; height: auto; aspect-ratio: 1 / 1; border-radius: 8px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3); }}
            .placeholder-quiz {{ display: flex; align-items: center; justify-content: center; background-color: #282828; }}
            .quiz-icon {{ width: 60%; height: auto; stroke: {colors['highlight_color']}; transition: stroke 0.2s ease-in-out; }}
            .album-art-link:hover .quiz-icon {{ stroke: {colors['button_hover_color']}; }}
            .control-arrow svg {{ width: {arrow_size}; height: {arrow_size}; stroke: {colors['highlight_color']}; stroke-width: {arrow_thickness}; transition: transform 0.3s ease, stroke 0.3s ease; }}
            .control-arrow:hover svg {{ stroke: {colors['button_hover_color']}; transform: scale({arrow_hover_scale}); }}
            h1 {{ color: #FFFFFF; font-size: clamp(1.5rem, 6vw, 2.5rem); margin-bottom: 0.5rem; min-height: 1.2em; }}
            h2 {{ color: #B3B3B3; font-size: clamp(1rem, 3vw, 1.2rem); margin: 0.5rem 0 1.5rem; min-height: 1.2em; }}
            .year-question {{ color: {colors['highlight_color']}; font-size: clamp(1.1rem, 4vw, 1.4rem); font-weight: bold; margin-top: 2rem; margin-bottom: 1.5rem;}}
            .info-section {{ width: 100%; text-align: center; }}
            .info-box strong {{ color: #FFFFFF; }}
            .info-box h3 {{ color: #FFFFFF; margin-top: 1.5rem; margin-bottom: 0.5rem;}}
            .info-divider {{ margin: 2rem 0; border: 0; border-top: 1px solid #333; }}
            .button-container {{ display: flex; justify-content: center; align-items: center; gap: 15px; flex-wrap: wrap; }}
            .button {{ padding: 12px 24px; background-color: {colors['highlight_color']}; color: {colors['button_text_color']}; text-decoration: none; border-radius: 50px; font-weight: bold; margin-top: 20px; display: inline-block; transition: background-color 0.3s, transform 0.3s ease; }}
            .button:hover {{ background-color: {colors['button_hover_color']}; transform: scale({button_hover_scale}); }}
            .prominent-year {{ font-size: clamp(3rem, 12vw, 4rem); font-weight: bold; color: {colors['highlight_color']}; margin: 1rem 0; }}
            .progress-svg-container {{ width: 80%; max-width: 350px; margin: 20px auto 0; }}
            .progress-interactive-area {{ width: 80%; margin: 0 auto; height: 14px; cursor: pointer; }}
            .progress-interactive-area svg {{ width: 100%; height: 100%; overflow: visible; }}
            #progressTrack, #progressFill {{ fill: none; stroke-width: {progress_bar_thickness}; stroke-linecap: round; stroke-linejoin: round; transition: stroke-width 0.2s ease, stroke 0.2s ease; }}
            #progressTrack {{ stroke: #444; }}
            #progressFill {{ stroke: {colors['highlight_color']}; }}
            .progress-interactive-area:hover #progressFill, .progress-interactive-area:hover #progressTrack {{ stroke-width: {progress_bar_thickness + progress_bar_hover_increase_px}; }}
            .progress-interactive-area:hover #progressFill {{ stroke: {colors['button_hover_color']}; }}
            .player-mode-toggle {{ margin-top: 30px; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; gap: 10px; }}
            .toggle-label {{ font-size: 0.9rem; color: #B3B3B3; }}
            .controls-cluster {{ display: flex; align-items: center; justify-content: center; gap: 18px; }}
            .switch {{ position: relative; display: inline-block; width: 50px; height: 28px; }}
            .switch input {{ opacity: 0; width: 0; height: 0; }}
            .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #444; transition: .4s; border-radius: 28px; }}
            .slider:before {{ position: absolute; content: ""; height: 22px; width: 22px; left: 3px; bottom: 3px; background-color: #1a1a1a; transition: .4s; border-radius: 50%; }}
            input:checked + .slider {{ background-color: {colors['highlight_color']}; }}
            input:checked + .slider:before {{ transform: translateX(22px); }}
            .random-song-button {{ display: flex; align-items: center; justify-content: center; width: 34px; height: 34px; background-color: #333; border-radius: 50%; transition: background-color 0.3s ease; }}
            .random-song-button svg {{ width: 18px; height: 18px; stroke: #B3B3B3; transition: stroke 0.3s ease; }}
            .random-song-button:hover {{ background-color: {colors['highlight_color']}; }}
            .random-song-button:hover svg {{ stroke: {colors['button_text_color']}; }}
            .theme-picker {{ position: relative; display: flex; }}
            .theme-options-container {{ position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); display: flex; gap: 12px; padding: 10px; background-color: #282828; border-radius: 50px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); opacity: 0; visibility: hidden; transform: translate(-50%, 10px); transition: opacity 0.3s ease, transform 0.3s ease, visibility 0.3s; }}
            .theme-options-container.active {{ opacity: 1; visibility: visible; transform: translate(-50%, 0); }}
            .theme-dot {{ width: 24px; height: 24px; border-radius: 50%; border: 2px solid #555; transition: transform 0.2s, background 0.3s; display: block; cursor: pointer; }}
            .theme-dot:hover {{ transform: scale(1.2); }}
            .main-dot {{ width: 30px; height: 30px; border-color: #888; }}

            .album-theme-active {{
                background: linear-gradient(135deg,rgba(246, 255, 0, 1) 10%, rgba(255, 199, 0, 1) 18%, rgba(255, 117, 0, 1) 24%, rgba(255, 0, 0, 1) 35%, rgba(218, 0, 255, 1) 47%, rgba(117, 82, 255, 1) 60%, rgba(0, 178, 255, 1) 71%, rgba(0, 255, 133, 1) 83%, rgba(246, 255, 0, 1) 100%);
            }}

        </style>
        </head>
        <body>
        <div class="container">
            <div class="album-art-container">
                <a href="/previous" class="control-arrow"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg></a>
                <a href="/play_pause" class="album-art-link">{image_html}</a>
                <a href="/next" class="control-arrow"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></a>
            </div>
            <div class="progress-svg-container"><div class="progress-interactive-area"><svg viewBox="0 0 300 14"><path id="progressTrack" d=""></path><path id="progressFill" d=""></path></svg></div></div>
            <h1>{display_title}</h1><h2>{display_artist}</h2>{year_question_html}{info_section_html}
            <div class="button-container">
                <a href="{button_link}" class="button">{button_text}</a>
            </div>
            <div class="player-mode-toggle">
                <label for="playerMode" class="toggle-label">Player-Modus</label>
                <div class="controls-cluster">
                    {theme_selector_html}
                    <label class="switch">
                        <input type="checkbox" id="playerMode" name="playerMode" {player_mode_checked}>
                        <span class="slider"></span>
                    </label>
                    <a href="/play_random" class="random-song-button" title="Zufälliger Song aus Playlist">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                            <circle cx="8.5" cy="8.5" r="0.5" fill="currentColor"></circle>
                            <circle cx="15.5" cy="15.5" r="0.5" fill="currentColor"></circle>
                            <circle cx="15.5" cy="8.5" r="0.5" fill="currentColor"></circle>
                            <circle cx="8.5" cy="15.5" r="0.5" fill="currentColor"></circle>
                            <circle cx="12" cy="12" r="0.5" fill="currentColor"></circle>
                        </svg>
                    </a>
                </div>
            </div>
            <a href="/logout" style="font-size: 0.8rem; color: #888; margin-top: 10px; display:inline-block;">Logout</a>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const progressTrack = document.getElementById('progressTrack'); const progressFill = document.getElementById('progressFill'); const interactiveArea = document.querySelector('.progress-interactive-area'); const svgWidth = 300; const svgHeight = 14; const midHeight = svgHeight / 2; const amplitude = 6; const frequency = 0.05; const segments = 150; const waveSpeed = {wave_animation_speed};
                let initialTrackId = '{current_track_id}'; const pollingInterval = {polling_interval_seconds} * 1000;
                if (initialTrackId === 'None') {{ initialTrackId = null; }}
                let currentProgress = {progress_ms}; const totalDuration = {duration_ms}; const isPlaying = {str(is_playing).lower()};
                let animationFrameId = null; let animationStartTime = performance.now();
                function generateWavePath(phase) {{ let path = `M 0 ${{midHeight}}`; for (let i = 0; i <= segments; i++) {{ const x = (i / segments) * svgWidth; const fadeWidth = svgWidth * 0.1; let currentAmplitude = amplitude; if (x < fadeWidth) {{ currentAmplitude = amplitude * Math.sin((x / fadeWidth) * (Math.PI / 2)); }} else if (x > svgWidth - fadeWidth) {{ currentAmplitude = amplitude * Math.sin(((svgWidth - x) / fadeWidth) * (Math.PI / 2)); }} const y = midHeight + Math.sin(x * frequency + phase) * currentAmplitude; path += ` L ${{x.toFixed(3)}} ${{y.toFixed(3)}}`; }} return path; }}
                function updateProgressBar(progress) {{ if (totalDuration > 0) {{ const progressRatio = Math.min(progress / totalDuration, 1); const dynamicPhase = progressRatio * Math.PI * waveSpeed; const wavePath = generateWavePath(dynamicPhase); progressTrack.setAttribute('d', wavePath); progressFill.setAttribute('d', wavePath); const totalLength = progressFill.getTotalLength(); if (totalLength > 0) {{ progressFill.style.strokeDasharray = totalLength; progressFill.style.strokeDashoffset = totalLength * (1 - progressRatio); }} }} }}
                function animate(currentTime) {{ const elapsedTime = currentTime - animationStartTime; const newProgress = currentProgress + elapsedTime; updateProgressBar(newProgress); if (newProgress < totalDuration) {{ animationFrameId = requestAnimationFrame(animate); }} }}
                function startAnimation() {{ if (isPlaying) {{ animationStartTime = performance.now(); animationFrameId = requestAnimationFrame(animate); }} }}
                function stopAnimation() {{ if (animationFrameId) {{ cancelAnimationFrame(animationFrameId); animationFrameId = null; }} }}
                updateProgressBar(currentProgress); startAnimation();
                interactiveArea.addEventListener('click', function(event) {{ if (totalDuration > 0) {{ stopAnimation(); const rect = interactiveArea.getBoundingClientRect(); const clickX = event.clientX - rect.left; const clickPercentage = Math.max(0, Math.min(1, clickX / rect.width)); const seekPositionMs = Math.round(clickPercentage * totalDuration); currentProgress = seekPositionMs; updateProgressBar(currentProgress); startAnimation(); fetch('/seek', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ position_ms: seekPositionMs }}) }}).catch(error => console.error('Error seeking track:', error)); }} }});
                setInterval(function() {{ fetch('/check-song').then(response => response.ok ? response.json() : Promise.reject('Network response was not ok')).then(data => {{ if (data && data.track_id !== initialTrackId) {{ window.location.reload(); }} }}).catch(error => console.error('Error during polling:', error)); }}, pollingInterval);
                const playerModeToggle = document.getElementById('playerMode');
                if (playerModeToggle) {{ playerModeToggle.addEventListener('change', function() {{ const isEnabled = this.checked; fetch('/toggle-player-mode', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ playerMode: isEnabled }}) }}).then(response => response.ok ? response.json() : Promise.reject('Failed to toggle mode')).then(data => {{ if (data.success) {{ window.location.reload(); }} }}).catch(error => console.error('Error:', error)); }}); }}
                const themePickerToggle = document.getElementById('theme-picker-toggle');
                const themeOptions = document.getElementById('theme-options');
                if (themePickerToggle && themeOptions) {{
                    themePickerToggle.addEventListener('click', function(event) {{
                        event.stopPropagation();
                        themeOptions.classList.toggle('active');
                    }});
                    document.addEventListener('click', function() {{
                        if (themeOptions.classList.contains('active')) {{
                            themeOptions.classList.remove('active');
                        }}
                    }});
                }}
            }});
        </script>
        </body>
        </html>
        """

        return render_template_string(html_content)

    except Exception as e:
        theme_name = session.get('theme', 'default')
        colors = PALETTES.get(theme_name, PALETTES['default'])
        
        # NEUE, VERBESSERTE FEHLERSEITE
        image_html_error = f"""
        <div class="placeholder-quiz">
            <svg class="quiz-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polygon points="10 8 16 12 10 16 10 8"></polygon>
            </svg>
        </div>
        """
        
        error_html = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
            <title>Fehler - Song Quiz</title>
            <style>
                * {{ box-sizing: border-box; }}
                body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #121212; color: #B3B3B3; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; min-height: 100vh; margin: 0; text-align: center; padding-top: 5vh; padding-bottom: 5vh; }}
                .container {{ width: calc(100% - 2rem); max-width: 600px; padding: 2rem; border-radius: 12px; background-color: #1a1a1a; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); }}
                .album-art-container {{ display: flex; align-items: center; justify-content: center; gap: 20px; width: 100%; max-width: 450px; margin: 0 auto 1.5rem; }}
                .album-art-link {{ flex: 1 1 0; min-width: 0; display: flex; justify-content: center; transition: transform 0.3s ease; }}
                .album-art-link:hover {{ transform: scale({album_art_hover_scale}); }}
                .placeholder-quiz {{ width: 100%; max-width: 300px; height: auto; aspect-ratio: 1 / 1; border-radius: 8px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3); display: flex; align-items: center; justify-content: center; background-color: #282828; }}
                .quiz-icon {{ width: 50%; height: auto; stroke: {colors['highlight_color']}; transition: stroke 0.2s ease-in-out; }}
                 .album-art-link:hover .quiz-icon {{ stroke: {colors['button_hover_color']}; }}
                .control-arrow svg {{ width: {arrow_size}; height: {arrow_size}; stroke: {colors['highlight_color']}; stroke-width: {arrow_thickness}; transition: transform 0.3s ease, stroke 0.3s ease; }}
                .control-arrow:hover svg {{ stroke: {colors['button_hover_color']}; transform: scale({arrow_hover_scale}); }}
                h1 {{ color: #FFFFFF; font-size: clamp(1.5rem, 6vw, 2.5rem); margin-bottom: 0.5rem; }}
                h2 {{ color: #B3B3B3; font-size: clamp(1rem, 3vw, 1.2rem); margin: 0.5rem 0 1.5rem; font-weight: 400; line-height: 1.6; }}
                .button {{ padding: 12px 24px; background-color: {colors['highlight_color']}; color: {colors['button_text_color']}; text-decoration: none; border-radius: 50px; font-weight: bold; margin-top: 20px; display: inline-block; transition: background-color 0.3s, transform 0.3s ease; }}
                .button:hover {{ background-color: {colors['button_hover_color']}; transform: scale({button_hover_scale}); }}
                .error-details {{ margin-top: 2rem; font-size: 0.8rem; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="album-art-container">
                    <a href="/previous" class="control-arrow"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg></a>
                    <a href="/play_pause" class="album-art-link">{image_html_error}</a>
                    <a href="/next" class="control-arrow"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></a>
                </div>
                <h1>Fehler oder kein Song aktiv</h1>
                <h2>Bitte starte die Wiedergabe auf einem deiner Geräte. Du kannst dafür auch auf den Play-Button oben klicken.</h2>
                <a href="/" class="button">Aktualisieren</a>
                <p class="error-details"><small>Details: {e}</small></p>
                <a href="/logout" style="font-size: 0.8rem; color: #888; margin-top: 20px; display:inline-block;">Logout</a>
            </div>
        </body>
        </html>
        """
        return render_template_string(error_html)


@app.route("/check-song")
def check_song():
    sp = get_spotify_client()
    if not sp: return jsonify({'track_id': None})
    try:
        current_track = sp.currently_playing()
        track_id = current_track['item']['id'] if current_track and current_track.get('item') else None
        return jsonify({'track_id': track_id})
    except Exception:
        return jsonify({'track_id': None})

@app.route('/seek', methods=['POST'])
def seek():
    sp = get_spotify_client()
    if not sp: return jsonify({'success': False, 'error': 'Not logged in'})
    try:
        data = request.get_json()
        position_ms = data.get('position_ms')
        if isinstance(position_ms, int):
            sp.seek_track(position_ms)
            time.sleep(0.2)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid position'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/toggle-player-mode', methods=['POST'])
def toggle_player_mode():
    try:
        data = request.get_json()
        session['player_mode'] = data.get('playerMode', False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/solve")
def solve():
    if 'quiz_state' in session:
        quiz_state = session['quiz_state']
        quiz_state['is_solved'] = True
        session['quiz_state'] = quiz_state
    return redirect(url_for('home'))

@app.route("/play_pause")
def play_pause():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for('home'))
    try:
        current_track = sp.currently_playing()
        if current_track and current_track.get('is_playing'):
            sp.pause_playback()
            print("Playback paused.")
        else:
            sp.start_playback()
            print("Playback started.")
    except spotipy.exceptions.SpotifyException as e:
        if "No active device found" in str(e) or "Player command failed" in str(e):
            print("No active device found. Searching for an available one.")
            try:
                # KORREKTUR: Wir holen die Liste mit .get('devices', []) sicher aus dem Container-Objekt.
                device_list = sp.devices().get('devices', [])
                if device_list:
                    # DEINE PRIORITÄTENLISTE
                    priorities = {'Smartphone': 1, 'Computer': 2, 'Speaker': 3}

                    # Wir sortieren nun die device_list, was eine echte Liste von Geräten ist.
                    sorted_devices = sorted(device_list, key=lambda d: priorities.get(d['type'], 99))
                    
                    # --- FÜGE DIESEN DEBUG-BLOCK EIN ---
                    print("--- Sortierte Geräteliste (Priorität: Smartphone > Computer > Speaker) ---")
                    for i, device in enumerate(sorted_devices):
                        print(f"  {i+1}. Name: {device.get('name', 'N/A')}, Typ: {device.get('type', 'N/A')}")
                    print("--------------------------------------------------------------------")
                    # --- ENDE DEBUG-BLOCK ---


                    best_device = sorted_devices[0]
                    best_device_id = best_device['id']
                    print(f"No active device. Activating best-choice device: {best_device['name']} ({best_device['type']})")
                    sp.start_playback(device_id=best_device_id)
                else:
                    print("No available devices found for user.")
            except Exception as device_error:
                print(f"Error while trying to activate a device: {device_error}")
        else:
            print(f"An unexpected Spotify API error occurred: {e}")
    except Exception as e:
        print(f"A general error occurred in play_pause: {e}")
    
    time.sleep(0.5)
    return redirect(url_for('home'))

@app.route("/next")
def next_track():
    sp = get_spotify_client()
    if not sp: return redirect(url_for('home'))
    try:
        sp.next_track()
        session.pop('quiz_state', None)
        time.sleep(0.5)
    except Exception:
        pass
    return redirect(url_for('home'))

@app.route("/previous")
def previous_track():
    sp = get_spotify_client()
    if not sp: return redirect(url_for('home'))
    try:
        sp.previous_track()
        session.pop('quiz_state', None)
        time.sleep(0.5)
    except Exception:
        pass
    return redirect(url_for('home'))

# NEUE ROUTE FÜR ZUFÄLLIGEN SONG AUS PLAYLIST
@app.route("/play_random")
def play_random():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for('home'))

    playlist_uri = "spotify:playlist:76urfTElnBTZh1HXxDckec"

    try:
        # 1. Shuffle-Modus aktivieren
        sp.shuffle(True)
        # 2. Wiedergabe der Playlist starten (Spotify wählt durch Shuffle einen zufälligen Startpunkt)
        sp.start_playback(context_uri=playlist_uri)
        # Kurze Pause, damit der neue Song geladen werden kann, bevor die Seite neu lädt
        time.sleep(0.7)
    except spotipy.exceptions.SpotifyException as e:
        # Fehlerbehandlung, falls z.B. kein aktives Gerät gefunden wird
        print(f"Spotify API Fehler: {e}")
        # Optional: Eine Fehlermeldung an den User weiterleiten
        pass
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        pass

    return redirect(url_for('home'))

@app.route("/set-theme/<theme_name>")
def set_theme(theme_name):
    """Speichert die vom Nutzer gewählte Farbpalette in der Session."""
    if theme_name in PALETTES:
        session['theme'] = theme_name
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
