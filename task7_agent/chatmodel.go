package main

import (
	"context"
	"fmt"
	"io"

	"github.com/cloudwego/eino/components/tool"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/flow/agent/react"
	"github.com/cloudwego/eino/schema"
)

func createTravelAgent(ctx context.Context, kgService *KnowledgeGraphService) (*react.Agent, error) {
	chatModel, err := createOpenAIChatModel(ctx)
	if err != nil {
		return nil, err
	}

	kgTool, err := newKnowledgeGraphTool(kgService)
	if err != nil {
		return nil, fmt.Errorf("create knowledge graph tool failed: %w", err)
	}

	agent, err := react.NewAgent(ctx, &react.AgentConfig{
		ToolCallingModel: chatModel,
		MaxStep:          20,
		ToolsConfig: compose.ToolsNodeConfig{
			Tools: []tool.BaseTool{kgTool},
		},
		// Some models output plain text before function call chunks in stream mode.
		// The default checker only inspects the first non-empty chunk and may miss tool calls.
		StreamToolCallChecker: fullStreamToolCallChecker,
		MessageModifier: func(_ context.Context, input []*schema.Message) []*schema.Message {
			output := make([]*schema.Message, 0, len(input)+1)
			output = append(output, schema.SystemMessage(getTravelSystemPrompt()))
			output = append(output, input...)
			return output
		},
	})
	if err != nil {
		return nil, fmt.Errorf("create react agent failed: %w", err)
	}

	return agent, nil
}

func streamTravelPlan(ctx context.Context, agent *react.Agent, history []*schema.Message, userMessage string) (*schema.StreamReader[*schema.Message], error) {
	messages := make([]*schema.Message, 0, len(history)+1)
	messages = append(messages, history...)
	messages = append(messages, schema.UserMessage(userMessage))
	return agent.Stream(ctx, messages)
}

func fullStreamToolCallChecker(_ context.Context, sr *schema.StreamReader[*schema.Message]) (bool, error) {
	defer sr.Close()

	for {
		msg, err := sr.Recv()
		if err == io.EOF {
			return false, nil
		}
		if err != nil {
			return false, err
		}

		if len(msg.ToolCalls) > 0 {
			return true, nil
		}
	}
}
