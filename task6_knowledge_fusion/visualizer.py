#!/usr/bin/env python3
"""
任务6：多源程序性知识的融合与可视化 - 可视化模块

功能：
1. 绘制知识图谱（主图 + 条件附图）
2. 支持基于游览顺序的层次布局
3. 生成更清晰的节点/边样式
"""

import os
import platform
import json
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict, Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
from matplotlib.lines import Line2D

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None


# =============================================================================
# 中文字体设置
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
# 样式映射
# =============================================================================

NODE_SHAPES = {
    'poi': 'o',
    'transport': 'd',
    'operation': 's',
    'condition': 'h',
    'time_period': '^',
    'entry_exit': 'p'
}

DEFAULT_COLORS = {
    'poi': '#3B82F6',
    'transport': '#22C55E',
    'operation': '#F59E0B',
    'condition': '#8B5CF6',
    'time_period': '#6366F1',
    'entry_exit': '#EC4899'
}

CONDITION_SUBTYPE_COLORS = {
    'other': '#8B5CF6',
    'weather': '#7C3AED',
    'route': '#6D28D9',
    'transport': '#5B21B6',
    'ticketing': '#4C1D95',
    'section_header': '#A78BFA',
    'context_location': '#9333EA',
    'ticketing_failure': '#7E22CE',
    'visit_scope': '#6B21A8',
    'unknown': '#8B5CF6'
}


class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""

    def __init__(self, config_path: str = None):
        if not HAS_NETWORKX:
            raise ImportError("需要安装 networkx: pip install networkx")

        self.node_config = self._load_node_config(config_path)
        self.edge_config = self._load_edge_config(config_path)

    def _load_node_config(self, config_path: str = None) -> Dict:
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config/node_types.json')

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return DEFAULT_COLORS

    def _load_edge_config(self, config_path: str = None) -> Dict:
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config/edge_types.json')

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def visualize_knowledge_graph(
        self,
        graph: nx.DiGraph,
        output_path: str,
        mode: str = 'layered',
        export_main: bool = False,
        export_condition: bool = False,
        figsize: Tuple[int, int] = (18, 12)
    ) -> Dict[str, str]:
        """
        输出单张综合知识图（兼容旧文件名）。

        Args:
            graph: NetworkX有向图
            output_path: 兼容输出文件路径（旧文件名）
            mode: 布局模式
            export_main: 是否额外导出 _main 文件（默认关闭）
            export_condition: 是否导出 _conditions 文件（默认关闭）
            figsize: 画布大小

        Returns:
            产物路径字典
        """
        if graph.number_of_nodes() == 0:
            print("  跳过可视化（图谱为空）")
            return {}

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        base, ext = os.path.splitext(output_path)
        legacy_path = output_path
        main_path = f"{base}_main{ext}"
        condition_path = f"{base}_conditions{ext}"

        # 主图：始终生成 legacy_path，保持兼容
        self._draw_main_graph(graph, legacy_path, figsize=figsize, mode=mode)

        artifacts = {'legacy': legacy_path}

        if export_main:
            self._draw_main_graph(graph, main_path, figsize=figsize, mode=mode)
            artifacts['main'] = main_path

        if export_condition:
            self._draw_condition_graph(graph, condition_path, figsize=figsize)
            artifacts['conditions'] = condition_path

        return artifacts

    def _truncate_label(self, text: str, limit: int = 10) -> str:
        if len(text) <= limit:
            return text
        return text[:limit - 1] + '…'

    def _safe_support(self, edge_data: Dict[str, Any], default_value: float = 1.0) -> float:
        support = edge_data.get('support_count', edge_data.get('weight', default_value))
        if isinstance(support, (int, float)):
            return max(0.5, float(support))
        return default_value

    def _compute_main_layout(self, graph: nx.DiGraph, focus_condition_nodes: Set[str]) -> Dict[str, Tuple[float, float]]:
        """按顺序层次布局：POI为主，时段在上，关键条件靠近关联POI。"""
        pos: Dict[str, Tuple[float, float]] = {}

        poi_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'poi']
        period_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'time_period']

        seq_edges = [
            (u, v, d) for u, v, d in graph.edges(data=True)
            if d.get('edge_type') == 'sequence' and u in poi_nodes and v in poi_nodes
        ]

        route_pool = set()
        node_route_membership = defaultdict(set)
        node_rank_candidates = defaultdict(list)

        for u, v, edge_data in seq_edges:
            route_ids = edge_data.get('route_ids', [])
            if isinstance(route_ids, list):
                for route_id in route_ids:
                    route_pool.add(route_id)
                    node_route_membership[u].add(route_id)
                    node_route_membership[v].add(route_id)
            seq_indices = edge_data.get('sequence_indices', [])
            if isinstance(seq_indices, list) and seq_indices:
                base_rank = min(seq_indices)
                node_rank_candidates[u].append(float(base_rank))
                node_rank_candidates[v].append(float(base_rank) + 0.6)

        route_list = sorted(route_pool)
        route_band = {}
        if route_list:
            center = (len(route_list) - 1) / 2.0
            for idx, route_id in enumerate(route_list):
                route_band[route_id] = (idx - center) * 0.45

        fallback_rank = {node: idx for idx, node in enumerate(sorted(poi_nodes))}
        poi_rank = {}
        for node in poi_nodes:
            if node_rank_candidates[node]:
                poi_rank[node] = min(node_rank_candidates[node])
            else:
                poi_rank[node] = float(fallback_rank[node])

        sorted_by_rank = sorted(poi_nodes, key=lambda n: (poi_rank[n], graph.nodes[n].get('label', '')))
        unique_ranks = sorted({poi_rank[n] for n in poi_nodes})
        rank_to_x = {rank: idx / max(1, len(unique_ranks) - 1) for idx, rank in enumerate(unique_ranks)}

        group_counts = defaultdict(int)
        for node in sorted_by_rank:
            rank = poi_rank[node]
            groups = node_route_membership.get(node, set())
            if len(groups) == 1:
                band = route_band.get(next(iter(groups)), 0.0)
            else:
                band = 0.0

            group_key = (rank, round(band, 2))
            offset = group_counts[group_key]
            group_counts[group_key] += 1
            y = band - 0.06 * offset
            pos[node] = (rank_to_x.get(rank, 0.5), y)

        # 时段节点放顶部，并与其覆盖POI的平均x对齐
        for idx, period_node in enumerate(period_nodes):
            successors = [n for n in graph.successors(period_node) if n in pos]
            if successors:
                x = sum(pos[n][0] for n in successors) / len(successors)
            else:
                x = idx / max(1, len(period_nodes) - 1)
            pos[period_node] = (x, 1.0)

        # 关键条件节点放上中部，靠近目标POI
        for idx, cond_node in enumerate(sorted(focus_condition_nodes)):
            linked_pois = [n for n in graph.successors(cond_node) if n in pos]
            if linked_pois:
                x = sum(pos[n][0] for n in linked_pois) / len(linked_pois)
            else:
                x = 0.5
            y = 0.65 - 0.09 * idx
            pos[cond_node] = (x, y)

        return pos

    def _draw_main_graph(
        self,
        graph: nx.DiGraph,
        output_path: str,
        figsize: Tuple[int, int],
        mode: str = 'layered'
    ) -> None:
        scenic_spot = graph.graph.get('scenic_spot', '景区')
        recommended_route = graph.graph.get('recommended_route', {})
        recommended_route_id = recommended_route.get('route_id', '')

        condition_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'condition']
        condition_nodes = sorted(
            condition_nodes,
            key=lambda n: (graph.out_degree(n), graph.nodes[n].get('importance_score', 0.0)),
            reverse=True
        )
        focus_condition_nodes = set(condition_nodes[:6])

        if mode == 'layered':
            pos = self._compute_main_layout(graph, focus_condition_nodes)
        else:
            pos = nx.spring_layout(graph, seed=42)

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor('white')

        # 1) 绘制顺序边（主信息）
        seq_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if d.get('edge_type') == 'sequence' and u in pos and v in pos
        ]
        recommended_seq_edges = [
            (u, v) for u, v in seq_edges
            if graph.get_edge_data(u, v).get('is_recommended')
        ]
        normal_seq_edges = [edge for edge in seq_edges if edge not in recommended_seq_edges]

        normal_seq_widths = [
            1.6 + 0.5 * min(3.0, self._safe_support(graph.get_edge_data(u, v), 1.0))
            for u, v in normal_seq_edges
        ]
        if normal_seq_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=normal_seq_edges,
                edge_color=self.edge_config.get('sequence', {}).get('color', '#2563EB'),
                width=normal_seq_widths,
                alpha=0.50,
                arrows=True,
                arrowsize=14,
                arrowstyle='-|>',
                ax=ax,
                connectionstyle='arc3,rad=0.08'
            )

        recommended_seq_widths = [
            2.3 + 0.7 * min(3.0, self._safe_support(graph.get_edge_data(u, v), 1.0))
            for u, v in recommended_seq_edges
        ]
        if recommended_seq_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=recommended_seq_edges,
                edge_color='#F97316',
                width=recommended_seq_widths,
                alpha=0.88,
                arrows=True,
                arrowsize=16,
                arrowstyle='-|>',
                ax=ax,
                connectionstyle='arc3,rad=0.09'
            )

        # 2) 绘制时段边（弱化）
        temporal_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if d.get('edge_type') == 'temporal' and u in pos and v in pos
        ]
        if temporal_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=temporal_edges,
                edge_color=self.edge_config.get('temporal', {}).get('color', '#6366F1'),
                width=1.0,
                alpha=0.25,
                arrows=False,
                style='solid',
                ax=ax
            )

        # 3) 绘制关键条件边（只显示少量）
        conditional_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if d.get('edge_type') == 'conditional' and u in focus_condition_nodes and u in pos and v in pos
        ]
        if conditional_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=conditional_edges,
                edge_color=self.edge_config.get('conditional', {}).get('color', '#8B5CF6'),
                width=1.2,
                alpha=0.45,
                arrows=True,
                arrowsize=10,
                style='dotted',
                ax=ax,
                connectionstyle='arc3,rad=0.06'
            )

        # 4) 绘制节点
        poi_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'poi' and n in pos]
        visitor_poi_nodes = [n for n in poi_nodes if graph.nodes[n].get('source') == 'visitor']
        official_poi_nodes = [n for n in poi_nodes if n not in visitor_poi_nodes]
        period_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'time_period' and n in pos]
        focus_conditions = [n for n in focus_condition_nodes if n in pos]

        official_poi_sizes = [
            500 + 550 * min(1.5, graph.nodes[n].get('importance_score', 1.0))
            for n in official_poi_nodes
        ]
        if official_poi_nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=official_poi_nodes,
                node_color=self.node_config.get('poi', {}).get('color', '#3B82F6'),
                node_shape='o',
                node_size=official_poi_sizes,
                alpha=0.88,
                edgecolors='white',
                linewidths=1.4,
                ax=ax
            )

        visitor_poi_sizes = [
            600 + 620 * min(1.5, graph.nodes[n].get('importance_score', 1.0))
            for n in visitor_poi_nodes
        ]
        if visitor_poi_nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=visitor_poi_nodes,
                node_color='#FB923C',
                node_shape='o',
                node_size=visitor_poi_sizes,
                alpha=0.95,
                edgecolors='#7C2D12',
                linewidths=1.8,
                ax=ax
            )

        if period_nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=period_nodes,
                node_color=self.node_config.get('time_period', {}).get('color', '#6366F1'),
                node_shape='^',
                node_size=520,
                alpha=0.8,
                edgecolors='white',
                linewidths=1.2,
                ax=ax
            )

        if focus_conditions:
            cond_colors = []
            for node in focus_conditions:
                subtype = graph.nodes[node].get('condition_subtype', 'other')
                cond_colors.append(CONDITION_SUBTYPE_COLORS.get(subtype, '#8B5CF6'))
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=focus_conditions,
                node_color=cond_colors,
                node_shape='h',
                node_size=650,
                alpha=0.88,
                edgecolors='white',
                linewidths=1.2,
                ax=ax
            )

        # 5) 标签（简洁）
        labels = {}
        for node in poi_nodes + period_nodes + focus_conditions:
            node_data = graph.nodes[node]
            label = node_data.get('display_label', node_data.get('label', ''))
            if node_data.get('node_type') == 'poi':
                short_label = self._truncate_label(label, 8)
                if node in visitor_poi_nodes:
                    labels[node] = f'★{short_label}'
                else:
                    labels[node] = short_label
            else:
                labels[node] = self._truncate_label(label, 10)

        nx.draw_networkx_labels(
            graph,
            pos,
            labels=labels,
            font_size=9,
            font_family='sans-serif',
            ax=ax
        )

        # 6) 图例
        legend_handles = [
            Line2D([0], [0], color=self.edge_config.get('sequence', {}).get('color', '#2563EB'), lw=2.5, label='游览顺序'),
            Line2D([0], [0], color='#F97316', lw=3.0, label='推荐路线'),
            Line2D([0], [0], color=self.edge_config.get('temporal', {}).get('color', '#6366F1'), lw=1.2, alpha=0.5, label='时段关联'),
            Line2D([0], [0], color=self.edge_config.get('conditional', {}).get('color', '#8B5CF6'), lw=1.5, linestyle=':', label='关键条件'),
            Line2D([0], [0], marker='o', color='w', label='景点', markerfacecolor=self.node_config.get('poi', {}).get('color', '#3B82F6'), markersize=9),
            Line2D([0], [0], marker='o', color='w', label='游客高频景点', markerfacecolor='#FB923C', markeredgecolor='#7C2D12', markersize=9),
            Line2D([0], [0], marker='^', color='w', label='时段', markerfacecolor=self.node_config.get('time_period', {}).get('color', '#6366F1'), markersize=9),
            Line2D([0], [0], marker='h', color='w', label='条件', markerfacecolor='#8B5CF6', markersize=9)
        ]
        ax.legend(handles=legend_handles, loc='upper left', fontsize=9, framealpha=0.92, ncol=2)

        route_suffix = f' | 推荐路线: {recommended_route_id}' if recommended_route_id else ''
        ax.set_title(f'{scenic_spot} - 游览知识图谱（主图）{route_suffix}', fontsize=17, fontweight='bold', pad=18)
        ax.set_axis_off()
        ax.margins(0.08)

        plt.tight_layout()
        plt.savefig(output_path, dpi=220, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"  已生成: {output_path}")

    def _compute_condition_layout(self, graph: nx.DiGraph) -> Dict[str, Tuple[float, float]]:
        pos: Dict[str, Tuple[float, float]] = {}

        condition_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'condition']
        poi_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'poi']

        cond_sorted = sorted(condition_nodes, key=lambda n: graph.out_degree(n), reverse=True)
        poi_sorted = sorted(poi_nodes, key=lambda n: graph.in_degree(n), reverse=True)

        for idx, node in enumerate(cond_sorted):
            y = 1 - (idx + 1) / (len(cond_sorted) + 1)
            pos[node] = (0.10, y)

        for idx, node in enumerate(poi_sorted):
            y = 1 - (idx + 1) / (len(poi_sorted) + 1)
            pos[node] = (0.90, y)

        return pos

    def _draw_condition_graph(self, graph: nx.DiGraph, output_path: str, figsize: Tuple[int, int]) -> None:
        scenic_spot = graph.graph.get('scenic_spot', '景区')

        cond_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'condition']
        if not cond_nodes:
            # 没有条件节点时生成提示图
            fig, ax = plt.subplots(figsize=figsize)
            fig.patch.set_facecolor('white')
            ax.text(0.5, 0.5, f'{scenic_spot} 无条件关系可视化内容', ha='center', va='center', fontsize=14)
            ax.set_axis_off()
            plt.tight_layout()
            plt.savefig(output_path, dpi=220, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            print(f"  已生成: {output_path}")
            return

        pos = self._compute_condition_layout(graph)
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor('white')

        cond_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if d.get('edge_type') == 'conditional' and u in pos and v in pos
        ]

        widths = [
            1.0 + 0.4 * min(3.0, self._safe_support(graph.get_edge_data(u, v), 1.0))
            for u, v in cond_edges
        ]

        if cond_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=cond_edges,
                edge_color=self.edge_config.get('conditional', {}).get('color', '#8B5CF6'),
                width=widths,
                style='dotted',
                alpha=0.55,
                arrows=True,
                arrowsize=11,
                arrowstyle='-|>',
                ax=ax,
                connectionstyle='arc3,rad=0.03'
            )

        poi_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'poi' and n in pos]
        condition_nodes = [n for n, d in graph.nodes(data=True) if d.get('node_type') == 'condition' and n in pos]

        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=poi_nodes,
            node_color=self.node_config.get('poi', {}).get('color', '#3B82F6'),
            node_shape='o',
            node_size=520,
            alpha=0.9,
            edgecolors='white',
            linewidths=1.2,
            ax=ax
        )

        cond_colors = []
        for node in condition_nodes:
            subtype = graph.nodes[node].get('condition_subtype', 'other')
            cond_colors.append(CONDITION_SUBTYPE_COLORS.get(subtype, '#8B5CF6'))

        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=condition_nodes,
            node_color=cond_colors,
            node_shape='h',
            node_size=650,
            alpha=0.92,
            edgecolors='white',
            linewidths=1.2,
            ax=ax
        )

        labels = {}
        for node in poi_nodes:
            labels[node] = self._truncate_label(graph.nodes[node].get('display_label', graph.nodes[node].get('label', '')), 9)
        for node in condition_nodes:
            labels[node] = self._truncate_label(graph.nodes[node].get('display_label', graph.nodes[node].get('label', '')), 12)

        nx.draw_networkx_labels(
            graph,
            pos,
            labels=labels,
            font_size=9,
            font_family='sans-serif',
            ax=ax
        )

        subtype_counter = Counter(graph.nodes[n].get('condition_subtype', 'other') for n in condition_nodes)
        subtype_handles = []
        for subtype, _ in subtype_counter.most_common(5):
            subtype_handles.append(
                mpatches.Patch(color=CONDITION_SUBTYPE_COLORS.get(subtype, '#8B5CF6'), label=f'条件:{subtype}')
            )

        legend_handles = [
            Line2D([0], [0], color=self.edge_config.get('conditional', {}).get('color', '#8B5CF6'), lw=1.8, linestyle=':', label='条件关系'),
            Line2D([0], [0], marker='o', color='w', label='景点', markerfacecolor=self.node_config.get('poi', {}).get('color', '#3B82F6'), markersize=9),
            Line2D([0], [0], marker='h', color='w', label='条件', markerfacecolor='#8B5CF6', markersize=9)
        ] + subtype_handles

        ax.legend(handles=legend_handles, loc='upper left', fontsize=9, framealpha=0.92, ncol=2)

        ax.set_title(f'{scenic_spot} - 条件关系图（附图）', fontsize=17, fontweight='bold', pad=18)
        ax.set_axis_off()
        ax.margins(0.10)

        plt.tight_layout()
        plt.savefig(output_path, dpi=220, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"  已生成: {output_path}")


# =============================================================================
# 便捷函数
# =============================================================================

def visualize_graph(
    graph: nx.DiGraph,
    output_path: str,
    mode: str = 'layered'
) -> Dict[str, str]:
    """
    便捷函数：可视化知识图谱

    Args:
        graph: NetworkX图
        output_path: 输出路径（兼容路径）
        mode: 布局模式
    """
    visualizer = KnowledgeGraphVisualizer()
    return visualizer.visualize_knowledge_graph(graph, output_path, mode=mode)


if __name__ == '__main__':
    from data_loader import MultiSourceDataLoader
    from knowledge_fusion import KnowledgeFusionEngine
    from graph_builder import KnowledgeGraphBuilder

    loader = MultiSourceDataLoader()
    spot_data = loader.load_scenic_spot('九寨沟')

    if 'error' not in spot_data:
        engine = KnowledgeFusionEngine('九寨沟')
        fused = engine.build_composite_knowledge(spot_data)

        builder = KnowledgeGraphBuilder()
        graph = builder.build_graph(fused)

        viz = KnowledgeGraphVisualizer()
        viz.visualize_knowledge_graph(
            graph,
            'output/visualizations/test_knowledge_graph.png',
            mode='layered'
        )
