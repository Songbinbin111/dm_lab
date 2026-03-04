# 任务 7：旅游规划智能助手 (Agent)

## 任务目标
构建基于知识图谱的交互式 Agent。

## 文件结构

```text
task7_agent/
├── main.go
├── knowledge_graph_tool.go
├── go.mod
├── go.sum
└── .env
```

## 任务过程

- **第 1 步：智谱AI开放平台登录**:

  登录 [智谱AI开放平台](https://open.bigmodel.cn/)，在 API Keys 页面创建一个新的密钥（Secret Key）。复制这个新创建的密钥。

- **第 2 步：环境配置**
  安装 Go 语言（1.225版本）(从[Go官网](https://golang.google.cn/dl/)下载对应系统环境的)，并在 `task7_agent` 目录下创建 `.env` 文件（3min）：
  ```env
  OPENAI_API_KEY=your_zhipu_key_here
  OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4
  OPENAI_MODEL_NAME="glm-4"
  ```

- **第 3 步：运行 Agent**
  ```bash
  go run .
  ```
  ![77259467364](E:\dataLab\task7_agent\assets\1772594673647.png)

  ![77259470113](E:\dataLab\task7_agent\assets\1772594701134.png)

  注意事项**：

  - **端口冲突**：默认使用 8080 端口，若被占用请在 `main.go` 中修改。
  - **工具链接**：Agent 会读取任务 6 的 JSON 路径，请确保路径配置正确。

- **预计耗时**：40 - 60 分钟
