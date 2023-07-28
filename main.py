import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.util import prompt_for_user_token
from spotipy import SpotifyOAuth
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
import re
from lyrics_extractor import SongLyrics
from flask import Flask, request, render_template
from dotenv import load_dotenv
import os


app = Flask(__name__)
load_dotenv()
sid = SentimentIntensityAnalyzer()

# SPOTIFY WEB API
cid = os.getenv("CLIENT_ID")
secret = os.getenv("CLIENT_SECRET")
gcs_api_key = os.getenv("GCS_API_KEY")
gcs_engine_id = os.getenv("GCS_ENGINE_ID")
username = os.getenv("SPOTIFY_USERNAME")
scope = "playlist-modify-public"
client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
token = prompt_for_user_token(username,
                              scope,
                              client_id=cid,
                              client_secret=secret,
                              redirect_uri='http://127.0.0.1:5000')
sp = spotipy.Spotify(auth=token)
extract_lyrics = SongLyrics(gcs_api_key, gcs_engine_id)


@app.route("/showSentiment", methods=["GET"])
def show_sentiment_option():
    return render_template("main_page.html")


@app.route("/classify", methods=["GET", "POST"])
def classify_songs():
    playlist_link = request.form['url']
    playlist_name = request.form['playlist_name']
    method = request.form['method']
    playlist_details = sp.user_playlist_create(username, name=playlist_name)
    playlist_uri = playlist_link.split("/")[-1].split("?")[0]
    items = sp.playlist_tracks(playlist_uri)["items"]
    lst = []
    track_ids = []
    for track in items:
        # Track name
        track_name = track["track"]["name"]
        track_id = track["track"]["id"]
        print(track_name)

        # extract lyrics
        lyric = extract_lyrics.get_lyrics(track_name)
        lyric['lyrics'] = lyric['lyrics'].replace("\n\n", "\n")
        lyric['lyrics'] = re.sub("\[.*?\]", "", lyric['lyrics'])
        lyric['lyrics'] = re.sub("  +", " ", lyric['lyrics']).strip()

        # Sentiment analyzer
        num_positive = 0
        num_negative = 0
        num_neutral = 0
        for sentence in lyric['lyrics'].split("\n"):
            comp = sid.polarity_scores(sentence)
            comp = comp['compound']
            if comp >= 0.5:
                if method == "Positive":
                    track_ids.append(track_id)
                num_positive += 1
            elif -0.5 < comp < 0.5:
                if method == "Neutral":
                    track_ids.append(track_id)
                num_neutral += 1
            else:
                if method == "Negative":
                    track_ids.append(track_id)
                num_negative += 1
        num_total = num_negative + num_neutral + num_positive
        percent_negative = (num_negative / float(num_total)) * 100
        percent_neutral = (num_neutral / float(num_total)) * 100
        percent_positive = (num_positive / float(num_total)) * 100
        if percent_positive > percent_negative and percent_positive > percent_neutral:
            lst.append({track_name: "positive"})
        elif percent_negative>percent_neutral:
            lst.append({track_name: "negative"})
        else:
            lst.append({track_name: "neutral"})
    sp.user_playlist_add_tracks(username, playlist_details["id"], track_ids)
    print(playlist_details['external_urls']['spotify'])
    return lst


@app.route("/")
def main_page():
    return render_template("landing_page.html")


if __name__ == "__main__":
    app.run(debug=True)
