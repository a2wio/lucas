package handlers

import (
	"encoding/json"
	"html/template"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/a2wio/lucas/dashboard/db"
)

type Handler struct {
	db      *db.DB
	tmpl    *template.Template
	logPath string
}

func New(database *db.DB, tmpl *template.Template, logPath string) *Handler {
	return &Handler{
		db:      database,
		tmpl:    tmpl,
		logPath: logPath,
	}
}

type PageData struct {
	Page          string
	Namespaces    []db.NamespaceStats
	CurrentNS     string
	Runs          []db.Run
	SelectedRun   *db.Run
	SelectedFixes []db.Fix
	Stats         *db.NamespaceStats
	Log           string
	Sessions      []db.Session
	TokenUsage    []db.TokenUsage
	CostStats     *db.CostStats
	Runbooks      []Runbook
}

type Runbook struct {
	Name        string
	Filename    string
	Description string
	Triggers    []string
}

func (h *Handler) readLog() string {
	data, err := os.ReadFile(h.logPath)
	if err != nil {
		return "No lucas log available yet. Waiting for first run..."
	}
	lines := strings.Split(string(data), "\n")
	if len(lines) > 200 {
		lines = lines[len(lines)-200:]
	}
	return strings.Join(lines, "\n")
}

// Main page - Overview
func (h *Handler) Index(w http.ResponseWriter, r *http.Request) {
	namespace := r.URL.Query().Get("ns")
	runIDStr := r.URL.Query().Get("run")

	namespaces, _ := h.db.GetNamespaces()

	// If no namespace selected and we have namespaces, select first
	if namespace == "" && len(namespaces) > 0 {
		namespace = namespaces[0].Namespace
	}

	runs, _ := h.db.GetRuns(namespace, 50)

	var selectedRun *db.Run
	var selectedFixes []db.Fix

	// If run specified, get it; otherwise get latest
	if runIDStr != "" {
		runID, _ := strconv.Atoi(runIDStr)
		selectedRun, _ = h.db.GetRun(runID)
		if selectedRun != nil {
			selectedFixes, _ = h.db.GetFixesByRun(runID)
		}
	} else if len(runs) > 0 {
		selectedRun, _ = h.db.GetRun(runs[0].ID)
		if selectedRun != nil {
			selectedFixes, _ = h.db.GetFixesByRun(runs[0].ID)
		}
	}

	var stats *db.NamespaceStats
	if namespace != "" {
		stats, _ = h.db.GetNamespaceStats(namespace)
	}

	data := PageData{
		Page:          "overview",
		Namespaces:    namespaces,
		CurrentNS:     namespace,
		Runs:          runs,
		SelectedRun:   selectedRun,
		SelectedFixes: selectedFixes,
		Stats:         stats,
		Log:           h.readLog(),
	}

	err := h.tmpl.ExecuteTemplate(w, "index.html", data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

// Sessions page
func (h *Handler) SessionsPage(w http.ResponseWriter, r *http.Request) {
	namespace := r.URL.Query().Get("ns")
	namespaces, _ := h.db.GetNamespaces()

	if namespace == "" && len(namespaces) > 0 {
		namespace = namespaces[0].Namespace
	}

	sessions, _ := h.db.GetSessions()

	var stats *db.NamespaceStats
	if namespace != "" {
		stats, _ = h.db.GetNamespaceStats(namespace)
	}

	data := PageData{
		Page:       "sessions",
		Namespaces: namespaces,
		CurrentNS:  namespace,
		Stats:      stats,
		Sessions:   sessions,
	}

	err := h.tmpl.ExecuteTemplate(w, "index.html", data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

// Costs page
func (h *Handler) CostsPage(w http.ResponseWriter, r *http.Request) {
	namespace := r.URL.Query().Get("ns")
	namespaces, _ := h.db.GetNamespaces()

	if namespace == "" && len(namespaces) > 0 {
		namespace = namespaces[0].Namespace
	}

	tokenUsage, _ := h.db.GetTokenUsage(100)
	costStats, _ := h.db.GetCostStats()

	var stats *db.NamespaceStats
	if namespace != "" {
		stats, _ = h.db.GetNamespaceStats(namespace)
	}

	data := PageData{
		Page:       "costs",
		Namespaces: namespaces,
		CurrentNS:  namespace,
		Stats:      stats,
		TokenUsage: tokenUsage,
		CostStats:  costStats,
	}

	err := h.tmpl.ExecuteTemplate(w, "index.html", data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

// Runbooks page
func (h *Handler) RunbooksPage(w http.ResponseWriter, r *http.Request) {
	namespace := r.URL.Query().Get("ns")
	namespaces, _ := h.db.GetNamespaces()

	if namespace == "" && len(namespaces) > 0 {
		namespace = namespaces[0].Namespace
	}

	var stats *db.NamespaceStats
	if namespace != "" {
		stats, _ = h.db.GetNamespaceStats(namespace)
	}

	data := PageData{
		Page:       "runbooks",
		Namespaces: namespaces,
		CurrentNS:  namespace,
		Stats:      stats,
		Runbooks:   nil, // Static runbooks defined in template
	}

	err := h.tmpl.ExecuteTemplate(w, "index.html", data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

// HTMX partials
func (h *Handler) RunsList(w http.ResponseWriter, r *http.Request) {
	namespace := r.URL.Query().Get("ns")
	runs, _ := h.db.GetRuns(namespace, 50)

	data := struct {
		Runs      []db.Run
		CurrentNS string
	}{runs, namespace}

	h.tmpl.ExecuteTemplate(w, "runs-list.html", data)
}

func (h *Handler) RunDetail(w http.ResponseWriter, r *http.Request) {
	runIDStr := r.URL.Query().Get("id")
	if runIDStr == "" {
		http.Error(w, "Missing run id", http.StatusBadRequest)
		return
	}

	runID, _ := strconv.Atoi(runIDStr)
	run, err := h.db.GetRun(runID)
	if err != nil {
		http.Error(w, "Run not found", http.StatusNotFound)
		return
	}

	fixes, _ := h.db.GetFixesByRun(runID)

	data := struct {
		Run   *db.Run
		Fixes []db.Fix
	}{run, fixes}

	h.tmpl.ExecuteTemplate(w, "run-detail.html", data)
}

func (h *Handler) Stats(w http.ResponseWriter, r *http.Request) {
	namespace := r.URL.Query().Get("ns")
	stats, _ := h.db.GetNamespaceStats(namespace)
	h.tmpl.ExecuteTemplate(w, "stats.html", stats)
}

func (h *Handler) LiveLog(w http.ResponseWriter, r *http.Request) {
	log := h.readLog()
	w.Header().Set("Content-Type", "text/html")
	escaped := template.HTMLEscapeString(log)
	escaped = strings.ReplaceAll(escaped, "\n", "<br>")
	w.Write([]byte(escaped))
}

// API endpoints (JSON)
func (h *Handler) APINamespaces(w http.ResponseWriter, r *http.Request) {
	namespaces, err := h.db.GetNamespaces()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(namespaces)
}

func (h *Handler) APIRuns(w http.ResponseWriter, r *http.Request) {
	namespace := r.URL.Query().Get("ns")
	runs, err := h.db.GetRuns(namespace, 100)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(runs)
}

func (h *Handler) APIRun(w http.ResponseWriter, r *http.Request) {
	idStr := r.URL.Query().Get("id")
	id, _ := strconv.Atoi(idStr)

	run, err := h.db.GetRun(id)
	if err != nil {
		http.Error(w, "Not found", http.StatusNotFound)
		return
	}

	fixes, _ := h.db.GetFixesByRun(id)

	result := struct {
		Run   *db.Run  `json:"run"`
		Fixes []db.Fix `json:"fixes"`
	}{run, fixes}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

// Session handlers

func (h *Handler) SessionsList(w http.ResponseWriter, r *http.Request) {
	sessions, _ := h.db.GetSessions()
	h.tmpl.ExecuteTemplate(w, "sessions-list.html", sessions)
}

func (h *Handler) APISessions(w http.ResponseWriter, r *http.Request) {
	sessions, err := h.db.GetSessions()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(sessions)
}

func (h *Handler) APIDeleteSession(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	sessionID := r.URL.Query().Get("id")
	if sessionID == "" {
		http.Error(w, "Missing session id", http.StatusBadRequest)
		return
	}

	err := h.db.DeleteSession(sessionID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Write([]byte("deleted"))
}
