CREATE TABLE leaderboard_scores (
  mode TEXT NOT NULL CHECK (mode IN ('classic', 'constance')),
  nickname_key TEXT NOT NULL,
  nickname TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 9999),
  achieved_at TEXT NOT NULL,
  PRIMARY KEY (mode, nickname_key)
);

CREATE INDEX leaderboard_rank
ON leaderboard_scores (mode, score DESC, achieved_at ASC);
