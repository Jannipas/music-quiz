# --------------------
# music-quiz15.5
# 
# Last Version: music-quiz15.4
#   Funktion find_original_release_info() komplett überarbeitet
#   Aggressives Title cleaning etwas geschwächt
#
# New Changes:
#   find_original_release_info(): Einzelne Query Abfragen für jeden Artist anstatt eine Abfrage für alle Artist
#   terms_to_remove(): Neue Regex Patterns hinzugefügt, um Titelbereinigung zu verbessern
#   Grau etwas heller gemacht
#   Rotes Theme hinzugefügt
# --------------------

import os
import time
import re
from io import BytesIO
import colorsys
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from dotenv import load_dotenv
from PIL import Image
import requests
import json

load_dotenv()

# --- FLASK-ANWENDUNG INITIALISIEREN ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# --- SPOTIPY CACHE HANDLER FÜR FLASK SESSION ---
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
    'album': {'name': 'Album-Cover'},
    'default': {'name': 'Lavendel (Standard)',      'highlight_color': '#C06EF3', 'button_hover_color': '#9F47D6', 'button_text_color': '#FFFFFF'},
    'emerald_green': {'name': 'Smaragd Grün',       'highlight_color': '#1DB954', 'button_hover_color': '#1AA34A', 'button_text_color': '#FFFFFF'},
    'ocean_blue': {'name': 'Ozeanblau',             'highlight_color': '#2D8BBA', 'button_hover_color': '#246D92', 'button_text_color': '#FFFFFF'},
    'butter_yellow': {'name': 'Buttergelb',         'highlight_color': '#f2d34c', 'button_hover_color': '#efc23b', 'button_text_color': '#1d1d1d'},
    'sunset_orange': {'name': 'Sonnenuntergang',    'highlight_color': '#F56E28', 'button_hover_color': '#C45820', 'button_text_color': '#FFFFFF'},
    'ruby_red': {'name': 'Rubinrot',                'highlight_color': '#FF0000', 'button_hover_color': '#CC0000', 'button_text_color': '#FFFFFF'},
    'white': {'name': 'Weiß',                       'highlight_color': "#FFFFFF", 'button_hover_color': "#E6E6E6", 'button_text_color': '#1d1d1d'}
}

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
icon_png = 'icon2.png'
TOKEN_INFO_KEY = 'spotify_token_info'



# --- FUNKTIONEN FÜR DIE AUTHENTIFIZIERUNG ---
def create_spotify_oauth():
    return SpotifyOAuth(client_id=os.environ.get('CLIENT_ID'), client_secret=os.environ.get('CLIENT_SECRET'), redirect_uri=os.environ.get('REDIRECT_URI'), scope=scope, cache_handler=FlaskSessionCacheHandler(session))

def get_spotify_client():
    token_info = session.get(TOKEN_INFO_KEY)
    if not token_info: return None
    if token_info['expires_at'] - int(time.time()) < 60:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    session[TOKEN_INFO_KEY] = token_info
    return spotipy.Spotify(auth=token_info['access_token'])

# --- FUNKTIONEN FÜR DIE FARBANALYSE ---
def darken_color(hex_color, amount=0.85):
    try:
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darker_rgb = tuple(int(c * amount) for c in rgb)
        return f"#{darker_rgb[0]:02x}{darker_rgb[1]:02x}{darker_rgb[2]:02x}"
    except Exception:
        return hex_color

def get_text_color_for_bg(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        return '#1d1d1d' if luminance > 150 else '#FFFFFF'
    except Exception:
        return '#FFFFFF'

def analyze_album_art(image_url):
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        with Image.open(BytesIO(response.content)) as img:
            img.thumbnail((64, 64))
            paletted_img = img.convert("RGB").quantize(colors=64)
            palette = paletted_img.getpalette()
            raw_colors_rgb = [tuple(palette[i:i+3]) for i in range(0, len(palette), 3)]

        candidate_colors = []
        for r, g, b in raw_colors_rgb:
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            if s >= 0.25 and v >= 0.5:
                score = s * v
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

        if not highlight_color: return PALETTES['default']
        return {'name': 'Album-Cover', 'highlight_color': highlight_color, 'button_hover_color': darken_color(highlight_color), 'button_text_color': get_text_color_for_bg(highlight_color)}
    except Exception as e:
        print(f"Fehler bei der Farbanalyse: {e}")
        return PALETTES['default']

# --- HTML FÜR THEME-PICKER ERSTELLEN ---
def generate_theme_selector_html(theme_name, colors):
    temp_palettes = PALETTES.copy()
    if theme_name == 'album':
        temp_palettes['album'] = colors
    
    options_html = ""
    for key, palette in temp_palettes.items():
        album_dot_class = "album-theme-active" if key == 'album' else ""
        dot_style = f'background-color: {palette["highlight_color"]};' if key != 'album' else ''
        options_html += f'<a href="/set-theme/{key}" class="theme-dot {album_dot_class}" style="{dot_style}" title="{palette["name"]}"></a>'

    main_dot_style = f"background-color: {colors['highlight_color']};" if theme_name != 'album' else ""
    
    return f"""
    <div class="theme-picker">
        <div id="theme-picker-toggle" class="theme-dot main-dot {'album-theme-active' if theme_name == 'album' else ''}" style="{main_dot_style}" title="Farbe ändern"></div>
        <div id="theme-options" class="theme-options-container">{options_html}</div>
    </div>"""

# --- FUNKTION ZUR TITEL BEREINIGUNG ---
def clean_title(title):

    terms_to_remove = [
        r"'", r"’", r"`", r"\"", r",", r"\s*-\s*\d{4}",
        r"\s*\(.*?Remastered.*?\)", r"\s*\(.*?Remaster.*?\)",
        r"\s*\(.*?Live.*?\)", r"\s*\(.*?Edit.*?\)", r"\s*\(.*?Single.*?\)", r"\s*\(.*?Mono.*?\)", r"\s*\(.*?From.*?\)",
        r"\s*\(.*?Stereo.*?\)", r"\s*\(.*?Original.*?\)", r"\s*\(.*?Radio.*?\)", r"\s*\(.*?Mix.*?\)", r"\s*\(.*?Version.*?\)",
        r"\s*\[.*?Remastered.*?\]", r"\s*\[.*?Remaster.*?\]",
        r"\s*\[.*?Live.*?\]", r"\s*\[.*?Edit.*?\]", r"\s*\[.*?Single.*?\]", r"\s*\[.*?Mono.*?\]", r"\s*\[.*?From.*?\]",
        r"\s*\[.*?Stereo.*?\]", r"\s*\[.*?Original.*?\]", r"\s*\[.*?Radio.*?\]", r"\s*\[.*?Mix.*?\]", r"\s*\[.*?Version.*?\]",
        r"\s*-.*?Remastered.*", r"\s*-.*?Remaster.*",
        r"\s+-.*?Live.*", r"\s*-.*?Edit.*", r"\s*-.*?Single.*", r"\s*-.*?Mono.*", r"\s*-.*?From.*",
        r"\s*-.*?Stereo.*", r"\s*-.*?Original.*", r"\s*-.*?Radio.*", r"\s*-.*?Mix.*", r"\s*-.*?Version.*"
    ]
    
    for pattern in terms_to_remove:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE).strip()
    return title

# --- ORIGINAL-RELEASE-JAHR FINDEN ---
def find_original_release_info(sp, item):
    track_name_raw = item["name"]
    # artists_string = ", ".join([artist["name"] for artist in item["artists"]])
    initial_release_year = int(item["album"]["release_date"].split('-')[0])
    
    cleaned_original_track_name = clean_title(track_name_raw)
    original_artist_names_lower = [artist["name"].lower() for artist in item["artists"]]
    
    candidate_list = []

    try:
        
        artist_list = [artist["name"] for artist in item["artists"]]
        all_search_items = []

        for artist in artist_list:
            search_query = f'track:"{cleaned_original_track_name}" artist:"{artist}"'
            results = sp.search(q=search_query, type="track", limit=50)
            all_search_items.extend(results['tracks']['items'])
        
        for result in all_search_items:
            try:

                result_artist_names_lower = [artist["name"].lower() for artist in result["artists"]]
                if not any(artist_name in result_artist_names_lower for artist_name in original_artist_names_lower):
                    continue

        
                cleaned_result_track_name = clean_title(result['name'])
                if cleaned_original_track_name.lower() == cleaned_result_track_name.lower():
                    candidate = {
                        'year': int(result['album']['release_date'].split('-')[0]),
                        'album_name': result['album']['name'],
                       'album_type': result['album']['album_type']
                    }
                    
                    if candidate['album_type'] in ['album', 'single']:
                        candidate_list.append(candidate)

            except (KeyError, ValueError, IndexError):
                continue
        

        if candidate_list:
            # print("--- DEBUG-AUSGABE: Inhalt von candidate_list ---")
            # print(json.dumps(candidate_list, indent=2))
            # print("--------------------------------------------")

            best_match = min(candidate_list, key=lambda c: c['year'])
            # print("--- DEBUG-AUSGABE: Inhalt von best_match ---")
            # print(json.dumps(best_match, indent=2))
            # print("--------------------------------------------")

            return {
                'year': best_match['year'],
                'album_name': best_match['album_name'],
                'cleaned_track_name': cleaned_original_track_name
            }

    except Exception as e:
        print(f"Fehler bei der Spotify-Suche für das Originaljahr: {e}")

    # Notfall
    print("No Candidates")
    return {
        'year': initial_release_year,
        'album_name': item["album"]["name"],
        'cleaned_track_name': cleaned_original_track_name
    }


# --- HAUPT-ROUTEN ---
@app.route("/login")
def login():
    return redirect(create_spotify_oauth().get_authorize_url())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/callback")
def callback():
    sp_oauth = create_spotify_oauth()
    session[TOKEN_INFO_KEY] = sp_oauth.get_access_token(request.args.get('code'))
    return redirect(url_for('home'))

@app.route("/")
def home():
    sp = get_spotify_client()
    theme_name = session.get('theme', 'default')
    colors = PALETTES.get(theme_name, PALETTES['default']).copy()

    if not sp:
        return render_template('login.html', colors=colors, button_hover_scale=button_hover_scale)

    try:
        current_track = sp.currently_playing()
        
        if not current_track or not current_track.get('item'):
            image_html_error = """
            <div class="placeholder-quiz">
                <svg class="quiz-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle><polygon points="10 8 16 12 10 16 10 8"></polygon>
                </svg>
            </div>"""
            return render_template('error.html', e="Kein Song aktiv.", colors=PALETTES['default'], image_html_error=image_html_error, album_art_hover_scale=album_art_hover_scale, arrow_hover_scale=arrow_hover_scale, button_hover_scale=button_hover_scale, arrow_size=arrow_size, arrow_thickness=arrow_thickness)

        item = current_track['item']
        album_image_url = item['album']['images'][0]['url'] if item['album']['images'] else ""
        if theme_name == 'album':
            colors.update(analyze_album_art(album_image_url))
        
        current_track_id = item['id']
        quiz_state = session.get('quiz_state', {})
        if current_track_id != quiz_state.get('track_id'):
            quiz_state = {'track_id': current_track_id, 'is_solved': False}
            session['quiz_state'] = quiz_state

        is_player_mode = session.get('player_mode', False)
        show_solution = is_player_mode or quiz_state.get('is_solved', False)

        display_title = "Welcher Song ist das?"
        display_artist = "Wer ist der Interpret?"
        year_question_html = '<h3 class="year-question">Aus welchem Jahr?</h3>'
        info_section_html = ""
        button_text = "Auflösen"
        button_link = "/solve"
        image_html = """
        <div class="placeholder-quiz">
            <svg class="quiz-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
        </div>"""

        if show_solution:
            display_title = item["name"]
            display_artist = ", ".join([artist["name"] for artist in item["artists"]])
            album_name = item["album"]["name"]
            initial_release_year = int(item["album"]["release_date"].split('-')[0])
            
            original_info = find_original_release_info(sp, item)
            original_release_year = original_info['year']
            
            year_question_html = ""
            button_text = "Nächstes Lied"
            button_link = "/next"
            image_html = f'<img class="album-art" src="{album_image_url}" alt="Album Cover">'

            initial_year_html = ""
            original_info_html = ""
            prominent_year_html = f'<p class="prominent-year">{initial_release_year}</p>'
            if original_release_year < initial_release_year:
                prominent_year_html = f'<p class="prominent-year">{original_release_year}</p>'
                initial_year_html = f'<p><strong>Veröffentlichungsjahr:</strong> {initial_release_year}</p>'
                original_info_html = f"""
                    <div class="info-box">
                        <h3>Originalversion</h3>
                        <p><strong>Original-Titel für Suche:</strong> {original_info['cleaned_track_name']}</p>
                        <p><strong>Original-Album:</strong> {original_info['album_name']}</p>
                    </div>"""

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

        theme_selector_html = generate_theme_selector_html(theme_name, colors)

        return render_template('index.html',
            colors=colors, image_html=image_html, display_title=display_title, display_artist=display_artist,
            year_question_html=year_question_html, info_section_html=info_section_html, button_link=button_link,
            button_text=button_text, player_mode_checked='checked' if is_player_mode else '',
            theme_selector_html=theme_selector_html, current_track_id=current_track_id,
            progress_ms=current_track.get('progress_ms', 0), duration_ms=item.get('duration_ms', 0),
            is_playing=current_track.get('is_playing', False), wave_animation_speed=wave_animation_speed,
            polling_interval_seconds=polling_interval_seconds, album_art_hover_scale=album_art_hover_scale,
            arrow_hover_scale=arrow_hover_scale, arrow_size=arrow_size, arrow_thickness=arrow_thickness,
            button_hover_scale=button_hover_scale, progress_bar_thickness=progress_bar_thickness,
            progress_bar_hover_increase_px=progress_bar_hover_increase_px, icon_svg=icon_svg, icon_png=icon_png
        )

    except Exception as e:
        print(f"Ein unerwarteter Fehler ist in der home-Route aufgetreten: {e}")
        return render_template('true_error.html', e=e, colors=colors, button_hover_scale=button_hover_scale)

# --- PLAYER STEUERUNGS ROUTEN ---
@app.route("/check-song")
def check_song():
    sp = get_spotify_client()
    if not sp: return jsonify({'track_id': None})
    try:
        current_track = sp.currently_playing()
        return jsonify({'track_id': current_track['item']['id'] if current_track and current_track.get('item') else None})
    except Exception:
        return jsonify({'track_id': None})

@app.route('/seek', methods=['POST'])
def seek():
    sp = get_spotify_client()
    if not sp: return jsonify({'success': False, 'error': 'Not logged in'})
    try:
        position_ms = request.get_json().get('position_ms')
        if isinstance(position_ms, int):
            sp.seek_track(position_ms)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid position'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/toggle-player-mode', methods=['POST'])
def toggle_player_mode():
    try:
        session['player_mode'] = request.get_json().get('playerMode', False)
        session.modified = True
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/solve")
def solve():
    if 'quiz_state' in session:
        quiz_state = session['quiz_state']
        quiz_state['is_solved'] = True
        session['quiz_state'] = quiz_state
        session.modified = True
    return redirect(url_for('home'))

def execute_playback_action(action):
    sp = get_spotify_client()
    if not sp: return redirect(url_for('home'))
    try:
        action()
        session.pop('quiz_state', None)
        time.sleep(0.5)
    except Exception:
        pass
    return redirect(url_for('home'))

@app.route("/next")
def next_track():
    return execute_playback_action(get_spotify_client().next_track)

@app.route("/previous")
def previous_track():
    return execute_playback_action(get_spotify_client().previous_track)

@app.route("/play_pause")
def play_pause():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for('home'))
    try:
        playback_state = sp.current_playback()
        if playback_state and playback_state['is_playing']:
            sp.pause_playback()
        else:
            sp.start_playback()
    except spotipy.exceptions.SpotifyException as e:
        if "No active device found" in str(e) or "Player command failed" in str(e):
            print("Kein aktives Gerät gefunden. Suche nach verfügbaren Geräten.")
            try:
                devices = sp.devices().get('devices', [])
                if devices:
                    priorities = {'Smartphone': 1, 'Computer': 2, 'Speaker': 3}
                    sorted_devices = sorted(devices, key=lambda d: priorities.get(d['type'], 99))
                    best_device_id = sorted_devices[0]['id']
                    print(f"Aktiviere bestes Gerät: {sorted_devices[0]['name']}")
                    sp.transfer_playback(best_device_id, force_play=True)
            except Exception as device_error:
                print(f"Fehler bei der Geräteaktivierung: {device_error}")
        else:
            print(f"Spotify-API-Fehler in play_pause: {e}")
    
    time.sleep(0.5)
    return redirect(url_for('home'))

@app.route("/play_random")
def play_random():
    sp = get_spotify_client()
    if not sp: return redirect(url_for('home'))
    playlist_uri = "spotify:playlist:76urfTElnBTZh1HXxDckec"
    try:
        sp.shuffle(True)
        sp.start_playback(context_uri=playlist_uri)
        time.sleep(0.7)
    except Exception as e:
        print(f"Fehler beim Starten der Playlist: {e}")
    return redirect(url_for('home'))

@app.route("/set-theme/<theme_name>")
def set_theme(theme_name):
    if theme_name in PALETTES:
        session['theme'] = theme_name
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)