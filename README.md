# **旅游攻略知识图谱与智能助手项目教学文档**

本教程将引导您完成从源码获取、数据处理到构建一个能够智能规划路线的旅游 Agent 的全过程。整个项目分为 8 个核心阶段（任务 0-7），每个任务都建立在前一个任务的基础之上。

---

## **任务 0：环境准备与源码获取**
**目标**：配置本地开发环境并获取项目源代码。
**执行位置**：您希望存放项目的本地根目录（如 `E:\dm_lab`）。

- **第 1 步：克隆 GitHub 仓库**
  打开终端，克隆项目到本地：
  ```bash
  git clone https://github.com/Songbinbin111/dm_lab.git
  cd dm_lab
  ```
- **第 2 步：安装 Python 环境**
  建议使用 Python 3.8+。建议创建虚拟环境以保持环境整洁。
- **注意事项**：
  - 确保已安装 `git` 工具。
  - Windows 用户建议在 PowerShell 或 Git Bash 中操作。
  - 若克隆速度慢，可考虑使用国内镜像或直接下载 ZIP 包。
- **预计耗时**：10 - 15 分钟

---

## **任务 1：数据采集与预处理**
**目标**：获取并清洗原始游记数据，为后续的 NLP 任务打好基础。
**执行位置**：`task1_data_collection` 目录。

- **第 1 步：安装依赖库**（6min）
  ```bash
  pip install pandas openpyxl
  ```

> 本实验python版本要求3.6+，建议3.8，如果你安装了多个 Python 版本，最稳妥的方法是使用 py -3 启动器来调用 Python 3 的 pip或者修改系统的 PATH 环境变量(之后的命令也是如此)：
>
> ~~~bash
> py -3 -m pip install pandas openpyxl
> ~~~

成功结果如下：出现Requirement already satisfied

可以通过此命令确认：

~~~bash
py -3 -c "import pandas; import openpyxl; print('Pandas version:', pandas.__version__); print('Openpyxl version:', openpyxl.__version__)"
~~~

如果能正常输出版本号，说明安装成功。

- 第 2 步：查看原始数据(1min)
  在 `data/data.xlsx` 中查看三个景区（九寨沟、故宫、黄山）的官方推荐路线和游客游记。

- **第 3 步：运行清洗脚本**（3min）

  **执行位置**：`task1_data_collection` 目录。

  ```bash
  python preprocess.py
  ```

如果出现：No such file or directory: 'data.xlsx'，这是因为根据脚本的默认行为，它会在当前工作目录下寻找 data.xlsx 。而我们的项目结构是将数据文件存放在 data/ 子目录中的。这时运行脚本时，我们需要通过参数明确告诉它输入和输出文件的 正确路径：

~~~bash
py preprocess.py -i data/data.xlsx -o data/data_cleaned.xlsx
~~~

- **第 4 步：查看清洗后的数据**变化（2min）

  **位置**：`task1_data_collection`/data 目录。

查看data.xlsx和data_cleaned.xlsx的内容，观察是否去除空值、格式统一、删除了游记顶部的标题、作者、日期、来源等元数据、去除了类似 【上午】 、 【行程安排】 等导航式标签等等，将 非结构化的自然语言文本 转化为 结构化的程序性描述语料。

- 预计耗时：15 分钟

---

## **任务 2：游览步骤的实体识别**
**目标**：从清洗后的文本中识别出核心实体：景点 (POI)、交通方式、时间节点。
**执行位置**：`task2_entity_recognition` 目录。

- **第 1 步：安装 NLP 相关依赖**（5min）
  ```bash
  pip install jieba wordcloud matplotlib
  ```
  成功结果如下：出现Successfully installed ...

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

- 第 4 步：查看生成的词云图(3min)

  查看output\wordcloud下生成的词云图，检查实体识别的准确性（是否准确输出景点）、词频权重的体现（字号越大 的词代表在游记中出现的频率越高）、词典过滤的效果（没有出现明显的广告词或无意义的助词）。

> 由于词云生成的随机性：词语位置、旋转方向、颜色分配等会发生变化。

- **预计耗时**：20 分钟

---

## **任务 3：游览路线的层级结构挖掘**
**目标**：解析官方路线逻辑，并将其与游客实际路线对比。
**执行位置**：`task3_route_hierarchy` 目录。

- **第 1 步：运行分析程序**(10min)
  ```bash
  python main_task3.py
  ```

- 第 2 步：检查 `hierarchies/` 下的 JSON 和 PNG 图片。（5min）

- 第 3 步：检查comparisons/下的图片和报告（2min）

- 第 4 步：单独运行各模块(4min)

~~~ bash
# 只解析路线
python route_parser.py

# 只做对比分析
python route_analyzer.py
~~~

- 第 5 步:检查route_hierarchy和route_comparison两文件夹下是否生成了对应的解析和对比报告，并且查看其中内容（3min）

- 预计耗时：30 分钟

---

## **任务 4：程序性知识的共指消解**
**目标**：解决文本中的代词指代问题（如将“这里”指向具体景点）。
**执行位置**：`task4_coref_resolution` 目录。

- **第 1 步：运行消解程序**
  ```bash
  python main.py
  ```

  或者分步运行：

  ~~~bash
  python3 coref_extractor.py  # 提取代词并自动消解
  python3 evaluator.py         # 评估结果
  python3 visualizer.py        # 生成可视化图表
  ~~~

- **预计耗时**：15 分钟

---

## **任务 5：条件性游览建议的抽取**
**目标**：提取带有前提条件的建议（如“如果...建议...”）。
**执行位置**：`task5_conditional_advice` 目录。

- **第 1 步：运行抽取脚本**
  ```bash
  python main.py
  ```

- **第 2 步：检查配置**
  根据需要调整 `config/` 中的触发词库。
- **注意事项**：
  - 提取质量高度依赖正则表达式，建议根据语料特点增加新的 `patterns`。
  - 抽取结果会直接影响任务 7 中 Agent 的回答丰富度。
- **预计耗时**：40 - 60 分钟

---

## **任务 6：多源程序性知识的融合与可视化**
**目标**：将所有提取成果融合成一张结构化的知识图谱。
**执行位置**：`task6_knowledge_fusion` 目录。

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

- 注意事项：

  - **依赖关系**：这是项目的汇总任务，必须确保任务 1-5 的输出文件都已正确生成。
  - **图谱质量**：如果生成的图谱节点过多或过乱，可以调整 `knowledge_fusion.py` 中的评分阈值。

- **预计耗时**：10 分钟

---

## **任务 7：旅游规划智能助手 (Agent)**
**目标**：构建基于知识图谱的交互式 Agent。
**执行位置**：`task7_agent` 目录。

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
- **注意事项**：
  - **端口冲突**：默认使用 8080 端口，若被占用请在 `main.go` 中修改。
  - **工具链接**：Agent 会读取任务 6 的 JSON 路径，请确保路径配置正确。
- **预计耗时**：40 - 60 分钟



# 修改汇总

修改任务二generate_wordcloud.py文件base_dir = 'wordcloud'等共7处，将输出目录定位在了output下。

修改任务三main_task3.py里的路径问题，处理任务依赖，并且修改了不同环境下生成的图片运行中文字体是方框的问题

修改了任务三route_parser.py和python route_analyzer.py的输入路径，拥有自己的输出目录route_hierarchy和route_comparison

修改了任务三route_parser.py，增加箭头连接的格式

修改了visualizer.py里的内容，加入了字体配置

修改了任务七的go.mod里的一个依赖，升级其版本号

任务七（Agent）调整：
- 接入改为使用智谱 AI OpenAI 兼容接口，`.env` 中新增/统一：
  - `OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4`
