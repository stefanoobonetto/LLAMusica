import os 
from spoti import *
from spotipy.oauth2 import SpotifyOAuth


# To access CLIENT_ID and CLIENT_SECRET, see the dashboard of your Spotify for Developers account https://developer.spotify.com/dashboard
# Now I've exported the CLIENT_ID and CLIENT_SECRET as environment variables

# sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))
# is the same as

def main():
    authenticate()

    # Fetch user data
    print("Fetching your top tracks...")
    top_tracks = get_user_top_tracks()
    for song in top_tracks[:5]:
        print(song)

    print("\nFetching your top artists...")
    top_artists = get_user_top_artists()
    for artist in top_artists[:5]:
        print(artist)

    # Search for an artist
    print("\nSearching for an artist...")
    artist_name = "Adele"
    artist = search_artist(artist_name)
    if artist:
        print(f"Found artist: {artist}")

    # Create and populate a playlist
    print("\nCreating a playlist...")
    playlist = create_playlist("My Top Tracks", "A playlist of my favorite songs.")
    track_ids = [track.id for track in top_tracks[:10]]
    add_tracks_to_playlist(playlist['id'], track_ids)

    # Get recommendations
    print("\nGetting recommendations based on top tracks...")
    recommendations = get_recommendations(seed_tracks=[top_tracks[0].id], limit=5)
    for rec in recommendations:
        print(rec)

if __name__ == "__main__":
    main()
