# 🎵 Spotify Random Playlist Generator

A modern, polished random playlist generator using the Spotify API and Flet.

---

## Features

- Generate random playlists from your existing Spotify playlists.
- Modern GUI with dark mode and light mode support.
- Secure credential storage using keyring.
- Input validation and user friendly error handling.
- Log out button to remove stored credentials.
- Direct link to open the generated playlist in Spotify.
- Async handling and loading spinners for smooth experience.

---

## Installation

1. Clone the repository:
2. Install dependencies:

```bash
pip install spotipy flet keyring requests
```
or
```bash
pip3 install spotipy flet keyring requests
```

## Usage
1. Run the app using:
```bash
python app.py
```
or
```bash
python3 app.py
```
2. Enter your Spotify Client ID, Client Secret, and Username.
3. Enter the number of tracks and the name of your new playlist.
4. Click Generate Playlist to add the playlist to your Spotify account.
5. Click the link to open the playlist directly in Spotify.
6. Use the Log Out button to remove saved credentials.
