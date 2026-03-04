# 任务2：游览步骤的实体识别

## 任务目标
1. 定义游览程序的三类实体：景点POI、交通方式、时间节点
2. 使用Jieba分词+自定义词典，从游记中识别上述实体
3. 绘制各类实体的词频统计图（词频云或柱状图）

## 文件结构

```
task2_entity_recognition/
├── custom_dicts/           # 自定义词典
│   ├── poi/               # POI词典（按景区分类）
│   │   ├── jiuzhaigou.txt
│   │   ├── gugong.txt
│   │   └── huangshan.txt
│   ├── transport.txt      # 交通方式词典
│   └── time.txt           # 时间节点词典
├── entity_extraction.py   # 实体提取主程序
├── generate_wordcloud.py  # 词云图生成程序
├── entity_results.json    # 实体提取结果
└── output/                # 输出文件夹
    └── wordcloud/         # 词云图
        ├── gugong/
        ├── huangshan/
        └── jiuzhaigou/
└── debug/                 # 调试脚本
    └── debug_normalize.py # 标准化调试
```

## 脚本说明

### entity_extraction.py
实体提取主程序，功能包括：
- 使用Jieba分词加载自定义词典
- 从游记中识别三类实体（POI、交通、时间）
- 提取景区特定的POI名称
- 输出结构化的实体数据

### generate_wordcloud.py
词云图生成程序，功能包括：
- 读取实体提取结果
- 过滤停用词
- 生成三类实体的词云图
- 支持中文字体显示

## 使用方法

### 1. 实体提取
```bash
python entity_extraction.py
```
输出：`entity_results.json`

### 2. 生成词云图
```bash
python generate_wordcloud.py
```
输出：`output/wordcloud/*/*.png`

## 任务过程

- **第 1 步：安装 NLP 相关依赖**（5min）
  ```bash
  pip install jieba wordcloud matplotlib
  ```
  成功结果如下：出现Successfully installed ...

  ![77250864519](E:\dm_lab\assets\1772508645193.png)

- **第 2 步：维护自定义词典**（3min）
  检查 `custom_dicts/` 目录，浏览 poi/ 下的 gugong.txt , huangshan.txt , jiuzhaigou.txt 文件，检查里面的景点名称是否和你采集的数据一致。如果不一致，可以手动补充，这能提高后续实体识别的准确率。

- **第 3 步：提取实体并可视化**(5min)
  ```bash
  python entity_extraction.py

  python generate_wordcloud.py
  ```
  >  如果出现No such file or directory: 'data_cleaned.xlsx' 。需要修改entity_extraction.py中的 load_data('data_cleaned.xlsx')，
  >
  > 将默认路径指向正确的位置：
  >
  > 633行  df = load_data('data_cleaned.xlsx') 改为 df = load_data('../task1_data_collection/data/data_cleaned.xlsx')

  注意事项：

  - **乱码问题**：生成词云图时若出现方框，请检查脚本中是否正确指向了支持中文的字体文件。
  - **词典格式**：自定义词典每行应为 `词语 词频 词性`，以空格分隔。

  运行成功结果如下：

  ![77254238865](E:\dataLab\assets\1772542388659.png)

  ![77254243556](E:\dataLab\assets\1772542435562.png)

- 第 4 步：查看生成的词云图(3min)

  查看output\wordcloud下生成的词云图，检查实体识别的准确性（是否准确输出景点）、词频权重的体现（字号越大 的词代表在游记中出现的频率越高）、词典过滤的效果（没有出现明显的广告词或无意义的助词），如下(总共9图)：

![77254260841](E:\dataLab\assets\1772542608413.png)

> 由于词云生成的随机性：词语位置、旋转方向、颜色分配等会发生变化。

- **预计耗时**：20 分钟
