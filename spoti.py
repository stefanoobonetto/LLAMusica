import os
import sys
import time
import glob
import random
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configuration data for Spotify APIs

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

PRINT_DEBUG = False

# These recommendations based on genre are used to substitute the Spotify APIs ge_recommendations fucntion, which actually doesn't work

recommendations = {
  "pop": [
    "People, I've been sad - Christine and the Queens",
    "Mystery of Love - Sufjan Stevens",
    "Cut Me - Moses Sumney",
    "Cellophane - FKA twigs",
    "Retrograde - James Blake",
    "A Palé - Rosalía",
    "Bags - Clairo",
    "All the Stars - Kendrick Lamar & SZA",
    "Midnight City - M83",
    "Electric Feel - MGMT",
    "Supercut - Lorde",
    "Ocean Eyes - Billie Eilish",
    "Talia - King Princess",
    "Somebody Else - The 1975",
    "Are You Bored Yet? - Wallows ft. Clairo"
  ],
  "rock": [
    "Apocalypse - Cigarettes After Sex",
    "Weird Fishes/Arpeggi - Radiohead",
    "Storm - Godspeed You! Black Emperor",
    "Rattlesnake - King Gizzard & the Lizard Wizard",
    "Concorde - Black Country, New Road",
    "Your Hand In Mine - Explosions in the Sky",
    "Reptilia - The Strokes",
    "How Soon Is Now? - The Smiths",
    "Paranoid Android - Radiohead",
    "Where Is My Mind? - Pixies",
    "Everlong - Foo Fighters",
    "Lithium - Nirvana",
    "Do I Wanna Know? - Arctic Monkeys",
    "1979 - The Smashing Pumpkins",
    "Baba O'Riley - The Who"
  ],
  "jazz": [
    "Little One - Immanuel Wilkins",
    "Lanquidity - Sun Ra",
    "The Epic - Kamasi Washington",
    "I'll Remember April - Brad Mehldau",
    "Doomed - Moses Sumney",
    "Celestial Blues - Andy Bey",
    "Take Five - Dave Brubeck",
    "Blue in Green - Miles Davis",
    "Feeling Good - Nina Simone",
    "Naima - John Coltrane",
    "Autumn Leaves - Bill Evans",
    "Lush Life - Johnny Hartman & John Coltrane",
    "Speak No Evil - Wayne Shorter",
    "Cantaloupe Island - Herbie Hancock",
    "Misty - Erroll Garner"
  ],
  "electronic": [
    "BIPP - SOPHIE",
    "An Eagle in Your Mind - Boards of Canada",
    "Singularity - Jon Hopkins",
    "Windowlicker - Aphex Twin",
    "Kid A - Radiohead",
    "Kong - Bonobo",
    "Ghosts 'n' Stuff - Deadmau5",
    "Xtal - Aphex Twin",
    "Acid Tracks - Phuture",
    "Night Owl - Metronomy",
    "Opus - Eric Prydz",
    "Elysium - Porter Robinson",
    "Music Sounds Better With You - Stardust",
    "Cerulean - Baths",
    "Divinity - Porter Robinson ft. Amy Millan"
  ],
  "hiphop": [
    "DUCKWORTH. - Kendrick Lamar",
    "The Light - Common",
    "Black Skinhead - Kanye West",
    "The Message - Nas",
    "John Muir - ScHoolboy Q",
    "Shook Ones Pt. II - Mobb Deep",
    "Alright - Kendrick Lamar",
    "95.south - J. Cole",
    "Can’t Tell Me Nothing - Kanye West",
    "Ms. Jackson - Outkast",
    "Grindin’ - Clipse",
    "One Mic - Nas",
    "Jesus Walks - Kanye West",
    "Passin' Me By - The Pharcyde",
    "Power - Kanye West"
  ],
  "r&b": [
    "Superpower - Beyoncé ft. Frank Ocean",
    "Say My Name - Destiny's Child",
    "When We - Tank",
    "Thinkin Bout You - Frank Ocean",
    "Untitled (How Does It Feel) - D'Angelo",
    "Adorn - Miguel",
    "Location - Khalid",
    "Come Through and Chill - Miguel ft. J. Cole",
    "Cranes in the Sky - Solange",
    "No Guidance - Chris Brown ft. Drake",
    "Focus - H.E.R.",
    "Love Galore - SZA ft. Travis Scott",
    "Let Me Love You - Mario",
    "Nice & Slow - Usher",
    "Prototype - Outkast"
  ],
  "soul": [
    "A Change Is Gonna Come - Sam Cooke",
    "Let's Stay Together - Al Green",
    "What's Going On - Marvin Gaye",
    "I Heard It Through the Grapevine - Marvin Gaye",
    "Respect - Aretha Franklin",
    "Ain't No Mountain High Enough - Marvin Gaye & Tammi Terrell",
    "Try a Little Tenderness - Otis Redding",
    "Superstition - Stevie Wonder",
    "The Makings of You - Curtis Mayfield",
    "For Once in My Life - Stevie Wonder",
    "I Put a Spell on You - Nina Simone",
    "Take Me to the River - Al Green",
    "Let's Get It On - Marvin Gaye",
    "These Arms of Mine - Otis Redding",
    "The Way - Jill Scott"
  ],
  "classical": [
    "Clair de Lune - Claude Debussy",
    "Moonlight Sonata - Ludwig van Beethoven",
    "Nocturne Op. 9 No. 2 - Frédéric Chopin",
    "The Four Seasons: Spring - Antonio Vivaldi",
    "Canon in D - Johann Pachelbel",
    "Gymnopédie No. 1 - Erik Satie",
    "Adagio for Strings - Samuel Barber",
    "Prelude in C Major - Johann Sebastian Bach",
    "Swan Lake Theme - Pyotr Ilyich Tchaikovsky",
    "Boléro - Maurice Ravel",
    "Requiem: Lacrimosa - Wolfgang Amadeus Mozart",
    "Carmen: Habanera - Georges Bizet",
    "Hungarian Rhapsody No. 2 - Franz Liszt",
    "Air on the G String - Johann Sebastian Bach",
    "Symphony No. 9: Ode to Joy - Ludwig van Beethoven"
  ],
  "folk": [
    "The Boxer - Simon & Garfunkel",
    "Pink Moon - Nick Drake",
    "The Night We Met - Lord Huron",
    "Home - Edward Sharpe & The Magnetic Zeros",
    "Fast Car - Tracy Chapman",
    "Helplessness Blues - Fleet Foxes",
    "Take Me Home, Country Roads - John Denver",
    "Skinny Love - Bon Iver",
    "Wagon Wheel - Old Crow Medicine Show",
    "Ho Hey - The Lumineers",
    "Rivers and Roads - The Head and the Heart",
    "Ophelia - The Lumineers",
    "Atlantic City - Bruce Springsteen",
    "Blowin' in the Wind - Bob Dylan",
    "Big Yellow Taxi - Joni Mitchell"
  ],
  "reggae": [
    "No Woman, No Cry - Bob Marley & The Wailers",
    "Israelites - Desmond Dekker",
    "Sweat (A La La La La Long) - Inner Circle",
    "Here I Come - Barrington Levy",
    "Red Red Wine - UB40",
    "One Love - Bob Marley & The Wailers",
    "Bad Boys - Inner Circle",
    "Kingston Town - UB40",
    "Buffalo Soldier - Bob Marley & The Wailers",
    "Boom Shakalak - Apache Indian",
    "54-46 Was My Number - Toots and the Maytals",
    "Pass the Dutchie - Musical Youth",
    "I Shot the Sheriff - Eric Clapton",
    "D'yer Mak'er - Led Zeppelin",
    "Sun Is Shining - Bob Marley"
  ]
}

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
    """
    Removes all cached authentication files.

    - Deletes any cached authentication files starting with ".cache".
    - In this way, no authentication is memorized, and the user must re-authenticate.
    """

    for cache_file in glob.glob(".cache*"):
        os.remove(cache_file)
        if PRINT_DEBUG:
            print(f"Removed cache file: {cache_file}")

def get_terminal_width():
    """
    Returns the width of the terminal, with a fallback value of 80.

    Returns:
        int: Terminal width in characters.
    """

    return os.get_terminal_size().columns if sys.stdout.isatty() else 80

def center_text(text):
    """
    Centers a given text based on the terminal width.

    - Splits the input text into lines.
    - Calculates padding to center each line.

    Args:
        text (str): The text to be centered.

    Returns:
        str: Centered text.
    """

    term_width = get_terminal_width()
    centered_lines = []
    
    for line in text.split("\n"):
        padding = (term_width - len(line)) // 2
        centered_lines.append(" " * max(0, padding) + line)

    return "\n".join(centered_lines)

def print_spoti_logo():
    """
    Displays a Spotify logo using ASCII art.

    - Colors the logo in Spotify green.
    - Centers the logo based on the terminal width.
    - Uses a slight delay to create a loading effect.
    """

    GREEN = "\033[92m"  
    RESET = "\033[0m"   

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

    term_width = get_terminal_width()

    for line in spotify_logo.split("\n"):
        padding = (term_width - len(line)) // 2
        print(" " * max(0, padding) + line)
        time.sleep(0.05)

def authenticate(force_auth=False):
    """
    Authenticates the user with Spotify and returns a Spotify client.

    - Uses `SpotifyOAuth` for authentication.
    - Clears cache if `force_auth` is True.
    - Displays a login prompt and Spotify logo.

    Args:
        force_auth (bool, optional): Whether to force re-authentication.

    Returns:
        spotipy.Spotify: An authenticated Spotify client instance.
    """
    
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
    return sp

def get_recommendations(args):
    """
    Retrieves a list of recommended songs based on a specified genre.

    - Uses a predefined dictionary of genre-based song recommendations.
    - Selects a random sample of songs based on the provided limit.

    Args:
        args (dict): A dictionary containing:
            - genre (str): The genre to get recommendations for.
            - limit (int): The number of songs to recommend.

    Returns:
        list[str]: A list of randomly selected recommended songs.
    """

    genre = args.get("genre")  
    limit = int(args.get("limit"))

    if genre not in recommendations:
        if PRINT_DEBUG: 
            print(f"Genre '{genre}' not found in recommendations.")  
        return []

    if not isinstance(limit, int) or limit <= 0:
        if PRINT_DEBUG: 
            print(f"Invalid limit: {limit}, returning all recommendations.") 
        return recommendations[genre]

    return random.sample(recommendations[genre], min(limit, len(recommendations[genre])))

def get_song_info(args):
    """
    Searches for a song on Spotify and retrieves its details.

    - Supports filtering by artist name and retrieving specific details.
    - Returns either a dictionary of requested details or a `Song` object.

    Args:
        args (dict): A dictionary containing:
            - song_name (str): The name of the song.
            - artist_name (str, optional): The artist name (if provided).
            - details (list, optional): Specific details to return.

    Returns:
        Song | dict | None: A `Song` object, a dictionary of details, or None if not found.
    """

    song_name = args["song_name"] 
    artist_name = args["artist_name"] if "artist_name" in args.keys() else None
    details = args["details"] if "details" in args.keys() else None
    
    if artist_name == None and details == None:
        details = ["artists"]

    if details and "artist_name" in details:
        details = ["artists" if detail == "artist_name" else detail for detail in details]

    song_query = f"track:{song_name}"
    results = sp.search(q=song_query, type="track", limit=1)

    if artist_name:
        while artist_name not in results['tracks']['items'][0]['artists'][0]['name']:    
            if PRINT_DEBUG:
                print(f"Artist '{artist_name}' not present in {results['tracks']['items'][0]['artists'][0]['name']}, retrying...")
            results = sp.search(q=song_query, type="track", limit=1)
        
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
        
        # Return a specific detail/s if requested, otherwise return the Song object
        if details and "all" not in details:
            return_dic = {}
            for detail in details:
                return_dic[detail] = getattr(song, detail, None)
            return return_dic
        return song
    return None

def get_artist_info(args):
    """
    Searches for an artist on Spotify and retrieves their details.

    - Returns either a dictionary of requested details or an `Artist` object.

    Args:
        args (dict): A dictionary containing:
            - artists (str): The name of the artist.
            - details (list): Specific details to return.

    Returns:
        Artist | dict | None: An `Artist` object, a dictionary of details, or None if not found.
    """

    if not args:
        if PRINT_DEBUG:
            print("No arguments provided.")
        return None

    artist_name = args["artists"]
    details = args["details"]

    try:
        results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)

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
    
def get_album_info(args):
    """
    Searches for an album on Spotify and retrieves its details.

    - Supports filtering by artist name and retrieving specific details.
    - Returns either a dictionary of requested details or an `Album` object.

    Args:
        args (dict): A dictionary containing:
            - album_name (str): The name of the album.
            - artist_name (str, optional): The artist name (if provided).
            - details (list): Specific details to return.

    Returns:
        Album | dict | None: An `Album` object, a dictionary of details, or None if not found.
    """

    if PRINT_DEBUG:
        print("ARGS: ", args)

    album_name = args["album_name"] 
    details = args["details"]

    if details and "artist_name" in details:
        details = ["artists" if detail == "artist_name" else detail for detail in details]
        
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

def get_username():
    """
    Retrieves the current authenticated Spotify user's display name.

    Returns:
        str: The display name of the user, or "Unknown" if not found.
    """

    return sp.me().get('display_name', 'Unknown')  

def get_user_top_tracks(args):
    """
    Fetches the user's top tracks on Spotify.

    - Uses Spotify's `current_user_top_tracks` API.

    Args:
        args (dict): A dictionary containing:
            - time_frame (str): The time range for the top tracks (short_term, medium_term, long_term).
            - limit (int): The number of top tracks to retrieve.

    Returns:
        list[str] | None: A list of top track names with artist names or None if no results are found.
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

def get_user_top_artists(args):
    """
    Fetches the user's top artists on Spotify.

    - Uses Spotify's `current_user_top_artists` API.

    Args:
        args (dict): A dictionary containing:
            - time_frame (str): The time range for the top artists (short_term, medium_term, long_term).
            - limit (int): The number of top artists to retrieve.

    Returns:
        list[str] | None: A list of top artist names or None if no results are found.
    """
    
    time_range = args["time_frame"]
    limit = args["limit"]
    
    results = sp.current_user_top_artists(limit=limit, time_range=time_range)
    if results['items']:
        return [
            artist['name'] for artist in results['items']
        ]
    return None
