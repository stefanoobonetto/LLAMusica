import os 
from spoti import *
from spotipy.oauth2 import SpotifyOAuth


# To access CLIENT_ID and CLIENT_SECRET, see the dashboard of your Spotify for Developers account https://developer.spotify.com/dashboard
# Now I've exported the CLIENT_ID and CLIENT_SECRET as environment variables

# sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))
# is the same as

if __name__ == "__main__":
    
    sp = authenticate(force_auth=True)
    
    