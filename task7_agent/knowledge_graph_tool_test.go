package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestKnowledgeGraphQuerySuccess(t *testing.T) {
	baseDir := setupTestKnowledgeGraphDir(t)
	service := NewKnowledgeGraphService(baseDir)

	result, err := service.Query(context.Background(), &KGQueryParams{
		ScenicSpot: "故宫",
		Query:      "我想带孩子玩一天",
	})
	if err != nil {
		t.Fatalf("query failed: %v", err)
	}

	if result.ScenicSpot != "故宫" {
		t.Fatalf("unexpected scenic spot: %s", result.ScenicSpot)
	}
	if len(result.RouteSummary) == 0 {
		t.Fatalf("expected non-empty route summary")
	}
	if len(result.Suggestions) == 0 {
		t.Fatalf("expected non-empty suggestions")
	}
	if len(result.SourceFiles) < 2 {
		t.Fatalf("expected source files to include graph and quality report")
	}
}

func TestKnowledgeGraphQueryUnknownSpot(t *testing.T) {
	baseDir := setupTestKnowledgeGraphDir(t)
	service := NewKnowledgeGraphService(baseDir)

	_, err := service.Query(context.Background(), &KGQueryParams{
		ScenicSpot: "不存在景区",
		Query:      "请给我建议",
	})
	if err == nil {
		t.Fatalf("expected error for unknown scenic spot")
	}
	if !strings.Contains(err.Error(), "not found") {
		t.Fatalf("unexpected error message: %v", err)
	}
}

func TestKnowledgeGraphQueryTopKAndRanking(t *testing.T) {
	baseDir := setupTestKnowledgeGraphDir(t)
	service := NewKnowledgeGraphService(baseDir)
	topK := 1

	result, err := service.Query(context.Background(), &KGQueryParams{
		ScenicSpot: "故宫",
		Query:      "亲子 路线 门票",
		TopK:       &topK,
	})
	if err != nil {
		t.Fatalf("query failed: %v", err)
	}

	if len(result.Suggestions) != 1 {
		t.Fatalf("expected topK=1, got %d", len(result.Suggestions))
	}

	best := result.Suggestions[0]
	joined := best.Condition + best.Advice + best.ConditionType
	if !(strings.Contains(joined, "路线") || strings.Contains(joined, "门票") || strings.Contains(joined, "亲子")) {
		t.Fatalf("unexpected top suggestion: %+v", best)
	}
}

func setupTestKnowledgeGraphDir(t *testing.T) string {
	t.Helper()

	baseDir := t.TempDir()

	graph := map[string]any{
		"nodes": []map[string]any{
			{"id": "poi_午门", "type": "poi", "label": "午门"},
			{"id": "poi_太和殿", "type": "poi", "label": "太和殿"},
			{"id": "poi_御花园", "type": "poi", "label": "御花园"},
		},
		"edges": []map[string]any{
			{
				"type":   "sequence",
				"source": "poi_午门",
				"target": "poi_太和殿",
				"properties": map[string]any{
					"is_recommended":               true,
					"recommended_sequence_indices": []int{1},
				},
			},
			{
				"type":   "sequence",
				"source": "poi_太和殿",
				"target": "poi_御花园",
				"properties": map[string]any{
					"is_recommended":               true,
					"recommended_sequence_indices": []int{2},
				},
			},
		},
	}

	quality := map[string]any{
		"condition_advice_samples": []map[string]any{
			{
				"condition":      "2小时快速游路线",
				"condition_type": "route",
				"poi":            "太和殿",
				"advice":         "推荐从午门进，快速游览中轴线",
			},
			{
				"condition":      "亲子出行",
				"condition_type": "visitor_type",
				"poi":            "御花园",
				"advice":         "建议优先安排休息点并减少绕路",
			},
			{
				"condition":      "门票购买",
				"condition_type": "ticketing",
				"poi":            "午门",
				"advice":         "建议提前预约并关注放票时间",
			},
		},
	}

	fused := map[string]any{
		"scenic_spot": "故宫",
	}

	mustWriteJSON(t, filepath.Join(baseDir, "故宫_graph.json"), graph)
	mustWriteJSON(t, filepath.Join(baseDir, "故宫_quality_report.json"), quality)
	mustWriteJSON(t, filepath.Join(baseDir, "故宫_fused.json"), fused)

	return baseDir
}

func mustWriteJSON(t *testing.T, path string, payload any) {
	t.Helper()
	bytes, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	if err := os.WriteFile(path, bytes, 0o644); err != nil {
		t.Fatalf("write file failed: %v", err)
	}
}
