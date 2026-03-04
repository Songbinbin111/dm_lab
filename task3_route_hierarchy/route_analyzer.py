#!/usr/bin/env python3
"""
路线对比分析器 - 比较官方推荐路线和游客实际路线的结构差异
"""

import json
import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, Any, Set, Tuple, Optional

import pandas as pd


PERIOD_ORDER = ["清晨", "上午", "中午", "下午", "傍晚", "晚上"]

TIME_PERIOD_NORMALIZATION = {
    "早上": "上午",
    "凌晨": "清晨",
    "白天": "下午",
}

DAY_LABELS = {"第一天", "第二天", "第三天", "第四天", "第五天"}


# 景点规范化映射：将游客的景点名称统一为官方标准名称
POI_NORMALIZATION_MAP = {
    "九寨沟": {
        "九寨": None,
        "九寨沟": None,
        "树正沟": None,
        "日则沟": None,
        "则查洼沟": None,
        "树正群海": None,
        "沟口": "沟口乘车",
        "高峰": None,
        "树正寨": "树正寨",  # 游客提到的真实景点，保留
        "树正瀑布": "树正瀑布",  # 游客提到的真实景点，保留
    },
    "故宫": {
        "东六宫": "东六宫区",
        "西六宫": "西六宫区",
        "三宫": None,
        "六宫": None,
        "钟表馆": None,  # 位于奉先殿，但是独立展厅，不应直接对齐
        "珍宝馆": None,  # 位于宁寿宫区，但是独立展厅，不应直接对齐
        "戏曲馆": None,  # 位于宁寿宫区，但是独立展厅，不应直接对齐
        "书画馆": None,  # 位于文华殿，但是独立展厅，不应直接对齐
        "乾清门": None,  # 独立门楼，不在官方路线中
        "中山公园": None,
        "天安门": None,
        "天安门广场": None,
        "北海": None,
        "北海公园": None,
        "景山": None,
        "景山公园": None,
        "凡尔赛宫": None,
        "东城区": None,
        "太湖区": None,
        "宫之主": None,
        "宫猫": None,
        "宫闱": None,
        "寒门": None,
        "小区": None,
        "水晶宫": None,
        "江山": None,
        "池春水": None,
        "海纳百川": None,
        "清宫": None,
        "皇宫": None,
        "秀山": None,
        "金銮殿": None,  # 太和殿的俗称，但不应重复计数
        "山西省": None,
        "延禧宫": None,
        "弘义阁": None,
        "承乾宫": None,
        "掖门": None,
        "故宫博物院": None,
        "景仁宫": None,
        "寿康宫": None,
        "故宫": None,
        "后宫": None,
        "中宫": None,
        "宫殿": None,
        "宫墙": None,
        "宫廷": None,
        "门匾": None,
        "东暖阁": None,
        "东华门": None,
        "太湖石": None,
        "寝宫": None,
        "山楂": None,
        "瓷宫": None,
        "畅音阁": None,
    },
    "黄山": {
        "云谷寺": "云谷寺景观区",
        "云谷景区": "云谷寺景观区",
        "始信峰": "始信峰景观区",
        "狮子峰": "狮子峰景观区",
        "排云亭": "排云亭景观区",
        "天海": "天海景观区",
        "天海景区": "天海景观区",
        "玉屏楼": "玉屏楼景观区",
        "玉屏景区": "玉屏楼景观区",
        "慈光阁": "慈光阁景观区",
        "松谷庵": "松谷庵景观区",
        "松谷景区": "松谷庵景观区",
        "北海": "北海中路",
        "北海景区": "北海中路",
        "西海": None,
        "西海景区": None,
        "南大门": "黄山南大门",
        "北大门": "黄山北大门",
        "玉屏": "玉屏楼景观区",
        "散花坞": None,  # 狮子峰景观区内，但不对齐到整个区域
        "清凉台": None,  # 狮子峰景观区内，但不对齐到整个区域
        "云谷索道": None,
        "玉屏索道": None,
        "太平索道": None,
        "前山": None,
        "后山": None,
        "云海": None,
        "仙山": None,
        "名山": None,
        "山峰": None,
        "峰顶": None,
        "山顶": None,
        "半山": None,
        "风景区": None,
        "服务区": None,
        "山庄": None,
        "爬山": None,
        "观海": None,
        "高峰": None,
        "松树": None,
        "黄山": None,
        "黄山区": None,
        "黄山市": None,
        "屯溪区": None,
        "天都峰": None,  # 独立山峰，不在官方路线中
        "天门": None,
        "黑虎松": None,
        "迎客松": None,  # 玉屏楼景观区内著名松树，但不对齐到整个区域
        "莲花峰": None,  # 独立山峰，不在官方路线中
        "鳌鱼峰": None,  # 天海景观区内，但不对齐到整个区域
        "西海大峡谷": None,
        "温泉景区": None,
        "挑山工": None,
        "故宫": None,
        "上海": None,
        "外滩": None,
        "黟山": None,
    },
}

# 通用停用词（非景点词汇）
COMMON_STOP_WORDS = {
    "上山",
    "下山",
    "登山",
    "进沟",
    "游览",
    "参观",
    "游玩",
    "山水",
    "云海",
    "海子",
    "湖水",
    "瀑布",
    "山峰",
    "峰顶",
    "山顶",
    "景区",
    "风景区",
    "区域",
    "区分",
    "半山",
    "高处",
    "专门",
    "热门",
    "门票",
    "门票价格",
    "海拔",
    "景观",
    "景色",
    "美景",
    "风景",
    "之门",
    "大殿",
    "大门",
    "东门",
    "西门",
    "南门",
    "北门",
    "门洞",
    "门牌",
}

NOISE_PATTERNS = [
    r"^\d+$",
    r"^\d+[分钟小时天]$",
    r".*门票.*",
    r".*路线$",
]

SPOT_TO_DICT = {
    "九寨沟": "jiuzhaigou",
    "故宫": "gugong",
    "黄山": "huangshan",
}

_SCENIC_POI_LEXICON_CACHE: Dict[str, Set[str]] = {}


def _stable_unique(items: List[str]) -> List[str]:
    """保序去重"""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _load_scenic_poi_lexicon(scenic_spot: str) -> Set[str]:
    """加载景区POI词典，用于识别“真实但不在官方推荐路线中的景点”"""
    if scenic_spot in _SCENIC_POI_LEXICON_CACHE:
        return _SCENIC_POI_LEXICON_CACHE[scenic_spot]

    lexicon: Set[str] = set()
    spot_en = SPOT_TO_DICT.get(scenic_spot)
    if not spot_en:
        _SCENIC_POI_LEXICON_CACHE[scenic_spot] = lexicon
        return lexicon

    dict_path = os.path.join("custom_dicts", "poi", f"{spot_en}.txt")
    if os.path.exists(dict_path):
        with open(dict_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    lexicon.add(parts[0])

    _SCENIC_POI_LEXICON_CACHE[scenic_spot] = lexicon
    return lexicon


def _clean_poi_text(raw_poi: str) -> str:
    """清理POI文本中的前后缀和格式噪声"""
    poi = raw_poi.strip()

    # 清理开头的项目符号/序号
    poi = re.sub(r"^[-•\s]+", "", poi)
    poi = re.sub(r"^\d+[.)、]\s*", "", poi)

    # 从“xxx:景点”中提取真正景点名
    match = re.search(r"[:：]\s*([\u4e00-\u9fa5A-Za-z0-9（）()]{2,24})$", poi)
    if match:
        poi = match.group(1).strip()

    # 去除末尾标点
    poi = poi.strip("，。；、,.!?！？")
    return poi


def _poi_key(poi: str) -> str:
    """生成用于匹配的POI键"""
    cleaned = re.sub(r"[（(][^）)]*[）)]", "", poi)
    cleaned = re.sub(r"(景观区|风景区|景区|旅游区|乘车|索道|缆车|路线)", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def _is_noise_poi(poi: str) -> bool:
    """判断是否为噪声词"""
    if poi in COMMON_STOP_WORDS:
        return True
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, poi):
            return True
    return False


def _align_to_official(
    poi: str,
    official_pois: Set[str],
    official_by_key: Dict[str, List[str]],
) -> Optional[str]:
    """将POI尽量对齐到官方标准景点"""
    if poi in official_pois:
        return poi

    plain = re.sub(r"[（(][^）)]*[）)]", "", poi).strip()
    if plain in official_pois:
        return plain

    # 通过核心词键匹配
    poi_key = _poi_key(poi)
    if poi_key and poi_key in official_by_key and len(official_by_key[poi_key]) == 1:
        return official_by_key[poi_key][0]

    # 包含关系匹配（例如 文华殿(书画馆) -> 文华殿）
    contains = [off for off in official_pois if off in poi or poi in off]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1:
        return max(contains, key=len)

    # 最后使用低风险模糊匹配
    if not poi_key:
        return None
    scored = []
    for off in official_pois:
        off_key = _poi_key(off)
        if not off_key:
            continue
        ratio = SequenceMatcher(None, poi_key, off_key).ratio()
        scored.append((ratio, off))
    if not scored:
        return None

    scored.sort(reverse=True)
    best_ratio, best_official = scored[0]
    second_ratio = scored[1][0] if len(scored) > 1 else 0
    if best_ratio >= 0.72 and (best_ratio - second_ratio) >= 0.08:
        return best_official
    return None


def normalize_visitor_poi(
    scenic_spot: str,
    visitor_poi: List[str],
    official_pois: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """规范化游客POI并尝试映射到官方景点"""
    official_pois = official_pois or set()
    official_by_key: Dict[str, List[str]] = {}
    for official in official_pois:
        key = _poi_key(official)
        if key:
            official_by_key.setdefault(key, []).append(official)

    normalization_map = POI_NORMALIZATION_MAP.get(scenic_spot, {})

    cleaned_sequence: List[str] = []
    strict_sequence: List[str] = []
    aligned_sequence: List[str] = []
    unmatched_sequence: List[str] = []
    dropped: List[str] = []

    for raw in visitor_poi:
        if not raw or not str(raw).strip():
            continue

        poi = _clean_poi_text(str(raw))
        if not poi:
            continue

        # 优先处理括号前主名
        plain = re.sub(r"[（(][^）)]*[）)]", "", poi).strip()
        if plain:
            poi = plain

        # 路线描述过滤
        if poi.startswith("-") or poi.endswith("路线"):
            dropped.append(poi)
            continue

        strict_poi = poi

        # 映射为None的词直接过滤（泛化词/噪声词）
        if strict_poi in normalization_map:
            mapped = normalization_map[strict_poi]
            if mapped is None:
                dropped.append(strict_poi)
                continue

        if _is_noise_poi(strict_poi):
            dropped.append(strict_poi)
            continue

        strict_sequence.append(strict_poi)

        # 景区特定映射（仅用于标准化计数口径）
        poi = strict_poi
        if poi in normalization_map and normalization_map[poi] is not None:
            poi = normalization_map[poi]

        cleaned_sequence.append(poi)

        if official_pois:
            aligned = _align_to_official(poi, official_pois, official_by_key)
            if aligned:
                aligned_sequence.append(aligned)
            else:
                unmatched_sequence.append(poi)
        else:
            aligned_sequence.append(poi)

    cleaned_unique = sorted(set(cleaned_sequence))
    aligned_unique = _stable_unique(aligned_sequence)
    unmatched_unique = sorted(set(unmatched_sequence))
    scenic_lexicon = _load_scenic_poi_lexicon(scenic_spot)

    # 未对齐词分为两类：
    # 1) valid_extra_unique: 真实景点，但不在官方推荐路线中（应计入游客额外景点）
    # 2) unknown_unmatched_unique: 无法确认的词（保留为未对齐）
    valid_extra_unique = sorted([poi for poi in unmatched_unique if poi in scenic_lexicon])
    unknown_unmatched_unique = sorted([poi for poi in unmatched_unique if poi not in scenic_lexicon])
    valid_extra_set = set(valid_extra_unique)

    counted_sequence: List[str] = []
    for poi in cleaned_sequence:
        if official_pois:
            aligned = _align_to_official(poi, official_pois, official_by_key)
            if aligned:
                counted_sequence.append(aligned)
            elif poi in valid_extra_set:
                counted_sequence.append(poi)
        else:
            counted_sequence.append(poi)

    return {
        "cleaned_sequence": cleaned_sequence,
        "cleaned_unique": cleaned_unique,
        "strict_sequence": strict_sequence,
        "strict_unique": sorted(set(strict_sequence)),
        "aligned_sequence": aligned_sequence,
        "aligned_unique": aligned_unique,
        "counted_sequence": counted_sequence,
        "counted_unique": _stable_unique(counted_sequence),
        "unmatched_unique": unmatched_unique,
        "valid_extra_unique": valid_extra_unique,
        "unknown_unmatched_unique": unknown_unmatched_unique,
        "raw_count": len(visitor_poi),
        "cleaned_unique_count": len(cleaned_unique),
        "aligned_unique_count": len(aligned_unique),
        "dropped_count": len(dropped),
    }


def _lcs_length(seq_a: List[str], seq_b: List[str]) -> int:
    """计算最长公共子序列长度"""
    if not seq_a or not seq_b:
        return 0
    dp = [[0] * (len(seq_b) + 1) for _ in range(len(seq_a) + 1)]
    for i, item_a in enumerate(seq_a, start=1):
        for j, item_b in enumerate(seq_b, start=1):
            if item_a == item_b:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def _infer_period_from_index(index: int, total: int) -> str:
    """基于序列位置推断时段"""
    if total <= 0:
        return "未知"
    ratio = (index + 1) / total
    if ratio <= 0.3:
        return "上午"
    if ratio <= 0.6:
        return "中午"
    if ratio <= 0.9:
        return "下午"
    return "傍晚"


class RouteComparator:
    """路线对比分析器"""

    def __init__(self, scenic_spot: str, official_data: Dict, visitor_data: Dict):
        self.scenic_spot = scenic_spot
        self.official_data = official_data
        self.visitor_data = visitor_data

    def _official_poi_set(self) -> Set[str]:
        """获取官方景点集合（去重）"""
        raw = self.official_data.get("parsed", {}).get("pois", [])
        return set(_stable_unique(raw))

    def _official_sequence(self) -> Tuple[List[str], str]:
        """获取官方序列及来源说明"""
        parsed = self.official_data.get("parsed", {})
        routes = parsed.get("routes", [])

        if self.scenic_spot == "九寨沟" and routes:
            seq = []
            first_from = routes[0].get("from_poi")
            if first_from:
                seq.append(first_from)
            seq.extend([r.get("poi", "") for r in routes if r.get("poi")])
            return _stable_unique([s for s in seq if s]), "explicit_route_sequence"

        if self.scenic_spot == "故宫" and routes:
            seq = [r.get("poi", "") for r in routes if r.get("poi")]
            return _stable_unique(seq), "numbered_sequence"

        if self.scenic_spot == "黄山" and routes:
            # 多线路场景下，取节点最多的一条作为代表官方路线
            route = max(routes, key=lambda r: len(r.get("nodes", [])))
            seq = [node for node in route.get("nodes", []) if node]
            return _stable_unique(seq), "representative_longest_route"

        return [], "unavailable"

    def _normalize_visitor(self, official_pois: Set[str]) -> Dict[str, Any]:
        raw_visitor_poi = self.visitor_data.get("poi", [])
        normalized = normalize_visitor_poi(self.scenic_spot, raw_visitor_poi, official_pois)
        normalized["raw_sequence"] = raw_visitor_poi
        return normalized

    def compare_coverage(self) -> Dict[str, Any]:
        """对比景点覆盖度（以官方景点对齐为准）"""
        official_pois = self._official_poi_set()
        visitor_norm = self._normalize_visitor(official_pois)

        strict_visitor_pois = set(visitor_norm["strict_unique"])
        strict_overlap = official_pois & strict_visitor_pois
        strict_union = official_pois | strict_visitor_pois
        strict_jaccard = len(strict_overlap) / len(strict_union) if strict_union else 0

        # 计数口径：已对齐官方景点 + 真实但不在官方推荐中的景点
        visitor_pois = set(visitor_norm["aligned_unique"]) | set(visitor_norm["valid_extra_unique"])
        overlap = official_pois & visitor_pois
        official_only = official_pois - visitor_pois
        visitor_only = visitor_pois - official_pois

        union = official_pois | visitor_pois
        jaccard = len(overlap) / len(union) if union else 0

        return {
            "official_poi_count": len(official_pois),
            "visitor_poi_count": len(visitor_pois),
            "overlap_count": len(overlap),
            "overlap_pois": sorted(list(overlap)),
            "official_only_pois": sorted(list(official_only)),
            "visitor_only_pois": sorted(list(visitor_only)),
            "jaccard_similarity": round(jaccard, 3),
            "strict_overlap_count": len(strict_overlap),
            "strict_jaccard_similarity": round(strict_jaccard, 3),
            "normalization_gain": len(overlap) - len(strict_overlap),
            "normalization_delta": round(jaccard - strict_jaccard, 3),
            "raw_visitor_poi_count": visitor_norm["raw_count"],
            "cleaned_unique_count": visitor_norm["cleaned_unique_count"],
            "valid_extra_poi_count": len(visitor_norm["valid_extra_unique"]),
            "valid_extra_visitor_pois": visitor_norm["valid_extra_unique"],
            "unmatched_poi_count": len(visitor_norm["unknown_unmatched_unique"]),
            "unmatched_visitor_pois": visitor_norm["unknown_unmatched_unique"],
            "filtered_count": visitor_norm["raw_count"] - len(visitor_pois),
        }

    def compare_time_distribution(self) -> Dict[str, Any]:
        """对比时间分布（支持三景区统一口径）"""
        official_dist: Dict[str, int] = {}
        method = "unavailable"
        parsed = self.official_data.get("parsed", {})
        routes = parsed.get("routes", [])

        if self.scenic_spot == "九寨沟":
            for route in routes:
                period = route.get("period", "未知")
                period = TIME_PERIOD_NORMALIZATION.get(period, period)
                if period in PERIOD_ORDER:
                    official_dist[period] = official_dist.get(period, 0) + 1
            method = "explicit_time_from_official_route"
        else:
            official_seq, seq_method = self._official_sequence()
            for idx, _poi in enumerate(official_seq):
                period = _infer_period_from_index(idx, len(official_seq))
                official_dist[period] = official_dist.get(period, 0) + 1
            if official_seq:
                method = f"inferred_from_{seq_method}"

        visitor_dist: Dict[str, int] = {}
        day_dist: Dict[str, int] = {}
        other_dist: Dict[str, int] = {}
        time_data = self.visitor_data.get("time", {})

        for rel_time in time_data.get("relative", []):
            normalized = TIME_PERIOD_NORMALIZATION.get(rel_time, rel_time)
            if normalized in DAY_LABELS:
                day_dist[normalized] = day_dist.get(normalized, 0) + 1
            elif normalized in PERIOD_ORDER:
                visitor_dist[normalized] = visitor_dist.get(normalized, 0) + 1
            else:
                other_dist[normalized] = other_dist.get(normalized, 0) + 1

        official_total = sum(official_dist.values())
        visitor_total = sum(visitor_dist.values())
        similarity = 0.0
        if official_total > 0 and visitor_total > 0:
            official_prop = [official_dist.get(p, 0) / official_total for p in PERIOD_ORDER]
            visitor_prop = [visitor_dist.get(p, 0) / visitor_total for p in PERIOD_ORDER]
            l1 = sum(abs(a - b) for a, b in zip(official_prop, visitor_prop))
            similarity = max(0.0, 1 - l1 / 2)

        return {
            "official_distribution": official_dist,
            "visitor_distribution": visitor_dist,
            "visitor_day_distribution": day_dist,
            "visitor_other_time_labels": other_dist,
            "official_total": official_total,
            "visitor_total": visitor_total,
            "distribution_similarity": round(similarity, 3),
            "official_distribution_method": method,
        }

    def compare_route_similarity(self) -> Dict[str, Any]:
        """对比路线相似度（集合 + 顺序）"""
        official_pois = self._official_poi_set()
        official_seq, seq_source = self._official_sequence()
        visitor_norm = self._normalize_visitor(official_pois)
        visitor_seq = _stable_unique(visitor_norm["counted_sequence"])
        visitor_set = set(visitor_seq)
        official_set = set(official_seq)

        # 集合相似度（覆盖视角）
        union = official_set | visitor_set
        overlap = official_set & visitor_set
        set_similarity = len(overlap) / len(union) if union else 0.0

        # 顺序相似度（路线视角）
        lcs = _lcs_length(official_seq, visitor_seq)
        sequence_similarity = (lcs / len(official_seq)) if official_seq else 0.0

        # 组合分数：顺序优先，集合为辅
        combined = 0.6 * sequence_similarity + 0.4 * set_similarity

        raw_sequence = visitor_norm.get("raw_sequence", [])
        low_confidence = bool(raw_sequence) and raw_sequence == sorted(raw_sequence)

        return {
            "official_sequence": official_seq,
            "visitor_sequence": visitor_seq,
            "official_sequence_source": seq_source,
            "lcs_length": lcs,
            "set_similarity": round(set_similarity, 3),
            "sequence_similarity": round(sequence_similarity, 3),
            "combined_similarity": round(combined, 3),
            "sequence_confidence": "low" if low_confidence else "medium_or_high",
            "sequence_confidence_note": (
                "游客POI序列疑似已排序去重，顺序相似度仅供参考"
                if low_confidence
                else "游客POI序列保留了部分顺序信息"
            ),
        }

    def compare_transport_usage(self) -> Dict[str, Any]:
        """对比交通方式使用"""
        official_transport = {}
        if self.scenic_spot == "九寨沟":
            for route in self.official_data.get("parsed", {}).get("routes", []):
                transport = route.get("transport", "")
                if transport:
                    official_transport[transport] = official_transport.get(transport, 0) + 1

        visitor_transport = {}
        transport_data = self.visitor_data.get("transport", {})
        for key in ["basic", "specific", "time_distance"]:
            for item in transport_data.get(key, []):
                visitor_transport[item] = visitor_transport.get(item, 0) + 1

        return {
            "official_transport": official_transport,
            "visitor_transport": visitor_transport,
        }

    def generate_full_comparison(self) -> Dict[str, Any]:
        """生成完整的对比报告"""
        coverage = self.compare_coverage()
        time_dist = self.compare_time_distribution()
        route_similarity = self.compare_route_similarity()
        transport = self.compare_transport_usage()

        return {
            "scenic_spot": self.scenic_spot,
            "coverage_comparison": coverage,
            "route_similarity": route_similarity,
            "time_distribution": time_dist,
            "transport_usage": transport,
            "summary": self._generate_summary(coverage, time_dist, route_similarity),
        }

    def _generate_summary(
        self,
        coverage: Dict[str, Any],
        time_dist: Dict[str, Any],
        route_similarity: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成对比摘要"""
        summary: Dict[str, Any] = {
            "coverage_level": "",
            "route_similarity_level": "",
            "time_distribution_level": "",
            "key_findings": [],
        }

        # 覆盖度评估
        jaccard = coverage["jaccard_similarity"]
        if jaccard >= 0.7:
            summary["coverage_level"] = "高度一致"
        elif jaccard >= 0.4:
            summary["coverage_level"] = "部分一致"
        else:
            summary["coverage_level"] = "差异较大"

        # 路线相似度评估
        route_score = route_similarity["combined_similarity"]
        if route_score >= 0.7:
            summary["route_similarity_level"] = "高度一致"
        elif route_score >= 0.4:
            summary["route_similarity_level"] = "部分一致"
        else:
            summary["route_similarity_level"] = "差异较大"

        # 时间分布评估
        time_score = time_dist["distribution_similarity"]
        if time_score >= 0.7:
            summary["time_distribution_level"] = "高度一致"
        elif time_score >= 0.4:
            summary["time_distribution_level"] = "部分一致"
        else:
            summary["time_distribution_level"] = "差异较大"

        if coverage["official_only_pois"]:
            summary["key_findings"].append(
                f"游客未覆盖 {len(coverage['official_only_pois'])} 个官方推荐景点"
            )

        if coverage["unmatched_poi_count"] > 0:
            summary["key_findings"].append(
                f"检测到 {coverage['unmatched_poi_count']} 个游客POI无法对齐到官方名称"
            )

        if coverage.get("normalization_delta", 0) >= 0.25:
            summary["key_findings"].append(
                "标准化映射对覆盖度提升较大，需警惕口径过宽带来的高估风险"
            )

        if route_similarity["sequence_confidence"] == "low":
            summary["key_findings"].append("游客POI顺序信息置信度较低，顺序相似度需谨慎解释")

        if not summary["key_findings"]:
            summary["key_findings"].append("游客路线与官方路线整体一致")

        return summary


def load_visitor_data(entity_file: str) -> Dict:
    """加载游客实体数据"""
    with open(entity_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 按景区组织游客数据
    visitor_by_spot = {}
    for record in data.get('results', []):
        spot = record['scenic_spot']
        visitor_by_spot[spot] = record

    return visitor_by_spot


def load_official_hierarchy(hierarchy_file: str) -> Dict:
    """加载官方路线层级数据"""
    with open(hierarchy_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_comparison_report(scenic_spot: str,
                               official_data: Dict,
                               visitor_data: Dict) -> Dict:
    """为指定景区生成对比报告"""
    comparator = RouteComparator(scenic_spot, official_data, visitor_data)
    return comparator.generate_full_comparison()


def main():
    """主函数：生成所有景区的对比报告"""
    print("=" * 60)
    print("路线对比分析")
    print("=" * 60)

    # 创建输出目录
    import os
    if not os.path.exists('route_comparison'):
        os.makedirs('route_comparison')

    # 景区映射
    spot_en_map = {
        '九寨沟': 'jiuzhaigou',
        '故宫': 'gugong',
        '黄山': 'huangshan'
    }

    # 加载游客数据
    print("\n[1/3] 加载游客实体数据...")
    visitor_data = load_visitor_data('../task2_entity_recognition/entity_results.json')

    # 加载官方路线数据
    print("[2/3] 加载官方路线数据...")
    official_data = {}
    for spot_cn, spot_en in spot_en_map.items():
        hierarchy_file = f'route_hierarchy/{spot_cn}_hierarchy.json'
        try:
            with open(hierarchy_file, 'r', encoding='utf-8') as f:
                official_data[spot_cn] = json.load(f)
        except FileNotFoundError:
            print(f"警告: 未找到 {hierarchy_file}")

    # 生成对比报告
    print("[3/3] 生成对比报告...")
    all_reports = []

    for spot_cn in spot_en_map.keys():
        if spot_cn not in official_data or spot_cn not in visitor_data:
            continue

        print(f"\n  分析 {spot_cn}...")

        report = generate_comparison_report(
            spot_cn,
            official_data[spot_cn],
            visitor_data[spot_cn]
        )

        all_reports.append(report)

        # 打印摘要
        print(f"    覆盖度: {report['coverage_comparison']['jaccard_similarity']}")
        print(f"    官方景点数: {report['coverage_comparison']['official_poi_count']}")
        print(f"    游客景点数: {report['coverage_comparison']['visitor_poi_count']}")
        print(f"    重合景点数: {report['coverage_comparison']['overlap_count']}")
        print(f"    评估: {report['summary']['coverage_level']}")

        for finding in report['summary']['key_findings']:
            print(f"    - {finding}")

    # 保存完整报告
    full_report = {
        "generated_at": str(pd.Timestamp.now()),
        "total_spots": len(all_reports),
        "reports": all_reports
    }

    with open('route_comparison/comparison_report.json', 'w', encoding='utf-8') as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    print(f"\n已生成对比报告: route_comparison/comparison_report.json")
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
