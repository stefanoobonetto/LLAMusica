import os
import glob
import spotipy
from spotipy.oauth2 import SpotifyOAuth

CLIENT_ID = '181dea1437d14614ae1f6cc4e6f0a54a'
CLIENT_SECRET = 'f03f9a3bd9554adcb58d6f12a8fcdc0a'
SPOTIPY_REDIRECT_URI = 'http://localhost:8080'
SCOPE = 'playlist-modify-public user-top-read'

class Artist:
    def __init__(self, id, name, genres, followers, popularity, spotify_url, images):
        self.id = id
        self.name = name
        self.genres = genres
        self.followers = followers
        self.popularity = popularity
        self.spotify_url = spotify_url
        self.images = images

    def __str__(self):
        return (
            f"Artist:\n"
            f"  Name: {self.name}\n"
            f"  Genres: {', '.join(self.genres) if self.genres else 'N/A'}\n"
            f"  Followers: {self.followers}\n"
            f"  Popularity: {self.popularity}\n"
            f"  Spotify URL: {self.spotify_url}"
        )

class Song:
    def __init__(self, id, name, artists, album, release_date, duration_ms, popularity, spotify_url, preview_url):
        self.id = id
        self.name = name
        self.artists = artists
        self.album = album
        self.release_date = release_date
        self.duration_ms = duration_ms
        self.popularity = popularity
        self.spotify_url = spotify_url
        self.preview_url = preview_url

    def __str__(self):
        return (
            f"Song:\n"
            f"  Name: {self.name}\n"
            f"  Artists: {', '.join(self.artists)}\n"
            f"  Album: {self.album}\n"
            f"  Release Date: {self.release_date}\n"
            f"  Duration: {self.duration_ms // 1000}s\n"
            f"  Popularity: {self.popularity}\n"
            f"  Spotify URL: {self.spotify_url}"
        )

class Album:
    def __init__(self, id, name, artists, release_date, total_tracks, genres, spotify_url, images):
        self.id = id
        self.name = name
        self.artists = artists
        self.release_date = release_date
        self.total_tracks = total_tracks
        self.genres = genres
        self.spotify_url = spotify_url
        self.images = images

    def __str__(self):
        return (
            f"Album:\n"
            f"  Name: {self.name}\n"
            f"  Artists: {', '.join(self.artists)}\n"
            f"  Release Date: {self.release_date}\n"
            f"  Total Tracks: {self.total_tracks}\n"
            f"  Genres: {', '.join(self.genres) if self.genres else 'N/A'}\n"
            f"  Spotify URL: {self.spotify_url}"
        )

def clear_cache():
    for cache_file in glob.glob(".cache*"):
        os.remove(cache_file)
        print(f"Removed cache file: {cache_file}")

def authenticate(force_auth=False):
    global sp
    if force_auth:
        clear_cache()
    print("Please log in to your Spotify account...")
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE,
        show_dialog=force_auth
    ))
    print("Authentication successful!")
    return sp

def create_playlist(name, description, public=True):
    user_id = sp.current_user()['id']
    playlist = sp.user_playlist_create(user=user_id, name=name, public=public, description=description)
    print(f"Playlist created: {playlist['external_urls']['spotify']}")
    return playlist

def add_tracks_to_playlist(playlist_id, track_ids):
    sp.playlist_add_items(playlist_id, track_ids)
    print(f"Added {len(track_ids)} tracks to playlist.")

def get_user_top_tracks():
    results = sp.current_user_top_tracks(limit=50, time_range='medium_term')
    songs = []
    for track in results['items']:
        artists = [artist['name'] for artist in track['artists']]
        songs.append(Song(
            id=track['id'],
            name=track['name'],
            artists=artists,
            album=track['album']['name'],
            release_date=track['album']['release_date'],
            duration_ms=track['duration_ms'],
            popularity=track['popularity'],
            spotify_url=track['external_urls']['spotify'],
            preview_url=track.get('preview_url')
        ))
    return songs

def get_user_top_artists():
    results = sp.current_user_top_artists(limit=50, time_range='medium_term')
    artists = []
    for artist_data in results['items']:
        artists.append(Artist(
            id=artist_data['id'],
            name=artist_data['name'],
            genres=artist_data['genres'],
            followers=artist_data['followers']['total'],
            popularity=artist_data['popularity'],
            spotify_url=artist_data['external_urls']['spotify'],
            images=artist_data['images']
        ))
    return artists

def search_artist(artist_name):
    results = sp.search(q=f'artist:{artist_name}', type='artist', limit=1)
    if results['artists']['items']:
        artist = results['artists']['items'][0]
        return Artist(
            id=artist['id'],
            name=artist['name'],
            genres=artist['genres'],
            followers=artist['followers']['total'],
            popularity=artist['popularity'],
            spotify_url=artist['external_urls']['spotify'],
            images=artist['images']
        )
    return None

def get_recommendations(seed_tracks=None, seed_artists=None, seed_genres=None, limit=10):
    recommendations = sp.recommendations(
        seed_tracks=seed_tracks,
        seed_artists=seed_artists,
        seed_genres=seed_genres,
        limit=limit
    )
    return [
        Song(
            id=track['id'],
            name=track['name'],
            artists=[artist['name'] for artist in track['artists']],
            album=track['album']['name'],
            release_date=track['album']['release_date'],
            duration_ms=track['duration_ms'],
            popularity=track['popularity'],
            spotify_url=track['external_urls']['spotify'],
            preview_url=track.get('preview_url')
        ) for track in recommendations['tracks']
    ]

