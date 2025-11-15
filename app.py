import random
import flet as ft
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
import keyring
import platform
import subprocess
import asyncio
import requests
import os
import base64
import platform

SERVICE_NAME = "spotify_app"

def is_dark_mode():
    system = platform.system()
    
    if system == "Windows":
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0  # 0 = dark, 1 = light
        except Exception:
            return False
    elif system == "Darwin":  # macOS
        try:
            cmd = ["defaults", "read", "-g", "AppleInterfaceStyle"]
            output = subprocess.run(cmd, capture_output=True, text=True)
            return "Dark" in output.stdout
        except Exception:
            return False
    else:
        # Linux fallback
        return False

def get_custom_theme(dark: bool):
    if dark:
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary="#6200EE",
                on_primary="#FFFFFF",
                secondary="#03DAC6",
                on_secondary="#000000",
                surface="#242331",
                on_surface="#FFFFFF",
                background="#242331",
                error="#CF6679",
                on_error="#000000",
            )
        )
    else:
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary="#6200EE",
                on_primary="#FFFFFF",
                secondary="#03DAC6",
                on_secondary="#000000",
                surface="#FFFFFF",
                on_surface="#000000",
                background="#FFFFFF",
                error="#B00020",
                on_error="#FFFFFF",
            )
        )

def logout(e):
    username = keyring.get_password(SERVICE_NAME, "username") or ""

    keyring.delete_password(SERVICE_NAME, "client_id")
    keyring.delete_password(SERVICE_NAME, "client_secret")
    keyring.delete_password(SERVICE_NAME, "username")

    cache_file = f".cache"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print(f"Deleted cached token: {cache_file}")

    page = e.page
    page.controls.clear()
    page.update()
    main(page)

def build_logout_bar():
    logout_button = ft.TextButton(
        "Log out",
        on_click=logout,
        style=ft.ButtonStyle(color="#FFFFFF")
    )

    return ft.Stack(
        controls=[
            ft.Container(
                content=logout_button,
                padding=ft.Padding(0, 0, 10, 0),
                alignment=ft.alignment.top_right
            )
        ]
    )

def main(page: ft.Page):
    page.window.title_bar_hidden = True
    page.window.frameless = False
    page.update()

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    dark_mode = is_dark_mode()
    page.bgcolor = "#242331" if dark_mode else None
    
    page.theme = get_custom_theme(dark_mode)
    page.theme_mode = "dark" if dark_mode else "light"
    page.bgcolor = "#242331" if dark_mode else None
    page.window.min_width = 500
    page.window.min_height = 400

    page.title = "Spotify Playlist Generator"
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"
    page.window.title_bar_hidden = True
    page.window.frameless = False

    def get_credentials():
        client_id = keyring.get_password(SERVICE_NAME, "client_id")
        client_secret = keyring.get_password(SERVICE_NAME, "client_secret")
        username = keyring.get_password(SERVICE_NAME, "username")
        return client_id, client_secret, username

    def store_credentials(client_id, client_secret, username):
        keyring.set_password(SERVICE_NAME, "client_id", client_id)
        keyring.set_password(SERVICE_NAME, "client_secret", client_secret)
        keyring.set_password(SERVICE_NAME, "username", username)
    
    cursor_color = "#FFFFFF" if dark_mode else "#000000"
    selection_color = "#6D49FF" if dark_mode else "#B3D8FF"
    
    client_id_input = ft.TextField(label="Spotify Client ID", width=300, border_radius=12, cursor_color=cursor_color, cursor_width=1, selection_color=selection_color)
    client_secret_input = ft.TextField(
        label="Spotify Client Secret", password=True, can_reveal_password=True, width=300, border_radius=12, cursor_color=cursor_color, cursor_width=1, selection_color=selection_color
    )
    username_input = ft.TextField(label="Spotify Username", width=300, border_radius=12, cursor_color=cursor_color, cursor_width=1, selection_color=selection_color)
    status_text = ft.Text("", color="red")

    stored_client_id, stored_client_secret, stored_username = get_credentials()
    if stored_client_id and stored_client_secret and stored_username:
        spinner = ft.ProgressRing(width=40, height=40, color="#e53265")
        page.add(
            ft.Column(
                [spinner, ft.Text("Loading...")],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()
        try:
            sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=stored_client_id,
                    client_secret=stored_client_secret,
                    redirect_uri="http://127.0.0.1:8888/callback",
                    scope="playlist-modify-private",
                )
            )
            playlists = sp.user_playlists(user=stored_username)["items"]
            playlist_ids = [p["id"] for p in playlists]
            show_playlist_generator(page, sp, stored_username, playlist_ids)
            return
        except Exception as err:
            status_text.value = f"⚠️ Stored credentials invalid: {err}"
            page.update()

    async def proceed_to_playlist_screen(e):
        client_id = client_id_input.value.strip()
        client_secret = client_secret_input.value.strip()
        username = username_input.value.strip()
        redirect_uri = "http://127.0.0.1:8888/callback"

        if not client_id or not client_secret or not username:
            status_text.value = "⚠️ Please fill in all fields."
            page.update()
            return

        # Show spinner
        spinner.visible = True
        page.update()

        # Run the blocking Spotify code in a background thread
        try:
            sp, playlist_ids = await asyncio.to_thread(authenticate_spotify, client_id, client_secret, username, redirect_uri)
            store_credentials(client_id, client_secret, username)
            page.window.to_front()
            page.update()

            spinner.visible = False
            page.update()
            show_playlist_generator(page, sp, username, playlist_ids)

        except ValueError as err:
            spinner.visible = False
            if str(err) == "incorrect_credentials":
                status_text.value = "Invalid credentials"
            else:
                status_text.value = f"Unexpected error: {err}"
            page.update()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            spinner.visible = False
            status_text.value = "Network error: Unable to reach Spotify"
            page.update()

        except Exception as err:
            spinner.visible = False
            status_text.value = f"Unexpected error: {err}"
            page.update()

            page.update()
            
    client_id_input.on_submit = proceed_to_playlist_screen
    client_secret_input.on_submit = proceed_to_playlist_screen
    username_input.on_submit = proceed_to_playlist_screen
            
    def validate_client_credentials(client_id, client_secret):
        token_url = "https://accounts.spotify.com/api/token"
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        try:
            resp = requests.post(
                token_url,
                headers={"Authorization": f"Basic {auth_header}"},
                data={"grant_type": "client_credentials"},
                timeout=5,
            )
            if resp.status_code == 400 and "invalid_client" in resp.text:
                return False
            return True
        except requests.RequestException:
            # Network issue; let the caller handle it
            raise

    def authenticate_spotify(client_id, client_secret, username, redirect_uri):
        # PRE-CHECK
        if not validate_client_credentials(client_id, client_secret):
            raise ValueError("incorrect_credentials")

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-private",
        )

        try:
            sp = spotipy.Spotify(auth_manager=auth_manager)
            sp.current_user()
        except SpotifyOauthError:
            raise ValueError("incorrect_credentials")
        except spotipy.exceptions.SpotifyException as err:
            if err.http_status in (400, 401, 403, 404):
                raise ValueError("incorrect_credentials")
            else:
                raise

        try:
            playlists = sp.user_playlists(user=username)["items"]
        except Exception:
            raise ValueError("incorrect_credentials")

        playlist_ids = [p["id"] for p in playlists]
        return sp, playlist_ids
    
    spinner = ft.ProgressRing(width=18, height=18, color="#FFFFFF", visible=False, stroke_width=2)
    continue_button = ft.Container(
        width=300,
        border_radius=12,
        padding=10,
        bgcolor="#6d4aff",
        content=ft.Stack(
            controls=[
                ft.Row([ft.Text("Continue", color="#FFFFFF")], alignment="center"),
                ft.Row([spinner], alignment="end", expand=True)
            ]
        )
    )
    continue_button.on_click = proceed_to_playlist_screen

    page.add(
        ft.Column(
            [
                ft.Text("🎵 Spotify Playlist Generator", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Enter your Spotify credentials to continue:"),
                client_id_input,
                client_secret_input,
                username_input,
                continue_button,
                status_text,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

# --- Step 2: Playlist generator UI ---
def show_playlist_generator(page: ft.Page, sp, username, playlist_ids):
    page.controls.clear()

    status = ft.Text("")
    link_button = ft.TextButton(
        visible=False,
        style=ft.ButtonStyle(color="#e53265")
    )
    dark_mode = is_dark_mode()
    cursor_color = "#FFFFFF" if dark_mode else "#000000"
    selection_color = "#6D49FF" if dark_mode else "#B3D8FF"
    
    num_tracks_input = ft.TextField(label="Number of tracks", width=300, border_radius=12, cursor_color=cursor_color, cursor_width=1, selection_color=selection_color)
    playlist_name_input = ft.TextField(label="New playlist name", width=300, border_radius=12, cursor_color=cursor_color, cursor_width=1, selection_color=selection_color)
    spinner = ft.ProgressRing(width=18, height=18, color="#FFFFFF", visible=False, stroke_width=2)

    generate_button = ft.Container(
        width=300,
        border_radius=12,
        padding=10,
        bgcolor="#6d4aff",
        content=ft.Stack(
            controls=[
                ft.Row([ft.Text("Generate Playlist", color="#FFFFFF")], alignment="center"),
                ft.Row([spinner], alignment="end", expand=True)
            ]
        )
    )

    def generate_playlist(e):
        spinner.visible = True
        page.update()

        try:
            value = num_tracks_input.value.strip()

            # Check if user left the field empty
            if not value:
                status.value = "⚠️ Please enter the number of tracks."
                spinner.visible = False
                page.update()
                return

            # Check for numeric input only
            if not value.isdigit():
                status.value = "⚠️ Number of tracks must be a valid number."
                spinner.visible = False
                page.update()
                return

            num_tracks = int(value)
            playlist_name = playlist_name_input.value.strip()
            if not playlist_name:
                status.value = "⚠️ Please enter a playlist name."
                spinner.visible = False
                page.update()
                return

            playlist_id = random.choice(playlist_ids)
            tracks = sp.playlist_tracks(playlist_id)["items"]
            track_ids = [t["track"]["id"] for t in tracks if t.get("track")]
            if len(track_ids) < num_tracks:
                status.value = f"⚠️ Not enough tracks ({len(track_ids)} available)."
                spinner.visible = False
                page.update()
                return

            random_tracks = random.sample(track_ids, k=num_tracks)
            new_playlist = sp.user_playlist_create(user=username, name=playlist_name, public=False)
            sp.playlist_add_items(new_playlist["id"], random_tracks)
            playlist_url = new_playlist["external_urls"]["spotify"]

            status.value = "✅ Playlist generated!"
            link_button.text = "Open playlist"
            link_button.on_click = lambda e: page.launch_url(playlist_url)
            link_button.visible = True

        except Exception as err:
            status.value = f"Error: {err}"

        spinner.visible = False
        page.update()

    generate_button.on_click = generate_playlist

    # --- Build logout button separately ---
    dark_mode = is_dark_mode()

    logout_button = ft.TextButton(
        "Log out",
        on_click=logout,
        style=ft.ButtonStyle(
            color="#FFFFFF" if dark_mode else "#000000"  # White in dark mode, black in light mode
        )
    )
    logout_container = ft.Container(
        content=logout_button,
        alignment=ft.alignment.top_right,
        padding=ft.Padding(10, 10, 0, 0),  # top=10, right=10
    )

    # --- Main page layout ---
    page.add(
        ft.Column(
            [
                ft.Row(
                    [logout_container],
                    alignment=ft.MainAxisAlignment.END
                ),
                ft.Column(
                    [
                        ft.Text("🎶 Create a Random Playlist", size=24, weight=ft.FontWeight.BOLD),
                        num_tracks_input,
                        playlist_name_input,
                        generate_button,
                        status,
                        link_button,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True
                )
            ],
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )
    page.update()

ft.app(target=main)
