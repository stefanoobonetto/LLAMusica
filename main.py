import os 
from spoti import *
from spotipy.oauth2 import SpotifyOAuth


# To access CLIENT_ID and CLIENT_SECRET, see the dashboard of your Spotify for Developers account https://developer.spotify.com/dashboard
# Now I've exported the CLIENT_ID and CLIENT_SECRET as environment variables

# sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))
# is the same as

def main():
    # Authenticate the user
    authenticate(force_auth=True)

    # Get recommendations based on a mix of artists, songs, and genres
    recommended_songs = get_recommendations(
        artists=["Taylor Swift", "Drake"],
        songs=["Blinding Lights"],
        genres=["pop", "hip-hop"],
        limit=10
    )

    # Display recommendations
    print("\nRecommended Songs:")
    for song in recommended_songs:
        print(song)

if __name__ == "__main__":
    main()