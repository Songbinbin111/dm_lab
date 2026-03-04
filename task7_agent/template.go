package main

import (
	"context"
	"strings"

	"github.com/cloudwego/eino/components/prompt"
	"github.com/cloudwego/eino/schema"
)

const travelSystemPrompt = `你是一名专业的旅游规划Agent，负责根据用户需求提供可执行、清晰、贴合人群特征的游览建议。

工作要求：
1. 当问题涉及景点推荐、路线安排、时长规划、游客类型（如亲子/老人/情侣）或门票交通时，优先调用工具 query_travel_knowledge_graph 获取知识图谱依据，再给出结论。
1.1 如果要调用工具，请直接发起工具调用，不要先输出“我来帮你查询/我先查一下”等过渡句。
2. 回答要结构化，尽量包含：推荐路线、关键景点、注意事项、可替代方案。
3. 若用户信息不足，先进行简短追问（如景区、时长、同行人群）。
4. 不编造数据来源；若工具没有给出足够信息，需明确说明并给出保守建议。`

func getTravelSystemPrompt() string {
	return strings.TrimSpace(travelSystemPrompt)
}

func createTemplate() prompt.ChatTemplate {
	return prompt.FromMessages(schema.FString,
		schema.SystemMessage(getTravelSystemPrompt()),
		schema.MessagesPlaceholder("chat_history", true),
		schema.UserMessage("{question}"),
	)
}

func createMessagesFromTemplate(question string, chatHistory []*schema.Message) ([]*schema.Message, error) {
	template := createTemplate()

	if chatHistory == nil {
		chatHistory = []*schema.Message{}
	}

	return template.Format(context.Background(), map[string]any{
		"question":     question,
		"chat_history": chatHistory,
	})
}
