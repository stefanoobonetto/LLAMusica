import os
import time
import glob
import spotipy
from utils import get_terminal_width, center_text, PRINT_DEBUG
from spotipy.oauth2 import SpotifyOAuth

CLIENT_ID = '181dea1437d14614ae1f6cc4e6f0a54a'
CLIENT_SECRET = 'f03f9a3bd9554adcb58d6f12a8fcdc0a'
SPOTIPY_REDIRECT_URI = 'http://localhost:8080'
SCOPE = (
    "ugc-image-upload",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "app-remote-control",
    "streaming",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-follow-modify",
    "user-follow-read",
    "user-read-playback-position",
    "user-top-read",
    "user-read-recently-played",
    "user-library-modify",
    "user-library-read",
    "user-read-email",
    "user-read-private"
)

class Artist:
    def __init__(self, id, name, genres, followers, popularity, spotify_url, images, top_tracks=None):
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
            f"  Spotify URL: {self.spotify_url}\n"
        )


class Song:
    def __init__(self, id, name, artists, album, release_date, duration, popularity, spotify_url, preview_url):
        self.id = id
        self.name = name
        self.artists = artists
        self.album = album
        self.release_date = release_date
        self.duration = duration // 1000  # Convert to seconds
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
            f"  Duration: {self.duration}s\n"
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
        if PRINT_DEBUG:
            print(f"Removed cache file: {cache_file}")


def print_spoti_logo():
    GREEN = "\033[92m"  # Spotify Green
    RESET = "\033[0m"   # Reset to default color

    spotify_logo = f"""{GREEN}    
⠀⠀⠀⠀⠀⠀⠀⢀⣠⣤⣤⣶⣶⣶⣶⣤⣤⣄⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢀⣤⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣤⡀⠀⠀⠀⠀
⠀⠀⠀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⠀⠀⠀
⠀⢀⣾⣿⡿⠿⠛⠛⠛⠉⠉⠉⠉⠛⠛⠛⠿⠿⣿⣿⣿⣿⣿⣷⡀⠀
⠀⣾⣿⣿⣇⠀⣀⣀⣠⣤⣤⣤⣤⣤⣀⣀⠀⠀⠀⠈⠙⠻⣿⣿⣷⠀
⢠⣿⣿⣿⣿⡿⠿⠟⠛⠛⠛⠛⠛⠛⠻⠿⢿⣿⣶⣤⣀⣠⣿⣿⣿⡄
⢸⣿⣿⣿⣿⣇⣀⣀⣤⣤⣤⣤⣤⣄⣀⣀⠀⠀⠉⠛⢿⣿⣿⣿⣿⡇
⠘⣿⣿⣿⣿⣿⠿⠿⠛⠛⠛⠛⠛⠛⠿⠿⣿⣶⣦⣤⣾⣿⣿⣿⣿⠃
⠀⢿⣿⣿⣿⣿⣤⣤⣤⣤⣶⣶⣦⣤⣤⣄⡀⠈⠙⣿⣿⣿⣿⣿⡿⠀
⠀⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣾⣿⣿⣿⣿⡿⠁⠀
⠀⠀⠀⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⠀
⠀⠀⠀⠀⠈⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠈⠙⠛⠛⠿⠿⠿⠿⠛⠛⠋⠁⠀⠀⠀⠀⠀⠀⠀
{RESET}"""

    # Get the terminal width
    term_width = get_terminal_width()

    # Print Spotify Logo Centered
    for line in spotify_logo.split("\n"):
        # Calculate padding for centering
        padding = (term_width - len(line)) // 2
        print(" " * max(0, padding) + line)
        time.sleep(0.05)  # Small delay for a "loading" effect


def authenticate(force_auth=False):
    global sp
    if force_auth:
        clear_cache()
    print(center_text("\n\nPlease log in to your Spotify account..."))
    print_spoti_logo()
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-library-read user-top-read playlist-read-private",
        show_dialog=force_auth
    ))
    print(center_text("\nAuthentication successful!\n"))
    return sp

#  SEARCH A GIVEN SONG AND RETURN IT OR RETURN THE DETAIL ASKED FOR

def get_song_info(args):
    """
    Search for a song on Spotify and return its details.

    Parameters:
        song_name (str): The name of the song to search for.
        detail (str, optional): Specific detail to extract from the song information. 
                                Options: "id", "name", "artists", "album", "release_date", 
                                "duration_ms", "popularity", "spotify_url", "preview_url".

    Returns:
        Song: An instance of the Song class with detailed information about the song.
        None: If no song is found or the query fails.
    """
    song_name = args["song_name"] 
    artist_name = args["artist_name"] if "artist_name" in args.keys() else None
    details = args["details"] if "details" in args.keys() else None
    
    if artist_name == None and details == None:
        details = ["artists"]

    if details and "artist_name" in details:
        details = ["artists" if detail == "artist_name" else detail for detail in details]

    # print("Song name: ", song_name)
    # print("Artist name: ", artist_name)
    # print("Details: ", details)

    # song_query = f"track:{song_name} {artist_name}" if artist_name else f"track:{song_name}"
    song_query = f"track:{song_name}"
    results = sp.search(q=song_query, type="track", limit=1)

    if artist_name:
        while artist_name not in results['tracks']['items'][0]['artists'][0]['name']:    
            if PRINT_DEBUG:
                print(f"Artist '{artist_name}' not present in {results['tracks']['items'][0]['artists'][0]['name']}, retrying...")
            results = sp.search(q=song_query, type="track", limit=1)
    
    # print("\n\n\nResults: ", results)
    
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        song = Song(
            id=track['id'],
            name=track['name'],
            artists=[artist['name'] for artist in track['artists']],
            album=track['album']['name'],
            release_date=track['album']['release_date'],
            duration=track['duration_ms'],
            popularity=track['popularity'],
            spotify_url=track['external_urls']['spotify'],
            preview_url=track['preview_url']
        )
        
        # print("SONG: ", song)
        # Return a specific detail/s if requested, otherwise return the Song object
        if details and "all" not in details:
            return_dic = {}
            for detail in details:
                return_dic[detail] = getattr(song, detail, None)
            return return_dic
        return song
    return None

# SEARCH A GIVEN ARTIST AND RETURN IT OR RETURN THE DETAIL ASKED FOR

def get_artist_info(args):
    """
    Search for an artist on Spotify and return their details, including top tracks.
    """
    if not args:
        if PRINT_DEBUG:
            print("No arguments provided.")
        return None

    # print("\n\n-----> ARGS: ", args)

    artist_name = args["artists"]
    details = args["details"]

    # print("Artist name: ", artist_name)
    # print("Details: ", details)

    try:
        # Search for the artist using Spotify's API
        results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)

        # print("\n\n\nResults: ", results)
        
        if results['artists']['items']:
            artist_data = results['artists']['items'][0]

            artist = Artist(
                id=artist_data['id'],
                name=artist_data['name'],
                genres=artist_data['genres'],
                followers=artist_data['followers']['total'],
                popularity=artist_data['popularity'],
                spotify_url=artist_data['external_urls']['spotify'],
                images=artist_data['images']
            )

            # Return a specific detail if requested, otherwise return the Artist object
            if details and "all" not in details:
                return_dic = {detail: getattr(artist, detail, None) for detail in details}
                return return_dic

            return artist
    except Exception as e:
        if PRINT_DEBUG:
            print(f"Error fetching artist info: {e}")
        return None
    
# SEARCH A GIVEN ALBUM AND RETURN IT OR RETURN THE DETAIL ASKED FOR

def get_album_info(args):
    """
    Search for an album on Spotify and return its details.

    Parameters:
        album_name (str): The name of the album to search for.
        detail (str, optional): Specific detail to extract from the album information.
                                Options: "id", "name", "artists", "release_date", "total_tracks",
                                "genres", "spotify_url", "images".

    Returns:
        Album: An instance of the Album class with detailed information about the album.
        None: If no album is found or the query fails.
    """    

    if PRINT_DEBUG:
        print("ARGS: ", args)

    album_name = args["album_name"] 
    artist_name = args["artist_name"] if "artist_name" in args.keys() else None
    details = args["details"]

    if details and "artist_name" in details:
        details = ["artists" if detail == "artist_name" else detail for detail in details]

    # print("Album name: ", album_name)
    # print("Artist name: ", artist_name)
    # print("Details: ", details)
        
    results = sp.search(q=f"album:{album_name}", type="album", limit=1)
    if results['albums']['items']:
        album_data = results['albums']['items'][0]
        album = Album(
            id=album_data['id'],
            name=album_data['name'],
            artists=[artist['name'] for artist in album_data['artists']],
            release_date=album_data['release_date'],
            total_tracks=album_data['total_tracks'],
            genres=album_data.get('genres', []),  # Genres may not always be available
            spotify_url=album_data['external_urls']['spotify'],
            images=album_data['images']
        )
        
        # Return a specific detail/s if requested, otherwise return the Album object
        if details and "all" not in details:
            return_dic = {}
            
            # print("\n\n\nASK for DETAILS: ", details, "\n\n\n")
            for detail in details:
                return_dic[detail] = getattr(album, detail, None)
            return return_dic
        return album
    return None

# GET NEWEST RELEASES

def get_new_releases(country=None, limit=10):
    """
    Fetch new album releases on Spotify.

    Parameters:
        limit (int, optional): Number of new releases to fetch. Default is 10.

    Returns:
        list[Album]: A list of Album instances representing new releases.
    """
    results = sp.new_releases(country=country, limit=limit)
    if results['albums']['items']:
        return [
            Album(
                id=album['id'],
                name=album['name'],
                artists=[artist['name'] for artist in album['artists']],
                release_date=album['release_date'],
                total_tracks=album['total_tracks'],
                genres=[],  # Genres are not provided in the new releases endpoint
                spotify_url=album['external_urls']['spotify'],
                images=album['images']
            )
            for album in results['albums']['items']
        ]
    return None

# GET USER'S TOP TRACKS

def get_username():
    return sp.me().get('display_name', 'Unknown')  # User's chosen display name

def get_user_top_tracks(args):
    """
    Fetch the user's top tracks.

    Parameters:
        limit (int, optional): Number of top tracks to fetch. Default is 10.

    Returns:
        list[Song]: A list of Song instances representing the user's top tracks.
    """
    
    time_range = args["time_frame"]
    limit = args["limit"]
    
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    if results['items']:
        return [        
            f"{track['name']} - {', '.join(artist['name'] for artist in track['artists'])}"
            for track in results['items']
        ]
    return None

# GET USER'S TOP ARTISTS

def get_user_top_artists(args):
    """
    Fetch the user's top artists.

    Parameters:
        limit (int, optional): Number of top artists to fetch. Default is 10.

    Returns:
        list[Artist]: A list of Artist instances representing the user's top artists.
    """
    
    time_range = args["time_frame"]
    limit = args["limit"]
    
    results = sp.current_user_top_artists(limit=limit, time_range=time_range)
    if results['items']:
        return [
            artist['name'] for artist in results['items']
        ]
    return None

# GET ARTIST'S RELATED ARTISTS

def get_related_artists(artist_name):
    artist_data = get_artist_info(artist_name)
    if not artist_data:
        if PRINT_DEBUG:
            print(f"Artista '{artist_name}' non trovato.")
        return None

    artist_id = artist_data.id
    try:
        results = sp.artist_related_artists(artist_id)
        if 'artists' in results and results['artists']:
            return [
                Artist(
                    id=related_artist['id'],
                    name=related_artist['name'],
                    genres=related_artist['genres'],
                    followers=related_artist['followers']['total'],
                    popularity=related_artist['popularity'],
                    spotify_url=related_artist['external_urls']['spotify'],
                    images=related_artist['images']
                )
                for related_artist in results['artists']
            ]
        else:
            if PRINT_DEBUG:
                print(f"Nessun artista correlato trovato per '{artist_name}'.")
            return None
    except spotipy.exceptions.SpotifyException as e:
        if PRINT_DEBUG:
            print(f"Errore durante la ricerca degli artisti correlati: {e}")
    except Exception as e:
        if PRINT_DEBUG:
            print(f"Errore sconosciuto durante la ricerca degli artisti correlati: {e}")
    return None
