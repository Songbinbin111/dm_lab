package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/cloudwego/eino/schema"
	"github.com/joho/godotenv"
)

func main() {
	_ = godotenv.Load()

	ctx := context.Background()
	kgDir, err := defaultKnowledgeGraphDir()
	if err != nil {
		log.Fatalf("resolve knowledge graph dir failed: %v", err)
	}

	kgService := NewKnowledgeGraphService(kgDir)
	agent, err := createTravelAgent(ctx, kgService)
	if err != nil {
		log.Fatalf("create travel agent failed: %v", err)
	}

	store := NewSessionStore()
	server, err := NewChatServer(func(r *http.Request, history []*schema.Message, userMessage string) (*schema.StreamReader[*schema.Message], error) {
		return streamTravelPlan(r.Context(), agent, history, userMessage)
	}, store)
	if err != nil {
		log.Fatalf("create chat server failed: %v", err)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	addr := ":" + port
	log.Printf("task8 travel agent is running at http://127.0.0.1%s", addr)
	if err := http.ListenAndServe(addr, server.Handler()); err != nil {
		log.Fatalf("server exited with error: %v", err)
	}
}
