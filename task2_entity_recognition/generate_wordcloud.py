#!/usr/bin/env python3
"""
从entity_results.json生成词云图
"""

import json
import os
import re
from collections import Counter
from matplotlib.font_manager import FontProperties

try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
except ImportError:
    print("需要安装 wordcloud 和 matplotlib")
    print("请运行: pip install wordcloud matplotlib")
    exit(1)


def extract_poi_names(poi_list):
    """从POI列表中提取真正的POI名称

    处理格式如：
    - "- 半日游路线:午门" -> "午门"
    - "小时快速游路线:午门" -> "午门"
    - 普通POI直接保留
    """
    extracted = []
    for item in poi_list:
        # 匹配格式：xxx:POI名称 或 xxx：POI名称
        match = re.search(r'[:：]\s*([\u4e00-\u9fa5]{2,6})$', item)
        if match:
            extracted.append(match.group(1))
        else:
            # 如果不包含路线格式，直接使用原词（但过滤掉非地名的词）
            # 过滤以"-"开头的路线描述
            if not item.startswith('-') and not item.endswith('路线'):
                extracted.append(item)
    return extracted


def get_chinese_font():
    """获取中文字体路径"""
    import platform
    system = platform.system()

    if system == 'Darwin':  # macOS
        fonts = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/Library/Fonts/Arial Unicode.ttf'
        ]
    elif system == 'Windows':
        fonts = [
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttc',
        ]
    else:  # Linux
        fonts = [
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        ]

    for font in fonts:
        if os.path.exists(font):
            return font
    return None


def generate_wordcloud(freq_dict, output_path, title, font_path):
    """生成词云图"""
    # 过滤低频词
    filtered = {k: v for k, v in freq_dict.items() if v >= 1}

    if not filtered:
        print(f"警告: 没有足够的数据生成词云图: {title}")
        return

    # 创建词云
    wc = WordCloud(
        font_path=font_path,
        width=1200,
        height=600,
        background_color='white',
        max_words=100,
        colormap='viridis',
        prefer_horizontal=0.7,
        scale=2,
        margin=10
    )

    # 生成词云
    wc.generate_from_frequencies(filtered)

    # 保存图片
    plt.figure(figsize=(15, 8))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    title_font = FontProperties(fname=font_path) if font_path else None
    plt.title(title, fontsize=20, fontproperties=title_font)
    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"已生成词云图: {output_path}")


def main():
    print("=" * 60)
    print("从entity_results.json生成词云图")
    print("=" * 60)

    # 读取JSON数据
    print("\n[1/3] 读取entity_results.json...")
    with open('entity_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data['results']

    # 创建输出目录
    print("\n[2/3] 创建输出目录...")
    base_dir = os.path.join('output', 'wordcloud')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    spot_name_map = {
        '九寨沟': 'jiuzhaigou',
        '故宫': 'gugong',
        '黄山': 'huangshan'
    }

    for record in results:
        spot_cn = record['scenic_spot']
        spot_en = spot_name_map.get(spot_cn, spot_cn)
        spot_dir = os.path.join(base_dir, spot_en)
        if not os.path.exists(spot_dir):
            os.makedirs(spot_dir, exist_ok=True)

    # 获取字体
    print("\n[3/3] 生成词云图...")
    font_path = get_chinese_font()
    if not font_path:
        print("警告: 未找到中文字体，词云可能显示不正确")

    # 为每个景区生成3张词云图
    for record in results:
        spot_cn = record['scenic_spot']
        spot_en = spot_name_map.get(spot_cn, spot_cn)

        print(f"\n  处理 {spot_cn}...")

        # POI词云
        if record['poi']:
            # 提取真正的POI名称（从"路线:POI"格式中提取）
            poi_names = extract_poi_names(record['poi'])
            # 过滤掉非地名的副词
            stop_words = {'专门', '上山', '热门', '门票', '门票价格', '上海', '外滩'}
            filtered_poi = [word for word in poi_names if word not in stop_words]
            poi_freq = Counter(filtered_poi)
            output_path = os.path.join(base_dir, spot_en, 'poi.png')
            generate_wordcloud(dict(poi_freq), output_path, f'{spot_cn} - 景点POI', font_path)

        # 交通词云
        all_transport = []
        for cat in ['basic', 'specific', 'time_distance']:
            all_transport.extend(record['transport'].get(cat, []))
        if all_transport:
            transport_freq = Counter(all_transport)
            output_path = os.path.join(base_dir, spot_en, 'transport.png')
            generate_wordcloud(dict(transport_freq), output_path, f'{spot_cn} - 交通方式', font_path)

        # 时间词云
        all_time = []
        for cat in ['exact', 'relative', 'duration']:
            all_time.extend(record['time'].get(cat, []))
        if all_time:
            time_freq = Counter(all_time)
            output_path = os.path.join(base_dir, spot_en, 'time.png')
            generate_wordcloud(dict(time_freq), output_path, f'{spot_cn} - 时间节点', font_path)

    print(f"\n已生成 {len(results) * 3} 张词云图到 {base_dir} 目录")
    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
