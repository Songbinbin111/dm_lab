package main

import (
	"sync"
	"testing"

	"github.com/cloudwego/eino/schema"
)

func TestSessionStoreBasicOps(t *testing.T) {
	store := NewSessionStore()
	store.AppendMessage("s1", schema.UserMessage("hello"))
	store.AppendMessage("s1", schema.AssistantMessage("world", nil))
	store.AppendMessage("s2", schema.UserMessage("foo"))

	ids := store.ListSessionIDs()
	if len(ids) != 2 {
		t.Fatalf("expected 2 session ids, got %d", len(ids))
	}

	msgs := store.GetMessages("s1")
	if len(msgs) != 2 {
		t.Fatalf("expected 2 messages, got %d", len(msgs))
	}

	store.DeleteSession("s1")
	if len(store.GetMessages("s1")) != 0 {
		t.Fatalf("expected s1 to be deleted")
	}
}

func TestSessionStoreConcurrentAppend(t *testing.T) {
	store := NewSessionStore()

	const workers = 8
	const each = 50

	var wg sync.WaitGroup
	wg.Add(workers)
	for i := 0; i < workers; i++ {
		go func(worker int) {
			defer wg.Done()
			for j := 0; j < each; j++ {
				store.AppendMessage("concurrent", schema.UserMessage("m"))
			}
		}(i)
	}
	wg.Wait()

	msgs := store.GetMessages("concurrent")
	expected := workers * each
	if len(msgs) != expected {
		t.Fatalf("expected %d messages, got %d", expected, len(msgs))
	}
}
