# 任务1：景区指南数据采集与预处理

## 任务目标
1. 采集3个景区的官方游览推荐路线（如"一日游最佳路线"/"亲子游攻略"）
2. 采集对应景区的游客游记各5篇
3. 数据清洗和格式统一

## 数据说明

### 原始数据
- `data.xlsx`: 采集的原始数据，包含官方路线和游客游记。
  - **数据集规模**：本实验使用了 Low (低资源) 和 Middle (中等资源) 规模的数据集，共包含15篇精选游记（每个景区5篇），以模拟真实场景下的数据稀疏性挑战。

### 清洗后数据
- `data_cleaned.xlsx`: 经过清洗和格式统一的数据
  - 包含3个景区（九寨沟、故宫、黄山）
  - 每个景区包含官方推荐路线和游客游记

## 脚本说明

### preprocess.py
数据预处理脚本，主要功能：
- 读取原始Excel数据
- 数据清洗（去除空值、格式统一）
- 输出清洗后的数据到 `data_cleaned.xlsx`

## 使用方法

```bash
python preprocess.py
```

## 输入输出

**输入:**
- `data/data.xlsx` - 原始采集的数据

**输出:**
- `data/data_cleaned.xlsx` - 清洗后的数据（供后续任务使用）

## 任务过程

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

成功结果如下：

- **第 4 步：查看清洗后的数据**变化（2min）

  **位置**：`task1_data_collection`/data 目录。

查看data.xlsx和data_cleaned.xlsx的内容，观察是否去除空值、格式统一、删除了游记顶部的标题、作者、日期、来源等元数据、去除了类似 【上午】 、 【行程安排】 等导航式标签等等，将 非结构化的自然语言文本 转化为 结构化的程序性描述语料。

效果对比如下：

- 预计耗时：15 分钟
