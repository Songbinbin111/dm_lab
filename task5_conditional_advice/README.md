# 任务5：条件性游览建议的抽取

## 任务目标

1. 从游记文本中提取条件性建议（如“如果...建议...”“若是...可以...”）
2. 构建“条件 -> 建议”映射表
3. 分析不同游客类型（亲子、老人、情侣等）的建议差异

## 当前实现

### 抽取策略

当前版本采用“规则匹配 + 回退抽取 + 多重过滤 + 去重”流程：

1. **规则匹配（命名组）**
   - `if_then`
   - `if_not_then`
   - `condition_suffix_then`
   - `for_group_then`
   - `desire_then`
2. **候选片段增强**
   - 句子切分后，生成原句/分句/相邻分句组合
3. **回退抽取**
   - 当主规则未命中时，基于建议触发词（建议/推荐/最好/可以...）回退提取
4. **质量控制**
   - 过滤叙述性误提取（如“可以看到...”）
   - 过滤明显噪声（过短、格式异常、重复片段）
5. **去重合并**
   - 同句同建议合并
   - 条件一致且建议前后缀重复的条目合并

关键代码：
- `processor.py`
- `config/condition_patterns.json`
- `config/condition_classification.json`

### 条件类型（细化后）

- `time`（时间条件）
- `weather`（天气条件）
- `crowd`（人流条件）
- `physical`（体力条件）
- `visitor_type`（游客类型）
- `budget`（预算条件）
- `time_duration`（时长条件）
- `ticketing`（票务条件）
- `transport`（交通条件）
- `route`（路线条件）
- `equipment`（装备条件）
- `policy`（规则条件）
- `other`（其他条件）

## 文件结构

```text
task5_conditional_advice/
├── README.md
├── main.py
├── processor.py
├── analyzer.py
├── visualizer.py
├── evaluator.py
├── config/
│   ├── condition_patterns.json
│   ├── condition_classification.json
│   └── visitor_type_patterns.json
└── output/
    ├── conditional_advice.json
    ├── condition_mapping.json
    ├── visitor_analysis.json
    ├── statistics_report.json
    ├── annotation_template.xlsx
    └── visualizations/
        ├── condition_distribution.png
        ├── visitor_comparison.png
        ├── advice_network.png
        └── scenic_spot_comparison.png
```

## 使用方法

### 1. 完整流程

```bash
cd task5_conditional_advice
python main.py
```

### 2. 分阶段运行

```bash
python main.py --extract
python main.py --analyze
python main.py --visualize
python main.py --evaluate
```

## 输出说明

### `output/conditional_advice.json`

## 任务过程

- **第 1 步：运行抽取脚本**
  ```bash
  python main.py
  ```

成功结果如下:

![77254988859](E:\dataLab\assets\1772549888594.png)

![77254990319](E:\dataLab\assets\1772549903191.png)

- **第 2 步：检查配置**
  根据需要调整 `config/` 中的触发词库。
- **注意事项**：
  - 提取质量高度依赖正则表达式，建议根据语料特点增加新的 `patterns`。
  - 抽取结果会直接影响任务 7 中 Agent 的回答丰富度。
- **预计耗时**：40 - 60 分钟
