import pickle
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk

# Spotify credentials
CLIENT_ID = "7335aa21c3bd4655bbe5574fb412acb3"
CLIENT_SECRET = "6851bd5d72d64c599941ee535db64e60"
REDIRECT_URI = "http://localhost:8501"

# Spotify OAuth initialization
sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        redirect_uri=REDIRECT_URI,
                        scope="playlist-modify-public")

# Streamlit Session State
if 'spotify_token' not in st.session_state:
    token_info = None
    auth_url = sp_oauth.get_authorize_url()
    st.write(f"[Login to Spotify]({auth_url})")

    # Check if the code parameter is in the URL
    if 'code' in st.query_params:
        code = st.query_params['code']
        token_info = sp_oauth.get_access_token(code)
        st.session_state['spotify_token'] = token_info['access_token']

# Use the token from session state
if 'spotify_token' in st.session_state:
    sp = spotipy.Spotify(auth=st.session_state['spotify_token'])

    # Load the data and similarity matrix
    music = pickle.load(open('df.pkl', 'rb'))
    similarity = pickle.load(open('similarity.pkl', 'rb'))

    # Initialize Sentiment Analyzer
    nltk.download('vader_lexicon')
    sia = SentimentIntensityAnalyzer()


    # Function to get song album cover URL
    def get_song_album_cover_url(song_name):
        search_query = f"track:{song_name}"
        results = sp.search(q=search_query, type="track")
        if results and results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            album_cover_url = track["album"]["images"][0]["url"]
            return album_cover_url
        else:
            return "https://i.postimg.cc/0QNxYz4V/social.png"


    # Function to recommend songs based on sentiment and similarity
    def recommend(song, sentiment=None):
        index = music[music['Title'] == song].index[0]
        distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
        recommended_music_names = []
        recommended_music_posters = []

        for i in distances[1:21]:
            song_title = music.iloc[i[0]]['Title']
            song_sentiment = sia.polarity_scores(music.iloc[i[0]]['Lyrics'])['compound']

            if sentiment == 'happy' and song_sentiment > 0.2:
                recommended_music_posters.append(get_song_album_cover_url(song_title))
                recommended_music_names.append(song_title)
            elif sentiment == 'sad' and song_sentiment < -0.2:
                recommended_music_posters.append(get_song_album_cover_url(song_title))
                recommended_music_names.append(song_title)
            elif sentiment == 'neutral' and -0.2 <= song_sentiment <= 0.2:
                recommended_music_posters.append(get_song_album_cover_url(song_title))
                recommended_music_names.append(song_title)

        return recommended_music_names, recommended_music_posters


    st.markdown(
        """
        <style>
        @font-face {
            font-family: 'Trajan';
            src: url('https://example.com/path-to-your-font-file/trajan.ttf') format('truetype');
        }

        .custom-font {
            font-family: 'Trajan', serif;
            font-size: 45px;
            background: linear-gradient(to right, #e6e305, #ff7300);
            -webkit-background-clip: text;
            color: transparent;
            text-align: center;
        }
        </style>
        <h1 class="custom-font">Sangeet</h1>
        """,
        unsafe_allow_html=True,
    )

    st.header('Music Recommender System')

    music_list = music['Title'].values
    selected_song = st.selectbox("Type or select a song from the dropdown", music_list)
    sentiment_option = st.selectbox("Select Sentiment", ["happy", "sad", "neutral"])

    if st.button('Show Recommendation'):
        recommended_music_names, recommended_music_posters = recommend(selected_song, sentiment_option)
        st.session_state['recommended_music_names'] = recommended_music_names
        st.session_state['recommended_music_posters'] = recommended_music_posters

        for i in range(len(recommended_music_names)):
            st.write(f"{recommended_music_names[i]}")
            st.image(recommended_music_posters[i])

    if st.button('Create Spotify Playlist'):
        if 'recommended_music_names' in st.session_state:
            recommended_music_names = st.session_state['recommended_music_names']
            track_ids = []
            for song_name in recommended_music_names:
                search_query = f"track:{song_name}"
                results = sp.search(q=search_query, type="track")
                if results and results["tracks"]["items"]:
                    track_id = results["tracks"]["items"][0]['id']
                    track_ids.append(track_id)

            # Create the playlist
            user_id = sp.current_user()['id']
            playlist = sp.user_playlist_create(user=user_id, name=f"My {sentiment_option.capitalize()} Playlist",
                                               public=True)
            sp.playlist_add_items(playlist_id=playlist['id'], items=track_ids)

            # Save the playlist URL
            playlist_url = playlist['external_urls']['spotify']
            st.session_state['playlist_url'] = playlist_url

            st.success(f"{sentiment_option.capitalize()} Playlist created successfully!")
            st.write(f"[Open Playlist]({playlist_url})")
        else:
            st.error("No recommendations available. Please show recommendations first.")
