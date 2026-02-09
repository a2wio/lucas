package db

import (
	"database/sql"

	_ "github.com/mattn/go-sqlite3"
)

type Run struct {
	ID         int
	StartedAt  string
	EndedAt    string
	Namespace  string
	Mode       string
	Status     string // ok, fixed, failed, running
	PodCount   int
	ErrorCount int
	FixCount   int
	Report     string
	Log        string
}

type Fix struct {
	ID           int
	RunID        int
	Timestamp    string
	Namespace    string
	PodName      string
	ErrorType    string
	ErrorMessage string
	FixApplied   string
	Status       string
}

type Session struct {
	ThreadTS  string
	SessionID string
	Channel   string
	Namespace string
	CreatedAt string
	UpdatedAt string
}

type NamespaceStats struct {
	Namespace  string
	RunCount   int
	OkCount    int
	FixedCount int
	FailedCount int
}

type TokenUsage struct {
	ID           int
	RunID        int
	Namespace    string
	Model        string
	InputTokens  int
	OutputTokens int
	TotalTokens  int
	Cost         float64
	CreatedAt    string
}

type CostStats struct {
	TotalInputTokens  int
	TotalOutputTokens int
	TotalTokens       int
	TotalCost         float64
}

type DB struct {
	conn *sql.DB
}

func New(path string) (*DB, error) {
	conn, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, err
	}

	// Create runs table
	_, err = conn.Exec(`
		CREATE TABLE IF NOT EXISTS runs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			started_at TEXT NOT NULL,
			ended_at TEXT,
			namespace TEXT NOT NULL,
			mode TEXT NOT NULL DEFAULT 'autonomous',
			status TEXT NOT NULL DEFAULT 'running',
			pod_count INTEGER DEFAULT 0,
			error_count INTEGER DEFAULT 0,
			fix_count INTEGER DEFAULT 0,
			report TEXT,
			log TEXT
		)
	`)
	if err != nil {
		return nil, err
	}

	// Create fixes table with run_id
	_, err = conn.Exec(`
		CREATE TABLE IF NOT EXISTS fixes (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			timestamp TEXT NOT NULL,
			namespace TEXT NOT NULL,
			pod_name TEXT NOT NULL,
			error_type TEXT NOT NULL,
			error_message TEXT,
			fix_applied TEXT,
			status TEXT DEFAULT 'pending',
			FOREIGN KEY (run_id) REFERENCES runs(id)
		)
	`)
	if err != nil {
		return nil, err
	}

	// Add run_id column if it doesn't exist (migration for existing DBs)
	conn.Exec(`ALTER TABLE fixes ADD COLUMN run_id INTEGER`)

	// Create token_usage table
	_, err = conn.Exec(`
		CREATE TABLE IF NOT EXISTS token_usage (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			namespace TEXT NOT NULL,
			model TEXT NOT NULL,
			input_tokens INTEGER DEFAULT 0,
			output_tokens INTEGER DEFAULT 0,
			total_tokens INTEGER DEFAULT 0,
			cost REAL DEFAULT 0,
			created_at TEXT NOT NULL,
			FOREIGN KEY (run_id) REFERENCES runs(id)
		)
	`)
	if err != nil {
		return nil, err
	}

	return &DB{conn: conn}, nil
}

func (db *DB) Close() error {
	return db.conn.Close()
}

// Run operations

func (db *DB) CreateRun(namespace, mode string) (int64, error) {
	result, err := db.conn.Exec(`
		INSERT INTO runs (started_at, namespace, mode, status)
		VALUES (datetime('now'), ?, ?, 'running')
	`, namespace, mode)
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

func (db *DB) CompleteRun(id int64, status string, podCount, errorCount, fixCount int, report, log string) error {
	_, err := db.conn.Exec(`
		UPDATE runs SET
			ended_at = datetime('now'),
			status = ?,
			pod_count = ?,
			error_count = ?,
			fix_count = ?,
			report = ?,
			log = ?
		WHERE id = ?
	`, status, podCount, errorCount, fixCount, report, log, id)
	return err
}

func (db *DB) GetRuns(namespace string, limit int) ([]Run, error) {
	query := `
		SELECT id, started_at, COALESCE(ended_at, ''), namespace, mode, status,
		       pod_count, error_count, fix_count, COALESCE(report, ''), COALESCE(log, '')
		FROM runs
	`
	args := []interface{}{}

	if namespace != "" {
		query += " WHERE namespace = ?"
		args = append(args, namespace)
	}

	query += " ORDER BY started_at DESC LIMIT ?"
	args = append(args, limit)

	rows, err := db.conn.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var runs []Run
	for rows.Next() {
		var r Run
		err := rows.Scan(&r.ID, &r.StartedAt, &r.EndedAt, &r.Namespace, &r.Mode,
			&r.Status, &r.PodCount, &r.ErrorCount, &r.FixCount, &r.Report, &r.Log)
		if err != nil {
			return nil, err
		}
		runs = append(runs, r)
	}
	return runs, nil
}

func (db *DB) GetRun(id int) (*Run, error) {
	var r Run
	err := db.conn.QueryRow(`
		SELECT id, started_at, COALESCE(ended_at, ''), namespace, mode, status,
		       pod_count, error_count, fix_count, COALESCE(report, ''), COALESCE(log, '')
		FROM runs WHERE id = ?
	`, id).Scan(&r.ID, &r.StartedAt, &r.EndedAt, &r.Namespace, &r.Mode,
		&r.Status, &r.PodCount, &r.ErrorCount, &r.FixCount, &r.Report, &r.Log)
	if err != nil {
		return nil, err
	}
	return &r, nil
}

func (db *DB) GetLastRunTime(namespace string) (string, error) {
	var lastRun string
	err := db.conn.QueryRow(`
		SELECT COALESCE(MAX(ended_at), '') FROM runs WHERE namespace = ? AND status != 'running'
	`, namespace).Scan(&lastRun)
	return lastRun, err
}

// Namespace operations

func (db *DB) GetNamespaces() ([]NamespaceStats, error) {
	rows, err := db.conn.Query(`
		SELECT
			namespace,
			COUNT(*) as run_count,
			SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) as ok_count,
			SUM(CASE WHEN status = 'fixed' THEN 1 ELSE 0 END) as fixed_count,
			SUM(CASE WHEN status = 'failed' OR status = 'issues_found' THEN 1 ELSE 0 END) as failed_count
		FROM runs
		GROUP BY namespace
		ORDER BY namespace
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var stats []NamespaceStats
	for rows.Next() {
		var s NamespaceStats
		err := rows.Scan(&s.Namespace, &s.RunCount, &s.OkCount, &s.FixedCount, &s.FailedCount)
		if err != nil {
			return nil, err
		}
		stats = append(stats, s)
	}
	return stats, nil
}

func (db *DB) GetNamespaceStats(namespace string) (*NamespaceStats, error) {
	var s NamespaceStats
	s.Namespace = namespace

	err := db.conn.QueryRow(`SELECT COUNT(*) FROM runs WHERE namespace = ?`, namespace).Scan(&s.RunCount)
	if err != nil {
		return nil, err
	}
	// Count 'ok' status as ok
	db.conn.QueryRow(`SELECT COUNT(*) FROM runs WHERE namespace = ? AND status = 'ok'`, namespace).Scan(&s.OkCount)
	// Count 'fixed' status as fixed
	db.conn.QueryRow(`SELECT COUNT(*) FROM runs WHERE namespace = ? AND status = 'fixed'`, namespace).Scan(&s.FixedCount)
	// Count 'failed' and 'issues_found' as failed (issues that need attention)
	db.conn.QueryRow(`SELECT COUNT(*) FROM runs WHERE namespace = ? AND (status = 'failed' OR status = 'issues_found')`, namespace).Scan(&s.FailedCount)

	return &s, nil
}

// Fix operations

func (db *DB) GetFixes(limit int) ([]Fix, error) {
	rows, err := db.conn.Query(`
		SELECT id, COALESCE(run_id, 0), timestamp, namespace, pod_name, error_type,
		       COALESCE(error_message, ''), COALESCE(fix_applied, ''), status
		FROM fixes
		ORDER BY timestamp DESC
		LIMIT ?
	`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var fixes []Fix
	for rows.Next() {
		var f Fix
		err := rows.Scan(&f.ID, &f.RunID, &f.Timestamp, &f.Namespace, &f.PodName,
			&f.ErrorType, &f.ErrorMessage, &f.FixApplied, &f.Status)
		if err != nil {
			return nil, err
		}
		fixes = append(fixes, f)
	}
	return fixes, nil
}

func (db *DB) GetFixesByRun(runID int) ([]Fix, error) {
	rows, err := db.conn.Query(`
		SELECT id, COALESCE(run_id, 0), timestamp, namespace, pod_name, error_type,
		       COALESCE(error_message, ''), COALESCE(fix_applied, ''), status
		FROM fixes
		WHERE run_id = ?
		ORDER BY timestamp DESC
	`, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var fixes []Fix
	for rows.Next() {
		var f Fix
		err := rows.Scan(&f.ID, &f.RunID, &f.Timestamp, &f.Namespace, &f.PodName,
			&f.ErrorType, &f.ErrorMessage, &f.FixApplied, &f.Status)
		if err != nil {
			return nil, err
		}
		fixes = append(fixes, f)
	}
	return fixes, nil
}

func (db *DB) GetStats() (total, success, failed, pending int, err error) {
	err = db.conn.QueryRow("SELECT COUNT(*) FROM fixes").Scan(&total)
	if err != nil {
		return
	}
	err = db.conn.QueryRow("SELECT COUNT(*) FROM fixes WHERE status = 'success'").Scan(&success)
	if err != nil {
		return
	}
	err = db.conn.QueryRow("SELECT COUNT(*) FROM fixes WHERE status = 'failed'").Scan(&failed)
	if err != nil {
		return
	}
	err = db.conn.QueryRow("SELECT COUNT(*) FROM fixes WHERE status = 'pending' OR status = 'analyzing'").Scan(&pending)
	return
}

// Session operations

func (db *DB) GetSessions() ([]Session, error) {
	rows, err := db.conn.Query(`
		SELECT thread_ts, session_id, channel, COALESCE(namespace, ''), created_at, updated_at
		FROM slack_sessions
		ORDER BY updated_at DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var sessions []Session
	for rows.Next() {
		var s Session
		err := rows.Scan(&s.ThreadTS, &s.SessionID, &s.Channel, &s.Namespace, &s.CreatedAt, &s.UpdatedAt)
		if err != nil {
			return nil, err
		}
		sessions = append(sessions, s)
	}
	return sessions, nil
}

func (db *DB) GetSessionCount() (int, error) {
	var count int
	err := db.conn.QueryRow("SELECT COUNT(*) FROM slack_sessions").Scan(&count)
	return count, err
}

func (db *DB) DeleteSession(sessionID string) error {
	_, err := db.conn.Exec("DELETE FROM slack_sessions WHERE session_id = ?", sessionID)
	return err
}

// Token usage operations

func (db *DB) GetTokenUsage(limit int) ([]TokenUsage, error) {
	rows, err := db.conn.Query(`
		SELECT id, COALESCE(run_id, 0), namespace, model, input_tokens, output_tokens, total_tokens, cost, created_at
		FROM token_usage
		ORDER BY created_at DESC
		LIMIT ?
	`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var usage []TokenUsage
	for rows.Next() {
		var u TokenUsage
		err := rows.Scan(&u.ID, &u.RunID, &u.Namespace, &u.Model, &u.InputTokens, &u.OutputTokens, &u.TotalTokens, &u.Cost, &u.CreatedAt)
		if err != nil {
			return nil, err
		}
		usage = append(usage, u)
	}
	return usage, nil
}

func (db *DB) GetCostStats() (*CostStats, error) {
	var stats CostStats
	err := db.conn.QueryRow(`
		SELECT
			COALESCE(SUM(input_tokens), 0),
			COALESCE(SUM(output_tokens), 0),
			COALESCE(SUM(total_tokens), 0),
			COALESCE(SUM(cost), 0)
		FROM token_usage
	`).Scan(&stats.TotalInputTokens, &stats.TotalOutputTokens, &stats.TotalTokens, &stats.TotalCost)
	if err != nil {
		return nil, err
	}
	return &stats, nil
}

func (db *DB) RecordTokenUsage(runID int, namespace, model string, inputTokens, outputTokens int, cost float64) error {
	_, err := db.conn.Exec(`
		INSERT INTO token_usage (run_id, namespace, model, input_tokens, output_tokens, total_tokens, cost, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
	`, runID, namespace, model, inputTokens, outputTokens, inputTokens+outputTokens, cost)
	return err
}
