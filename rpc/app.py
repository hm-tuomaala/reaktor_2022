import sqlite3
import requests
import json
import os
import math
from flask import Flask, render_template, request, redirect, make_response
from flask_apscheduler import APScheduler

app = Flask(__name__)

API_BASE = "bad-api-assignment.reaktor.com"
DATABASE = os.path.join(os.path.dirname(__file__), 'database.db')

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

def paginate(items_list, items_per_page, page):
    ret_items = {}
    pages = {}
    items_per_page = 100

    for i in range(math.ceil(len(items_list) / items_per_page)):
        pages[i + 1] = items_list[i * items_per_page : (i + 1) * items_per_page]

    ret_items["pages"] = len(pages.keys())
    ret_items["list"] = pages[page]
    ret_items["next"] = None if page == ret_items["pages"] else page + 1
    ret_items["prev"] = None if page == 1 else page - 1
    ret_items["current"] = page

    return ret_items


def get_db_connection():
    # Set time out to 20min -> clients must wait while database is updating
    conn = sqlite3.connect(DATABASE, timeout=1200)
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

                # Filter out games where a person played themselves :D
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



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/update")
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
    page = request.args.get("page", 1, type=int)

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
                   '(' || a_hand || ')',
                   '(' || b_hand || ')',
                   player_b,
                   winner
              FROM games
             WHERE player_a = ?
                OR player_b = ?
             ORDER BY 2 DESC """,
        (name, name)
    )

    g = [('{0:<25} {1:<25} {2:<18} {3:>10} vs. {4:<11} {5:<}'.format(x[0], x[1], x[2], x[3], x[4], x[5]), x[6]) for x in games]

    items_per_page = 100
    ret_items = paginate(g, items_per_page, page)

    try:
        data["name"] = stats[0][0]
        data["hand"] = stats[0][1]
        data["hand_count"] = stats[0][2]
        data["total"] = stats[0][3]
        data["wins"] = stats[0][4]
        data["ratio"] = stats[0][5]
    except IndexError:
        # Searched person was not found in the database
        return f"{name} was not found in the database"
    return render_template("history.html", data = data, games=ret_items)

@app.route("/live")
def live():
    return render_template("live.html", api = "ws://" + API_BASE + "/rps/live")


@app.route("/games")
def games():
    page = request.args.get("page", 1, type=int)
    mg_cookie = request.cookies.get("most_games")

    data = {}

    games = query_db(
        """ SELECT id,
                   DATETIME(ROUND(time / 1000), 'unixepoch', 'localtime') AS time,
                   player_a,
                   '(' || a_hand || ')',
                   '(' || b_hand || ')',
                   player_b,
                   winner
              FROM games
             ORDER BY 2 DESC """
    )

    g = [
        ['{0:<25} {1:<25} <strong>{2:<18} {3:>10}</strong> vs. {4:<11} {5:<}'.format(x[0], x[1], x[2], x[3], x[4], x[5])] if x[2] == x[6] else
        ['{0:<25} {1:<25} {2:<18} {3:>10} vs. <strong>{4:<11} {5:<}</strong>'.format(x[0], x[1], x[2], x[3], x[4], x[5])] if x[5] == x[6] else
        ['{0:<25} {1:<25} {2:<18} {3:>10} vs. {4:<11} {5:<}'.format(x[0], x[1], x[2], x[3], x[4], x[5])] for x in games
    ]

    items_per_page = 200
    ret_items = paginate(g, items_per_page, page)

    if mg_cookie:
        # Get stats from the browser memory

        mw_cookie = request.cookies.get("most_wins")
        br_cookie = request.cookies.get("best_ratio")
        mph_cookie = request.cookies.get("mph")
        mvh_cookie = request.cookies.get("mvh")

        data["most_games"] = mg_cookie
        data["most_wins"] = mw_cookie
        data["best_ratio"] = br_cookie
        data["mph"] = mph_cookie
        data["mvh"] =  mvh_cookie

        print("RETURN DATA FROM COOKIES")

        return render_template('games.html', data=data, games=ret_items)

    stats = query_db(
        """ SELECT q1.player || ' (' || q1.games || ')' AS most_games,
                   q2.player || ' (' || q2.wins || ')' AS most_wins,
                   q3.player || ' (' || printf('%.5f',q3.ratio) || ')' AS best_ratio,
                   q4.hand || ' (' || q4.total || ')' AS mph,
                   q5.hand || ' (' || q5.total || ')' AS mvh
              FROM (
                   SELECT player, COUNT(*) AS games, 1 AS j
                     FROM (
                          SELECT player_a AS player FROM games
                           UNION ALL
                          SELECT player_b AS player FROM games
                          )
                    GROUP BY player
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                 ) q1
            JOIN (
                 SELECT player, COUNT(*) AS wins, 1 AS j
                   FROM (
                        SELECT player_a AS player FROM games
                         WHERE winner = player_a
                         UNION ALL
                        SELECT player_b AS player FROM games
                         WHERE winner = player_b
                         )
                   GROUP BY player
                   ORDER BY COUNT(*) DESC
                   LIMIT 1
                 ) q2
              ON q1.j = q2.j
            JOIN (
                 SELECT w.player, wins, games, (wins * 1.0 / games) AS ratio, 1 AS j
                   FROM (
                        SELECT player, COUNT(*) AS wins
                          FROM (
                               SELECT player_a AS player FROM games
                                WHERE winner = player_a
                                UNION ALL
                               SELECT player_b AS player FROM games
                                WHERE winner = player_b
                               )
                         GROUP BY player
                         ORDER BY COUNT(*) DESC
                         ) w
                    JOIN (
                         SELECT player, COUNT(*) AS games
                           FROM (
                                SELECT player_a AS player FROM games
                                 UNION ALL
                                SELECT player_b AS player FROM games
                                )
                          GROUP BY player
                          ORDER BY COUNT(*) DESC
                          ) g
                      ON w.player = g.player
                   ORDER BY 4 DESC
                   LIMIT 1
                 ) q3
              ON q1.j = q3.j
            JOIN (
                 SELECT hand, COUNT(*) AS total, 1 AS j
                   FROM (
                        SELECT a_hand AS hand FROM games
                         UNION ALL
                        SELECT b_hand AS hand FROM games
                        )
                  GROUP BY hand
                  ORDER BY COUNT(*) DESC
                  LIMIT 1
                  ) q4
               ON q1.j = q4.j
             JOIN (
                  SELECT hand, COUNT(*) AS total, 1 AS j
                    FROM (
                         SELECT a_hand AS hand FROM games
                          WHERE winner = player_a
                          UNION ALL
                         SELECT b_hand AS hand FROM games
                          WHERE winner = player_b
                         )
                   GROUP BY hand
                   ORDER BY COUNT(*) DESC
                   LIMIT 1
                  ) q5
               ON q1.j = q5.j """
    )

    print("DATA FROM THE QUERY")

    data["most_games"] = stats[0][0]
    data["most_wins"] = stats[0][1]
    data["best_ratio"] = stats[0][2]
    data["mph"] = stats[0][3]
    data["mvh"] =  stats[0][4]

    resp = make_response(render_template('games.html', data=data, games=ret_items))

    resp.set_cookie("most_games", stats[0][0], max_age=5*60)
    resp.set_cookie("most_wins", stats[0][1], max_age=5*60)
    resp.set_cookie("best_ratio", stats[0][2], max_age=5*60)
    resp.set_cookie("mph", stats[0][3], max_age=5*60)
    resp.set_cookie("mvh", stats[0][4], max_age=5*60)

    return resp



if __name__ == "__main__":
    # Database must be up to date before serving clients
    update_db_from_history()

    scheduler.api_enabled = True
    scheduler.init_app(app)
    scheduler.add_job(id = 'background_update_db', func=background_update_db, trigger="interval", minutes=5, misfire_grace_time=900)
    scheduler.start()

    app.run()
