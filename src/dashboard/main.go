package main

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/a2wio/lucas/dashboard/db"
	"github.com/a2wio/lucas/dashboard/handlers"
)

// Auth credentials (defaults, can be overridden via env vars)
var (
	authUser = "a2wmin"
	authPass = "a2wssword"
)

// Session store
var (
	sessions     = make(map[string]time.Time)
	sessionMutex sync.RWMutex
	sessionTTL   = 24 * time.Hour
)

// generateSessionID creates a random session ID
func generateSessionID() string {
	b := make([]byte, 32)
	rand.Read(b)
	return hex.EncodeToString(b)
}

// isValidSession checks if a session is valid
func isValidSession(sessionID string) bool {
	sessionMutex.RLock()
	defer sessionMutex.RUnlock()
	expiry, exists := sessions[sessionID]
	return exists && time.Now().Before(expiry)
}

// createSession creates a new session
func createSession() string {
	sessionID := generateSessionID()
	sessionMutex.Lock()
	sessions[sessionID] = time.Now().Add(sessionTTL)
	sessionMutex.Unlock()
	return sessionID
}

// deleteSession removes a session
func deleteSession(sessionID string) {
	sessionMutex.Lock()
	delete(sessions, sessionID)
	sessionMutex.Unlock()
}

// authRequired wraps a handler with session authentication
func authRequired(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		cookie, err := r.Cookie("session")
		if err != nil || !isValidSession(cookie.Value) {
			http.Redirect(w, r, "/login", http.StatusFound)
			return
		}
		next(w, r)
	}
}

func main() {
	sqlitePath := os.Getenv("SQLITE_PATH")
	if sqlitePath == "" {
		sqlitePath = "/data/lucas.db"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	logPath := os.Getenv("LOG_PATH")
	if logPath == "" {
		logPath = "/data/lucas.log"
	}

	// Auth credentials from env (optional)
	if u := os.Getenv("AUTH_USER"); u != "" {
		authUser = u
	}
	if p := os.Getenv("AUTH_PASS"); p != "" {
		authPass = p
	}

	database, err := db.New(sqlitePath)
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}
	defer database.Close()

	// Template functions
	funcMap := template.FuncMap{
		"dict": func(values ...interface{}) map[string]interface{} {
			m := make(map[string]interface{})
			for i := 0; i < len(values); i += 2 {
				if i+1 < len(values) {
					m[values[i].(string)] = values[i+1]
				}
			}
			return m
		},
		"formatNumber": func(n int) string {
			// Format number with commas (e.g., 1234567 -> 1,234,567)
			str := fmt.Sprintf("%d", n)
			if len(str) <= 3 {
				return str
			}
			var result []byte
			for i, c := range str {
				if i > 0 && (len(str)-i)%3 == 0 {
					result = append(result, ',')
				}
				result = append(result, byte(c))
			}
			return string(result)
		},
	}

	// Parse all templates together
	tmpl, err := template.New("").Funcs(funcMap).ParseGlob("templates/*.html")
	if err != nil {
		log.Fatalf("Failed to parse templates: %v", err)
	}

	tmpl, err = tmpl.ParseGlob("templates/partials/*.html")
	if err != nil {
		log.Fatalf("Failed to parse partials: %v", err)
	}

	h := handlers.New(database, tmpl, logPath)

	// Login page
	http.HandleFunc("/login", func(w http.ResponseWriter, r *http.Request) {
		// If already logged in, redirect to home
		if cookie, err := r.Cookie("session"); err == nil && isValidSession(cookie.Value) {
			http.Redirect(w, r, "/", http.StatusFound)
			return
		}

		if r.Method == http.MethodGet {
			tmpl.ExecuteTemplate(w, "login.html", nil)
			return
		}

		// POST - handle login
		username := r.FormValue("username")
		password := r.FormValue("password")

		if subtle.ConstantTimeCompare([]byte(username), []byte(authUser)) == 1 &&
			subtle.ConstantTimeCompare([]byte(password), []byte(authPass)) == 1 {
			sessionID := createSession()
			http.SetCookie(w, &http.Cookie{
				Name:     "session",
				Value:    sessionID,
				Path:     "/",
				HttpOnly: true,
				MaxAge:   int(sessionTTL.Seconds()),
			})
			http.Redirect(w, r, "/", http.StatusFound)
			return
		}

		tmpl.ExecuteTemplate(w, "login.html", map[string]string{"Error": "Invalid username or password"})
	})

	// Logout
	http.HandleFunc("/logout", func(w http.ResponseWriter, r *http.Request) {
		if cookie, err := r.Cookie("session"); err == nil {
			deleteSession(cookie.Value)
		}
		http.SetCookie(w, &http.Cookie{
			Name:   "session",
			Value:  "",
			Path:   "/",
			MaxAge: -1,
		})
		http.Redirect(w, r, "/login", http.StatusFound)
	})

	// Page routes (with session auth)
	http.HandleFunc("/", authRequired(h.Index))
	http.HandleFunc("/sessions", authRequired(h.SessionsPage))
	http.HandleFunc("/costs", authRequired(h.CostsPage))
	http.HandleFunc("/runbooks", authRequired(h.RunbooksPage))

	// HTMX partial routes (with session auth)
	http.HandleFunc("/partials/runs", authRequired(h.RunsList))
	http.HandleFunc("/partials/run", authRequired(h.RunDetail))
	http.HandleFunc("/partials/stats", authRequired(h.Stats))
	http.HandleFunc("/partials/log", authRequired(h.LiveLog))
	http.HandleFunc("/partials/sessions", authRequired(h.SessionsList))

	// API routes (with session auth)
	http.HandleFunc("/api/namespaces", authRequired(h.APINamespaces))
	http.HandleFunc("/api/runs", authRequired(h.APIRuns))
	http.HandleFunc("/api/run", authRequired(h.APIRun))
	http.HandleFunc("/api/sessions", authRequired(h.APISessions))
	http.HandleFunc("/api/session", authRequired(h.APIDeleteSession))

	// Health check (no auth - for k8s probes)
	http.HandleFunc("/health", h.Health)

	// Static assets (no auth - needed for login page)
	http.Handle("/assets/", http.StripPrefix("/assets/", http.FileServer(http.Dir("templates/assets"))))

	log.Printf("Dashboard starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
