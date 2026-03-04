#!/usr/bin/env python3
"""
景区游记数据预处理脚本

功能:
1. 去除元数据（标题、日期、来源、作者等）
2. 清洗特殊字符（HTML标签、表情符号、网址等）
3. 格式统一（全角转半角、标点符号规范化）
4. 空白字符规范化

使用方法:
    python preprocess.py                           # 使用默认路径
    python preprocess.py -i data.xlsx -o out.xlsx  # 指定输入输出路径
"""

import re
import argparse
import sys
from typing import Optional

try:
    import pandas as pd
except ImportError:
    print("错误: 需要安装 pandas 库")
    print("请运行: pip install pandas openpyxl")
    sys.exit(1)


# =============================================================================
# 1. MetadataRemover - 元数据去除器
# =============================================================================

class MetadataRemover:
    """去除游记中的元数据标签"""

    # 元数据模式定义（按优先级排序）
    PATTERNS = [
        # Pattern 1: Title: xxx\nDate: xxx\nSource: xxx\n\n (故宫游记格式)
        r'(?:Title|标题)[：:]\s*[^\n]*\n(?:Date|日期)[：:]\s*[^\n]*\n(?:Source|来源)[：:]\s*[^\n]*\n+',

        # Pattern 2: 标题\nPublication Date: xxx\nSource: xxx\n\n
        r'^[^\n]+\n(?:Publication\s+Date|发布日期)[：:][^\n]*\n(?:Source|来源)[：:][^\n]*\n+',

        # Pattern 3: 【xxx--游记】\n\n
        r'【[^】]+游记[^\]]*】\n+',

        # Pattern 4: 【标题】\n\n
        r'【[^】]+】\n+',

        # Pattern 5: 标题\n(日期时间)\n (包含各种日期格式)
        r'^[^\n]+\n\([^)]*\d{4}[^)]*\)\n+',

        # Pattern 6: 标题\n作者：xxx\n\n (黄山游记格式)
        r'^[^\n]+\n作者[：:][^\n]+\n+',

        # Pattern 7: 已移除（原模式过于激进，会导致有效数据丢失）
    ]

    @classmethod
    def remove_metadata(cls, text: Optional[str]) -> Optional[str]:
        """
        去除文本中的元数据

        Args:
            text: 待处理的文本

        Returns:
            去除元数据后的文本
        """
        if not text or pd.isna(text):
            return text

        result = str(text).strip()

        # 先单独处理文本开头的简短标题（只在开头应用一次）
        # 避免在全文匹配时删除有效内容
        result = re.sub(r'^[^\n]{1,50}\n{2,}', '', result, count=1)

        # 然后应用其他模式
        for pattern in cls.PATTERNS:
            result = re.sub(pattern, '', result, flags=re.MULTILINE)

        return result.strip()


# =============================================================================
# 2. TextCleaner - 文本清洗器
# =============================================================================

class TextCleaner:
    """通用文本清洗"""

    # 需要去除的内容模式
    PATTERNS = {
        'html_tags': r'<[^>]+>',                    # HTML标签
        'urls': r'https?://[^\s\u4e00-\u9fff]+',    # 网址链接
        'emails': r'\b[\w.-]+@[\w.-]+\.\w+\b',      # 邮箱
        'phone': r'1[3-9]\d{9}',                    # 手机号
        'qq': r'[Qq]{2}[:：]?\s*\d{5,12}',          # QQ号
        'wechat': r'[微信|wx]{2}[:：]?\s*[^\s]{4,20}',  # 微信号
    }

    # 表情符号 Unicode 范围
    EMOJI_RANGES = [
        r'[\U0001F600-\U0001F64F]',  # 表情符号
        r'[\U0001F300-\U0001F5FF]',  # 符号和象形文字
        r'[\U0001F680-\U0001F6FF]',  # 交通和地图符号
        r'[\U0001F1E0-\U0001F1FF]',  # 国旗
        r'[\U00002702-\U000027B0]',  # 装饰符号
        r'[\U000024C2-\U000024FF]',  # 其他符号 (修复范围，避免匹配中文)
        r'[\U0001F900-\U0001F9FF]',  # 补充符号
        r'[\U0001FA70-\U0001FAFF]',  # 符号和象形文字扩展
    ]

    # 广告/推广关键词模式
    AD_PATTERNS = [
        r'扫码[关注关注]?关注',
        r'(?:关注|点赞|收藏|转发|分享)[关注关注]{0,2}(?:公众号|账号|博主)?',
        r'二维码[关注关注]?(?:扫描|识别|关注)',
        r'广告|推广|合作|赞助',
        r'更多精彩(?:内容|游记|攻略)?[关注关注]?请[关注关注]?关注',
    ]

    @classmethod
    def clean(cls, text: Optional[str]) -> Optional[str]:
        """
        执行所有清洗操作

        Args:
            text: 待处理的文本

        Returns:
            清洗后的文本
        """
        if not text or pd.isna(text):
            return text

        result = str(text)

        # 去除HTML标签、URL、邮箱等
        for name, pattern in cls.PATTERNS.items():
            result = re.sub(pattern, '', result)

        # 去除表情符号
        for emoji_range in cls.EMOJI_RANGES:
            result = re.sub(emoji_range, '', result)

        # 去除广告推广内容
        for ad_pattern in cls.AD_PATTERNS:
            result = re.sub(ad_pattern, '', result)

        return result

    @classmethod
    def normalize_whitespace(cls, text: Optional[str]) -> Optional[str]:
        """
        规范化空白字符

        Args:
            text: 待处理的文本

        Returns:
            规范化后的文本
        """
        if not text or pd.isna(text):
            return text

        result = str(text)

        # 去除行首行尾空格
        result = re.sub(r'^[ \t]+|[ \t]+$', '', result, flags=re.MULTILINE)

        # 将多个连续空格替换为单个空格
        result = re.sub(r' {2,}', ' ', result)

        # 将多个连续换行替换为最多两个换行
        result = re.sub(r'\n{3,}', '\n\n', result)

        # 去除首尾空白
        result = result.strip()

        return result


# =============================================================================
# 3. FormatNormalizer - 格式规范化器
# =============================================================================

class FormatNormalizer:
    """文本格式规范化"""

    # 全角数字映射
    FULLWIDTH_DIGITS = str.maketrans(
        '０１２３４５６７８９',
        '0123456789'
    )

    # 全角字母映射
    FULLWIDTH_LETTERS = str.maketrans(
        'ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ'
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ',
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    )

    # 标点符号映射（中文标点 → 英文标点）
    PUNCTUATION_MAP = {
        '：': ':',
        '；': ';',
        '，': ',',
        '。': '.',
        '？': '?',
        '！': '!',
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '《': '<',
        '》': '>',
    }

    @classmethod
    def convert_fullwidth(cls, text: Optional[str]) -> Optional[str]:
        """
        全角转半角

        Args:
            text: 待处理的文本

        Returns:
            转换后的文本
        """
        if not text or pd.isna(text):
            return text

        result = str(text)

        # 转换数字
        result = result.translate(cls.FULLWIDTH_DIGITS)

        # 转换字母
        result = result.translate(cls.FULLWIDTH_LETTERS)

        return result

    @classmethod
    def normalize_punctuation(cls, text: Optional[str]) -> Optional[str]:
        """
        标点符号规范化

        Args:
            text: 待处理的文本

        Returns:
            规范化后的文本
        """
        if not text or pd.isna(text):
            return text

        result = str(text)

        # 应用标点映射（逐个替换）
        for cn, en in cls.PUNCTUATION_MAP.items():
            result = result.replace(cn, en)

        return result

    @classmethod
    def normalize_all(cls, text: Optional[str]) -> Optional[str]:
        """
        执行所有格式规范化

        Args:
            text: 待处理的文本

        Returns:
            规范化后的文本
        """
        if not text or pd.isna(text):
            return text

        result = cls.convert_fullwidth(text)
        result = cls.normalize_punctuation(result)

        return result


# =============================================================================
# 4. 处理流程
# =============================================================================

def process_text(text: Optional[str]) -> Optional[str]:
    """
    完整的文本处理流程

    Args:
        text: 待处理的文本

    Returns:
        处理后的文本
    """
    if not text or pd.isna(text):
        return text

    # Step 0: 将Excel中的字面量 \n 转换为真正的换行符
    result = str(text).replace('\\n', '\n')

    # Step 1: 去除元数据
    result = MetadataRemover.remove_metadata(result)

    # Step 2: 清洗文本
    result = TextCleaner.clean(result)

    # Step 3: 规范化空白字符
    result = TextCleaner.normalize_whitespace(result)

    # Step 4: 格式规范化
    result = FormatNormalizer.normalize_all(result)

    return result


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    处理整个DataFrame

    Args:
        df: 原始数据框

    Returns:
        处理后的数据框
    """
    # 创建副本避免修改原数据
    df_cleaned = df.copy()

    # 获取需要处理的列（除景区名称外的所有文本列）
    text_columns = [col for col in df.columns if col != '景区名称']

    print(f"处理列: {text_columns}")

    # 对每列应用处理
    for col in text_columns:
        df_cleaned[col] = df[col].apply(process_text)

    return df_cleaned


def load_data(input_path: str) -> pd.DataFrame:
    """加载Excel数据"""
    try:
        df = pd.read_excel(input_path)
        print(f"成功读取: {input_path}")
        print(f"数据形状: {df.shape}")
        print(f"列名: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"读取文件失败: {e}")
        sys.exit(1)


def save_data(df: pd.DataFrame, output_path: str) -> None:
    """保存Excel数据"""
    try:
        df.to_excel(output_path, index=False, engine='openpyxl')
        print(f"成功保存: {output_path}")
    except Exception as e:
        print(f"保存文件失败: {e}")
        sys.exit(1)


def print_summary(df_original: pd.DataFrame, df_cleaned: pd.DataFrame) -> None:
    """打印处理摘要"""
    print("\n" + "=" * 50)
    print("处理摘要")
    print("=" * 50)

    text_columns = [col for col in df_original.columns if col != '景区名称']

    for col in text_columns:
        original_len = df_original[col].astype(str).str.len().sum()
        cleaned_len = df_cleaned[col].astype(str).str.len().sum()

        if original_len > 0:
            reduction = (1 - cleaned_len / original_len) * 100
            print(f"{col:16s}: 原始 {original_len:6d} 字符 → 清洗后 {cleaned_len:6d} 字符 (减少 {reduction:5.1f}%)")
        else:
            print(f"{col:16s}: 无数据")

    print("=" * 50)


# =============================================================================
# 5. 主程序
# =============================================================================

def main():
    """主程序"""
    parser = argparse.ArgumentParser(
        description='景区游记数据预处理脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    python preprocess.py                           # 使用默认路径
    python preprocess.py -i data.xlsx -o out.xlsx  # 指定输入输出路径
    python preprocess.py --keep-punctuation        # 保留中文标点符号
        '''
    )

    parser.add_argument(
        '--input', '-i',
        default='data.xlsx',
        help='输入Excel文件路径 (默认: data.xlsx)'
    )

    parser.add_argument(
        '--output', '-o',
        default='data_cleaned.xlsx',
        help='输出Excel文件路径 (默认: data_cleaned.xlsx)'
    )

    parser.add_argument(
        '--keep-punctuation',
        action='store_true',
        help='保留中文标点符号，不转换为英文标点'
    )

    args = parser.parse_args()

    # 如果选择保留中文标点，修改规范化函数
    if args.keep_punctuation:
        FormatNormalizer.normalize_punctuation = lambda x: x
        print("模式: 保留中文标点符号")

    print("\n" + "=" * 50)
    print("景区游记数据预处理脚本")
    print("=" * 50)

    # 读取数据
    print(f"\n[1/4] 读取数据...")
    df = load_data(args.input)

    # 处理数据
    print(f"\n[2/4] 处理数据...")
    df_cleaned = process_dataframe(df)

    # 保存数据
    print(f"\n[3/4] 保存数据...")
    save_data(df_cleaned, args.output)

    # 打印摘要
    print(f"\n[4/4] 完成摘要")
    print_summary(df, df_cleaned)

    print("\n处理完成！")


if __name__ == '__main__':
    main()
