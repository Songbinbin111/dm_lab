package main

import (
	"sort"
	"sync"

	"github.com/cloudwego/eino/schema"
)

type SessionStore struct {
	mu            sync.RWMutex
	conversations map[string][]*schema.Message
}

func NewSessionStore() *SessionStore {
	return &SessionStore{
		conversations: make(map[string][]*schema.Message),
	}
}

func (s *SessionStore) ListSessionIDs() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	ids := make([]string, 0, len(s.conversations))
	for id := range s.conversations {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func (s *SessionStore) GetMessages(sessionID string) []*schema.Message {
	s.mu.RLock()
	defer s.mu.RUnlock()

	msgs := s.conversations[sessionID]
	out := make([]*schema.Message, 0, len(msgs))
	out = append(out, msgs...)
	return out
}

func (s *SessionStore) AppendMessage(sessionID string, msg *schema.Message) {
	if sessionID == "" || msg == nil {
		return
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	s.conversations[sessionID] = append(s.conversations[sessionID], msg)
}

func (s *SessionStore) DeleteSession(sessionID string) {
	if sessionID == "" {
		return
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.conversations, sessionID)
}
