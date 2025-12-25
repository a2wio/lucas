package handlers

import (
	"html/template"
	"net/http"

	"github.com/kubeden/clopus-watcher/dashboard/db"
)

type Handler struct {
	db       *db.DB
	tmpl     *template.Template
	partials *template.Template
}

func New(database *db.DB, tmpl, partials *template.Template) *Handler {
	return &Handler{
		db:       database,
		tmpl:     tmpl,
		partials: partials,
	}
}

type PageData struct {
	Fixes   []db.Fix
	Total   int
	Success int
	Failed  int
	Pending int
}

func (h *Handler) Index(w http.ResponseWriter, r *http.Request) {
	fixes, err := h.db.GetFixes(100)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	total, success, failed, pending, err := h.db.GetStats()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	data := PageData{
		Fixes:   fixes,
		Total:   total,
		Success: success,
		Failed:  failed,
		Pending: pending,
	}

	err = h.tmpl.ExecuteTemplate(w, "index.html", data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

func (h *Handler) Fixes(w http.ResponseWriter, r *http.Request) {
	fixes, err := h.db.GetFixes(100)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	total, success, failed, pending, err := h.db.GetStats()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	data := PageData{
		Fixes:   fixes,
		Total:   total,
		Success: success,
		Failed:  failed,
		Pending: pending,
	}

	err = h.partials.ExecuteTemplate(w, "fixes-table.html", data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}
