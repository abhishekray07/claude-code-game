CREATE TABLE IF NOT EXISTS enrolled (
  email TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS progress (
  email TEXT NOT NULL,
  level_number INTEGER NOT NULL,
  completed_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (email, level_number),
  FOREIGN KEY (email) REFERENCES enrolled(email)
);
