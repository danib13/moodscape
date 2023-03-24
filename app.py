import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from random import randint
from helpers import apology, login_required, lookup, getCityLatLong, getSong, check_spotify, setup_spotify
import base64
from datetime import datetime

# Configure application
app = Flask(__name__)

# # Custom filter
# app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///mood.db")

# Make sure API keys are set
if not os.environ.get("API_KEY_GOOGLE"):
    raise RuntimeError("API_KEY_GOOGLE not set")

if not os.environ.get("API_KEY_WEATHER"):
    raise RuntimeError("API_KEY_WEATHER not set")

if not os.environ.get("SPOTIFY_CLIENT_ID"):
    raise RuntimeError("SPOTIFY_CLIENT_ID not set")

if not os.environ.get("SPOTIFY_CLIENT_SECRET"):
    raise RuntimeError("SPOTIFY_CLIENT_SECRET not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show main page"""
    user_id = session["user_id"]
    username = db.execute("SELECT username FROM users WHERE id = ?", user_id)
    try:
        name = username[0]["username"]
    except:
        return redirect("/login")

    return render_template("index.html", name=name)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # check inputs
        if not username:
            return apology("Username is blank.")
        elif db.execute("SELECT username FROM users WHERE username=?", username):
            # print("taken")
            return apology("Username already taken.")

        if not confirmation or not password:
            return apology("One of password fields is blank.")
        elif confirmation != password:
            return apology("Password does not match.")

        # insert user
        pwhash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, pwhash)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Update Password"""

    # Get user_id
    user_id = session["user_id"]

    username = request.form.get("username")
    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not username:
            return apology("Username is blank", 403)

        # Ensure old password was submitted
        elif not old_password:
            return apology("must provide current password", 403)

        # Ensure new password was submitted
        elif not new_password:
            return apology("must provide new password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("old_password")):
            return apology("invalid username and/or password", 403)

        if rows[0]["id"] == user_id:
            # insert new pw
            pwhash = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=8)
            db.execute("UPDATE users SET hash = ? WHERE id = ? and username = ?", pwhash, user_id, username)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("settings.html")

@app.route("/start", methods=["GET", "POST"])
@login_required
def start():
    """Start page"""
    user_id = session["user_id"]
    username = db.execute("SELECT username FROM users WHERE id = ?", user_id)

    try:
        name = username[0]["username"]
    except:
        return redirect("/login")

    location = request.form.get("location")
    weather = request.form.get("weather")
    songs = {}
    a_song = {}
    song_count = 6
    genre_count = 3

    if request.method == "POST":
        weather = request.form.get("weather")

        if location or weather:
            if location:
                print(location)
                coords=getCityLatLong(location)
                lat = coords["latitude"]
                lon = coords["longitude"]
                # debugging: print(f"lat:{lat}, lon:{lon}\n")
                results = lookup(lat,lon)
                print(results)
                weather = results["icon"]
            else:
                weather = weather

            # list
            genres = []
            genres = db.execute("SELECT genre FROM weather_genre WHERE weather = ?",weather)

            song_list = []
            # db.execute("DELETE FROM song_info;")
            for p in range(genre_count):
                # randomly pick one genre from that weather!
                pick_genre = genres[randint(0,len(genres)-1)]["genre"]
                print(pick_genre)

                acs=setup_spotify()
                print("SPOTIFY SETUP COMPLETE\n")

                # give genre to Spotify API
                a_song = getSong(pick_genre,acs,song_count)

                print(a_song)
                for x in a_song:
                    print("Title: " + x["title"])
                    try:
                        db.execute("INSERT INTO song_info (title, artist, genre) VALUES (?,?,?)", x["title"], x["artist"],pick_genre)
                        if x not in song_list:
                            song_list.append(x)
                    except:
                        print("Already in song directory")
                        # but not user history
                        if x not in song_list:
                            song_list.append(x)

            # WORKS UP TO HERE!! SONG RECCOMENDATIONS BASED ON GIVEN WEATHER
            print (song_list)
            for s in song_list:
                song_id = db.execute("SELECT id FROM song_info WHERE title=? and artist=?",s["title"],s["artist"])
                print(song_id) # it showed as [{'id': 531}]
                db.execute("INSERT INTO user_song_history (user_id,song_id) VALUES (?,?)", user_id, song_id[0]["id"])
                # add to user reccomendations_songs
            # songs = db.execute("SELECT * FROM song_info ORDER BY title")
            song_list=sorted(song_list, key=lambda x:x["title"])

        else:
            apology("Cannot submit Blank fields.")

        return render_template("results.html", weather=weather, songs=song_list)

    # User reached route via GET (as by clicking a link or via redirect)
    elif request.method == "GET":
        weatherTypes = db.execute("SELECT weather FROM weather_type")

        return render_template("start.html", weatherTypes=weatherTypes)
    else:
        apology("not post or get")

@app.route("/rand")
@login_required
def random_():
    """Show a some reccomendations."""
    user_id = session["user_id"]
    username = db.execute("SELECT username FROM users WHERE id = ?", user_id)

    try:
        name = username[0]["username"]
    except:
        return redirect("/login")

    weather = db.execute("SELECT weather FROM weather_type WHERE id=?",(randint(1,10),))
    # debug # print(weather[0])
    songs = {}

    # list
    genre = []
    genre = db.execute("SELECT genre FROM weather_genre WHERE weather=?",(weather[0]['weather'],))
    song_count = 2
    genre_count = len(genre)
    song_list = []

    print(genre)

    acs=setup_spotify()
    print("SPOTIFY SETUP COMPLETE\n")
    # debug # print(genre_count)
    for x in range(1,genre_count):
        pick_genre = genre[x]["genre"]
        # give genre to Spotify API
        songs = getSong(pick_genre,acs,song_count)

        # debug # print(songs)
        for x in songs:
            # debug # print("Title: " + x["title"])
            song_list.append(x)

    # debug # print(song_list)

    return render_template("random.html", name=name,weather=weather, songs=song_list)


@app.route("/history")
@login_required
def history():
    """Show history of reccommendations"""
    user_id = session["user_id"]

    list = db.execute("SELECT * FROM user_song_history WHERE user_id=?",user_id)
    # debug # print(list)
    history = db.execute("SELECT DISTINCT * FROM song_info JOIN user_song_history ON song_info.id = user_song_history.song_id WHERE (user_id=?) ORDER BY title",user_id)
    # debug # print(history)

    return render_template("history.html",history=history)