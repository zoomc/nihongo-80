-- Preserve raw review ratings and sentence drafts; no client grading accepted.
ALTER TABLE events ADD COLUMN session_payload TEXT;
