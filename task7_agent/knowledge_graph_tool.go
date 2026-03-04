package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"maps"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/components/tool/utils"
)

const defaultTopK = 5

var queryKeywordHints = []string{
	"亲子", "孩子", "老人", "长辈", "情侣", "拍照", "摄影", "门票", "预约", "路线", "顺序", "快速",
	"半天", "一天", "两天", "2小时", "两小时", "索道", "缆车", "观光车", "地铁", "避开", "高峰", "雨天", "晴天", "体力",
}

var hanWordRegexp = regexp.MustCompile(`\p{Han}{2,}`)

type KGQueryParams struct {
	ScenicSpot string `json:"scenic_spot,omitempty" jsonschema_description:"景区名称，可选值包括九寨沟、故宫、黄山"`
	Query      string `json:"query" jsonschema_description:"用户原始旅游需求"`
	TopK       *int   `json:"top_k,omitempty" jsonschema_description:"返回建议数量，默认5"`
}

type KGSuggestion struct {
	Condition     string `json:"condition"`
	ConditionType string `json:"condition_type"`
	POI           string `json:"poi"`
	Advice        string `json:"advice"`
}

type KGResult struct {
	ScenicSpot   string         `json:"scenic_spot"`
	RouteSummary []string       `json:"route_summary"`
	Suggestions  []KGSuggestion `json:"suggestions"`
	SourceFiles  []string       `json:"source_files"`
}

type adviceSample struct {
	Condition     string
	ConditionType string
	POI           string
	Advice        string
}

type rankedSuggestion struct {
	Suggestion KGSuggestion
	Score      int
}

type sequenceEdge struct {
	Source      string
	Target      string
	Index       int
	Recommended bool
}

type KnowledgeGraphService struct {
	baseDir string
}

func defaultKnowledgeGraphDir() (string, error) {
	if v := strings.TrimSpace(os.Getenv("KNOWLEDGE_GRAPH_DIR")); v != "" {
		return v, nil
	}

	wd, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("get workdir failed: %w", err)
	}

	candidates := []string{
		filepath.Join(wd, "task6_knowledge_fusion", "output", "knowledge_graph"),
		filepath.Join(wd, "..", "task6_knowledge_fusion", "output", "knowledge_graph"),
	}

	for _, c := range candidates {
		if st, err := os.Stat(c); err == nil && st.IsDir() {
			return filepath.Clean(c), nil
		}
	}

	return filepath.Clean(candidates[1]), nil
}

func NewKnowledgeGraphService(baseDir string) *KnowledgeGraphService {
	return &KnowledgeGraphService{baseDir: filepath.Clean(baseDir)}
}

func newKnowledgeGraphTool(service *KnowledgeGraphService) (tool.InvokableTool, error) {
	if service == nil {
		dir, err := defaultKnowledgeGraphDir()
		if err != nil {
			return nil, err
		}
		service = NewKnowledgeGraphService(dir)
	}

	return utils.InferTool(
		"query_travel_knowledge_graph",
		"Query the tourism knowledge graph and return route summary + condition-based suggestions.",
		service.ToolInvoke,
	)
}

func (s *KnowledgeGraphService) ToolInvoke(ctx context.Context, params *KGQueryParams) (string, error) {
	if params != nil {
		log.Printf("[kg_tool] query scenic_spot=%q top_k=%v text=%q", params.ScenicSpot, params.TopK, truncateLog(params.Query, 220))
	}

	result, err := s.Query(ctx, params)
	if err != nil {
		log.Printf("[kg_tool] query failed: %v", err)
		return "", err
	}

	log.Printf("[kg_tool] result scenic_spot=%s route_points=%d suggestions=%d", result.ScenicSpot, len(result.RouteSummary), len(result.Suggestions))

	payload, err := json.Marshal(result)
	if err != nil {
		return "", fmt.Errorf("marshal knowledge graph result failed: %w", err)
	}
	return string(payload), nil
}

func (s *KnowledgeGraphService) Query(_ context.Context, params *KGQueryParams) (*KGResult, error) {
	if params == nil {
		return nil, errors.New("params is required")
	}
	if strings.TrimSpace(params.Query) == "" {
		return nil, errors.New("query is required")
	}

	topK := defaultTopK
	if params.TopK != nil {
		topK = *params.TopK
	}
	if topK < 1 {
		topK = 1
	}
	if topK > 20 {
		topK = 20
	}

	spots, err := s.availableSpots()
	if err != nil {
		return nil, err
	}
	if len(spots) == 0 {
		return nil, fmt.Errorf("no scenic spot graph found in %s", s.baseDir)
	}

	spot := strings.TrimSpace(params.ScenicSpot)
	if spot == "" {
		spot = detectScenicSpot(params.Query, spots)
	}
	if spot == "" {
		if slices.Contains(spots, "故宫") {
			spot = "故宫"
		} else {
			spot = spots[0]
		}
	}

	if !slices.Contains(spots, spot) {
		return nil, fmt.Errorf("scenic_spot %q not found, available: %s", spot, strings.Join(spots, ", "))
	}

	graphPath := filepath.Join(s.baseDir, spot+"_graph.json")
	qualityPath := filepath.Join(s.baseDir, spot+"_quality_report.json")
	fusedPath := filepath.Join(s.baseDir, spot+"_fused.json")

	graphData, err := loadJSONMap(graphPath)
	if err != nil {
		return nil, err
	}
	qualityData, err := loadJSONMap(qualityPath)
	if err != nil {
		return nil, err
	}

	routeSummary := buildRouteSummaryFromGraph(graphData)

	samples := extractAdviceSamples(qualityData)
	if len(samples) == 0 {
		samples = extractAdviceSamplesFromGraph(graphData)
	}

	keywords := extractQueryKeywords(params.Query)
	ranked := rankAdviceSamples(samples, keywords)

	suggestions := make([]KGSuggestion, 0, topK)
	for i := 0; i < len(ranked) && i < topK; i++ {
		suggestions = append(suggestions, ranked[i].Suggestion)
	}

	if len(suggestions) == 0 && len(routeSummary) > 0 {
		suggestions = append(suggestions, KGSuggestion{
			Condition:     "推荐路线兜底",
			ConditionType: "route",
			POI:           routeSummary[0],
			Advice:        "当前条件建议不足，建议先按推荐路线游览后再细化偏好。",
		})
	}

	sourceFiles := make([]string, 0, 3)
	sourceFiles = append(sourceFiles, graphPath, qualityPath)
	if _, err := os.Stat(fusedPath); err == nil {
		sourceFiles = append(sourceFiles, fusedPath)
	}

	return &KGResult{
		ScenicSpot:   spot,
		RouteSummary: routeSummary,
		Suggestions:  suggestions,
		SourceFiles:  sourceFiles,
	}, nil
}

func (s *KnowledgeGraphService) availableSpots() ([]string, error) {
	entries, err := filepath.Glob(filepath.Join(s.baseDir, "*_graph.json"))
	if err != nil {
		return nil, fmt.Errorf("scan graph files failed: %w", err)
	}
	spots := make([]string, 0, len(entries))
	for _, entry := range entries {
		name := strings.TrimSuffix(filepath.Base(entry), "_graph.json")
		if name != "" {
			spots = append(spots, name)
		}
	}
	sort.Strings(spots)
	return spots, nil
}

func detectScenicSpot(query string, spots []string) string {
	for _, spot := range spots {
		if strings.Contains(query, spot) {
			return spot
		}
	}
	return ""
}

func loadJSONMap(path string) (map[string]any, error) {
	payload, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s failed: %w", path, err)
	}

	var decoded map[string]any
	if err := json.Unmarshal(payload, &decoded); err != nil {
		return nil, fmt.Errorf("parse %s failed: %w", path, err)
	}
	return decoded, nil
}

func buildRouteSummaryFromGraph(graph map[string]any) []string {
	nodeLabels := map[string]string{}
	if nodes, ok := graph["nodes"].([]any); ok {
		for _, rawNode := range nodes {
			node, ok := rawNode.(map[string]any)
			if !ok {
				continue
			}
			id, _ := node["id"].(string)
			label, _ := node["label"].(string)
			if id != "" && label != "" {
				nodeLabels[id] = label
			}
		}
	}

	allEdges := make([]sequenceEdge, 0)
	recommendedCount := 0

	if edges, ok := graph["edges"].([]any); ok {
		for _, rawEdge := range edges {
			edge, ok := rawEdge.(map[string]any)
			if !ok {
				continue
			}
			typeValue, _ := edge["type"].(string)
			if typeValue != "sequence" {
				continue
			}

			sourceID, _ := edge["source"].(string)
			targetID, _ := edge["target"].(string)
			sourceLabel := nodeLabels[sourceID]
			targetLabel := nodeLabels[targetID]
			if sourceLabel == "" || targetLabel == "" {
				continue
			}

			recommended := false
			index := 1_000_000
			if props, ok := edge["properties"].(map[string]any); ok {
				recommended, _ = props["is_recommended"].(bool)
				indices := extractIndices(props["recommended_sequence_indices"])
				if len(indices) == 0 {
					indices = extractIndices(props["sequence_indices"])
				}
				if len(indices) > 0 {
					sort.Ints(indices)
					index = indices[0]
				}
			}

			if recommended {
				recommendedCount++
			}

			allEdges = append(allEdges, sequenceEdge{
				Source:      sourceLabel,
				Target:      targetLabel,
				Index:       index,
				Recommended: recommended,
			})
		}
	}

	selected := allEdges
	if recommendedCount > 0 {
		selected = selected[:0]
		for _, edge := range allEdges {
			if edge.Recommended {
				selected = append(selected, edge)
			}
		}
	}

	sort.Slice(selected, func(i, j int) bool {
		if selected[i].Index == selected[j].Index {
			if selected[i].Source == selected[j].Source {
				return selected[i].Target < selected[j].Target
			}
			return selected[i].Source < selected[j].Source
		}
		return selected[i].Index < selected[j].Index
	})

	route := make([]string, 0)
	for _, edge := range selected {
		if len(route) == 0 {
			route = append(route, edge.Source, edge.Target)
			continue
		}
		if route[len(route)-1] == edge.Source {
			route = append(route, edge.Target)
			continue
		}
		if !slices.Contains(route, edge.Source) {
			route = append(route, edge.Source)
		}
		if !slices.Contains(route, edge.Target) || route[len(route)-1] != edge.Target {
			route = append(route, edge.Target)
		}
	}

	return stableUnique(route)
}

func extractIndices(raw any) []int {
	values, ok := raw.([]any)
	if !ok {
		return nil
	}

	indices := make([]int, 0, len(values))
	for _, v := range values {
		switch n := v.(type) {
		case float64:
			indices = append(indices, int(n))
		case int:
			indices = append(indices, n)
		}
	}
	return indices
}

func extractAdviceSamples(quality map[string]any) []adviceSample {
	rawList, ok := quality["condition_advice_samples"].([]any)
	if !ok {
		return nil
	}

	samples := make([]adviceSample, 0, len(rawList))
	for _, raw := range rawList {
		item, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		sample := adviceSample{
			Condition:     fmt.Sprintf("%v", item["condition"]),
			ConditionType: fmt.Sprintf("%v", item["condition_type"]),
			POI:           fmt.Sprintf("%v", item["poi"]),
			Advice:        fmt.Sprintf("%v", item["advice"]),
		}
		if strings.TrimSpace(sample.Advice) == "" {
			continue
		}
		samples = append(samples, sample)
	}

	return samples
}

func extractAdviceSamplesFromGraph(graph map[string]any) []adviceSample {
	nodeByID := map[string]map[string]any{}
	if nodes, ok := graph["nodes"].([]any); ok {
		for _, rawNode := range nodes {
			node, ok := rawNode.(map[string]any)
			if !ok {
				continue
			}
			id, _ := node["id"].(string)
			if id != "" {
				nodeByID[id] = node
			}
		}
	}

	out := make([]adviceSample, 0)
	if edges, ok := graph["edges"].([]any); ok {
		for _, rawEdge := range edges {
			edge, ok := rawEdge.(map[string]any)
			if !ok {
				continue
			}
			edgeType, _ := edge["type"].(string)
			if edgeType != "conditional" {
				continue
			}
			sourceID, _ := edge["source"].(string)
			targetID, _ := edge["target"].(string)
			source := nodeByID[sourceID]
			target := nodeByID[targetID]
			if len(source) == 0 || len(target) == 0 {
				continue
			}

			advice := ""
			if props, ok := edge["properties"].(map[string]any); ok {
				if text, ok := props["advice"].(string); ok {
					advice = text
				}
			}
			if advice == "" {
				continue
			}

			cond := ""
			condType := "other"
			if props, ok := source["properties"].(map[string]any); ok {
				if v, ok := props["raw_condition"].(string); ok && v != "" {
					cond = v
				}
				if v, ok := props["condition_type"].(string); ok && v != "" {
					condType = v
				}
			}
			if cond == "" {
				if label, ok := source["label"].(string); ok {
					cond = label
				}
			}
			poi, _ := target["label"].(string)

			out = append(out, adviceSample{Condition: cond, ConditionType: condType, POI: poi, Advice: advice})
		}
	}
	return out
}

func extractQueryKeywords(query string) []string {
	query = strings.TrimSpace(query)
	if query == "" {
		return nil
	}

	keywords := make([]string, 0, 32)
	for _, hint := range queryKeywordHints {
		if strings.Contains(query, hint) {
			keywords = append(keywords, hint)
		}
	}
	keywords = append(keywords, hanWordRegexp.FindAllString(query, -1)...)
	return stableUnique(keywords)
}

func rankAdviceSamples(samples []adviceSample, keywords []string) []rankedSuggestion {
	ranked := make([]rankedSuggestion, 0, len(samples))
	for _, sample := range samples {
		text := strings.Join([]string{sample.Condition, sample.ConditionType, sample.POI, sample.Advice}, " ")
		score := 0
		for _, keyword := range keywords {
			if keyword != "" && strings.Contains(text, keyword) {
				score++
			}
		}
		if score == 0 {
			score = 1
		}
		ranked = append(ranked, rankedSuggestion{
			Suggestion: KGSuggestion{
				Condition:     sample.Condition,
				ConditionType: sample.ConditionType,
				POI:           sample.POI,
				Advice:        sample.Advice,
			},
			Score: score,
		})
	}

	sort.SliceStable(ranked, func(i, j int) bool {
		if ranked[i].Score == ranked[j].Score {
			if ranked[i].Suggestion.ConditionType == ranked[j].Suggestion.ConditionType {
				return ranked[i].Suggestion.Condition < ranked[j].Suggestion.Condition
			}
			return ranked[i].Suggestion.ConditionType < ranked[j].Suggestion.ConditionType
		}
		return ranked[i].Score > ranked[j].Score
	})

	return deduplicateRanked(ranked)
}

func deduplicateRanked(items []rankedSuggestion) []rankedSuggestion {
	seen := map[string]struct{}{}
	result := make([]rankedSuggestion, 0, len(items))
	for _, item := range items {
		key := strings.TrimSpace(item.Suggestion.Condition) + "|" + strings.TrimSpace(item.Suggestion.POI) + "|" + strings.TrimSpace(item.Suggestion.Advice)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		result = append(result, item)
	}
	return result
}

func stableUnique(values []string) []string {
	seen := map[string]struct{}{}
	result := make([]string, 0, len(values))
	for _, v := range values {
		v = strings.TrimSpace(v)
		if v == "" {
			continue
		}
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		result = append(result, v)
	}
	return result
}

func cloneAnyMap(m map[string]any) map[string]any {
	if m == nil {
		return nil
	}
	copied := make(map[string]any, len(m))
	maps.Copy(copied, m)
	return copied
}
