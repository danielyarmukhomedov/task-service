package main

import (
"encoding/json"
"log"
"net/http"
"sync"
)

type Stats struct {
TotalTasks int `json:"total_tasks"`
}

var (
totalTasks int
mutex      sync.Mutex
)

func main() {
// Эндпоинт 1: Отдает текущую статистику для фронтенда
http.HandleFunc("/analytics", func(w http.ResponseWriter, r *http.Request) {
w.Header().Set("Content-Type", "application/json")
mutex.Lock()
json.NewEncoder(w).Encode(Stats{TotalTasks: totalTasks})
mutex.Unlock()
})

// Эндпоинт 2: Принимает сигналы от фронтенда для увеличения счетчика
http.HandleFunc("/analytics/increment", func(w http.ResponseWriter, r *http.Request) {
if r.Method == http.MethodPost {
mutex.Lock()
totalTasks++
mutex.Unlock()
w.WriteHeader(http.StatusOK)
w.Write([]byte(`{"status":"success"}`))
return
}
w.WriteHeader(http.StatusMethodNotAllowed)
})

log.Println("Analytics Service running on port 9000 (Pure Go)")
log.Fatal(http.ListenAndServe(":9000", nil))
}
