package main

import (
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net/http"
	"strings"

	"github.com/cloudwego/eino/schema"
)

//go:embed web/*
var webFiles embed.FS

type StreamFn func(r *http.Request, history []*schema.Message, userMessage string) (*schema.StreamReader[*schema.Message], error)

type ChatServer struct {
	store    *SessionStore
	streamFn StreamFn
	staticFS http.Handler
}

func NewChatServer(agentStream StreamFn, store *SessionStore) (*ChatServer, error) {
	if agentStream == nil {
		return nil, errors.New("agent stream function is required")
	}
	if store == nil {
		store = NewSessionStore()
	}

	subFS, err := fs.Sub(webFiles, "web")
	if err != nil {
		return nil, fmt.Errorf("load embedded web files failed: %w", err)
	}

	return &ChatServer{
		store:    store,
		streamFn: agentStream,
		staticFS: http.FileServer(http.FS(subFS)),
	}, nil
}

func (s *ChatServer) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/chat", s.handleChat)
	mux.HandleFunc("/api/history", s.handleHistory)
	mux.HandleFunc("/", s.handleWeb)
	return mux
}

func (s *ChatServer) handleWeb(w http.ResponseWriter, r *http.Request) {
	if strings.HasPrefix(r.URL.Path, "/api/") {
		http.NotFound(w, r)
		return
	}

	// Let FileServer handle "/" directly; rewriting to "/index.html"
	// triggers FileServer's canonical redirect back to "/", causing loops.
	s.staticFS.ServeHTTP(w, r)
}

func (s *ChatServer) handleChat(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	sessionID := strings.TrimSpace(r.URL.Query().Get("id"))
	message := strings.TrimSpace(r.URL.Query().Get("message"))
	if sessionID == "" || message == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "missing id or message"})
		return
	}

	history := s.store.GetMessages(sessionID)
	log.Printf("[chat] session=%s history=%d user=%q", sessionID, len(history), message)
	sr, err := s.streamFn(r, history, message)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	defer sr.Close()

	headers := w.Header()
	headers.Set("Content-Type", "text/event-stream")
	headers.Set("Cache-Control", "no-cache")
	headers.Set("Connection", "keep-alive")

	flusher, ok := w.(http.Flusher)
	if !ok {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "streaming unsupported"})
		return
	}

	chunks := make([]*schema.Message, 0, 16)
	var finalText strings.Builder

	for {
		msg, recvErr := sr.Recv()
		if recvErr != nil {
			if errors.Is(recvErr, schema.ErrNoValue) {
				continue
			}
			if !errors.Is(recvErr, io.EOF) {
				log.Printf("[chat] session=%s stream_recv_error=%v", sessionID, recvErr)
			}
			break
		}
		chunks = append(chunks, msg)

		if len(msg.ToolCalls) > 0 {
			for _, tc := range msg.ToolCalls {
				log.Printf("[chat] session=%s tool_call name=%s args=%s", sessionID, tc.Function.Name, truncateLog(tc.Function.Arguments, 180))
			}
		}
		if msg.Role == schema.Tool {
			log.Printf("[chat] session=%s tool_result tool=%s content=%s", sessionID, msg.ToolName, truncateLog(msg.Content, 180))
		}

		if msg.Content != "" {
			finalText.WriteString(msg.Content)
			if err := writeSSEData(w, msg.Content); err != nil {
				log.Printf("[chat] session=%s sse_write_error=%v", sessionID, err)
				break
			}
			flusher.Flush()
		}
	}

	assistantMessage, concatErr := schema.ConcatMessages(chunks)
	if concatErr != nil || assistantMessage == nil || strings.TrimSpace(assistantMessage.Content) == "" {
		assistantMessage = schema.AssistantMessage(finalText.String(), nil)
	}

	s.store.AppendMessage(sessionID, schema.UserMessage(message))
	s.store.AppendMessage(sessionID, assistantMessage)
	log.Printf("[chat] session=%s assistant=%q", sessionID, truncateLog(assistantMessage.Content, 600))

	_, _ = w.Write([]byte("event: done\ndata: [DONE]\n\n"))
	flusher.Flush()
}

func (s *ChatServer) handleHistory(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.handleGetHistory(w, r)
	case http.MethodDelete:
		s.handleDeleteHistory(w, r)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
	}
}

func (s *ChatServer) handleGetHistory(w http.ResponseWriter, r *http.Request) {
	sessionID := strings.TrimSpace(r.URL.Query().Get("id"))
	if sessionID == "" {
		writeJSON(w, http.StatusOK, map[string]any{"ids": s.store.ListSessionIDs()})
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"id":       sessionID,
		"messages": s.store.GetMessages(sessionID),
	})
}

func (s *ChatServer) handleDeleteHistory(w http.ResponseWriter, r *http.Request) {
	sessionID := strings.TrimSpace(r.URL.Query().Get("id"))
	if sessionID == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "missing id"})
		return
	}

	s.store.DeleteSession(sessionID)
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeSSEData(w http.ResponseWriter, data string) error {
	data = strings.ReplaceAll(data, "\r\n", "\n")
	for _, line := range strings.Split(data, "\n") {
		if _, err := fmt.Fprintf(w, "data: %s\n", line); err != nil {
			return err
		}
	}
	_, err := w.Write([]byte("\n"))
	return err
}

func truncateLog(s string, n int) string {
	s = strings.TrimSpace(s)
	if n <= 0 || len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
