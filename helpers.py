import os
import requests
import urllib.parse
import json
import base64

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(latitude,longitude):
    """Look up weather at Lat,Long ."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY_WEATHER")
        url = f"https://api.pirateweather.net/forecast/{api_key}/{latitude},{longitude}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        result = response.json()
        return {
            "temp": result["currently"]["temperature"],
            "tempMin": int(result["daily"]["data"][0]["temperatureLow"]),
            "tempMax": result["daily"]["data"][0]["temperatureHigh"],
            "icon": result["currently"]["icon"]
        }
    # data is a list, not a dictionary, so it needs [0]

    # add more exception handlers to see the issue and cause
    except KeyError as ke:
        print(f"KeyError: {ke}")
        return None
    except TypeError as te:
        print(f"TypeError: {te}")
        return None
    except ValueError as ve:
        print(f"ValueError: {ve}")
        return None
    except requests.RequestException as re:
        print(f"RequestException: {re}")
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None


def getCityLatLong(cityName):
    """Look up Lat,Long for city."""

    # Contact API
    try:
        # Set up Request
        api_key = os.environ.get("API_KEY_GOOGLE")
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'address': cityName, 'key': api_key}

        # Send the API Request
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        # to get things like "new york" to work, we had to remove response.text
        # since it was getting 2 values but expected 1
        result = response.json() # response.json(response.text)
        location = result['results'][0]['geometry']['location']
        latitude = float(location['lat'])
        longitude = float(location['lng'])
        # debugging: print(f"latitude:{latitude},longitude:{longitude}\n")
        return {
            "latitude": latitude,
            "longitude": longitude
        }
    # add more exception handlers to see the issue and cause
    except KeyError as ke:
        print(f"KeyError: {ke}")
        return None
    except TypeError as te:
        print(f"TypeError: {te}")
        return None
    except ValueError as ve:
        print(f"ValueError: {ve}")
        return None
    except requests.RequestException as re:
        print(f"RequestException: {re}")
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def setup_spotify():
    # Set up the API endpoint and client credentials
    url = 'https://accounts.spotify.com/api/token'
    client_id = os.environ.get('SPOTIFY_CLIENT_ID')
    client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')

    # Encode the client ID and client secret using base64 encoding
    client_creds = f'{client_id}:{client_secret}'
    client_creds_b64 = base64.b64encode(client_creds.encode())

    # Set up the request headers and body
    headers = {'Authorization': f'Basic {client_creds_b64.decode()}'}
    data = {'grant_type': 'client_credentials'}

    # Make a POST request to the API endpoint to request an access token
    response = requests.post(url, headers=headers, data=data)

    # Check if there was an error in the API response
    if response.status_code != 200:
        print(f"Error: {response.json()['error_description']}")
        exit()

    # Extract the access token from the API response
    access_token = response.json()['access_token']

    # Print the access token
    # print(access_token)
    return(access_token)

def check_spotify(access_token):
    # Set up the Spotify API endpoint
    url = 'https://api.spotify.com/v1/me'

    # Make a GET request to the Spotify API with the access token
    response = requests.get(url, headers={'Authorization': f'Bearer {access_token}'})

    # Check if there was an error in the API response
    if response.status_code != 200:
        print(f"Error: {response.json()['error']['message']}")
        exit()

    # Print the list of scopes granted to the access token
    print(response.json()['scopes'])


def getSong(genre,access_token,count):
   # Set up the Spotify API endpoint and search parameters
    url = 'https://api.spotify.com/v1/search'
    query = {'q': f'genre:{genre}', 'type': 'track'}

    # Get the access token from the environment variable
    access_token = access_token #os.environ.get('SPOTIFY_ACCESS_TOKEN')

    # Make a GET request to the Spotify API with the search parameters
    response = requests.get(url, params=query, headers={'Authorization': f'Bearer {access_token}'})

    # Check if there was an error in the API response
    if response.status_code != 200:
        print(f"Error: {response.json()['error']['message']}")
        exit()

    # Parse the response JSON to retrieve the track information
    tracks = response.json()['tracks']['items']

    # debug # print(tracks[0]['album']['images'])

    # get the track names and artist names for the first track
    songs = []
    i=-1
    for track in tracks[:count]:
        i+=1
        songs.append({"title": track["name"], "artist": track["artists"][0]["name"], "genre": genre, "uri": track['uri'], "image": track['album']['images'][0]})

    return songs

    # for track in tracks[:10]:
    #     return [{"title": track["name"],"artist": track["artists"][0]["name"]}]