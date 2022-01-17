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
    # Set time out to 20min -> clients must wait while database is updating
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
                        "INSERT INTO games_players (player_name, game_id) VALUES (?, ?)",
                        (player_a["name"], id)
                    )

                    conn.execute(
                        "INSERT INTO games_players (player_name, game_id) VALUES (?, ?)",
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
        """ SELECT name
              FROM players
             ORDER BY name ASC """
    )
    names = ["%s" % x for x in names]
    return render_template("players.html", names = names)

@app.route("/players/<name>")
def player(name):
    data = {}
    games = query_db(
        """ SELECT p1.game_id AS id,
                   p1.player_name AS player1,
                   p2.player_name AS player2,
                   g.winner,
                   g.time
              FROM games_players p1
              JOIN games_players p2
                ON p1.game_id = p2.game_id
              JOIN games g
                ON p1.game_id = g.id
             WHERE p1.player_name <> p2.player_name
               AND p1.player_name = ?
             ORDER BY g.time DESC """,
        (name,)
    )

    wins = query_db(
        """ SELECT COUNT(*) AS wins
              FROM games
             WHERE winner = ? """,
        (name,)
    )

    try:
        data["games"] = games
        data["name"] = games[0][1]
        data["total"] = wins[0][0]
        data["ratio"] = "%.4f" % (data["total"] / len(data["games"]))
    except IndexError:
        # Searched person was not found in the database
        return f"{name} was not found in the database"
    return render_template("history.html", data = data)

@app.route("/live")
def live():
    return render_template("live.html", api = "ws://" + API_BASE + "/rps/live")

if __name__ == "__main__":
    # Database must be up to date before serving clients
    update_db_from_history()

    scheduler.api_enabled = True
    scheduler.init_app(app)
    scheduler.add_job(id = 'background_update_db', func=background_update_db, trigger="interval", minutes=5, misfire_grace_time=900)
    scheduler.start()

    app.run()
