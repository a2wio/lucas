package main

import (
	"html/template"
	"log"
	"net/http"
	"os"

	"github.com/kubeden/clopus-watcher/dashboard/db"
	"github.com/kubeden/clopus-watcher/dashboard/handlers"
)

func main() {
	// Get config from environment
	sqlitePath := os.Getenv("SQLITE_PATH")
	if sqlitePath == "" {
		sqlitePath = "/data/watcher.db"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// Initialize database
	database, err := db.New(sqlitePath)
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}
	defer database.Close()

	// Parse templates
	tmpl, err := template.ParseGlob("templates/*.html")
	if err != nil {
		log.Fatalf("Failed to parse templates: %v", err)
	}

	partials, err := template.ParseGlob("templates/partials/*.html")
	if err != nil {
		log.Fatalf("Failed to parse partials: %v", err)
	}

	// Create handler
	h := handlers.New(database, tmpl, partials)

	// Routes
	http.HandleFunc("/", h.Index)
	http.HandleFunc("/fixes", h.Fixes)
	http.HandleFunc("/health", h.Health)

	log.Printf("Dashboard starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
