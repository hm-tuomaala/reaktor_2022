DROP TABLE IF EXISTS games;
-- DROP TABLE IF EXISTS players;
-- DROP TABLE IF EXISTS games_players;

CREATE TABLE games (
  id TEXT UNIQUE PRIMARY KEY,
  time INTEGER NOT NULL,
  player_a TEXT NOT NULL,
  player_b TEXT NOT NULL,
  a_hand TEXT CHECK(a_hand IN ('SCISSORS', 'ROCK', 'PAPER')),
  b_hand TEXT CHECK(b_hand IN ('SCISSORS', 'ROCK', 'PAPER')),
  winner TEXT NOT NULL
);

-- CREATE TABLE players (
--   name TEXT UNIQUE PRIMARY KEY
-- );
--
-- CREATE TABLE games_players (
--   id INTEGER PRIMARY KEY AUTOINCREMENT,
--   game_id TEXT NOT NULL,
--   player_name INTEGER NOT NULL,
--   FOREIGN KEY (game_id) REFERENCES games (id),
--   FOREIGN KEY (player_name) REFERENCES players (name),
--   UNIQUE(game_id, player_name)
-- );
