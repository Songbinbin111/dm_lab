#!/usr/bin/env python3
"""
任务3：游览路线的层级结构挖掘 - 主程序

功能：
1. 分析官方指南中的路线描述方式
2. 构建时间维度的游览层级结构
3. 比较官方推荐路线和游客实际路线的结构差异
"""

import os
import json
from typing import Dict
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np

# 先设置中文字体
from matplotlib.font_manager import FontProperties

def setup_matplotlib_font():
    """设置matplotlib中文字体"""
    import platform
    from matplotlib import font_manager
    system = platform.system()

    # 常见中文字体路径
    font_paths = []
    if system == 'Darwin':  # macOS
        font_paths = ['/System/Library/Fonts/PingFang.ttc', '/Library/Fonts/Arial Unicode.ttf']
    elif system == 'Windows':
        font_paths = ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']
    else:  # Linux
        font_paths = ['/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']

    found_font = False
    for path in font_paths:
        if os.path.exists(path):
            try:
                # 显式注册字体文件
                font_manager.fontManager.addfont(path)
                # 获取该字体文件对应的家族名称
                prop = font_manager.FontProperties(fname=path)
                font_name = prop.get_name()
                
                # 设置为默认字体
                matplotlib.rcParams['font.sans-serif'] = [font_name, 'SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
                matplotlib.rcParams['font.family'] = 'sans-serif'
                found_font = True
                break
            except Exception as e:
                print(f"警告: 无法加载字体 {path}: {e}")

    if not found_font:
        # 最后的兜底方案：尝试常见的系统字体名称
        matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'STHeiti']

    matplotlib.rcParams['axes.unicode_minus'] = False

setup_matplotlib_font()

from route_parser import RouteParser, TimeHierarchyBuilder
from route_analyzer import RouteComparator, load_visitor_data, generate_comparison_report


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


def visualize_time_hierarchy(hierarchy_data: Dict, scenic_spot: str, output_path: str):
    """可视化时间层级结构"""
    scenic_spot = hierarchy_data.get('scenic_spot', scenic_spot)
    structure_type = hierarchy_data.get('structure_type', 'unknown')

    if scenic_spot == "九寨沟" and structure_type == "time_based":
        visualize_jiuzhaigou_hierarchy(hierarchy_data, output_path)
    elif scenic_spot == "故宫":
        visualize_gugong_hierarchy(hierarchy_data, output_path)
    elif scenic_spot == "黄山":
        visualize_huangshan_hierarchy(hierarchy_data, output_path)


def visualize_jiuzhaigou_hierarchy(hierarchy: Dict, output_path: str):
    """可视化九寨沟的时间层级结构"""
    hierarchy_data = hierarchy.get('hierarchy', {})

    fig, ax = plt.subplots(figsize=(14, 8))

    # 构建层级数据
    periods = list(hierarchy_data.keys())
    period_order = ["清晨", "上午", "中午", "下午", "傍晚", "晚上"]
    periods = [p for p in period_order if p in periods]

    y_positions = []
    pois_by_period = []

    for period in periods:
        activities = hierarchy_data[period].get('activities', [])
        pois = [act['poi'] for act in activities]
        pois_by_period.extend(pois)
        y_positions.extend([period] * len(pois))

    # 创建散点图
    x_data = list(range(len(pois_by_period)))
    y_data = y_positions

    # 按时段给不同颜色
    colors = []
    color_map = {
        "清晨": "#FFD700",
        "上午": "#87CEEB",
        "中午": "#FF6347",
        "下午": "#9370DB",
        "傍晚": "#FFA500",
        "晚上": "#4169E1"
    }
    for y in y_data:
        colors.append(color_map.get(y, "#CCCCCC"))

    plt.scatter(x_data, y_data, c=colors, s=300, alpha=0.7, edgecolors='black', linewidths=1)

    # 添加POI标签
    for i, (x, y, poi) in enumerate(zip(x_data, y_data, pois_by_period)):
        plt.annotate(poi, (x, y), xytext=(5, 5), textcoords='offset points',
                    fontsize=9, alpha=0.8)

    plt.xlabel('游览顺序', fontsize=12)
    plt.ylabel('时段', fontsize=12)
    plt.title('九寨沟 - 时间维度游览层级结构', fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def visualize_gugong_hierarchy(hierarchy: Dict, output_path: str):
    """可视化故宫的层级结构 - 按照实际空间布局"""
    parsed_data = hierarchy.get('parsed', {})
    routes = parsed_data.get('routes', [])
    if not routes:
        # 兼容仅提供层级结构（无 parsed）的情况
        route_hierarchy = hierarchy.get('hierarchy', {})
        # Flatten structure if nested
        if '游览路线' not in route_hierarchy and 'hierarchy' in route_hierarchy:
             route_hierarchy = route_hierarchy.get('hierarchy', {})
             
        full_sequence = route_hierarchy.get('游览路线', {}).get('full_sequence', [])
        routes = [{"poi": poi} for poi in full_sequence]

    fig, ax = plt.subplots(figsize=(16, 12))

    # 故宫景点空间位置定义 (x: 东西位置, y: 南北位置)
    # 南为下，北为上；西为左，东为右
    positions = {
        # 中轴线（从南到北）
        '午门': (0, 0),
        '太和门': (0, 1),
        '太和殿': (0, 2),
        '中和殿': (0, 2.5),
        '保和殿': (0, 3),
        '乾清门': (0, 3.5),  # Added
        '乾清宫': (0, 4),
        '交泰殿': (0, 4.5),
        '坤宁宫': (0, 5),
        '御花园': (0, 6),
        '神武门': (0, 7),

        # 西路
        '武英殿': (-2, 1),
        '西六宫区': (-2, 4.5),
        '奉先殿': (-2.5, 3.5),
        '故宫冰窖餐厅': (-1.5, 5.5), # Approximate

        # 东路
        '文华殿': (2, 1),
        '东六宫区': (2, 4.5),
        '宁寿宫区': (2.5, 5.5),
        '东华门': (3, 1), # Added
        '午门出口': (0.5, 0), # Added near Wu Men

        # 养心殿（在中轴线西侧）
        '养心殿': (-1, 4.2),
    }

    # 按区域分组
    zones = {
        '外朝（前朝）': ['午门', '太和门', '太和殿', '中和殿', '保和殿', '文华殿', '武英殿', '东华门', '午门出口'],
        '内廷（后寝）': ['乾清门', '乾清宫', '交泰殿', '坤宁宫', '养心殿', '西六宫区', '东六宫区', '故宫冰窖餐厅'],
        '御花园及以北': ['御花园', '奉先殿', '宁寿宫区', '神武门']
    }

    zone_colors = {
        '外朝（前朝）': '#FFD700',
        '内廷（后寝）': '#87CEEB',
        '御花园及以北': '#9370DB'
    }

    # 绘制区域边界 - 降低透明度
    zone_boundaries = {
        '外朝（前朝）': {'y_min': 0, 'y_max': 3.5},
        '内廷（后寝）': {'y_min': 3.5, 'y_max': 5},
        '御花园及以北': {'y_min': 5, 'y_max': 7.5}
    }

    for zone, bounds in zone_boundaries.items():
        ax.axhspan(bounds['y_min'], bounds['y_max'], alpha=0.05,
                   color=zone_colors.get(zone, '#CCCCCC'))

    # 绘制中轴线
    ax.axvline(x=0, ymin=0, ymax=1, color='red', linestyle='--',
              alpha=0.3, linewidth=2)

    # 获取游览顺序
    poi_sequence = [r['poi'] for r in routes]

    # 绘制连接线（显示游览路径）- 先绘制，确保在点下方
    for i in range(len(poi_sequence) - 1):
        poi1 = poi_sequence[i]
        poi2 = poi_sequence[i + 1]

        if poi1 in positions and poi2 in positions:
            x1, y1 = positions[poi1]
            x2, y2 = positions[poi2]

            # 使用箭头连接
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                       arrowprops=dict(arrowstyle='->', color='gray',
                                     alpha=0.3, lw=2))

    # 绘制景点节点 - 提高zorder确保在最上层
    for i, poi in enumerate(poi_sequence):
        if poi in positions:
            x, y = positions[poi]

            # 确定景点所属区域
            zone = None
            for z, pois in zones.items():
                if poi in pois:
                    zone = z
                    break

            color = zone_colors.get(zone, '#CCCCCC')

            # 先绘制序号标签（在节点右侧）
            ax.text(x + 0.15, y, str(i + 1), ha='left', va='center',
                   fontsize=8, fontweight='bold', zorder=6,
                   bbox=dict(boxstyle='circle', facecolor='white',
                           edgecolor='black', alpha=0.9, pad=0.3))

            # 绘制节点 - 使用更大更明显的点
            ax.plot(x, y, 'o', markersize=18, markerfacecolor=color,
                   markeredgecolor='black', markeredgewidth=2.5, alpha=1.0, zorder=10)

            # 添加景点名称（在点上方）
            ax.text(x, y + 0.25, poi, ha='center', va='center',
                   fontsize=9, fontweight='bold', zorder=11,
                   bbox=dict(boxstyle='round,pad=0.4',
                           facecolor='white', edgecolor='gray',
                           alpha=0.85))

    # 添加方向指示
    ax.text(0, -0.5, '南', ha='center', va='top', fontsize=14,
           fontweight='bold', color='red')
    ax.text(0, 7.5, '北', ha='center', va='bottom', fontsize=14,
           fontweight='bold', color='red')
    ax.text(-3.5, 3.5, '西', ha='right', va='center', fontsize=14,
           fontweight='bold', color='blue')
    ax.text(3.5, 3.5, '东', ha='left', va='center', fontsize=14,
           fontweight='bold', color='blue')

    # 添加说明
    info_text = "游览路线说明：\n"
    info_text += "• 数字表示游览顺序\n"
    info_text += "• 红色虚线为中轴线\n"
    info_text += "• 不同颜色表示不同区域"

    ax.text(0.98, 0.02, info_text,
           transform=ax.transAxes, fontsize=9,
           verticalalignment='bottom',
           horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax.set_title('故宫 - 空间布局与游览路线', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('东西方向', fontsize=12)
    ax.set_ylabel('南北方向', fontsize=12)
    ax.set_xlim(-4, 4)
    ax.set_ylim(-1, 8)
    ax.grid(True, alpha=0.1, linestyle='--', zorder=0)

    # 自定义图例
    legend_elements = [
        mlines.Line2D([0], [0], color='red', linestyle='--', label='中轴线'),
        mlines.Line2D([0], [0], color='gray', linestyle='-', label='游览路径')
    ]
    for zone, color in zone_colors.items():
        legend_elements.append(mlines.Line2D([0], [0], marker='o', color='w',
                                            markerfacecolor=color, markersize=10,
                                            label=zone, linestyle='None'))

    ax.legend(handles=legend_elements, loc='upper left', fontsize=9,
             framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def visualize_huangshan_hierarchy(hierarchy: Dict, output_path: str):
    """可视化黄山的层级结构 - 显示线路交汇和空间关系"""
    hierarchy_data = hierarchy.get('hierarchy', {})
    routes = hierarchy_data.get('可选线路', {})
    common_pois = hierarchy.get('common_pois', {})

    fig, ax = plt.subplots(figsize=(16, 12))

    # 线路颜色
    route_colors = {
        '线路一': '#FF6B6B',
        '线路二': '#4ECDC4',
        '线路三': '#45B7D1',
        '线路四': '#96CEB4',
        '线路五': '#FFEAA7'
    }

    # 收集所有节点及其位置信息
    all_nodes = {}  # node -> {x, y, routes}
    node_y_position = {}  # 用于Y轴布局

    # 计算每个节点出现的频率
    node_frequency = {}
    for route_name, route_data in routes.items():
        for node in route_data.get('nodes', []):
            node_frequency[node] = node_frequency.get(node, 0) + 1

    # 按频率分组节点
    high_freq_nodes = [n for n, f in node_frequency.items() if f >= 3]
    medium_freq_nodes = [n for n, f in node_frequency.items() if f == 2]
    low_freq_nodes = [n for n, f in node_frequency.items() if f == 1]

    # 分配Y坐标：高频节点在上层，中频在中层，低频在下层
    y_level = 0
    node_y_map = {}

    for nodes in [high_freq_nodes, medium_freq_nodes, low_freq_nodes]:
        for node in sorted(nodes):
            node_y_map[node] = y_level
            y_level -= 1

    # 为每条线路分配X坐标
    route_x_offset = {}
    x_spacing = 2.5
    for i, route_name in enumerate(sorted(routes.keys())):
        route_x_offset[route_name] = i * x_spacing

    # 绘制节点和连接线
    node_drawn = set()

    for route_name, route_data in routes.items():
        nodes = route_data.get('nodes', [])
        base_x = route_x_offset[route_name]
        color = route_colors.get(route_name, '#87CEEB')

        # 绘制路线节点
        for i, node in enumerate(nodes):
            x = base_x + i * 0.8
            y = node_y_map[node]

            # 存储节点位置
            if node not in all_nodes:
                all_nodes[node] = {'x': x, 'y': y, 'routes': [], 'frequency': node_frequency[node]}
            all_nodes[node]['routes'].append(route_name)

            # 绘制节点
            if node not in node_drawn:
                # 根据频率设置大小和颜色
                freq = node_frequency[node]
                size = 300 + freq * 100
                alpha = min(0.6 + freq * 0.1, 1.0)  # 确保alpha不超过1

                # 共享节点用特殊标记
                if freq >= 3:
                    edge_color = 'red'
                    edge_width = 3
                    marker = 'D'  # 菱形
                elif freq == 2:
                    edge_color = 'orange'
                    edge_width = 2
                    marker = 's'  # 方形
                else:
                    edge_color = 'gray'
                    edge_width = 1
                    marker = 'o'  # 圆形

                ax.scatter(x, y, s=size, c=color, marker=marker,
                          alpha=alpha, edgecolors=edge_color,
                          linewidths=edge_width, zorder=5)

                # 添加节点标签
                ax.annotate(node, (x, y),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, alpha=0.8,
                           bbox=dict(boxstyle='round,pad=0.3',
                                   facecolor='white', alpha=0.7))

                node_drawn.add(node)

        # 绘制路线连接线
        for i in range(len(nodes) - 1):
            node1 = nodes[i]
            node2 = nodes[i + 1]

            if node1 in all_nodes and node2 in all_nodes:
                x1 = all_nodes[node1]['x']
                y1 = all_nodes[node1]['y']
                x2 = all_nodes[node2]['x']
                y2 = all_nodes[node2]['y']

                # 使用贝塞尔曲线连接
                import numpy as np
                t = np.linspace(0, 1, 20)
                # 控制点让线条更平滑
                mid_x = (x1 + x2) / 2
                mid_y = min(y1, y2) - 0.5

                for j in range(len(t) - 1):
                    # 二次贝塞尔曲线
                    px = (1-t[j])**2 * x1 + 2*(1-t[j])*t[j] * mid_x + t[j]**2 * x2
                    py = (1-t[j])**2 * y1 + 2*(1-t[j])*t[j] * mid_y + t[j]**2 * y2
                    px_next = (1-t[j+1])**2 * x1 + 2*(1-t[j+1])*t[j+1] * mid_x + t[j+1]**2 * x2
                    py_next = (1-t[j+1])**2 * y1 + 2*(1-t[j+1])*t[j+1] * mid_y + t[j+1]**2 * y2

                    ax.plot([px, px_next], [py, py_next],
                           color=color, alpha=0.5, linewidth=1.5, zorder=1)

    # 添加线路图例
    legend_elements = []
    for route_name, color in route_colors.items():
        if route_name in routes:
            entrance = routes[route_name].get('entrance', '')
            cableway = routes[route_name].get('cableway', '')
            label = f"{route_name} ({entrance}/{cableway})"
            legend_elements.append(mlines.Line2D([0], [0], marker='o', color='w',
                                            markerfacecolor=color, markersize=10,
                                            label=label, linestyle='None'))

    ax.legend(handles=legend_elements, loc='upper left', fontsize=9,
             framealpha=0.9)

    # 添加交汇点说明
    intersection_text = "节点说明：\n"
    intersection_text += "◆ 红色菱形 = 高频交汇点(3条以上线路)\n"
    intersection_text += "■ 橙色方形 = 中频交汇点(2条线路)\n"
    intersection_text += "● 灰色圆形 = 单线路点"

    ax.text(0.02, 0.02, intersection_text,
           transform=ax.transAxes, fontsize=9,
           verticalalignment='bottom',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax.set_title('黄山 - 多线路空间交汇结构图', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('线路方向', fontsize=12)
    ax.set_ylabel('节点层级', fontsize=12)
    ax.grid(True, alpha=0.15, linestyle='--')

    # 设置Y轴刻度
    ax.set_yticks(sorted(set(node_y_map.values())))
    ax.set_yticklabels([])

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def visualize_comparison(comparison_data: Dict, output_path: str):
    """可视化对比结果"""
    reports = comparison_data.get('reports', [])

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('官方路线 vs 游客路线对比分析', fontsize=18, fontweight='bold')

    # 提取数据
    scenic_spots = []
    coverage_scores = []
    route_scores = []
    time_scores = []
    official_counts = []
    visitor_counts = []
    overlap_counts = []
    unmatched_counts = []

    for report in reports:
        spot = report.get('scenic_spot', '')
        coverage = report.get('coverage_comparison', {})
        route_similarity = report.get('route_similarity', {})
        time_dist = report.get('time_distribution', {})

        scenic_spots.append(spot)
        coverage_scores.append(coverage.get('jaccard_similarity', 0))
        route_scores.append(route_similarity.get('combined_similarity', coverage.get('jaccard_similarity', 0)))
        time_scores.append(time_dist.get('distribution_similarity', 0))
        official_counts.append(coverage.get('official_poi_count', 0))
        visitor_counts.append(coverage.get('visitor_poi_count', 0))
        overlap_counts.append(coverage.get('overlap_count', 0))
        unmatched_counts.append(coverage.get('unmatched_poi_count', 0))

    x = list(range(len(scenic_spots)))
    width = 0.22

    # 1. 景点数量对比
    ax1 = axes[0, 0]
    ax1.bar([i - 1.5 * width for i in x], official_counts, width, label='官方景点数', color='#FFD700')
    ax1.bar([i - 0.5 * width for i in x], visitor_counts, width, label='游客对齐景点数', color='#87CEEB')
    ax1.bar([i + 0.5 * width for i in x], overlap_counts, width, label='重合景点数', color='#9370DB')
    ax1.bar([i + 1.5 * width for i in x], unmatched_counts, width, label='未对齐词数', color='#FF7F50')
    ax1.set_xlabel('景区', fontsize=12)
    ax1.set_ylabel('数量', fontsize=12)
    ax1.set_title('景点覆盖度与对齐质量', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenic_spots)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # 2. 路线相似度（集合 + 顺序）
    ax2 = axes[0, 1]
    colors = ['#FFD700', '#87CEEB', '#9370DB']
    ax2.bar(scenic_spots, route_scores, color=colors[:len(scenic_spots)])
    ax2.set_xlabel('景区', fontsize=12)
    ax2.set_ylabel('相似度', fontsize=12)
    ax2.set_title('路线相似度 (LCS+Jaccard 组合)', fontsize=14)
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for i, (spot, score) in enumerate(zip(scenic_spots, route_scores)):
        ax2.text(i, score + 0.02, f'{score:.3f}', ha='center', fontsize=10)

    # 3. 时间分布相似度（全部景区）
    ax3 = axes[1, 0]
    ax3.bar(scenic_spots, time_scores, color=colors[:len(scenic_spots)])
    ax3.set_xlabel('景区', fontsize=12)
    ax3.set_ylabel('相似度', fontsize=12)
    ax3.set_title('时间分布相似度', fontsize=14)
    ax3.set_ylim(0, 1)
    ax3.grid(True, alpha=0.3, axis='y')
    for i, score in enumerate(time_scores):
        ax3.text(i, score + 0.02, f'{score:.3f}', ha='center', fontsize=10)

    # 4. 评估摘要
    ax4 = axes[1, 1]
    ax4.axis('off')

    summary_text = "对比分析摘要\n" + "="*30 + "\n\n"

    for report in reports:
        spot = report.get('scenic_spot', '')
        summary = report.get('summary', {})
        coverage = report.get('coverage_comparison', {})
        coverage_level = summary.get('coverage_level', '')
        route_level = summary.get('route_similarity_level', '')
        time_level = summary.get('time_distribution_level', '')
        key_findings = summary.get('key_findings', [])

        summary_text += f"【{spot}】\n"
        summary_text += f"覆盖评估: {coverage_level}\n"
        summary_text += f"路线评估: {route_level}\n"
        summary_text += f"时间评估: {time_level}\n"
        summary_text += (
            f"未对齐词: {coverage.get('unmatched_poi_count', 0)} "
            f"(清洗后总词 {coverage.get('cleaned_unique_count', 0)})\n"
        )

        for finding in key_findings:
            summary_text += f"  • {finding}\n"

        summary_text += "\n"

    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
            fontsize=11, verticalalignment='top', family='sans-serif')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    """主函数"""
    print("=" * 60)
    print("任务3：游览路线的层级结构挖掘")
    print("=" * 60)

    # 创建输出目录
    for dir_name in ['hierarchies', 'comparisons']:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    # 景区映射
    spot_en_map = {
        '九寨沟': 'jiuzhaigou',
        '故宫': 'gugong',
        '黄山': 'huangshan'
    }

    # 加载数据
    print("\n[1/4] 加载数据...")
    df = pd.read_excel('../task1_data_collection/data/data_cleaned.xlsx')
    visitor_data = load_visitor_data('../task2_entity_recognition/entity_results.json')

    # 解析官方路线
    print("\n[2/4] 解析官方路线...")

    official_data = {}
    hierarchy_data = {}

    for idx, row in df.iterrows():
        scenic_spot = row['景区名称']
        route_text = row['官方游览路线']

        if pd.isna(route_text):
            continue

        print(f"  解析 {scenic_spot}...")

        # 解析路线
        parsed = RouteParser.parse(scenic_spot, route_text)
        official_data[scenic_spot] = {"parsed": parsed}

        # 构建层级结构
        hierarchy = TimeHierarchyBuilder.build_hierarchy(parsed)
        hierarchy_data[scenic_spot] = hierarchy

        # 保存层级数据
        hierarchy_file = f'hierarchies/{scenic_spot}_hierarchy.json'
        with open(hierarchy_file, 'w', encoding='utf-8') as f:
            json.dump({"parsed": parsed, "hierarchy": hierarchy}, f,
                     ensure_ascii=False, indent=2)

    # 生成对比报告
    print("\n[3/4] 生成对比分析...")

    all_reports = []

    for scenic_spot in spot_en_map.keys():
        if scenic_spot not in official_data or scenic_spot not in visitor_data:
            continue

        print(f"  分析 {scenic_spot}...")

        report = generate_comparison_report(
            scenic_spot,
            official_data[scenic_spot],
            visitor_data[scenic_spot]
        )

        all_reports.append(report)

    # 保存对比报告
    full_report = {
        "generated_at": str(pd.Timestamp.now()),
        "total_spots": len(all_reports),
        "reports": all_reports
    }

    with open('comparisons/comparison_report.json', 'w', encoding='utf-8') as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    # 生成可视化图表
    print("\n[4/4] 生成可视化图表...")

    # 层级结构图
    for scenic_spot in spot_en_map.keys():
        if scenic_spot in hierarchy_data:
            print(f"  生成 {scenic_spot} 层级结构图...")
            output_path = f'hierarchies/{scenic_spot}_hierarchy.png'
            visualize_time_hierarchy(hierarchy_data[scenic_spot], scenic_spot, output_path)

    # 对比分析图
    print("  生成对比分析图...")
    visualize_comparison(full_report, 'comparisons/comparison_charts.png')

    # 打印摘要
    print("\n" + "=" * 60)
    print("任务3完成！")
    print("=" * 60)
    print("\n输出文件:")
    print("  - hierarchies/*.json  : 层级结构数据")
    print("  - hierarchies/*.png  : 层级结构可视化")
    print("  - comparisons/comparison_report.json : 对比分析报告")
    print("  - comparisons/comparison_charts.png  : 对比分析图表")
    print()


if __name__ == '__main__':
    main()
