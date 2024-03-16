package main

import (
    "fmt"
    "net/http"
    "html/template"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "<html><body>Welcome to the Go Web Server! Visit /greet, /about, or /contact</body></html>")
    })

    http.HandleFunc("/about", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "<html><body><h1>About Us</h1><p>We are a team of passionate Gophers...</p></body></html>")
    })

    http.HandleFunc("/contact", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "<html><body><h1>Contact Us</h1><p>Email us at contact@example.com</p></body></html>")
    })

    http.HandleFunc("/greet", func(w http.ResponseWriter, r *http.Request) {
        name := r.URL.Query().Get("name")
        // Validate and sanitize the query param name
        if name == "" {
            http.Error(w, "Name parameter is missing", http.StatusBadRequest)
            return
        }
        // Escape the name to prevent XSS attacks
        name = template.HTMLEscapeString(name)

        // CSP header allowing only resources from the same origin. 
        // You might need to adjust this policy according to your application's requirements.
        
        // Set Content-Type header to prevent MIME-sniffing attacks
        w.Header().Set("Content-Type", "text/html; charset=utf-8")
        // Set Content-Security-Policy header
        w.Header().Set("Content-Security-Policy", "default-src 'self'")
        
        response := fmt.Sprintf("<html><body><h1>Hello, %s!</h1></body></html>", name)
        fmt.Fprint(w, response)
    })

    fmt.Println("Server is running at http://localhost:8080/")
    // serve the application over HTTPS if you want to
    // http.ListenAndServeTLS(":8080", "server.crt", "server.key", nil)
    http.ListenAndServe(":8080", nil)
}
