import os
import sqlite3
from flask import render_template
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, apology 
from wonderwords import RandomWord


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def get_db():
    db = sqlite3.connect("gameUsers.db", check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


@app.route("/")
def index():
    return render_template("index.html")


# Create a cursor object
with get_db() as db:
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        hash TEXT NOT NULL,
        latestScore INTEGER NOT NULL DEFAULT 0,
        level INTEGER NOT NULL DEFAULT 1,
        currentXp INTEGER NOT NULL DEFAULT 0
    );
    """)

    db.commit()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
           return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
           return apology("must provide password", 400)

        # Query database for username

        username = request.form.get("username")
        db=get_db()
        rows = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall() #used chatgpt to figure out that I had to use .fetchall, otherwise it would just be a cursor object, not the data, also when trying to get one data using select, I have to place a "," due to it being a tuple.

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return render_template("index.html")

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
    db= get_db()
    if request.method == "POST":
        Username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not Username or not password or not confirmation:
            return apology("Incomplete fields", 400)
        elif password != confirmation:
            return apology("Passwords do not match", 400)
        if db.execute("SELECT * FROM users WHERE username = ?", (Username,)).fetchone() is None:
            passwordhashy = generate_password_hash(password)
            db.execute("INSERT INTO users(username,hash) VALUES(?,?)",(Username,passwordhashy))
            rows = db.execute("SELECT id FROM users WHERE username = ?",(Username,))
            db.commit()
            if not rows:
                return apology("registration failed", 400)
            else:
                return redirect("/login")

        else:
            return apology("Username already exists", 400)

    else:
        return render_template("register.html")
    
@app.route("/play", methods=["GET", "POST"])
@login_required
def updateProfile():
    db= get_db()
    r = RandomWord()
    word = r.word(include_parts_of_speech=["noun"])
    if request.method == "POST":
        score = 0
        text = request.form.get("transcriptInput")
        if text == None:
            return apology("Blank message",400)
        elapsedTime = (int)(request.form.get("elapsedTime"))
        letters = sum(1 for ch in text if ch.isalpha())
        words =  sum(1 for ch in text if ch==" ") + 1
        scentences = text.count(";")+text.count("?")+text.count(".")+text.count("!")
        L = letters/words * 100
        S = scentences/words * 100
        index = round(0.0588 * L - 0.296 * S - 15.8)
        score += (index*2)
        score -= text.count("uh") + text.count("um")
        if word not in text:
            score-=5
        if elapsedTime>60:
            score-= 3*(elapsedTime-60)
        elif elapsedTime<45:
            score -= 3*(45-elapsedTime)
        #update level and xp
        currentLevel = (db.execute("SELECT level FROM users WHERE id = ?",(session["user_id"],))).fetchone()["level"]
        currentXp = (db.execute("SELECT currentXp FROM users WHERE id = ?",(session["user_id"],))).fetchone()["currentXp"]
        db.execute("UPDATE users SET latestScore = ? where id = ?", (score, session["user_id"]))
        if score+currentXp >= currentLevel * 10:
            db.execute("UPDATE users SET level = ? WHERE id = ?",(currentLevel+1,session["user_id"]))
            db.execute("UPDATE users SET currentXp = (currentXp-?) WHERE id = ?",(currentXp,session["user_id"]))
        elif score>0:
            db.execute("UPDATE users SET currentXp = (currentXp+?) WHERE id = ?",(score,session["user_id"]))
        level = db.execute("SELECT level FROM users WHERE id =?", (session["user_id"],)).fetchone()["level"]
        xp = db.execute("SELECT currentXp FROM users WHERE id =?", (session["user_id"],)).fetchone()["currentXp"]
        db.commit()
        return render_template("score.html",index=index,text=text,elapsedTime=elapsedTime,score = score,level = level, xp = xp,levelXp = level * 10)
    else:
        return render_template("play.html",word=word)
    
@app.route("/score", methods=["GET", "POST"])
@login_required
def displayScore():
    db = get_db()
    score = db.execute("SELECT latestScore FROM users WHERE id = ?", (session["user_id"],)).fetchone()["latestScore"]
    level = db.execute("SELECT level FROM users WHERE id =?", (session["user_id"],)).fetchone()["level"]
    xp = db.execute("SELECT currentXp FROM users WHERE id =?", (session["user_id"],)).fetchone()["currentXp"]
    return render_template("score.html",text = "Play a round, your last round's score is being displayed currently if you have played",score = score,level = level, xp = xp,elapsedTime = 0,levelXp = level * 10)
    

