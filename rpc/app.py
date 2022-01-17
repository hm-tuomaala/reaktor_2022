import sqlite3
import requests
import json
import urllib.parse
import atexit
from flask import Flask, render_template
from flask_apscheduler import APScheduler

app = Flask(__name__)

API_BASE = "bad-api-assignment.reaktor.com"

scheduler = APScheduler()



def get_winner(a, b):
    win = {
        "SCISSORS" : "PAPER",
        "PAPER" : "ROCK",
        "ROCK" : "SCISSORS"
    }

    if a["played"] == b["played"]:
        return "Tie"
    else:
        return a["name"] if win[a["played"]] == b["played"] else b["name"]


def get_db_connection():
    # Set time out to 20min -> clients must wait while database is updateing
    conn = sqlite3.connect("rpc/database.db", timeout=1200)
    return conn

def query_db(query, args = ()):
    cur = get_db_connection().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return rv

def update_db_from_history():
    api = "https://" + API_BASE
    cursor = "/rps/history"
    conn = get_db_connection()
    count = 0
    conn.execute("BEGIN TRANSACTION")
    try:
        while cursor:
            d = requests.get(api + cursor).json()
            d["data"] = sorted(d["data"], key=lambda x: -x['t'])
            for game in d["data"]:
                id = game["gameId"]
                type = game["type"]
                time = game["t"]
                player_a = game["playerA"]
                player_b = game["playerB"]

                if player_a["name"] != player_b["name"]:
                    winner = get_winner(player_a, player_b)

                    conn.execute(
                        "INSERT INTO games (id, time, winner) VALUES (?, ?, ?)",
                        (id, time, winner)
                    )

                    conn.execute(
                        "INSERT OR IGNORE INTO players (name, slug) VALUES (?, ?)",
                        (
                            player_a["name"],
                            urllib.parse.quote(player_a["name"])
                        )
                    )

                    conn.execute(
                        "INSERT OR IGNORE INTO players (name, slug) VALUES (?, ?)",
                        (
                            player_b["name"],
                            urllib.parse.quote(player_b["name"])
                        )
                    )

                    conn.execute(
                        "INSERT INTO games_players (player_id, game_id) VALUES (?, ?)",
                        (player_a["name"], id)
                    )

                    conn.execute(
                        "INSERT INTO games_players (player_id, game_id) VALUES (?, ?)",
                        (player_b["name"], id)
                    )

            cursor = d["cursor"]
            count += 1
            print(f"{count: } {cursor}")

        conn.commit()
        conn.close()

    except sqlite3.IntegrityError:
        conn.commit()
        conn.close()
        print("Database is now up to date")

def background_update_db():
    print("background update...")
    update_db_from_history()



@app.route('/')
def index():
    api = "https://" + API_BASE + "/rps/history"
    d = requests.get(api).json()
    d["data"] = sorted(d["data"], key=lambda x: -x['t'])
    return json.dumps(d["data"])

@app.route('/update')
def update():
    update_db_from_history()
    return "DATABASE UPDATED"


@app.route("/players")
def players():
    names = query_db(
        """SELECT name
           FROM players
           ORDER BY name ASC"""
    )
    names = ["%s" % x for x in names]
    return render_template("players.html", names = names)

@app.route("/players/<name>")
def player(name):
    player = query_db(
        """SELECT name
           FROM players
           WHERE slug = ?""",
           (name,)
    )
    print(player)
    return player[0][0] if player else f"{name} not found"

@app.route("/live")
def live():
    return render_template("live.html")

if __name__ == "__main__":
    # Database must be up to date before serving clients
    update_db_from_history()

    scheduler.api_enabled = True
    scheduler.init_app(app)
    scheduler.add_job(id = 'background_update_db', func=background_update_db, trigger="interval", minutes=5, misfire_grace_time=900)
    scheduler.start()

    app.run()
