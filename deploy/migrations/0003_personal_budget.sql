-- Small explicit application budgets, independent of Cloudflare's larger free limits.
CREATE TABLE IF NOT EXISTS sync_budget (id TEXT PRIMARY KEY, used INTEGER NOT NULL DEFAULT 0);
