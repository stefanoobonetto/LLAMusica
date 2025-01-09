import os
import glob
import spotipy
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
        scope="user-library-read user-top-read playlist-read-private",
        show_dialog=force_auth
    ))
    print("Authentication successful!")
    return sp

#  SEARCH A GIVEN SONG AND RETURN IT OR RETURN THE DETAIL ASKED FOR

def get_song_info(*args):
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
    song_name = args[0]
    details = [args[i] for i in range(1, len(args))] if len(args) > 1 else None
    
    print("Song name: ", song_name)
    print("Details: ", details)

    results = sp.search(q=f"track:{song_name}", type="track", limit=1)
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        song = Song(
            id=track['id'],
            name=track['name'],
            artists=[artist['name'] for artist in track['artists']],
            album=track['album']['name'],
            release_date=track['album']['release_date'],
            duration_ms=track['duration_ms'],
            popularity=track['popularity'],
            spotify_url=track['external_urls']['spotify'],
            preview_url=track['preview_url']
        )
        # Return a specific detail/s if requested, otherwise return the Song object
        if details and "all" not in details:
            return_dic = {}
            for detail in details:
                return_dic[detail] = getattr(song, detail, None)
            return return_dic
        return song
    return None

# SEARCH A GIVEN ARTIST AND RETURN IT OR RETURN THE DETAIL ASKED FOR

def get_artist_info(*args):
    """
    Search for an artist on Spotify and return their details, including top tracks.
    """
    if not args:
        print("No arguments provided.")
        return None

    artist_name = args[0]
    details = args[1:] if len(args) > 1 else None

    print("Artist name: ", artist_name)
    print("Details: ", details)

    try:
        # Search for the artist using Spotify's API
        results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)

        print("\n\n\nResults: ", results)
        
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
        print(f"Error fetching artist info: {e}")
        return None
    
# SEARCH A GIVEN ALBUM AND RETURN IT OR RETURN THE DETAIL ASKED FOR

def get_album_info(*args):
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
    album_name = args[0]
    details = [args[i] for i in range(1, len(args))] if len(args) > 1 else None
    
    print("Album name: ", album_name)
    print("Details: ", details)
        
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

def get_user_top_tracks(limit=10, time_range="medium_term"):
    """
    Fetch the user's top tracks.

    Parameters:
        limit (int, optional): Number of top tracks to fetch. Default is 10.

    Returns:
        list[Song]: A list of Song instances representing the user's top tracks.
    """
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    if results['items']:
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
                preview_url=track['preview_url']
            )
            for track in results['items']
        ]
    return None

# GET USER'S TOP ARTISTS

def get_user_top_artists(limit=10):
    """
    Fetch the user's top artists.

    Parameters:
        limit (int, optional): Number of top artists to fetch. Default is 10.

    Returns:
        list[Artist]: A list of Artist instances representing the user's top artists.
    """
    results = sp.current_user_top_artists(limit=limit)
    if results['items']:
        return [
            Artist(
                id=artist['id'],
                name=artist['name'],
                genres=artist['genres'],
                followers=artist['followers']['total'],
                popularity=artist['popularity'],
                spotify_url=artist['external_urls']['spotify'],
                images=artist['images']
            )
            for artist in results['items']
        ]
    return None

# GET ARTIST'S RELATED ARTISTS

def get_related_artists(artist_name):
    artist_data = get_artist_info(artist_name)
    if not artist_data:
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
            print(f"Nessun artista correlato trovato per '{artist_name}'.")
            return None
    except spotipy.exceptions.SpotifyException as e:
        print(f"Errore durante la ricerca degli artisti correlati: {e}")
    except Exception as e:
        print(f"Errore sconosciuto durante la ricerca degli artisti correlati: {e}")
    return None

# SEARCH FOR PLAYLISTS

def search_playlists(keyword, limit=5):
    """
    Search for playlists on Spotify by keyword.

    Parameters:
        keyword (str): The search keyword.
        limit (int, optional): Number of playlists to fetch. Default is 5.

    Returns:
        list[dict]: A list of playlist details.
    """
    try:
        results = sp.search(q=f"playlist:{keyword}", type="playlist", limit=limit)
        if results and 'playlists' in results and results['playlists']['items']:
            return [
                {
                    "id": playlist['id'],
                    "name": playlist['name'],
                    "owner": playlist['owner']['display_name'],
                    "spotify_url": playlist['external_urls']['spotify']
                }
                for playlist in results['playlists']['items']
            ]
        else:
            print(f"Nessuna playlist trovata con il termine '{keyword}'.")
            return None
    except Exception as e:
        print(f"Errore durante la ricerca delle playlist: {e}")
        return None

def test_functions():
    print("Inizio dei test per le funzioni di utilità di Spotify...")
    print("Autenticazione in corso...")
    sp = authenticate()

    print("\n--- TEST: Search for a Song ---")
    song_name = "Shape of You"
    song = get_song_info(song_name)
    print(f"Risultato per la canzone '{song_name}':\n", song if song else "Nessuna canzone trovata.")

    print("\n--- TEST: Search for an Artist ---")
    artist_name = "Ed Sheeran"
    artist = get_artist_info(artist_name)
    print(f"Risultato per l'artista '{artist_name}':\n", artist if artist else "Nessun artista trovato.")

    print("\n--- TEST: Search for an Album ---")
    album_name = "Divide"
    album = get_album_info(album_name)
    print(f"Risultato per l'album '{album_name}':\n", album if album else "Nessun album trovato.")

    print("\n--- TEST: Get Artist's Top Tracks ---")
    top_tracks = get_artist_top_tracks(artist_name)
    if top_tracks:
        print(f"Top Tracks per '{artist_name}':\n")
        for track in top_tracks:
            print(track, "\n")
    else:
        print(f"Nessuna traccia trovata per l'artista '{artist_name}'.")

    
    print("\n--- TEST: Get Newest Releases ---")
    new_releases = get_new_releases(limit=5)
    if new_releases:
        print("Nuove uscite:\n")
        for release in new_releases:
            print(release, "\n")
    else:
        print("Nessuna nuova uscita trovata.")

    print("\n--- TEST: Get User's Top Tracks ---")
    top_tracks_user = get_user_top_tracks(limit=5)
    if top_tracks_user:
        print("Le tracce più ascoltate dall'utente:\n")
        for track in top_tracks_user:
            print(track, "\n")
    else:
        print("Nessuna traccia principale trovata per l'utente.")

    print("\n--- TEST: Get User's Top Artists ---")
    top_artists_user = get_user_top_artists(limit=5)
    if top_artists_user:
        print("Gli artisti più ascoltati dall'utente:\n")
        for artist in top_artists_user:
            print(artist, "\n")
    else:
        print("Nessun artista principale trovato per l'utente.")

    print("\n--- TEST: Get Related Artists ---")
    related_artists = get_related_artists(artist_name)
    if related_artists:
        print(f"Artisti correlati a '{artist_name}':\n")
        for related in related_artists:
            print(related, "\n")
    else:
        print(f"Nessun artista correlato trovato per '{artist_name}'.")


    print("\n--- TEST: Search for Playlists ---")
    keyword = "Workout"
    playlists = search_playlists(keyword, limit=5)
    if playlists:
        print(f"Playlist trovate con il termine '{keyword}':\n")
        for playlist in playlists:
            print(f"Nome: {playlist['name']}, Proprietario: {playlist['owner']}, URL: {playlist['spotify_url']}")
    else:
        print(f"Nessuna playlist trovata con il termine '{keyword}'.")

    print("\n--- Tutti i test completati! ---")

if __name__ == "__main__":
    test_functions()