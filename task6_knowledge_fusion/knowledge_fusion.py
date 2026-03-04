#!/usr/bin/env python3
"""
任务6：多源程序性知识的融合与可视化 - 知识融合核心模块

功能：
1. POI名称标准化与对齐
2. 官方路线与游客POI融合
3. 条件建议与景点关联
4. 计算POI权重
"""

import re
from typing import Dict, List, Set, Any, Tuple
from collections import Counter, defaultdict
from enum import Enum


class POISource(Enum):
    """POI来源类型"""
    OFFICIAL = "official"      # 官方路线
    VISITOR = "visitor"        # 游客游记
    FUSED = "fused"           # 融合（两者都有）


class POINormalizer:
    """POI名称标准化器"""

    # 基于task3的POI标准化映射
    POI_NORMALIZATION_MAP = {
        "九寨沟": {
            "沟口": "沟口乘车",
            "高峰": None,  # 过滤噪声
            "专门": None,
            "上山": None,
        },
        "故宫": {
            "西六宫": "西六宫区",
            "东六宫": "东六宫区",
            "小区": None,
            "六宫": None,
            "清宫": None,
            "宫殿": None,
            "后宫": None,
            "故宫": None,
            "天安门": None,
            "南门": None,
            "北门": None,
            "东门": None,
        },
        "黄山": {
            "慈光阁": "慈光阁景观区",
            "玉屏景区": "玉屏楼景观区",
            "玉屏楼": "玉屏楼景观区",
            "天海景区": "天海景观区",
            "云谷景区": "云谷寺景观区",
            "云谷寺": "云谷寺景观区",
            "北海景区": "狮子峰景观区",
            "松谷景区": "松谷庵景观区",
            "始信峰": "始信峰景观区",
            "狮子峰": "狮子峰景观区",
            "排云亭": "排云亭景观区",
            "上山": None,
            "下山": None,
            "山峰": None,
            "名山": None,
            "观海": None,
            "黄山": None,
        }
    }

    def __init__(self, scenic_spot: str = None):
        """
        初始化标准化器

        Args:
            scenic_spot: 景区名称
        """
        self.scenic_spot = scenic_spot
        self.normalization_map = self.POI_NORMALIZATION_MAP.get(scenic_spot, {})

    def normalize(self, poi_name: str) -> Tuple[str, bool]:
        """
        标准化POI名称

        Args:
            poi_name: 原始POI名称

        Returns:
            (标准化后的名称, 是否应该保留)
        """
        if not poi_name or len(poi_name.strip()) < 2:
            return poi_name, False

        poi_name = poi_name.strip()

        # 检查是否在映射表中
        if poi_name in self.normalization_map:
            normalized = self.normalization_map[poi_name]
            if normalized is None:
                return poi_name, False  # 过滤
            return normalized, True

        return poi_name, True

    def normalize_list(self, poi_list: List[str]) -> List[str]:
        """
        批量标准化POI列表

        Args:
            poi_list: POI名称列表

        Returns:
            标准化后的POI列表（去重且过滤）
        """
        normalized_list = []
        seen = set()
        for poi in poi_list:
            normalized, keep = self.normalize(poi)
            if keep and normalized and normalized not in seen:
                seen.add(normalized)
                normalized_list.append(normalized)
        return normalized_list


class RouteNormalizer:
    """将不同结构的官方路线统一为可建图格式。"""

    def __init__(self, poi_normalizer: POINormalizer):
        self.poi_normalizer = poi_normalizer

    def _normalize_poi(self, poi_name: str) -> str:
        """标准化 POI，返回空字符串表示应过滤。"""
        normalized, keep = self.poi_normalizer.normalize(poi_name)
        if not keep or not normalized:
            return ""
        return normalized

    def _extract_structured_time_periods(self, official_routes: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取九寨沟这类按时段组织的路线信息。"""
        time_periods = defaultdict(list)

        hierarchy = official_routes.get('hierarchy', {})
        hierarchy_data = hierarchy.get('hierarchy', {}) if isinstance(hierarchy, dict) else {}

        for period, period_data in hierarchy_data.items():
            if not isinstance(period_data, dict) or 'activities' not in period_data:
                continue
            activities = period_data.get('activities', [])
            for activity in activities:
                poi = self._normalize_poi(activity.get('poi', ''))
                if poi and poi not in time_periods[period]:
                    time_periods[period].append(poi)

        return dict(time_periods)

    def _normalize_structured_time_route(self, parsed_routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_routes = []
        for idx, route in enumerate(parsed_routes):
            from_poi = self._normalize_poi(route.get('from_poi', ''))
            to_poi = self._normalize_poi(route.get('to_poi', ''))
            if not from_poi or not to_poi:
                continue
            normalized_routes.append({
                'from_poi': from_poi,
                'to_poi': to_poi,
                'route_id': 'main',
                'sequence_index': idx + 1,
                'period': route.get('period', ''),
                'transport': route.get('transport', ''),
                'time_start': route.get('time_start', ''),
                'time_end': route.get('time_end', ''),
                'duration': route.get('duration', ''),
                'source_format': 'structured_time_route'
            })
        return normalized_routes

    def _normalize_numbered_list(self, parsed_routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_routes = []
        ordered = sorted(
            [r for r in parsed_routes if isinstance(r, dict) and r.get('poi')],
            key=lambda x: x.get('sequence', 0)
        )
        for idx in range(len(ordered) - 1):
            from_poi = self._normalize_poi(ordered[idx].get('poi', ''))
            to_poi = self._normalize_poi(ordered[idx + 1].get('poi', ''))
            if not from_poi or not to_poi:
                continue
            normalized_routes.append({
                'from_poi': from_poi,
                'to_poi': to_poi,
                'route_id': 'main',
                'sequence_index': idx + 1,
                'period': '',
                'transport': '',
                'time_start': '',
                'time_end': '',
                'duration': '',
                'source_format': 'numbered_list'
            })
        return normalized_routes

    def _normalize_multi_route(self, parsed_routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_routes = []

        for route in parsed_routes:
            if not isinstance(route, dict):
                continue
            route_id = route.get('route_id', route.get('route_name', 'route'))
            nodes = route.get('nodes', [])
            if not isinstance(nodes, list) or len(nodes) < 2:
                continue

            for idx in range(len(nodes) - 1):
                from_poi = self._normalize_poi(nodes[idx])
                to_poi = self._normalize_poi(nodes[idx + 1])
                if not from_poi or not to_poi:
                    continue
                normalized_routes.append({
                    'from_poi': from_poi,
                    'to_poi': to_poi,
                    'route_id': route_id,
                    'sequence_index': idx + 1,
                    'period': '',
                    'transport': route.get('cableway', ''),
                    'time_start': '',
                    'time_end': '',
                    'duration': '',
                    'entrance': route.get('entrance', ''),
                    'source_format': 'multi_route_selection'
                })

        return normalized_routes

    def normalize_routes(self, official_routes: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一路线结构。

        Returns:
            {
                'normalized_routes': [...],
                'time_periods': {...},
                'official_pois': [...],
                'route_format': str,
                'report': {...}
            }
        """
        parsed = official_routes.get('parsed', {})
        route_format = parsed.get('route_format', 'unknown')
        parsed_routes = parsed.get('routes', []) if isinstance(parsed.get('routes', []), list) else []
        parsed_pois = parsed.get('pois', []) if isinstance(parsed.get('pois', []), list) else []

        if route_format == 'structured_time_route':
            normalized_routes = self._normalize_structured_time_route(parsed_routes)
            time_periods = self._extract_structured_time_periods(official_routes)
        elif route_format == 'numbered_list':
            normalized_routes = self._normalize_numbered_list(parsed_routes)
            time_periods = {}
        elif route_format == 'multi_route_selection':
            normalized_routes = self._normalize_multi_route(parsed_routes)
            time_periods = {}
        else:
            normalized_routes = self._normalize_structured_time_route(parsed_routes)
            time_periods = {}

        poi_set = set()
        for poi in parsed_pois:
            normalized = self._normalize_poi(poi)
            if normalized:
                poi_set.add(normalized)
        for route in normalized_routes:
            poi_set.add(route['from_poi'])
            poi_set.add(route['to_poi'])
        for _, period_pois in time_periods.items():
            for poi in period_pois:
                poi_set.add(poi)

        return {
            'normalized_routes': normalized_routes,
            'time_periods': time_periods,
            'official_pois': list(poi_set),
            'route_format': route_format,
            'report': {
                'route_format': route_format,
                'parsed_route_count': len(parsed_routes),
                'normalized_route_count': len(normalized_routes),
                'official_poi_count': len(poi_set),
                'time_period_count': len(time_periods)
            }
        }


class KnowledgeFusionEngine:
    """知识融合引擎"""

    # 融合配置
    POI_THRESHOLD = 2  # 游客POI文档频次阈值（5篇游记中出现>=2）
    OFFICIAL_WEIGHT = 0.7  # 官方路线权重
    VISITOR_WEIGHT = 0.3   # 游客POI权重
    MAX_VISITOR_SUPPLEMENTS = 8  # 每个景区最多补充的游客景点数
    MIN_VISITOR_SCORE = 0.55  # 游客补充景点评分阈值

    POI_SUFFIXES = (
        '海', '池', '宫', '殿', '门', '峰', '阁', '寺', '沟', '山', '区',
        '湖', '瀑', '滩', '寨', '景区', '中心站', '索道', '馆', '台', '亭'
    )
    VISITOR_GENERIC_WORDS = {
        '景区', '路线', '攻略', '上山', '下山', '名山', '山峰', '观海', '进沟',
        '九寨', '九寨沟', '故宫', '黄山', '天安门', '宫殿', '后宫', '大殿', '秀山'
    }

    def __init__(self, scenic_spot: str = None):
        """
        初始化融合引擎

        Args:
            scenic_spot: 景区名称
        """
        self.scenic_spot = scenic_spot
        self.normalizer = POINormalizer(scenic_spot)

    def extract_official_pois(self, official_routes: Dict) -> Dict[str, Any]:
        """
        从官方路线中提取POI信息

        Args:
            official_routes: 官方路线数据（hierarchy.json内容）

        Returns:
            {
                'pois': [...],           # POI列表
                'routes': [...],         # 路线信息
                'time_periods': {...}    # 时段分组
            }
        """
        parsed = official_routes.get('parsed', {})
        route_normalizer = RouteNormalizer(self.normalizer)
        normalized = route_normalizer.normalize_routes(official_routes)

        return {
            'pois': normalized['official_pois'],
            'routes': parsed.get('routes', []),
            'normalized_routes': normalized['normalized_routes'],
            'time_periods': normalized['time_periods'],
            'route_format': normalized['route_format'],
            'route_normalization_report': normalized['report']
        }

    def normalize_visitor_pois(
        self,
        visitor_pois: List[str],
        visitor_poi_freq_raw: Dict[str, int] = None
    ) -> Dict[str, int]:
        """
        标准化游客POI并统计频率

        Args:
            visitor_pois: 游客提到的POI列表

        Returns:
            {标准化POI: 频率}
        """
        poi_counter = Counter()

        for poi in visitor_pois:
            raw_freq = 1
            if visitor_poi_freq_raw and poi in visitor_poi_freq_raw:
                raw_freq = max(1, int(visitor_poi_freq_raw.get(poi, 1)))

            normalized, keep = self.normalizer.normalize(poi)
            if keep and normalized:
                poi_counter[normalized] += raw_freq

        return dict(poi_counter)

    def _is_valid_visitor_candidate(self, poi: str) -> bool:
        """过滤泛词/噪声，保留更像景点的候选。"""
        if not poi:
            return False
        if poi in self.VISITOR_GENERIC_WORDS:
            return False
        if re.match(r'^[前后东南西北中]山$', poi):
            return False
        if re.match(r'^[前后东南西北中]门$', poi):
            return False
        if len(poi) < 2 or len(poi) > 12:
            return False
        if re.fullmatch(r'[A-Za-z0-9\\-\\s]+', poi):
            return False
        return any(poi.endswith(suffix) for suffix in self.POI_SUFFIXES) or '景区' in poi

    def _score_visitor_candidate(self, poi: str, freq: int) -> float:
        """给游客候选景点打分，兼顾频次与形态信息。"""
        freq_score = min(freq / 5.0, 1.0)
        shape_score = 1.0 if any(poi.endswith(suffix) for suffix in self.POI_SUFFIXES) else 0.0
        length_score = 1.0 if 2 <= len(poi) <= 8 else 0.6
        score = 0.65 * freq_score + 0.25 * shape_score + 0.10 * length_score
        return round(score, 3)

    def fuse_official_visitor_routes(
        self,
        official_pois: List[str],
        visitor_poi_freq: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        融合官方路线与游客POI

        策略：
        1. 官方路线作为骨架
        2. 游客高频POI作为补充
        3. 计算融合权重

        Args:
            official_pois: 官方POI列表
            visitor_poi_freq: 游客POI频率字典

        Returns:
            {
                'fused_pois': [...],        # 融合后的POI列表
                'poi_weights': {...},       # POI权重
                'visitor_supplemented': [...]  # 游客补充的POI
            }
        """
        # 标准化官方POI
        official_normalized = self.normalizer.normalize_list(official_pois)

        # 构建结果
        fused_pois = []
        poi_weights = {}
        visitor_supplemented = []
        visitor_supplemented_details = []

        # 1. 添加官方POI
        for poi in official_normalized:
            weight = self.OFFICIAL_WEIGHT
            # 如果游客也提到，增加权重
            if poi in visitor_poi_freq:
                weight += self.VISITOR_WEIGHT * min(visitor_poi_freq[poi] / 5, 1.0)
            poi_weights[poi] = weight
            fused_pois.append(poi)

        # 2. 添加游客高频POI（官方没有的）并进行质量过滤
        candidates = []
        for poi, freq in visitor_poi_freq.items():
            if poi in official_normalized:
                continue
            if freq < self.POI_THRESHOLD:
                continue
            if not self._is_valid_visitor_candidate(poi):
                continue

            score = self._score_visitor_candidate(poi, freq)
            if score < self.MIN_VISITOR_SCORE:
                continue

            candidates.append({
                'poi': poi,
                'freq': freq,
                'score': score
            })

        candidates.sort(key=lambda x: (-x['freq'], -x['score'], x['poi']))
        selected_candidates = candidates[:self.MAX_VISITOR_SUPPLEMENTS]

        for item in selected_candidates:
            poi = item['poi']
            freq = item['freq']
            score = item['score']
            weight = max(0.45, self.VISITOR_WEIGHT * min(freq / 3.0, 1.5))
            poi_weights[poi] = round(weight, 3)
            fused_pois.append(poi)
            visitor_supplemented.append(poi)
            visitor_supplemented_details.append({
                'poi': poi,
                'doc_frequency': freq,
                'score': score,
                'source': POISource.VISITOR.value
            })

        return {
            'fused_pois': fused_pois,
            'poi_weights': poi_weights,
            'visitor_supplemented': visitor_supplemented,
            'visitor_supplemented_details': visitor_supplemented_details,
            'official_poi_count': len(official_normalized),
            'visitor_poi_count': len(visitor_poi_freq),
            'fused_poi_count': len(fused_pois)
        }

    def select_recommended_route(
        self,
        normalized_routes: List[Dict[str, Any]],
        visitor_poi_freq: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        选择推荐路线：
        - 单路线场景直接选 main
        - 多路线场景按“游客覆盖度 + 路线完整度”评分选最优
        """
        if not normalized_routes:
            return {'route_id': '', 'reason': 'no_route'}

        route_nodes = defaultdict(set)
        route_steps = defaultdict(int)

        for edge in normalized_routes:
            route_id = edge.get('route_id') or 'main'
            from_poi = edge.get('from_poi')
            to_poi = edge.get('to_poi')
            if from_poi:
                route_nodes[route_id].add(from_poi)
            if to_poi:
                route_nodes[route_id].add(to_poi)
            route_steps[route_id] += 1

        route_ids = sorted(route_nodes.keys())
        if len(route_ids) == 1:
            rid = route_ids[0]
            return {
                'route_id': rid,
                'reason': 'single_route',
                'score': 1.0,
                'route_scores': {rid: 1.0}
            }

        route_scores = {}
        for rid in route_ids:
            node_score = sum(visitor_poi_freq.get(node, 0) for node in route_nodes[rid])
            step_score = route_steps[rid]
            score = node_score * 0.75 + step_score * 0.25
            route_scores[rid] = round(score, 3)

        recommended_route_id = max(
            route_scores.items(),
            key=lambda x: (x[1], route_steps[x[0]], x[0])
        )[0]

        return {
            'route_id': recommended_route_id,
            'reason': 'visitor_coverage_score',
            'score': route_scores.get(recommended_route_id, 0.0),
            'route_scores': route_scores
        }

    def extract_poi_from_text(self, text: str, poi_set: Set[str]) -> List[str]:
        """
        从文本中提取POI关键词

        Args:
            text: 输入文本
            poi_set: POI集合

        Returns:
            匹配到的POI列表
        """
        matched = []
        if not text:
            return matched

        for poi in poi_set:
            if poi in text:
                matched.append(poi)

        return matched

    def link_advice_to_poi(
        self,
        advice_list: List[Dict],
        poi_set: Set[str]
    ) -> Dict[str, List[Dict]]:
        """
        将条件建议关联到相关POI

        Args:
            advice_list: 条件建议列表
            poi_set: 标准化后的POI集合

        Returns:
            {POI名称: [相关建议列表]}
        """
        poi_advice_map = {poi: [] for poi in poi_set}
        unmatched_advices = []

        for advice in advice_list:
            advice_text = advice.get('advice', {}).get('text', '')
            condition_text = advice.get('condition', {}).get('text', '')

            # 从建议文本和条件文本中提取POI
            combined_text = advice_text + ' ' + condition_text
            matched_pois = self.extract_poi_from_text(combined_text, poi_set)

            if matched_pois:
                for poi in matched_pois:
                    poi_advice_map[poi].append({
                        'advice_id': advice.get('advice_id'),
                        'condition': advice.get('condition'),
                        'advice_text': advice_text,
                        'pattern_type': advice.get('pattern_type')
                    })
            else:
                unmatched_advices.append({
                    'advice_id': advice.get('advice_id'),
                    'text': advice_text[:100]  # 截取前100字符
                })

        return {
            'poi_advice_map': poi_advice_map,
            'unmatched_advices': unmatched_advices,
            'matched_count': sum(len(v) for v in poi_advice_map.values()),
            'unmatched_count': len(unmatched_advices)
        }

    def build_composite_knowledge(
        self,
        spot_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建综合知识结构

        Args:
            spot_data: load_scenic_spot返回的数据

        Returns:
            融合后的综合知识
        """
        scenic_spot = spot_data.get('scenic_spot', '')
        self.scenic_spot = scenic_spot
        self.normalizer = POINormalizer(scenic_spot)

        # 1. 提取官方路线信息
        official_routes = spot_data.get('official_routes', {})
        official_data = self.extract_official_pois(official_routes)

        # 2. 标准化游客POI
        visitor_pois = spot_data.get('visitor_pois', [])
        visitor_poi_freq = self.normalize_visitor_pois(
            visitor_pois,
            spot_data.get('visitor_poi_freq', {})
        )

        # 3. 融合POI
        fusion_result = self.fuse_official_visitor_routes(
            official_data['pois'],
            visitor_poi_freq
        )

        recommended_route = self.select_recommended_route(
            official_data.get('normalized_routes', []),
            visitor_poi_freq
        )

        # 4. 关联建议到POI
        spot_advice = spot_data.get('spot_advice', [])
        poi_set = set(fusion_result['fused_pois'])
        advice_link_result = self.link_advice_to_poi(spot_advice, poi_set)

        # 5. 构建综合知识
        composite = {
            'scenic_spot': scenic_spot,
            'official_pois': official_data['pois'],
            'official_routes': official_data['routes'],
            'normalized_routes': official_data.get('normalized_routes', []),
            'route_format': official_data.get('route_format', ''),
            'route_normalization_report': official_data.get('route_normalization_report', {}),
            'recommended_route': recommended_route,
            'time_periods': official_data['time_periods'],
            'visitor_poi_freq': visitor_poi_freq,
            'fused_pois': fusion_result['fused_pois'],
            'poi_weights': fusion_result['poi_weights'],
            'visitor_supplemented': fusion_result['visitor_supplemented'],
            'visitor_supplemented_details': fusion_result.get('visitor_supplemented_details', []),
            'poi_advice_map': advice_link_result['poi_advice_map'],
            'unmatched_advices': advice_link_result['unmatched_advices'],
            'condition_cleaning_report': {
                'input_advice_count': advice_link_result['matched_count'],
                'output_advice_count': advice_link_result['matched_count'],
                'dropped_count': 0,
                'dropped_reasons': {}
            },
            'statistics': {
                'official_poi_count': fusion_result['official_poi_count'],
                'visitor_poi_count': fusion_result['visitor_poi_count'],
                'fused_poi_count': fusion_result['fused_poi_count'],
                'visitor_supplemented_count': len(fusion_result['visitor_supplemented']),
                'advice_matched_count': advice_link_result['matched_count'],
                'advice_unmatched_count': advice_link_result['unmatched_count']
            },
            'metadata': spot_data.get('metadata', {})
        }

        return composite


# =============================================================================
# 便捷函数
# =============================================================================

def fuse_spot_data(spot_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷函数：融合单个景区数据

    Args:
        spot_data: load_scenic_spot返回的数据

    Returns:
        融合后的综合知识
    """
    scenic_spot = spot_data.get('scenic_spot', '')
    engine = KnowledgeFusionEngine(scenic_spot)
    return engine.build_composite_knowledge(spot_data)


if __name__ == '__main__':
    # 测试代码
    from data_loader import MultiSourceDataLoader

    loader = MultiSourceDataLoader()
    spot_data = loader.load_scenic_spot('九寨沟')

    if 'error' not in spot_data:
        engine = KnowledgeFusionEngine('九寨沟')
        composite = engine.build_composite_knowledge(spot_data)

        print("融合结果:")
        print(f"  官方POI数: {composite['statistics']['official_poi_count']}")
        print(f"  游客POI数: {composite['statistics']['visitor_poi_count']}")
        print(f"  融合POI数: {composite['statistics']['fused_poi_count']}")
        print(f"  游客补充: {composite['statistics']['visitor_supplemented_count']}")
        print(f"  建议匹配: {composite['statistics']['advice_matched_count']}")
        print(f"  建议未匹配: {composite['statistics']['advice_unmatched_count']}")
        print(f"\n融合POI列表: {composite['fused_pois']}")
