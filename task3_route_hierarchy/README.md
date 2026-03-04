# 任务3：游览路线的层级结构挖掘

## 任务目标
1. 分析官方指南中的路线描述方式（如"上午游览A区，下午游览B区"）
2. 构建时间维度的游览层级结构（清晨→上午→中午→下午→傍晚）
3. 探索性任务：比较官方推荐路线和游客实际路线的结构差异

## 文件结构

```
task3_route_hierarchy/
├── route_parser.py          # 路线解析器
├── route_analyzer.py        # 路线对比分析器
├── main_task3.py            # 任务3主程序
├── route_hierarchy/         # 层级结构输出
│   ├── 九寨沟_hierarchy.json
│   ├── 九寨沟_hierarchy.png
│   ├── 故宫_hierarchy.json
│   ├── 故宫_hierarchy.png
│   ├── 黄山_hierarchy.json
│   └── 黄山_hierarchy.png
└── route_comparison/        # 对比分析输出
    ├── comparison_report.json
    └── comparison_charts.png
```

## 脚本说明

### route_parser.py
路线解析器，支持三种不同格式的官方路线：
- **九寨沟格式**: `→`连接 + 时间范围
- **故宫格式**: 编号列表（1.2.3...）
- **黄山格式**: 多线路选择（线路一/二/三...）

解析内容：
- 路线节点序列（景点顺序）
- 时间节点（精确时间、时段）
- 交通方式
- 游览时长
- 路线类型（半日游/全日游/多日游）

### route_analyzer.py
路线对比分析器，对比官方推荐路线和游客实际路线：

**分析维度：**
| 维度 | 官方路线 | 游客路线 | 分析方法 |
|------|---------|---------|---------|
| 景点覆盖度 | 预设景点集合 | 实际游览景点 | Jaccard相似度 |
| 时间分布 | 规划时间 | 实际时间 | 时段对比 |
| 路线顺序 | 线性/推荐 | 实际路径 | LCS序列对比 |
| 游览节奏 | 规划时长 | 实际停留 | 时长对比 |

**关键指标：**
- `jaccard_similarity`: 使用标准化后的相似度
- `strict_jaccard_similarity`: 不使用标准化的相似度
- `normalization_delta`: 标准化对相似度的影响
- `set_similarity`: 集合相似度（覆盖视角）
- `sequence_similarity`: 顺序相似度（路线视角）
- `combined_similarity`: 综合相似度（0.6×顺序 + 0.4×集合）

### main_task3.py
任务3主程序，执行完整流程：
1. 加载数据（entity_results.json, data_cleaned.xlsx）
2. 解析官方路线（route_parser.py）
3. 生成层级结构（时间维度）
4. 对比分析（route_analyzer.py）
5. 生成可视化图表

## 使用方法

### 运行完整流程
```bash
python main_task3.py
```

### 单独运行各模块

```bash
# 只解析路线
python route_parser.py

# 只做对比分析
python route_analyzer.py
```

## 任务过程

- **第 1 步：运行分析程序**(10min)
  ```bash
  python main_task3.py
  ```
  运行结果如下：

  ![77251408448](E:\dataLab\assets\1772542670228.png)

- 第 2 步：检查 `hierarchies/` 下的 JSON 和 PNG 图片。（5min）
  成功图片如下：

  ![77254679815](E:\dataLab\assets\1772546798157.png)

  ​

  ​


- 第 3 步：检查comparisons/下的图片和报告（2min）

  ![77254683587](E:\dataLab\assets\1772546835875.png)

- 第 4 步：单独运行各模块(4min)

~~~ bash
# 只解析路线
python route_parser.py

# 只做对比分析
python route_analyzer.py
~~~

运行成功截图：

![77254705168](E:\dataLab\assets\1772547051682.png)

![77254714345](E:\dataLab\assets\1772547143452.png)

- 第 5 步:检查route_hierarchy和route_comparison两文件夹下是否生成了对应的解析和对比报告，并且查看其中内容（3min）

- 预计耗时：30 分钟
