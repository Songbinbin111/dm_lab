package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/cloudwego/eino/schema"
)

func TestHistoryEndpoints(t *testing.T) {
	store := NewSessionStore()
	srv, err := NewChatServer(func(_ *http.Request, _ []*schema.Message, _ string) (*schema.StreamReader[*schema.Message], error) {
		return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("ok", nil)}), nil
	}, store)
	if err != nil {
		t.Fatalf("create server failed: %v", err)
	}

	handler := srv.Handler()

	listReq := httptest.NewRequest(http.MethodGet, "/api/history", nil)
	listRec := httptest.NewRecorder()
	handler.ServeHTTP(listRec, listReq)
	if listRec.Code != http.StatusOK {
		t.Fatalf("unexpected status: %d", listRec.Code)
	}

	var listPayload map[string]any
	if err := json.Unmarshal(listRec.Body.Bytes(), &listPayload); err != nil {
		t.Fatalf("decode history list failed: %v", err)
	}
	if _, ok := listPayload["ids"]; !ok {
		t.Fatalf("history list should contain ids")
	}

	delReq := httptest.NewRequest(http.MethodDelete, "/api/history?id=test-session", nil)
	delRec := httptest.NewRecorder()
	handler.ServeHTTP(delRec, delReq)
	if delRec.Code != http.StatusOK {
		t.Fatalf("unexpected delete status: %d", delRec.Code)
	}
}

func TestRootServesIndexWithoutRedirectLoop(t *testing.T) {
	store := NewSessionStore()
	srv, err := NewChatServer(func(_ *http.Request, _ []*schema.Message, _ string) (*schema.StreamReader[*schema.Message], error) {
		return schema.StreamReaderFromArray([]*schema.Message{schema.AssistantMessage("ok", nil)}), nil
	}, store)
	if err != nil {
		t.Fatalf("create server failed: %v", err)
	}

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	srv.Handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("unexpected status for root: %d", rec.Code)
	}
	if loc := rec.Header().Get("Location"); loc != "" {
		t.Fatalf("root should not redirect, but got Location=%s", loc)
	}
}

func TestChatEndpointSSE(t *testing.T) {
	store := NewSessionStore()
	srv, err := NewChatServer(func(_ *http.Request, _ []*schema.Message, _ string) (*schema.StreamReader[*schema.Message], error) {
		return schema.StreamReaderFromArray([]*schema.Message{
			schema.AssistantMessage("你好", nil),
			schema.AssistantMessage("，推荐先走中轴线。", nil),
		}), nil
	}, store)
	if err != nil {
		t.Fatalf("create server failed: %v", err)
	}

	handler := srv.Handler()
	chatReq := httptest.NewRequest(http.MethodGet, "/api/chat?id=s1&message=我想去故宫", nil)
	chatRec := httptest.NewRecorder()
	handler.ServeHTTP(chatRec, chatReq)

	if chatRec.Code != http.StatusOK {
		t.Fatalf("unexpected chat status: %d", chatRec.Code)
	}
	if !strings.Contains(chatRec.Header().Get("Content-Type"), "text/event-stream") {
		t.Fatalf("unexpected content type: %s", chatRec.Header().Get("Content-Type"))
	}

	bodyText := chatRec.Body.String()
	if !strings.Contains(bodyText, "data: 你好") {
		t.Fatalf("expected first chunk in sse body, got: %s", bodyText)
	}
	if !strings.Contains(bodyText, "event: done") {
		t.Fatalf("expected done event in sse body")
	}

	historyReq := httptest.NewRequest(http.MethodGet, "/api/history?id=s1", nil)
	historyRec := httptest.NewRecorder()
	handler.ServeHTTP(historyRec, historyReq)
	if historyRec.Code != http.StatusOK {
		t.Fatalf("unexpected history status: %d", historyRec.Code)
	}

	var detailPayload struct {
		ID       string            `json:"id"`
		Messages []*schema.Message `json:"messages"`
	}
	if err := json.Unmarshal(historyRec.Body.Bytes(), &detailPayload); err != nil {
		t.Fatalf("decode history detail failed: %v", err)
	}
	if detailPayload.ID != "s1" {
		t.Fatalf("unexpected session id: %s", detailPayload.ID)
	}
	if len(detailPayload.Messages) != 2 {
		t.Fatalf("expected 2 messages in history, got %d", len(detailPayload.Messages))
	}
}
