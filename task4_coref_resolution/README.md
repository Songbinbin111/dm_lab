# 任务4：程序性知识的共指消解

## 任务目标

1. 从游记中找出包含代词（"它"/"这里"/"该景点"等）的句子
2. 手工标注代词所指代的实体
3. 尝试用简单的规则（最近名词匹配）实现自动指代消解

## 文件结构

```
task4_coref_resolution/
├── main.py                  # 主入口文件
├── coref_extractor.py       # 代词提取与自动消解模块
├── evaluator.py             # 评估模块：对比自动消解与手工标注
├── visualizer.py            # 可视化模块：生成统计图表
├── README.md               # 本文件
├── annotated/               # 手工标注数据
│   └── manual_annotations.json
├── output/                  # 输出结果
│   ├── pronoun_sentences.json          # 提取的包含代词的句子
│   ├── auto_resolution_results.json    # 自动消解结果
│   ├── statistics_report.json          # 统计报告
│   ├── evaluation_report.json          # 评估报告
│   ├── evaluation_report.xlsx          # Excel格式评估报告
│   ├── annotation_template.xlsx        # 手工标注模板
│   └── visualizations/                 # 可视化图表（2张）
│       ├── evaluation_summary.png      # 综合评估报告（4合1图表）
│       └── pronoun_frequency.png       # 代词频率分布图
└── data/                   # 数据文件夹（预留）
```

## 使用方法

### 1. 运行完整流程

```bash
python main.py
```

或单独运行各模块：

```bash
python coref_extractor.py  # 提取代词并自动消解
python evaluator.py         # 评估结果
python visualizer.py        # 生成可视化图表
```

### 输出说明

**核心输出文件：**
- `output/pronoun_sentences.json` - 提取的包含代词的句子
- `output/auto_resolution_results.json` - 自动消解结果
- `output/statistics_report.json` - 统计报告
- `output/evaluation_report.json` - 评估报告
- `output/evaluation_report.xlsx` - Excel格式评估报告
- `annotated/manual_annotations.json` - 手工标注数据

**可视化图表（2张）：**
- `output/visualizations/evaluation_summary.png` - 综合评估报告（4合1图表）
- `output/visualizations/pronoun_frequency.png` - 代词频率分布图

## 核心模块说明

### 1. PronounDictionary（代词词典）

定义需要处理的指代词类型：

```python
# 人称代词
PERSONAL_PRONOUNS = ['它', '它们', '他', '她', '他们', '她们']

# 指示代词（地点/方位）
DEMONSTRATIVE_PRONOUNS = ['这里', '那里', '此处', '彼处']

# 指示短语
DEMONSTRATIVE_PHRASES = ['该景点', '该景区', '园内', '宫内', '景区内']
```

### 2. PronounSentenceExtractor（代词句子提取器）

功能：
- 将文本分割为句子
- 检测句子中是否包含代词
- 提取代词及其位置信息

### 3. NearestNounResolver（最近名词匹配消解器）

消解策略（按优先级）：

1. **POI优先匹配**：优先匹配POI词典中的景点名称
2. **最近名词匹配**：在句子内找最近的名词作为先行词
3. **噪声过滤**：过滤掉明显的非实体词

### 4. CoreferenceEvaluator（评估器）

评估指标：
- 总体准确率
- 按代词类型的准确率
- 按先行词类型的准确率

## 任务过程

- **第 1 步：运行消解程序**
  ```bash
  python main.py
  ```

  ![77254726509](E:\dataLab\assets\1772547265094.png)

  或者分步运行：

  ~~~bash
  python coref_extractor.py  # 提取代词并自动消解
  python evaluator.py         # 评估结果
  python visualizer.py        # 生成可视化图表
  ~~~

  结果如下：

  ![77254981738](E:\dataLab\assets\1772549817386.png)

  ​

- **预计耗时**：15 分钟
