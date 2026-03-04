#!/usr/bin/env python3
"""
任务6：多源程序性知识的融合与可视化 - 知识图谱构建模块

功能：
1. 定义节点和边类型
2. 构建NetworkX有向图
3. 导出图谱数据
"""

import json
import re
from typing import Dict, List, Any, Set, Tuple
from enum import Enum
from datetime import datetime
from collections import defaultdict

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None


class NodeType(Enum):
    """节点类型枚举"""
    POI = "poi"                  # 景点节点
    TRANSPORT = "transport"      # 交通方式节点
    OPERATION = "operation"      # 操作节点（购票/用餐等）
    CONDITION = "condition"      # 条件节点
    TIME_PERIOD = "time_period"  # 时段节点
    ENTRY_EXIT = "entry_exit"    # 入口/出口节点


class EdgeType(Enum):
    """边类型枚举"""
    SEQUENCE = "sequence"        # 游览顺序
    TRANSPORT = "transport"      # 交通连接
    CONDITIONAL = "conditional"  # 条件关系
    TEMPORAL = "temporal"        # 时间关系


class ConditionPostProcessor:
    """task6 内部条件后处理：清洗与 other 细分。"""

    SECTION_PATTERNS = [
        re.compile(r'^[一二三四五六七八九十]+[、.．]'),
        re.compile(r'^[（(]?[一二三四五六七八九十]+[)）]'),
        re.compile(r'^第[一二三四五六七八九十]+[章节条部分]')
    ]

    CONDITION_KEYWORDS = {
        '路线', '顺序', '门票', '抢票', '预约', '雨', '雪', '雾', '地铁', '索道', '缆车', '中转',
        '早', '晚', '提前', '入场', '体力', '老人', '亲子', '新手', '第一次', '路线', '入口', '出口'
    }

    ACTION_KEYWORDS = {
        '建议', '推荐', '最好', '可以', '不要', '别', '乘坐', '购买', '预订', '抢', '入场', '避开',
        '安排', '跟团', '前往', '走', '带', '坐', '休息'
    }

    TYPE_BASE_CONFIDENCE = {
        'time': 0.9,
        'weather': 0.9,
        'crowd': 0.85,
        'physical': 0.85,
        'visitor_type': 0.85,
        'budget': 0.8,
        'time_duration': 0.85,
        'ticketing': 0.9,
        'transport': 0.9,
        'route': 0.9,
        'equipment': 0.85,
        'policy': 0.8,
        'other': 0.6
    }

    OTHER_SUBTYPE_PATTERNS = {
        'ticketing_failure': re.compile(r'(抢不到|抢票失败|没票|无票|余票|放票)'),
        'context_location': re.compile(r'(北麓|南麓|东麓|西麓|附近|周边|景区|入口|出口)'),
        'visit_scope': re.compile(r'(看|游览|特展|展览|馆|景点|区域)')
    }

    def _clean_text(self, text: str) -> str:
        text = (text or '').strip()
        text = re.sub(r'\s+', '', text)
        return text.strip('，,。；;:："\'“”‘’()（）[]【】')

    def _is_section_header(self, condition_text: str) -> bool:
        for pattern in self.SECTION_PATTERNS:
            if pattern.search(condition_text):
                return True
        return False

    def _is_short_generic(self, condition_text: str) -> bool:
        if len(condition_text) >= 2:
            return False
        return not any(keyword in condition_text for keyword in self.CONDITION_KEYWORDS)

    def _is_prefix_noise(self, condition_text: str, advice_text: str) -> bool:
        if not condition_text or not advice_text:
            return False
        if not advice_text.startswith(condition_text):
            return False
        return not any(action in advice_text for action in self.ACTION_KEYWORDS)

    def _score_condition_confidence(
        self,
        cond_type: str,
        condition_text: str,
        advice_text: str,
        is_section_header: bool,
        is_prefix_noise: bool
    ) -> float:
        score = self.TYPE_BASE_CONFIDENCE.get(cond_type, 0.6)

        if len(condition_text) >= 6:
            score += 0.05
        if any(marker in advice_text for marker in self.ACTION_KEYWORDS):
            score += 0.05
        if is_section_header:
            score -= 0.25
        if is_prefix_noise:
            score -= 0.20

        return round(max(0.1, min(score, 0.98)), 3)

    def _rewrite_section_header_condition(self, condition_text: str, advice_text: str) -> str:
        """
        将“章节标题型条件”改写为更真实的条件描述。
        例如：四、游玩路线 -> 2小时快速游路线
        """
        if not self._is_section_header(condition_text):
            return condition_text

        # 优先提取“X小时快速游路线 / 半日游路线 / 深度游路线”等短语
        route_patterns = [
            r'(\d+小时[^:：，,。；;]{0,12}?路线)',
            r'((?:半日游|一日游|深度游|快速游)[^:：，,。；;]{0,10}?路线)',
            r'((?:推荐|建议)[-—]?\d+小时[^:：，,。；;]{0,12}?路线)'
        ]
        for pattern in route_patterns:
            match = re.search(pattern, advice_text)
            if match:
                candidate = self._clean_text(match.group(1))
                if candidate and not self._is_section_header(candidate):
                    return candidate

        # 回退：若建议中出现“路线”，截取其前面的短片段
        route_idx = advice_text.find('路线')
        if route_idx >= 0:
            start = max(0, route_idx - 8)
            candidate = self._clean_text(advice_text[start:route_idx + 2])
            if candidate and len(candidate) >= 4 and not self._is_section_header(candidate):
                return candidate

        # 无法改写时返回空，交给上层丢弃
        return ''

    def _infer_other_subtype(self, condition_text: str, advice_text: str) -> str:
        if self._is_section_header(condition_text):
            return 'section_header'

        for subtype, pattern in self.OTHER_SUBTYPE_PATTERNS.items():
            if pattern.search(condition_text) or pattern.search(advice_text):
                return subtype

        return 'unknown'

    def process(self, poi_advice_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        cleaned_poi_advice_map = {poi: [] for poi in poi_advice_map.keys()}
        condition_index: Dict[str, Dict[str, Any]] = {}

        report = {
            'input_advice_count': 0,
            'output_advice_count': 0,
            'dropped_count': 0,
            'dropped_reasons': defaultdict(int),
            'kept_other_subtypes': defaultdict(int)
        }

        for poi, advices in poi_advice_map.items():
            for advice in advices:
                report['input_advice_count'] += 1

                advice_text = self._clean_text(advice.get('advice_text', ''))
                cond_data = advice.get('condition', {})
                cond_text = self._clean_text(cond_data.get('text', ''))
                cond_type = cond_data.get('type', 'other')
                cond_type_label = cond_data.get('type_label', cond_type)

                if not cond_text:
                    report['dropped_count'] += 1
                    report['dropped_reasons']['empty_condition'] += 1
                    continue

                if self._is_short_generic(cond_text):
                    report['dropped_count'] += 1
                    report['dropped_reasons']['short_generic'] += 1
                    continue

                is_section_header = self._is_section_header(cond_text)
                if is_section_header:
                    rewritten = self._rewrite_section_header_condition(cond_text, advice_text)
                    if rewritten:
                        cond_text = rewritten
                        is_section_header = self._is_section_header(cond_text)
                    else:
                        report['dropped_count'] += 1
                        report['dropped_reasons']['section_header_unresolved'] += 1
                        continue

                is_prefix_noise = self._is_prefix_noise(cond_text, advice_text)
                confidence = self._score_condition_confidence(
                    cond_type,
                    cond_text,
                    advice_text,
                    is_section_header,
                    is_prefix_noise
                )

                condition_subtype = cond_type
                if cond_type == 'other':
                    condition_subtype = self._infer_other_subtype(cond_text, advice_text)
                    report['kept_other_subtypes'][condition_subtype] += 1
                elif is_section_header:
                    condition_subtype = 'section_header'

                if is_section_header:
                    report['dropped_reasons']['section_header_as_low_confidence'] += 1
                if is_prefix_noise:
                    report['dropped_reasons']['prefix_inference_as_low_confidence'] += 1

                cleaned_advice = dict(advice)
                cleaned_advice['condition'] = dict(cond_data)
                cleaned_advice['condition']['text'] = cond_text
                cleaned_advice['condition']['subtype'] = condition_subtype
                cleaned_advice['condition']['type_label'] = cond_type_label
                cleaned_advice['condition']['confidence'] = confidence
                cleaned_advice['advice_text'] = advice_text

                cleaned_poi_advice_map[poi].append(cleaned_advice)
                report['output_advice_count'] += 1

                cond_key = f"{cond_type}_{cond_text}"
                if cond_key not in condition_index:
                    condition_index[cond_key] = {
                        'type': cond_type,
                        'text': cond_text,
                        'raw_condition': cond_text,
                        'display_label': cond_text[:12] + ('…' if len(cond_text) > 12 else ''),
                        'subtype': condition_subtype,
                        'type_label': cond_type_label,
                        'avg_confidence': confidence,
                        'count': 0,
                        'pois': set(),
                        'advice_samples': []
                    }

                condition_index[cond_key]['count'] += 1
                condition_index[cond_key]['pois'].add(poi)
                prev_avg = condition_index[cond_key]['avg_confidence']
                prev_count = max(condition_index[cond_key]['count'] - 1, 0)
                condition_index[cond_key]['avg_confidence'] = round(
                    (prev_avg * prev_count + confidence) / condition_index[cond_key]['count'],
                    3
                )
                if advice_text and advice_text not in condition_index[cond_key]['advice_samples']:
                    if len(condition_index[cond_key]['advice_samples']) < 3:
                        condition_index[cond_key]['advice_samples'].append(advice_text)

        for key, cond in condition_index.items():
            cond['pois'] = sorted(cond['pois'])

        report['dropped_reasons'] = dict(report['dropped_reasons'])
        report['kept_other_subtypes'] = dict(report['kept_other_subtypes'])
        report['condition_node_count'] = len(condition_index)

        return {
            'poi_advice_map': cleaned_poi_advice_map,
            'condition_index': condition_index,
            'report': report
        }


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self, config_path: str = None):
        """
        初始化图谱构建器

        Args:
            config_path: 配置文件路径
        """
        if not HAS_NETWORKX:
            raise ImportError("需要安装 networkx: pip install networkx")

        self.node_config = self._load_node_config(config_path)
        self.edge_config = self._load_edge_config(config_path)
        self.condition_processor = ConditionPostProcessor()

    def _load_node_config(self, config_path: str = None) -> Dict:
        """加载节点配置"""
        if config_path is None:
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'config/node_types.json')

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 默认配置
            return {
                'poi': {'color': '#3B82F6', 'shape': 'o', 'size_base': 800},
                'transport': {'color': '#22C55E', 'shape': 'd', 'size_base': 400},
                'condition': {'color': '#8B5CF6', 'shape': 'h', 'size_base': 450}
            }

    def _load_edge_config(self, config_path: str = None) -> Dict:
        """加载边配置"""
        if config_path is None:
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'config/edge_types.json')

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 默认配置
            return {
                'sequence': {'color': '#3B82F6', 'style': 'solid'},
                'conditional': {'color': '#8B5CF6', 'style': 'dotted'}
            }

    def _generate_node_id(self, node_type: str, label: str) -> str:
        """生成唯一节点ID"""
        clean_label = re.sub(r'[^\w\u4e00-\u9fff]', '_', label)
        return f"{node_type}_{clean_label}"

    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(value, max_value))

    def build_graph(self, fused_data: Dict[str, Any]) -> nx.DiGraph:
        """
        构建知识图谱

        Args:
            fused_data: knowledge_fusion返回的融合数据

        Returns:
            NetworkX有向图
        """
        graph = nx.DiGraph()
        scenic_spot = fused_data.get('scenic_spot', '')

        condition_result = self.condition_processor.process(fused_data.get('poi_advice_map', {}))
        fused_data['poi_advice_map_cleaned'] = condition_result['poi_advice_map']
        fused_data['condition_index'] = condition_result['condition_index']
        fused_data['condition_cleaning_report'] = condition_result['report']

        # 1. 添加POI节点
        self._add_poi_nodes(graph, fused_data)

        # 2. 添加时段节点
        self._add_time_period_nodes(graph, fused_data)

        # 3. 添加条件节点
        self._add_condition_nodes(graph, fused_data)

        # 4. 创建边关系
        self._create_edges(graph, fused_data)

        # 5. 添加图属性
        graph.graph['scenic_spot'] = scenic_spot
        graph.graph['generated_at'] = datetime.now().isoformat()
        graph.graph['node_count'] = graph.number_of_nodes()
        graph.graph['edge_count'] = graph.number_of_edges()
        graph.graph['condition_cleaning_report'] = fused_data.get('condition_cleaning_report', {})
        graph.graph['recommended_route'] = fused_data.get('recommended_route', {})
        graph.graph['visitor_supplemented'] = fused_data.get('visitor_supplemented', [])

        return graph

    def _add_poi_nodes(self, graph: nx.DiGraph, fused_data: Dict) -> None:
        """添加POI节点"""
        fused_pois = fused_data.get('fused_pois', [])
        poi_weights = fused_data.get('poi_weights', {})
        official_pois = set(fused_data.get('official_pois', []))

        for poi in fused_pois:
            node_id = self._generate_node_id('poi', poi)

            if poi in official_pois:
                source = 'official'
            else:
                source = 'visitor'

            weight = poi_weights.get(poi, 1.0)
            importance = self._clamp(weight, 0.4, 1.4)

            graph.add_node(
                node_id,
                node_type=NodeType.POI.value,
                label=poi,
                display_label=poi,
                source=source,
                weight=weight,
                importance_score=importance,
                original_type='poi'
            )

    def _add_time_period_nodes(self, graph: nx.DiGraph, fused_data: Dict) -> None:
        """添加时段节点"""
        time_periods = fused_data.get('time_periods', {})

        for period in time_periods.keys():
            node_id = self._generate_node_id('period', period)

            graph.add_node(
                node_id,
                node_type=NodeType.TIME_PERIOD.value,
                label=period,
                display_label=period,
                source='official',
                weight=0.55,
                importance_score=0.55,
                original_type='time_period'
            )

    def _add_condition_nodes(self, graph: nx.DiGraph, fused_data: Dict) -> None:
        """添加条件节点"""
        condition_index = fused_data.get('condition_index', {})

        for cond_key, cond_data in condition_index.items():
            node_id = self._generate_node_id('condition', cond_key)
            count = cond_data.get('count', 1)
            normalized_weight = self._clamp(0.8 + 0.15 * count, 0.75, 1.6)
            importance = self._clamp(0.6 + 0.08 * count, 0.6, 1.2)

            graph.add_node(
                node_id,
                node_type=NodeType.CONDITION.value,
                label=cond_data.get('display_label', cond_data.get('text', '')),
                display_label=cond_data.get('display_label', cond_data.get('text', '')),
                raw_condition=cond_data.get('raw_condition', cond_data.get('text', '')),
                condition_type=cond_data.get('type', 'other'),
                condition_type_label=cond_data.get('type_label', cond_data.get('type', 'other')),
                condition_subtype=cond_data.get('subtype', 'unknown'),
                confidence=cond_data.get('avg_confidence', 0.6),
                advice_samples=cond_data.get('advice_samples', []),
                connected_pois=cond_data.get('pois', []),
                weight=normalized_weight,
                importance_score=importance,
                original_type='condition'
            )

    def _create_edges(self, graph: nx.DiGraph, fused_data: Dict) -> None:
        """创建边关系"""
        self._add_sequence_edges(graph, fused_data)
        self._add_temporal_edges(graph, fused_data)
        self._add_conditional_edges(graph, fused_data)

    def _add_sequence_edges(self, graph: nx.DiGraph, fused_data: Dict) -> None:
        """添加游览顺序边（基于统一路线结构，聚合重复边）。"""
        normalized_routes = fused_data.get('normalized_routes', [])
        edge_aggregation = {}
        recommended_route_id = fused_data.get('recommended_route', {}).get('route_id', '')

        for route in normalized_routes:
            from_poi = route.get('from_poi')
            to_poi = route.get('to_poi')
            if not from_poi or not to_poi:
                continue

            from_id = self._generate_node_id('poi', from_poi)
            to_id = self._generate_node_id('poi', to_poi)

            if from_id not in graph.nodes() or to_id not in graph.nodes():
                continue

            edge_key = (from_id, to_id)
            if edge_key not in edge_aggregation:
                edge_aggregation[edge_key] = {
                    'support_count': 0,
                    'route_ids': set(),
                    'route_support': defaultdict(int),
                    'sequence_indices': set(),
                    'transports': set(),
                    'source_formats': set(),
                    'time_windows': set(),
                    'durations': set(),
                    'recommended_support_count': 0,
                    'recommended_sequence_indices': set()
                }

            agg = edge_aggregation[edge_key]
            agg['support_count'] += 1
            route_id = str(route.get('route_id') or 'main')
            agg['route_ids'].add(route_id)
            agg['route_support'][route_id] += 1
            if route.get('sequence_index') is not None:
                agg['sequence_indices'].add(route.get('sequence_index'))
                if recommended_route_id and route_id == recommended_route_id:
                    agg['recommended_sequence_indices'].add(route.get('sequence_index'))
            if route.get('transport'):
                agg['transports'].add(route.get('transport'))
            if route.get('source_format'):
                agg['source_formats'].add(route.get('source_format'))
            if route.get('duration'):
                agg['durations'].add(route.get('duration'))
            if recommended_route_id and route_id == recommended_route_id:
                agg['recommended_support_count'] += 1

            time_window = f"{route.get('time_start', '')}-{route.get('time_end', '')}".strip('-')
            if time_window and time_window != '-':
                agg['time_windows'].add(time_window)

        for (from_id, to_id), agg in edge_aggregation.items():
            support_count = agg['support_count']
            recommended_support = agg['recommended_support_count']
            is_recommended = recommended_support > 0 if recommended_route_id else False
            graph.add_edge(
                from_id,
                to_id,
                edge_type=EdgeType.SEQUENCE.value,
                support_count=support_count,
                route_ids=sorted(agg['route_ids']),
                route_support=dict(sorted(agg['route_support'].items())),
                sequence_indices=sorted(agg['sequence_indices']),
                recommended_route_id=recommended_route_id,
                recommended_support_count=recommended_support,
                recommended_sequence_indices=sorted(agg['recommended_sequence_indices']),
                is_recommended=is_recommended,
                transport=' / '.join(sorted(agg['transports'])),
                source_format=' / '.join(sorted(agg['source_formats'])),
                time_windows=sorted(agg['time_windows']),
                durations=sorted(agg['durations']),
                weight=self._clamp(1.0 + 0.25 * (support_count - 1), 1.0, 3.0),
                importance_score=self._clamp(1.0 + 0.35 * (recommended_support - 1), 1.0, 3.0)
            )

    def _add_temporal_edges(self, graph: nx.DiGraph, fused_data: Dict) -> None:
        """添加时段关系边"""
        time_periods = fused_data.get('time_periods', {})

        for period, pois in time_periods.items():
            period_id = self._generate_node_id('period', period)
            if period_id not in graph.nodes():
                continue

            for poi in pois:
                poi_id = self._generate_node_id('poi', poi)
                if poi_id not in graph.nodes():
                    continue
                graph.add_edge(
                    period_id,
                    poi_id,
                    edge_type=EdgeType.TEMPORAL.value,
                    support_count=1,
                    weight=0.4
                )

    def _add_conditional_edges(self, graph: nx.DiGraph, fused_data: Dict) -> None:
        """添加条件关系边（聚合同一条件到同一POI的多条建议）。"""
        poi_advice_map = fused_data.get('poi_advice_map_cleaned', {})
        edge_aggregation = {}
        condition_advice_table = []

        for poi, advices in poi_advice_map.items():
            poi_id = self._generate_node_id('poi', poi)
            if poi_id not in graph.nodes():
                continue

            for advice in advices:
                condition = advice.get('condition', {})
                cond_type = condition.get('type', 'other')
                cond_text = condition.get('text', '')
                if not cond_text:
                    continue

                cond_key = f"{cond_type}_{cond_text}"
                cond_id = self._generate_node_id('condition', cond_key)
                if cond_id not in graph.nodes():
                    continue

                edge_key = (cond_id, poi_id)
                if edge_key not in edge_aggregation:
                    edge_aggregation[edge_key] = {
                        'advice_samples': [],
                        'support_count': 0
                    }

                advice_text = advice.get('advice_text', '')
                if advice_text and advice_text not in edge_aggregation[edge_key]['advice_samples']:
                    if len(edge_aggregation[edge_key]['advice_samples']) < 3:
                        edge_aggregation[edge_key]['advice_samples'].append(advice_text)

                edge_aggregation[edge_key]['support_count'] += 1

                condition_advice_table.append({
                    'condition': condition.get('text', ''),
                    'condition_type': cond_type,
                    'condition_subtype': condition.get('subtype', cond_type),
                    'poi': poi,
                    'advice': advice_text,
                    'advice_id': advice.get('advice_id', '')
                })

        for (cond_id, poi_id), agg in edge_aggregation.items():
            graph.add_edge(
                cond_id,
                poi_id,
                edge_type=EdgeType.CONDITIONAL.value,
                advice=agg['advice_samples'][0] if agg['advice_samples'] else '',
                advice_samples=agg['advice_samples'],
                support_count=agg['support_count'],
                weight=self._clamp(0.8 + 0.2 * (agg['support_count'] - 1), 0.8, 2.0)
            )

        graph.graph['condition_advice_table'] = condition_advice_table

    def _json_safe_value(self, value: Any) -> Any:
        """将属性值转换为可JSON序列化格式。"""
        if isinstance(value, set):
            return sorted(value)
        if isinstance(value, (list, tuple)):
            return [self._json_safe_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._json_safe_value(v) for k, v in value.items()}
        return value

    def export_graph(self, graph: nx.DiGraph, output_path: str) -> None:
        """
        导出图谱数据为JSON

        Args:
            graph: NetworkX图
            output_path: 输出文件路径
        """
        data = self._graph_to_json(graph)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _graph_to_json(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """将NetworkX图转换为JSON格式"""
        nodes = []
        for node_id, node_data in graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'type': node_data.get('node_type', 'unknown'),
                'label': node_data.get('label', ''),
                'properties': {
                    k: self._json_safe_value(v) for k, v in node_data.items()
                    if k not in ['node_type', 'label']
                }
            })

        edges = []
        for source, target, edge_data in graph.edges(data=True):
            edges.append({
                'source': source,
                'target': target,
                'type': edge_data.get('edge_type', 'unknown'),
                'properties': {
                    k: self._json_safe_value(v) for k, v in edge_data.items()
                    if k != 'edge_type'
                }
            })

        return {
            'metadata': {
                'scenic_spot': graph.graph.get('scenic_spot', ''),
                'generated_at': graph.graph.get('generated_at', ''),
                'graph_stats': {
                    'total_nodes': graph.number_of_nodes(),
                    'total_edges': graph.number_of_edges()
                },
                'condition_cleaning_report': self._json_safe_value(graph.graph.get('condition_cleaning_report', {}))
            },
            'nodes': nodes,
            'edges': edges
        }

    def get_graph_statistics(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """
        获取图谱统计信息

        Args:
            graph: NetworkX图

        Returns:
            统计信息字典
        """
        stats = {
            'total_nodes': graph.number_of_nodes(),
            'total_edges': graph.number_of_edges(),
            'node_types': {},
            'edge_types': {},
            'condition_subtypes': {}
        }

        for _, node_data in graph.nodes(data=True):
            node_type = node_data.get('node_type', 'unknown')
            stats['node_types'][node_type] = stats['node_types'].get(node_type, 0) + 1
            if node_type == NodeType.CONDITION.value:
                subtype = node_data.get('condition_subtype', 'unknown')
                stats['condition_subtypes'][subtype] = stats['condition_subtypes'].get(subtype, 0) + 1

        for _, _, edge_data in graph.edges(data=True):
            edge_type = edge_data.get('edge_type', 'unknown')
            stats['edge_types'][edge_type] = stats['edge_types'].get(edge_type, 0) + 1

        return stats


# =============================================================================
# 便捷函数
# =============================================================================

def build_knowledge_graph(fused_data: Dict[str, Any]) -> nx.DiGraph:
    """
    便捷函数：构建知识图谱

    Args:
        fused_data: 融合后的知识数据

    Returns:
        NetworkX有向图
    """
    builder = KnowledgeGraphBuilder()
    return builder.build_graph(fused_data)


if __name__ == '__main__':
    from data_loader import MultiSourceDataLoader
    from knowledge_fusion import KnowledgeFusionEngine

    loader = MultiSourceDataLoader()
    spot_data = loader.load_scenic_spot('九寨沟')

    if 'error' not in spot_data:
        engine = KnowledgeFusionEngine('九寨沟')
        fused = engine.build_composite_knowledge(spot_data)

        builder = KnowledgeGraphBuilder()
        graph = builder.build_graph(fused)

        print("图谱统计:")
        stats = builder.get_graph_statistics(graph)
        for key, value in stats.items():
            print(f"  {key}: {value}")
