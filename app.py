import os
import json

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
import sqlite3
from sqlite3 import Error
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import db_connect, login_required
# import helpers

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQLite database
db_file = "volleybuilder.db"
try:
    sql_create_drills_table = """CREATE TABLE IF NOT EXISTS 'drills' (
                                        'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                        'long_name' TEXT NOT NULL, 
                                        'description' TEXT NOT NULL,
                                        'type' TEXT NOT NULL,
                                        'min_players' NUMERIC, 
                                        'max_players' NUMERIC, 
                                        'assistants_reqd' NUMERIC NOT NULL, 
                                        'skill' TEXT,
                                        'goal_qty' NUMERIC,
                                        'goal_units' TEXT,
                                        'diagram' TEXT,
                                        'video' TEXT,
                                        'contributed_by' TEXT NOT NULL,
                                        'shareable' BOOL NOT NULL
                                        );"""

    sql_create_coaches_table = """CREATE TABLE IF NOT EXISTS 'coaches' (
                                        'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                        'username' TEXT NOT NULL,
                                        'hash' TEXT NOT NULL,
                                        'name' TEXT, 
                                        'team' TEXT,
                                        'default_time' NUMERIC,
                                        'default_courts' NUMERIC,
                                        'default_assistants' NUMERIC
                                        );"""

    sql_create_players_table = """CREATE TABLE IF NOT EXISTS 'players' (
                                        'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                        'coach_id' TEXT NOT NULL, 
                                        'name' TEXT, 
                                        'number' NUMERIC,
                                        'position_primary' TEXT, 
                                        'position_secondary' TEXT
                                        );"""

    sql_create_practices_table = """CREATE TABLE IF NOT EXISTS 'practices' (
                                        'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                        'coach_id' TEXT NOT NULL, 
                                        'date' NUMERIC,
                                        'objective' TEXT, 
                                        'notes' TEXT 
                                        );"""

    sql_create_used_drills_table = """CREATE TABLE IF NOT EXISTS 'used_drills' (
                                            'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                            'drill_id' TEXT NOT NULL, 
                                            'practice_id' TEXT NOT NULL,
                                            'goal_override' TEXT, 
                                            'duration' NUMERIC 
                                            );"""

    sql_create_player_drills_table = """CREATE TABLE IF NOT EXISTS 'player_drills' (
                                            'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                                            'used_drill_id' TEXT NOT NULL, 
                                            'player_id' TEXT NOT NULL 
                                            );"""
    with db_connect(db_file) as con:
        db = con.cursor()
        # create tables
        db.execute(sql_create_drills_table)
        db.execute(sql_create_coaches_table)
        db.execute(sql_create_players_table)
        db.execute(sql_create_practices_table)
        db.execute(sql_create_used_drills_table)
        db.execute(sql_create_player_drills_table)
except Error as e:
    con.rollback()
    print(e)
finally:
    con.close()


@app.route("/")
@login_required
def index():
    """ This is the home page """
    """Show all past practices"""
    coach_id = session["coach_id"]

    # Get coach name, team name/mascot from coaches table
    with db_connect(db_file) as con:
        con.row_factory = sqlite3.Row
        db = con.cursor()
        sql_select_coach = "SELECT name, team FROM coaches WHERE id is ?"
        db.execute(sql_select_coach, (coach_id,))
        coach_rows = db.fetchone()
        sql_select_practices = "SELECT id, date, objective FROM practices WHERE coach_id is ?"
        db.execute(sql_select_practices, (coach_id,))
        practice_rows = db.fetchall()
    coach = coach_rows["name"]
    team = coach_rows["team"]

    # Get past practices from practices table
    # past_practices = {date: , objective: , skills_drills: , game_drills: }
    past_practices = []

    for row in practice_rows:
        practice_id = practice_rows[row]["id"]
        practice_date = practice_rows[row]["date"]
        practice_objv = practice_rows[row]["objective"]

        past_practices.append({"practice_id": practice_id, "date": practice_date, "objective": practice_objv})

    return render_template("index.html", past_practices=past_practices, coach=coach,
                           team=team)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        # TODO: replace with bootstrap form checking
        if not request.form.get("username"):
            return render_template("login.html")

        # Ensure password was submitted
        # TODO: replace with bootstrap form checking
        elif not request.form.get("password"):
            return render_template("login.html")

        # Query database for username
        username = request.form.get("username")
        # TODO: convert form input to lowercase and store in DB as all lower
        with db_connect(db_file) as con:
            con.row_factory = sqlite3.Row
            db = con.cursor()
            sql_find_user = "SELECT * FROM coaches WHERE username = ?"
            db.execute(sql_find_user, (username,))
            rows = db.fetchall()

        print(rows)
        # Ensure username exists and password is correct
        # TODO: Currently this throws an "index out of range" error when the user does not exist
        hashed = rows[0]["hash"]
        passwd = request.form.get("password")
        print(hashed, passwd, len(rows))
        if len(rows) != 1 or not check_password_hash(hashed, passwd):
            print("Failed Login")
            return render_template("login.html")

        # Remember which user has logged in
        session["coach_id"] = rows[0]["id"]

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

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        # TODO: replace with bootstrap form checking
        if not request.form.get("username"):
            return render_template("register.html")

        # Ensure password was submitted
        # TODO: replace with bootstrap form checking
        elif not request.form.get("password"):
            return render_template("register.html")

        # Ensure passwords match
        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("register.html")

        # Save username and password for convenience
        username = request.form.get("username")
        passwd = request.form.get("password")

        # Query database for username
        with db_connect(db_file) as con:
            db = con.cursor()
            sql_find_user = "SELECT * FROM coaches WHERE username = ?"
            db.execute(sql_find_user, (username,))
            rows = db.fetchall()

        # Ensure username DOES NOT EXIST
        # TODO: someting else
        if len(rows) != 0:
            return render_template("register.html")

        # Hash password
        hashedpass = generate_password_hash(passwd)

        # Store username and password in the database
        with db_connect(db_file) as con:
            db = con.cursor()
            sql_add_coach = "INSERT INTO coaches (username, hash) VALUES (?, ?)"
            db.execute(sql_add_coach, (username, hashedpass))
            con.commit()

        # Redirect user to login page
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/new_drill", methods=["GET", "POST"])
@login_required
def new_drill():
    if request.method == "POST":
        #do stuff
        return redirect("/")

    else:
        return render_template("new_drill.html")

# Settings page
# Build practice from template
# Build practice from scratch
# View Practice --> practice_viewer
# View Drill --> drill_viewer
# Dill index
# Add drill --> new_drill
# Analytics
