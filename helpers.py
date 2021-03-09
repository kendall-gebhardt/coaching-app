from datetime import datetime
import json
import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
import sqlite3
from sqlite3 import Error

def db_connect(db_file):
    """ create a database connection to the SQLite database
            specified by db_file
        :param db_file: database file
        :return: Connection object or None
        """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("coach_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
