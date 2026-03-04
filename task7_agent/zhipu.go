package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/components/model"
)

func createOpenAIChatModel(ctx context.Context) (model.ToolCallingChatModel, error) {
	key := firstNonEmptyEnv("OPENAI_API_KEY", "ZHIPU_API_KEY")
	modelName := firstNonEmptyEnv("OPENAI_MODEL_NAME", "ZHIPU_MODEL_NAME")
	baseURL := firstNonEmptyEnv("OPENAI_API_BASE", "OPENAI_BASE_URL", "OPENAI_BASEURL", "ZHIPU_API_BASE", "ZHIPU_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.openai.com/v1"
	}

	if key == "" {
		return nil, errors.New("OPENAI_API_KEY is required")
	}
	if modelName == "" {
		return nil, errors.New("OPENAI_MODEL_NAME is required")
	}

	transport := &http.Transport{
		Proxy: http.ProxyFromEnvironment,
	}
	client := &http.Client{
		Timeout:   90 * time.Second,
		Transport: transport,
	}

	chatModel, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
		BaseURL:    baseURL,
		Model:      modelName,
		APIKey:     key,
		HTTPClient: client,
	})
	if err != nil {
		return nil, fmt.Errorf("create openai chat model failed: %w", err)
	}
	return chatModel, nil
}

func firstNonEmptyEnv(keys ...string) string {
	for _, key := range keys {
		value := os.Getenv(key)
		if value != "" {
			return value
		}
	}
	return ""
}
