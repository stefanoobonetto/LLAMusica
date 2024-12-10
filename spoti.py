import os 
import glob
import spotipy
from spotipy.oauth2 import SpotifyOAuth

CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = 'http://localhost:8080'  
SCOPE = 'playlist-modify-public user-top-read'

sp = None

from spotipy.oauth2 import SpotifyOAuth

def clear_cache():
    """Clear all Spotify cache files."""
    for cache_file in glob.glob(".cache*"):
        os.remove(cache_file)
        print(f"Removed cache file: {cache_file}")

def authenticate(force_auth=False):
    """
    Authenticate the user with Spotify and return a Spotipy client instance.
    Deletes any existing cache to ensure a fresh login if `force_auth` is True.
    """
    if force_auth:
        clear_cache()

    print("Please log in to your Spotify account...")
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE,
        show_dialog=True  # Forces the login dialog for the current user
    ))

    print("Authentication successful!")
    return sp


# Define the classes for storing information
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
            # f"  Images: {self.images}"
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
            # f"  Preview URL: {self.preview_url if self.preview_url else 'N/A'}"
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
            # f"  Images: {self.images}"
        )

def get_user_top_tracks():
    """Fetch the user's top-played tracks and encapsulate each track in a Song instance."""
    results = sp.current_user_top_tracks(limit=50, time_range='medium_term')  # You can adjust 'short_term' or 'long_term'
    top_tracks = results['items']
    
    songs = []
    for track in top_tracks:
        artists = [artist['name'] for artist in track['artists']]
        
        song = Song(
            id=track['id'],
            name=track['name'],
            artists=artists,
            album=track['album']['name'],
            release_date=track['album']['release_date'],
            duration_ms=track['duration_ms'],
            popularity=track['popularity'],
            spotify_url=track['external_urls']['spotify'],
            preview_url=track.get('preview_url')
        )
        songs.append(song)
    return songs

def get_user_top_albums():
    """Fetch the user's top albums from their top tracks and encapsulate in Album instances."""
    results = sp.current_user_top_tracks(limit=50, time_range='medium_term')  # You can adjust 'short_term' or 'long_term'
    top_tracks = results['items']

    album_map = {}
    for track in top_tracks:
        album_data = track['album']
        album_id = album_data['id']

        if album_id not in album_map:
            # Extract artists
            artists = [artist['name'] for artist in album_data['artists']]
            
            # Create an Album instance
            album = Album(
                id=album_id,
                name=album_data['name'],
                artists=artists,
                release_date=album_data['release_date'],
                total_tracks=album_data['total_tracks'],
                genres=[],  # Album genres are not always available in this API endpoint
                spotify_url=album_data['external_urls']['spotify'],
                images=album_data['images']
            )
            album_map[album_id] = album

    return list(album_map.values())

def get_user_top_artists():
    """Fetch the user's top artists and encapsulate each in Artist instances."""
    results = sp.current_user_top_artists(limit=50, time_range='medium_term')  # You can adjust 'short_term' or 'long_term'
    top_artists = results['items']
    
    artists = []
    for artist_data in top_artists:
        # Create an Artist instance
        artist = Artist(
            id=artist_data['id'],
            name=artist_data['name'],
            genres=artist_data['genres'],
            followers=artist_data['followers']['total'],
            popularity=artist_data['popularity'],
            spotify_url=artist_data['external_urls']['spotify'],
            images=artist_data['images']
        )
        artists.append(artist)
    
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
    else:
        return None

def search_song(song_name):
    results = sp.search(q=f'track:{song_name}', type='track', limit=1)
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        return Song(
            id=track['id'],
            name=track['name'],
            artists=[artist['name'] for artist in track['artists']],
            album=track['album']['name'],
            release_date=track['album']['release_date'],
            duration_ms=track['duration_ms'],
            popularity=track['popularity'],
            spotify_url=track['external_urls']['spotify'],
            preview_url=track.get('preview_url')
        )
    else:
        return None

def search_album(album_name):
    results = sp.search(q=f'album:{album_name}', type='album', limit=1)
    if results['albums']['items']:
        album = results['albums']['items'][0]
        return Album(
            id=album['id'],
            name=album['name'],
            artists=[artist['name'] for artist in album['artists']],
            release_date=album['release_date'],
            total_tracks=album['total_tracks'],
            genres=album.get('genres', []),  # not always available
            spotify_url=album['external_urls']['spotify'],
            images=album['images']
        )
    else:
        return None