DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS games_players;

CREATE TABLE games (
  id TEXT UNIQUE PRIMARY KEY,
  time INTEGER NOT NULL,
  winner TEXT NOT NULL
);

CREATE TABLE players (
  id TEXT UNIQUE PRIMARY KEY
);

CREATE TABLE games_players (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id TEXT NOT NULL,
  game_id TEXT NOT NULL,
  FOREIGN KEY (player_id) REFERENCES players (id),
  FOREIGN KEY (game_id) REFERENCES games (id)
  UNIQUE(player_id, game_id)
);
