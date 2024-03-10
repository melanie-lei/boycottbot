from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, copy_current_request_context, jsonify, redirect, render_template, session, request
import threading


import requests
import time, os
import urllib.parse

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

app = Flask(__name__)
app.secret_key = os.getenv("APP_KEY")



REDIRECT_URI = 'https://boycottbot.onrender.com/callback'
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'

SPOTIFY_GET_CURRENT_TRACK_URL = 'https://api.spotify.com/v1/me/player/currently-playing'
SPOTIFY_SKIP_URL = 'https://api.spotify.com/v1/me/player/next'

to_boycott = ["SEVENTEEN", "ENHYPEN", "NewJeans", "TOMORROW X TOGETHER", "LE SSERAFIM", "BOYNEXTDOOR", "TWS"]


@app.route('/')
def index():
  return "hello! <a href='/login'>login with spotify</a>"

@app.route('/login')
def login():
  scope = 'user-read-currently-playing user-modify-playback-state'

  params = {
    'client_id': client_id,
    'response_type': 'code',
    'scope': scope,
    'redirect_uri': REDIRECT_URI,
  }

  auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

  return redirect(auth_url)


@app.route('/callback')
def callback():
  if 'error' in request.args:
    return jsonify({"error": request.args['error']})

  if 'code' in request.args:
    req_body = {
      'code': request.args['code'],
      'grant_type': 'authorization_code',
      'redirect_uri': REDIRECT_URI,
      'client_id': client_id,
      'client_secret': client_secret
    }

    response = requests.post(TOKEN_URL, data=req_body)
    print(response.text)
    token_info = response.json()

    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

    return redirect('/listening')


@app.route('/listening', methods=['POST', 'GET'])
def get_listening():
  if 'access_token' not in session:
    return redirect('/login')
  
  if datetime.now().timestamp() > session['expires_at']:
    return redirect('/refresh-token')
  
  @copy_current_request_context
  def check():
    while datetime.now().timestamp() < session['expires_at']:
      headers = {
        'Authorization': f"Bearer {session['access_token']}"
      }

      response = requests.get(SPOTIFY_GET_CURRENT_TRACK_URL, headers=headers)
      track = response.json()

      if len(track['item']['album']['artists']) != 0: 
        if track['item']['album']['artists'][0]['name'] in to_boycott:
          requests.post(SPOTIFY_SKIP_URL, headers=headers)

      time.sleep(1)
    return redirect('/refresh-token')

  threading.Thread(target=check).start()


  if request.method == 'POST':
    add_artist = request.form['add-artist']
    remove_artist = request.form['remove-artist']

  if add_artist not in to_boycott:
    to_boycott.append(add_artist)

  if remove_artist in to_boycott:
    to_boycott.remove(remove_artist)

  render_template('index.html')
  

@app.route('/refresh-token')
def refresh_token():
  if 'refresh_token' not in session:
    return redirect('/login')
  
  if datetime.now().timestamp() > session['expires_at']:
    req_body = {
      'grant_type': 'refresh_token',
      'refresh_token': session['refresh_token'],
      'client_id': client_id,
      'client_secret': client_secret
    }

    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info = response.json()

    session['access_token'] = new_token_info['access_token']
    session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

    return redirect('/listening')



#if __name__ == '__main__':
#  app.run(host='0.0.0.0', debug=True)



