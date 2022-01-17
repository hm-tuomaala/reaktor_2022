DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS games_players;

CREATE TABLE games (
  id TEXT UNIQUE PRIMARY KEY,
  time INTEGER NOT NULL,
  winner TEXT NOT NULL
);

CREATE TABLE players (
  name TEXT UNIQUE PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL
);

CREATE TABLE games_players (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_name INTEGER NOT NULL,
  game_id TEXT NOT NULL,
  FOREIGN KEY (player_name) REFERENCES players (name),
  FOREIGN KEY (game_id) REFERENCES games (id)
  UNIQUE(player_name, game_id)
);
