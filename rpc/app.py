import sqlite3
import requests
import json
import urllib.parse
import atexit
from flask import Flask, render_template, request
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

                # Filter out games where person supposedly played themselves
                if game["playerA"]["name"] != game["playerB"]["name"]:
                    winner = get_winner(game["playerA"], game["playerB"])

                    conn.execute(
                        """ INSERT INTO games
                            (
                                id,
                                time,
                                player_a,
                                player_b,
                                a_hand,
                                b_hand,
                                winner
                            ) VALUES (?, ?, ?, ?, ?, ?, ?) """,
                        (
                            game["gameId"],
                            game["t"],
                            game["playerA"]["name"],
                            game["playerB"]["name"],
                            game["playerA"]["played"],
                            game["playerB"]["played"],
                            winner
                        )
                    )

            cursor = d["cursor"]
            count += 1
            print(f"{count: } {cursor}")

        conn.commit()
        conn.close()

    except sqlite3.IntegrityError:
        # Unique id error -> reached the newest game found in the database
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


@app.route("/players", methods=["GET"])
def players():
    names = query_db(
        """ SELECT DISTINCT player_a AS name
              FROM games
             UNION
            SELECT DISTINCT player_b AS name
              FROM games """
    )
    names = ["%s" % x for x in names]
    return render_template("players.html", names = names)

@app.route("/players/<name>")
def player(name):
    data = {}
    stats = query_db(
        """ SELECT q1.name,
                   q1.hand,
                   q1.hand_count,
                   q2.total AS total_games,
                   q3.wins,
                   printf('%.5f',(q3.wins * 1.0 / q2.total)) AS win_ratio
              FROM (
                   SELECT name,
                          hand,
                          COUNT(*) AS hand_count
                     FROM (
                          SELECT player_a AS name,
                                 a_hand AS hand,
                                 winner
                            FROM games
                           WHERE player_a = ?
                           UNION ALL
                          SELECT player_b AS name,
                                 b_hand AS hand,
                                 winner
                            FROM games
                           WHERE player_b = ?
                          )
                    GROUP BY name, hand
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                    ) q1
               JOIN (
                    SELECT ? AS name,
                           COUNT(*) AS total
                      FROM games
                     WHERE player_a = ?
                        OR player_b = ?
                    ) q2
                 ON q1.name = q2.name
               JOIN (
                    SELECT winner AS name,
                           COUNT(*) AS wins
                      FROM games
                     WHERE (player_a = ? AND winner = ?)
                        OR (player_b = ? AND winner = ?)
                    ) q3
                 ON q1.name = q3.name """,
        (name, name, name, name, name, name, name, name, name)
    )

    games = query_db(
        """ SELECT id,
                   DATETIME(ROUND(time / 1000), 'unixepoch', 'localtime') AS time,
                   player_a,
                   player_b,
                   a_hand,
                   b_hand,
                   winner
              FROM games
             WHERE player_a = ?
                OR player_b = ? """,
        (name, name)
    )

    try:
        data["games"] = games
        data["name"] = stats[0][0]
        data["hand"] = stats[0][1]
        data["hand_count"] = stats[0][2]
        data["total"] = stats[0][3]
        data["wins"] = stats[0][4]
        data["ratio"] = stats[0][5]
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
