# 任务6：多源程序性知识的融合与可视化

## 任务目标

1. 将官方指南的结构化路线与游客游记中提取的实体进行融合。
2. 构建包含“推荐路线 + 游客高频景点”的综合游览知识图。
3. 绘制知识图谱（节点：景点/条件；边：先后顺序/条件关系）。

## 当前实现概览

当前版本已实现以下关键能力：

1. **路线统一解析**：兼容 task3 的三类路线格式，并统一为标准边结构 `normalized_routes`。
2. **游客高频景点补充**：基于 task1 游记文档频次统计 + 规则过滤 + 评分策略，将高质量游客景点补充为图节点。
3. **推荐路线识别**：
   - 单路线景区：直接采用 `main`。
   - 多路线景区：按“游客覆盖度 + 路线完整度”评分选择推荐路线。
4. **条件关系构建**：沿用 task5 条件类型，并在 task6 进行轻量清洗与结构化增强。
5. **图谱可视化**：
   - 每个景区生成一张综合知识图谱。
   - **注**：由于输入数据量较小（15篇游记），生成的图谱可能呈现较简单的线性结构（特别是故宫），这是数据稀疏性的真实反映，而非算法缺陷。

## 文件结构

```text
task6_knowledge_fusion/
├── main.py
├── data_loader.py
├── knowledge_fusion.py
├── graph_builder.py
├── visualizer.py
├── README.md
├── config/
│   ├── node_types.json
│   └── edge_types.json
└── output/
    ├── knowledge_graph/
    │   ├── 九寨沟_fused.json
    │   ├── 故宫_fused.json
    │   ├── 黄山_fused.json
    │   ├── 九寨沟_graph.json
    │   ├── 故宫_graph.json
    │   ├── 黄山_graph.json
    │   ├── 九寨沟_quality_report.json
    │   ├── 故宫_quality_report.json
    │   └── 黄山_quality_report.json
    └── visualizations/
        ├── 九寨沟_knowledge_graph.png
        ├── 故宫_knowledge_graph.png
        └── 黄山_knowledge_graph.png
```

## 运行方式

```bash
cd task6_knowledge_fusion
python main.py
```

分阶段运行：

```bash
# 仅执行融合
python main.py --fusion

# 仅构建图谱
python main.py --build

# 仅生成可视化
python main.py --visualize

# 处理单个景区
python main.py --spot 故宫
```

## 模块说明

### data_loader.py

职责：
1. 加载 task2 实体结果、task3 路线结构、task5 条件建议。
2. 加载 task1 游记原文，按景区统计游客 POI 的文档频次（1~5）。

关键点：
1. `visitor_poi_freq` 不再固定为 1，而是基于真实游记频次统计。
2. 若缺少 pandas 或源文件不可读，会自动回退为保守策略（频次=1）。

### knowledge_fusion.py

职责：
1. POI 标准化与噪声过滤。
2. 路线统一解析（`RouteNormalizer`）。
3. 官方路线 + 游客高频景点融合。
4. 推荐路线选择。

融合策略（当前）：
1. 官方 POI 作为骨架。
2. 游客候选需满足：
- 文档频次达到阈值；
- 通过候选合法性过滤（非泛词、非明显噪声）；
- 评分达到最低门槛。
3. 对通过筛选的游客景点写入 `visitor_supplemented`，并真实进入节点层。

## 任务过程

- **第 1 步：执行融合流程**
  ```bash
  python main.py
  ```
  或者分阶段运行：

  ~~~bash
  # 仅执行融合
  python main.py --fusion

  # 仅构建图谱
  python main.py --build

  # 仅生成可视化
  python main.py --visualize

  # 处理单个景区
  python main.py --spot 故宫
  ~~~

  正确结果如下：

  ![77252225058](E:\dataLab\assets\1772551473974.png)

  ​

- 注意事项：

  - **依赖关系**：这是项目的汇总任务，必须确保任务 1-5 的输出文件都已正确生成。
  - **图谱质量**：如果生成的图谱节点过多或过乱，可以调整 `knowledge_fusion.py` 中的评分阈值。

- **预计耗时**：10 分钟
