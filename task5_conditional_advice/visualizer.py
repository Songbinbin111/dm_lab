#!/usr/bin/env python3
"""
任务5：条件性游览建议的抽取 - 可视化模块

功能：
1. 条件类型分布饼图
2. 游客类型对比图
3. 条件-建议网络图
4. 景区对比柱状图
"""

import os
import json
import platform
import re
import textwrap
from typing import Dict, List, Any
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
import numpy as np

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("警告: networkx 未安装，网络图功能将跳过")
    print("安装命令: pip install networkx")


# =============================================================================
# 1. 中文字体设置
# =============================================================================

def setup_chinese_font():
    """设置中文字体"""
    system = platform.system()

    if system == 'Darwin':
        font_path = '/System/Library/Fonts/PingFang.ttc'
    elif system == 'Windows':
        font_path = 'C:/Windows/Fonts/msyh.ttc'
    else:
        font_path = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'

    try:
        font_prop = font_manager.FontProperties(fname=font_path)
        matplotlib.rcParams['font.sans-serif'] = [font_prop.get_name()]
        matplotlib.rcParams['font.family'] = 'sans-serif'
        matplotlib.rcParams['axes.unicode_minus'] = False
        return font_prop
    except Exception:
        matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
        matplotlib.rcParams['axes.unicode_minus'] = False
        return None


FONT_PROP = setup_chinese_font()


# =============================================================================
# 2. 条件性建议可视化器
# =============================================================================

class ConditionalAdviceVisualizer:
    """条件性建议可视化器"""

    def __init__(self, stats_path: str, visitor_analysis_path: str):
        """
        初始化可视化器

        Args:
            stats_path: 统计报告路径
            visitor_analysis_path: 游客分析路径
        """
        with open(stats_path, 'r', encoding='utf-8') as f:
            self.stats = json.load(f)

        with open(visitor_analysis_path, 'r', encoding='utf-8') as f:
            self.visitor_analysis = json.load(f)

        self.by_scenic_spot = self.visitor_analysis.get('condition_analysis', {}).get('by_scenic_spot', {})
        self.condition_color_map = {
            'time': '#3B82F6',
            'weather': '#22C55E',
            'crowd': '#EF4444',
            'physical': '#F59E0B',
            'visitor_type': '#8B5CF6',
            'budget': '#14B8A6',
            'time_duration': '#334155',
            'ticketing': '#EC4899',
            'transport': '#0EA5E9',
            'route': '#84CC16',
            'equipment': '#F97316',
            'policy': '#6366F1',
            'other': '#9CA3AF',
        }

    def create_all_visualizations(self, output_dir: str):
        """
        生成所有可视化图表

        Args:
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)

        print("\n[生成可视化图表]")

        self.plot_condition_distribution(output_dir)
        self.plot_visitor_comparison(output_dir)
        self.plot_scenic_spot_comparison(output_dir)

        if HAS_NETWORKX:
            self.plot_advice_network(output_dir)
        else:
            print("  跳过网络图生成（需要 networkx）")

        print(f"  所有图表已保存到: {output_dir}")

    # ========================================================================
    # 图表1: 条件类型分布饼图
    # ========================================================================

    def plot_condition_distribution(self, output_dir: str):
        """绘制条件类型分布饼图"""
        by_condition = self.stats.get('by_condition_type', {})

        if not by_condition:
            print("  跳过条件分布图（无数据）")
            return

        labels = []
        sizes = []
        colors = []

        for cond_type, count in by_condition.items():
            label = self._get_condition_label(cond_type)
            labels.append(f"{label}\n({count}条)")
            sizes.append(count)
            colors.append(self.condition_color_map.get(cond_type, '#9CA3AF'))

        fig, ax = plt.subplots(figsize=(11, 8))
        _, _, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 11}
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)

        ax.set_title('条件类型分布', fontsize=16, fontweight='bold', pad=20)

        plt.tight_layout()
        plt.savefig(f"{output_dir}/condition_distribution.png", dpi=170, bbox_inches='tight')
        plt.close()
        print("  已生成: condition_distribution.png")

    def _get_condition_label(self, cond_type: str) -> str:
        """获取条件类型的中文标签"""
        label_map = {
            'time': '时间条件',
            'weather': '天气条件',
            'crowd': '人流条件',
            'physical': '体力条件',
            'visitor_type': '游客类型',
            'budget': '预算条件',
            'time_duration': '时长条件',
            'ticketing': '票务条件',
            'transport': '交通条件',
            'route': '路线条件',
            'equipment': '装备条件',
            'policy': '规则条件',
            'other': '其他条件'
        }
        return label_map.get(cond_type, cond_type)

    def _get_visitor_label(self, visitor_type: str) -> str:
        label_map = {
            'family': '亲子游',
            'elderly': '老年游',
            'couple': '情侣游',
            'solo': '独自游',
            'photographer': '摄影游',
            'experienced': '经验丰富',
            'beginner': '新手',
            'general': '一般游客',
        }
        return label_map.get(visitor_type, visitor_type)

    # ========================================================================
    # 图表2: 游客类型对比图（4合1布局）
    # ========================================================================

    def plot_visitor_comparison(self, output_dir: str):
        """绘制游客类型对比图"""
        by_type = self.visitor_analysis.get('visitor_type_analysis', {}).get('by_type', {})

        # 确保有数据，即使是空的
        preferred_types = ['family', 'elderly', 'couple', 'general']
        for vtype in preferred_types:
            if vtype not in by_type:
                by_type[vtype] = {'count': 0, 'condition_type_distribution': {}}

        main_types = preferred_types

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        for idx, vtype in enumerate(main_types):
            ax = axes[idx]
            data = by_type.get(vtype, {})
            cond_dist = data.get('condition_type_distribution', {})

            if cond_dist:
                cond_items = sorted(cond_dist.items(), key=lambda x: x[1], reverse=True)
                cond_labels = [self._get_condition_label(k) for k, _ in cond_items]
                cond_values = [v for _, v in cond_items]
                cond_colors = [self.condition_color_map.get(k, '#9CA3AF') for k, _ in cond_items]

                bars = ax.barh(cond_labels, cond_values, color=cond_colors)

                for bar, val in zip(bars, cond_values):
                    ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2, str(val), va='center', fontsize=9)

                ax.set_xlabel('建议数量', fontsize=10)
                ax.set_title(f'{self._get_visitor_label(vtype)} - 条件分布', fontsize=12, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)
            else:
                ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=14, color='gray')
                ax.set_title(self._get_visitor_label(vtype), fontsize=12)

        fig.suptitle('游客类型条件建议对比', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/visitor_comparison.png", dpi=170, bbox_inches='tight')
        plt.close()
        print("  已生成: visitor_comparison.png")

    # ========================================================================
    # 图表3: 景区对比柱状图
    # ========================================================================

    def plot_scenic_spot_comparison(self, output_dir: str):
        """绘制景区对比柱状图"""
        by_spot = self.by_scenic_spot
        
        # 强制包含九寨沟、故宫、黄山
        target_spots = ['九寨沟', '故宫', '黄山']
        
        # 确保每个景区都在 by_spot 中，即使数据为空
        for spot in target_spots:
            if spot not in by_spot:
                by_spot[spot] = {'condition_types': {}}

        if not by_spot:
            print("  跳过景区对比图（无数据）")
            return

        spots = target_spots
        condition_types = set()

        for spot_data in by_spot.values():
            cond_types = spot_data.get('condition_types', {})
            condition_types.update(cond_types.keys())
            
        # 如果没有任何条件类型，添加一个默认的
        if not condition_types:
            condition_types.add('other')

        condition_types = sorted(list(condition_types))

        data_matrix = []
        for spot in spots:
            row = []
            # 获取该景区的数据，如果不存在则为空字典
            spot_data = by_spot.get(spot, {}).get('condition_types', {})
            for cond_type in condition_types:
                row.append(spot_data.get(cond_type, 0))
            data_matrix.append(row)

        data_matrix = np.array(data_matrix).T

        fig, ax = plt.subplots(figsize=(12, 7))

        bottom = np.zeros(len(spots))
        for idx, cond_type in enumerate(condition_types):
            ax.bar(
                spots,
                data_matrix[idx],
                bottom=bottom,
                label=self._get_condition_label(cond_type),
                color=self.condition_color_map.get(cond_type, '#9CA3AF'),
                alpha=0.85,
            )
            bottom += data_matrix[idx]

        ax.set_xlabel('景区', fontsize=12, fontweight='bold')
        ax.set_ylabel('建议数量', fontsize=12, fontweight='bold')
        ax.set_title('各景区条件类型分布对比', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(f"{output_dir}/scenic_spot_comparison.png", dpi=170, bbox_inches='tight')
        plt.close()
        print("  已生成: scenic_spot_comparison.png")

    # ========================================================================
    # 图表4: 条件-建议分层网络图
    # ========================================================================

    def _strip_condition_prefix(self, cond_text: str) -> str:
        if ':' in cond_text:
            return cond_text.split(':', 1)[1].strip()
        return cond_text.strip()

    def _normalize_advice_text(self, advice_text: str) -> str:
        advice = re.sub(r'\s+', '', advice_text)
        advice = re.split(r'[。；！？!?]', advice)[0]
        return advice.strip('，,。；; ')

    def _shorten(self, text: str, max_len: int = 14) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len - 1] + '…'

    def _wrap_text(self, text: str, width: int = 9) -> str:
        if not text:
            return text
        wrapped = textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False)
        return '\n'.join(wrapped)

    def plot_advice_network(self, output_dir: str):
        """绘制分层条件-建议关联图"""
        by_condition = self.visitor_analysis.get('condition_analysis', {}).get('by_type', {})

        if not by_condition:
            print("  跳过网络图（无数据）")
            return

        G = nx.DiGraph()
        condition_nodes = []
        advice_nodes = set()

        ranked_types = sorted(by_condition.items(), key=lambda x: x[1].get('count', 0), reverse=True)
        max_condition_nodes = 18

        for cond_type, data in ranked_types:
            conditions = data.get('conditions', {})
            sorted_conditions = sorted(conditions.items(), key=lambda x: x[1].get('count', 0), reverse=True)

            for cond_text, cond_data in sorted_conditions[:4]:
                if len(condition_nodes) >= max_condition_nodes:
                    break

                cleaned_condition = self._shorten(self._strip_condition_prefix(cond_text), 18)
                cond_node = f"cond::{cond_type}::{len(condition_nodes)}"
                cond_weight = cond_data.get('count', 1)
                cond_label = f"{self._get_condition_label(cond_type)}\n{cleaned_condition}"

                G.add_node(
                    cond_node,
                    node_type='condition',
                    label=cond_label,
                    weight=cond_weight,
                    cond_type=cond_type,
                )
                condition_nodes.append(cond_node)

                advice_counter = Counter()
                for advice in cond_data.get('advice_list', []):
                    normalized_advice = self._normalize_advice_text(advice)
                    if normalized_advice:
                        advice_counter[normalized_advice] += 1

                for advice_text, count in advice_counter.most_common(2):
                    short_advice = self._shorten(advice_text, 18)
                    advice_node = f"advice::{short_advice}"

                    if advice_node not in G:
                        G.add_node(
                            advice_node,
                            node_type='advice',
                            label=short_advice,
                            weight=count,
                        )
                    else:
                        G.nodes[advice_node]['weight'] += count

                    if G.has_edge(cond_node, advice_node):
                        G[cond_node][advice_node]['weight'] += count
                    else:
                        G.add_edge(cond_node, advice_node, weight=count)

                    advice_nodes.add(advice_node)

            if len(condition_nodes) >= max_condition_nodes:
                break

        if len(condition_nodes) < 2 or len(advice_nodes) < 2:
            print("  跳过网络图（节点太少）")
            return

        advice_node_list = sorted(
            list(advice_nodes),
            key=lambda n: G.nodes[n].get('weight', 1),
            reverse=True,
        )[:20]

        G = G.subgraph(condition_nodes + advice_node_list).copy()
        condition_nodes = [n for n in G.nodes() if G.nodes[n].get('node_type') == 'condition']
        advice_node_list = [n for n in G.nodes() if G.nodes[n].get('node_type') == 'advice']

        fig, ax = plt.subplots(figsize=(16, 10))
        pos = {}

        sorted_conditions = sorted(condition_nodes, key=lambda n: G.nodes[n].get('weight', 1), reverse=True)
        sorted_advices = sorted(advice_node_list, key=lambda n: G.nodes[n].get('weight', 1), reverse=True)

        for idx, node in enumerate(sorted_conditions):
            y = 1 - (idx + 1) / (len(sorted_conditions) + 1)
            pos[node] = (0.22, y)

        for idx, node in enumerate(sorted_advices):
            y = 1 - (idx + 1) / (len(sorted_advices) + 1)
            pos[node] = (0.78, y)

        edges = list(G.edges(data=True))
        edge_widths = [0.6 + 0.9 * e[2].get('weight', 1) for e in edges]
        nx.draw_networkx_edges(
            G,
            pos,
            width=edge_widths,
            alpha=0.35,
            edge_color='#6B7280',
            arrows=False,
            ax=ax,
        )

        cond_types = sorted({G.nodes[n].get('cond_type') for n in sorted_conditions})
        for cond_type in cond_types:
            nodelist = [n for n in sorted_conditions if G.nodes[n].get('cond_type') == cond_type]
            node_sizes = [500 + G.nodes[n].get('weight', 1) * 110 for n in nodelist]
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=nodelist,
                node_color=self.condition_color_map.get(cond_type, '#64748B'),
                node_size=node_sizes,
                alpha=0.9,
                node_shape='o',
                linewidths=0.8,
                edgecolors='white',
                ax=ax,
            )

        advice_sizes = [420 + G.nodes[n].get('weight', 1) * 120 for n in sorted_advices]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=sorted_advices,
            node_color='#F97316',
            node_size=advice_sizes,
            alpha=0.85,
            node_shape='s',
            linewidths=0.8,
            edgecolors='white',
            ax=ax,
        )

        labels = {}
        for node, data in G.nodes(data=True):
            label = data.get('label', node)
            labels[node] = self._wrap_text(label, width=8)

        nx.draw_networkx_labels(
            G,
            pos,
            labels=labels,
            font_size=8,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.75, pad=0.2),
            ax=ax,
        )

        legend_elements = [
            mpatches.Patch(color='#3B82F6', label='条件节点（左）'),
            mpatches.Patch(color='#F97316', label='建议节点（右）')
        ]
        ax.legend(handles=legend_elements, loc='upper right', frameon=True)

        ax.text(0.22, 1.02, '条件', transform=ax.transAxes, fontsize=11, fontweight='bold', ha='center')
        ax.text(0.78, 1.02, '建议', transform=ax.transAxes, fontsize=11, fontweight='bold', ha='center')

        ax.set_title('条件-建议分层关联图（Top关系）', fontsize=16, fontweight='bold', pad=16)
        ax.axis('off')

        plt.tight_layout()
        plt.savefig(f"{output_dir}/advice_network.png", dpi=190, bbox_inches='tight')
        plt.close()
        print("  已生成: advice_network.png")


# =============================================================================
# 3. 主程序
# =============================================================================

if __name__ == '__main__':
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    stats_path = os.path.join(current_dir, 'output/statistics_report.json')
    visitor_path = os.path.join(current_dir, 'output/visitor_analysis.json')
    output_dir = os.path.join(current_dir, 'output/visualizations')

    if not os.path.exists(stats_path):
        print(f"错误: 统计报告不存在: {stats_path}")
        print("请先运行处理器和分析器")
        sys.exit(1)

    if not os.path.exists(visitor_path):
        print(f"错误: 游客分析不存在: {visitor_path}")
        print("请先运行分析器")
        sys.exit(1)

    visualizer = ConditionalAdviceVisualizer(stats_path, visitor_path)
    visualizer.create_all_visualizations(output_dir)

    print("\n可视化完成！")
