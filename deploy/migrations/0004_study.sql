-- Private v9 study data. The budget triggers run only for rows actually inserted;
-- RAISE rolls back the entire D1 batch, including session metadata and budget changes.
ALTER TABLE events ADD COLUMN knowledge_ids TEXT;
CREATE TABLE study_sessions (session TEXT PRIMARY KEY, day INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE rating_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
  kid TEXT NOT NULL, day INTEGER NOT NULL, rating TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX idx_rating_kid_id ON rating_events(kid, id);
CREATE TABLE study_projection (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
CREATE TRIGGER budget_event AFTER INSERT ON events BEGIN
  INSERT OR IGNORE INTO sync_budget(id,used) VALUES(substr(NEW.server_ts,1,10),0),('total',0);
  SELECT CASE WHEN (SELECT used FROM sync_budget WHERE id=substr(NEW.server_ts,1,10)) >= 1000 THEN RAISE(ABORT,'daily_budget') END;
  SELECT CASE WHEN (SELECT used FROM sync_budget WHERE id='total') >= 20000 THEN RAISE(ABORT,'storage_budget') END;
  UPDATE sync_budget SET used=used+1 WHERE id IN (substr(NEW.server_ts,1,10),'total');
END;
CREATE TRIGGER budget_rating AFTER INSERT ON rating_events BEGIN
  INSERT OR IGNORE INTO sync_budget(id,used) VALUES(substr(NEW.created_at,1,10),0),('total',0);
  SELECT CASE WHEN (SELECT used FROM sync_budget WHERE id=substr(NEW.created_at,1,10)) >= 1000 THEN RAISE(ABORT,'daily_budget') END;
  SELECT CASE WHEN (SELECT used FROM sync_budget WHERE id='total') >= 20000 THEN RAISE(ABORT,'storage_budget') END;
  UPDATE sync_budget SET used=used+1 WHERE id IN (substr(NEW.created_at,1,10),'total');
END;
CREATE INDEX idx_events_question_day_id ON events(qid,day,id);
