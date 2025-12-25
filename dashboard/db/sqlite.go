package db

import (
	"database/sql"

	_ "github.com/mattn/go-sqlite3"
)

type Fix struct {
	ID           int
	Timestamp    string
	Namespace    string
	PodName      string
	ErrorType    string
	ErrorMessage string
	FixApplied   string
	Status       string
}

type DB struct {
	conn *sql.DB
}

func New(path string) (*DB, error) {
	conn, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, err
	}

	// Ensure table exists
	_, err = conn.Exec(`
		CREATE TABLE IF NOT EXISTS fixes (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			timestamp TEXT NOT NULL,
			namespace TEXT NOT NULL,
			pod_name TEXT NOT NULL,
			error_type TEXT NOT NULL,
			error_message TEXT,
			fix_applied TEXT,
			status TEXT DEFAULT 'pending'
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

func (db *DB) GetFixes(limit int) ([]Fix, error) {
	rows, err := db.conn.Query(`
		SELECT id, timestamp, namespace, pod_name, error_type,
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
		err := rows.Scan(&f.ID, &f.Timestamp, &f.Namespace, &f.PodName,
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
