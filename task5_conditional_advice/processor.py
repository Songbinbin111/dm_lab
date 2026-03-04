#!/usr/bin/env python3
"""
任务5：条件性游览建议的抽取 - 核心提取模块

功能：
1. 从游记中提取条件-建议对
2. 对条件进行分类
3. 识别游客类型
4. 生成结构化输出
"""

import os
import re
import json
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime

try:
    import jieba  # noqa: F401
    import jieba.posseg as pseg  # noqa: F401
except ImportError:
    print("警告: jieba 未安装，某些功能可能受限")
    print("安装命令: pip install jieba")


# =============================================================================
# 1. 条件句式模式匹配器
# =============================================================================

class ConditionPatternMatcher:
    """条件句式模式匹配器"""

    def __init__(self, config_path: str = None):
        """
        初始化模式匹配器

        Args:
            config_path: 条件句式配置文件路径
        """
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config/condition_patterns.json')

        self.patterns = self._load_patterns(config_path)
        self.compiled_patterns: List[Tuple[str, re.Pattern]] = []
        for pattern_item in self.patterns:
            name = pattern_item.get("name", "unknown")
            regex = pattern_item.get("regex", "")
            if not regex:
                continue
            try:
                self.compiled_patterns.append((name, re.compile(regex)))
            except re.error as e:
                print(f"正则表达式错误 ({name}): {e}")

    def _default_patterns(self) -> List[Dict[str, str]]:
        """默认条件句式模式（必须显式抽出 condition 和 advice）。"""
        return [
            {
                "name": "if_then",
                "regex": (
                    r"(?:如果|若是|要是|假如|倘若)(?P<condition>[^，,。；:：!?]{1,45})"
                    r"(?:[,，]\s*)?(?P<advice>[^。；!?]{0,40}?(?:建议|可以|最好|推荐|需要|应该|不妨|可考虑|可选择|一定|千万|就|请|务必|记得)"
                    r"[^。；!?]{1,80})"
                ),
            },
            {
                "name": "if_not_then",
                "regex": (
                    r"(?:如果|若是|要是)(?P<condition>[^，,。；:：!?]{1,45})"
                    r"(?:[,，]\s*)?(?P<advice>[^。；!?]{0,30}?(?:不要|别|建议不要|最好别|千万别)[^。；!?]{1,90})"
                ),
            },
            {
                "name": "condition_suffix_then",
                "regex": (
                    r"(?P<condition>[^，。；:：!?]{2,40}?)(?:的话|时|的时候|情况下|期间|以后|之前|之后)"
                    r"(?:[,，]\s*)?(?P<advice>(?:建议|可以|最好|推荐|需要|应该|不妨|可考虑|可选择|一定|千万|就|请|务必|记得)"
                    r"[^。；!?]{2,120})"
                ),
            },
            {
                "name": "for_group_then",
                "regex": (
                    r"(?:对于|针对|带着|带上|带)(?P<condition>[^，。；:：!?]{1,30}?)(?:来说|游客|人群|朋友)?"
                    r"(?:[,，]\s*)?(?P<advice>(?:建议|可以|最好|推荐|需要|应该|不妨|可考虑|可选择|一定|千万|就|请|务必|记得)"
                    r"[^。；!?]{2,120})"
                ),
            },
            {
                "name": "desire_then",
                "regex": (
                    r"(?:想|若想|如果想|想要|打算|准备|计划)(?P<condition>[^，。；:：!?]{1,30}?)"
                    r"(?:[,，]\s*)?(?P<advice>(?:可以|建议|推荐|最好|一定|千万|就|请|务必|记得)[^。；!?]{2,120})"
                ),
            },
             {
                "name": "must_do",
                "regex": (
                    r"(?:去|在|到)(?P<condition>[^，。；:：!?]{2,15}?)(?:玩|游玩|旅游|旅行|的时候)?"
                    r"(?:[,，]\s*)?(?P<advice>(?:一定|千万|必须要|记得|务必)(?:要|不要|别)?[^。；!?]{2,50})"
                ),
            },
            {
                "name": "suggestion_prefix",
                "regex": (
                    r"(?:建议|推荐)(?P<condition>[^，。；:：!?]{2,20}?)(?:的时候|时)?"
                    r"(?:[,，]\s*)?(?P<advice>(?:可以|最好|要|去)[^。；!?]{2,50})"
                ),
            },
            {
                "name": "simple_advice",
                "regex": (
                     r"(?P<condition>[^，。；:：!?]{2,20}?)(?:[,，]\s*)?(?P<advice>(?:最好|一定要|千万要|记得要)[^。；!?]{2,50})"
                ),
            }
        ]

    def _load_patterns(self, config_path: str) -> List[Dict[str, str]]:
        """加载条件句式模式。兼容旧版 dict 配置。"""
        patterns = self._default_patterns()

        if not os.path.exists(config_path):
            return patterns

        with open(config_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        if isinstance(loaded, list):
            valid = [item for item in loaded if isinstance(item, dict) and item.get("regex")]
            return valid if valid else patterns

        if isinstance(loaded, dict):
            # 兼容旧版，自动转为新结构（旧规则精度较低，放在默认规则后）
            converted = []
            for name, regex in loaded.items():
                if isinstance(regex, str) and regex.strip():
                    converted.append({"name": f"legacy_{name}", "regex": regex})
            return patterns + converted

        return patterns

    def match(self, text: str) -> List[Tuple[str, str, str, str]]:
        """
        匹配条件句式

        Args:
            text: 待匹配的文本

        Returns:
            List of (pattern_name, condition, advice, full_match)
        """
        results = []
        for pattern_name, pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                full_match = match.group(0).strip()
                group_dict = match.groupdict()

                if "condition" in group_dict or "advice" in group_dict:
                    condition = (group_dict.get("condition") or "").strip()
                    advice = (group_dict.get("advice") or "").strip()
                else:
                    groups = match.groups()
                    condition = groups[0].strip() if len(groups) >= 1 else ""
                    advice = groups[1].strip() if len(groups) >= 2 else ""

                if len(condition) >= 2 and len(advice) >= 3:
                    results.append((pattern_name, condition, advice, full_match))

        return results


# =============================================================================
# 2. 条件分类器
# =============================================================================

class ConditionClassifier:
    """条件分类器"""

    def __init__(self, config_path: str = None):
        """
        初始化条件分类器

        Args:
            config_path: 条件分类配置文件路径
        """
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config/condition_classification.json')

        self.classification = self._load_classification(config_path)
        self.normalization_map = self._build_normalization_map()
        self.type_priority = {
            "visitor_type": 1,
            "weather": 2,
            "time": 3,
            "time_duration": 4,
            "crowd": 5,
            "physical": 6,
            "ticketing": 7,
            "transport": 8,
            "route": 9,
            "equipment": 10,
            "budget": 11,
            "policy": 12,
            "other": 99,
        }

    def _load_classification(self, config_path: str) -> Dict:
        """加载条件分类配置"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        return {
            "time": {"keywords": ["早上", "上午", "中午", "下午", "傍晚", "晚上", "清晨", "提前", "早起", "第一天", "第二天"], "label": "时间条件"},
            "weather": {"keywords": ["晴天", "下雨", "雾气", "大雾", "阴天", "雪", "雨天", "天气"], "label": "天气条件"},
            "crowd": {"keywords": ["人流", "高峰", "避开", "人多", "拥挤", "排队", "旺季", "淡季", "节假日"], "label": "人流条件"},
            "physical": {"keywords": ["体力", "腿", "爬山", "徒步", "步行", "累", "省体力"], "label": "体力条件"},
            "visitor_type": {"keywords": ["亲子", "老人", "儿童", "小孩", "家庭", "情侣", "独自", "新手", "第一次"], "label": "游客类型"},
            "budget": {"keywords": ["便宜", "贵", "经济", "省钱", "预算", "最便宜", "免费"], "label": "预算条件"},
            "time_duration": {"keywords": ["2小时", "半天", "一天", "多日", "时长", "快速游", "深度游"], "label": "时长条件"},
            "ticketing": {"keywords": ["门票", "抢票", "余票", "放票", "预约", "售票", "买票"], "label": "票务条件"},
            "transport": {"keywords": ["地铁", "公交", "索道", "缆车", "大巴", "高铁", "步行", "车站"], "label": "交通条件"},
            "route": {"keywords": ["路线", "顺序", "东门", "西门", "南门", "北门", "入口", "出口"], "label": "路线条件"},
            "equipment": {"keywords": ["登山杖", "手套", "鞋套", "背包", "防滑", "雨衣", "装备"], "label": "装备条件"},
            "policy": {"keywords": ["封闭", "开放", "闭馆", "旺季", "淡季", "规定", "执行"], "label": "规则条件"},
            "other": {"keywords": [], "label": "其他条件"},
        }

    def _build_normalization_map(self) -> Dict[str, Dict[str, str]]:
        """构建条件标准化映射表"""
        return {
            "time": {
                "早上": "上午", "清晨": "上午", "提前": "提前", "早起": "早上",
                "早进": "早上", "早进沟": "早上", "第一天": "时间安排", "第二天": "时间安排"
            },
            "weather": {
                "下雨": "雨天", "下雪": "雪天", "有雾": "雾天", "大雾": "雾天",
                "山下晴天": "天气", "山上下雨": "雨天"
            },
            "crowd": {
                "人多": "拥挤", "高峰期": "高峰", "节假日": "旺季"
            },
            "physical": {
                "体力好": "体力充足", "体力不足": "体力有限", "爬山": "徒步"
            },
            "ticketing": {
                "抢票": "门票紧张", "余票": "门票紧张", "放票": "放票时段", "预约": "预约入场"
            },
            "transport": {
                "地铁": "公共交通", "公交": "公共交通", "大巴": "公共交通", "缆车": "索道"
            },
            "route": {
                "东门": "东侧入口", "西门": "西侧入口", "南门": "南侧入口", "北门": "北侧入口"
            },
            "equipment": {
                "防滑鞋套": "防滑装备", "登山杖": "辅助装备"
            }
        }

    def classify(self, condition: str) -> Tuple[str, str]:
        """
        对条件进行分类

        Args:
            condition: 条件文本

        Returns:
            (primary_type, normalized_condition)
        """
        cleaned_condition = condition.strip()
        scores = defaultdict(int)

        for cond_type, config in self.classification.items():
            if cond_type == "other":
                continue
            for kw in config.get("keywords", []):
                if kw and kw in cleaned_condition:
                    scores[cond_type] += 2 if len(kw) >= 3 else 1

        if re.search(r"(凌晨|清晨|上午|下午|晚上|早起|提前|第一天|第二天|\d{1,2}点)", cleaned_condition):
            scores["time"] += 2
        if re.search(r"(雨|雪|雾|晴|阴|天气)", cleaned_condition):
            scores["weather"] += 2
        if re.search(r"(抢票|余票|放票|预约|门票)", cleaned_condition):
            scores["ticketing"] += 2
        if re.search(r"(地铁|公交|索道|缆车|步行|大巴|高铁)", cleaned_condition):
            scores["transport"] += 2
        if re.search(r"(入口|出口|路线|顺序|东门|西门|南门|北门)", cleaned_condition):
            scores["route"] += 2

        if not scores:
            return "other", self._normalize_condition(cleaned_condition, "other")

        primary_type = max(
            scores.items(),
            key=lambda x: (x[1], -self.type_priority.get(x[0], 99)),
        )[0]
        normalized = self._normalize_condition(cleaned_condition, primary_type)

        return primary_type, normalized

    def _normalize_condition(self, condition: str, cond_type: str) -> str:
        """标准化条件描述"""
        cond_type_map = self.normalization_map.get(cond_type, {})

        normalized = condition
        for old, new in cond_type_map.items():
            normalized = normalized.replace(old, new)

        normalized = re.sub(r"^\s*(如果|若是|要是|假如|倘若|当)\s*", "", normalized)
        normalized = re.sub(r"(的话|的时候|情况下|期间)$", "", normalized)
        normalized = normalized.strip(" ，,。！？；;:：")
        if normalized.startswith("是") and len(normalized) > 2:
            normalized = normalized[1:]
        if len(normalized) > 60:
            normalized = normalized[:60]

        label = self.classification.get(cond_type, {}).get("label", cond_type)
        return f"{label}: {normalized}"


# =============================================================================
# 3. 游客类型分类器
# =============================================================================

class VisitorTypeClassifier:
    """游客类型分类器"""

    def __init__(self, config_path: str = None):
        """
        初始化游客类型分类器

        Args:
            config_path: 游客类型配置文件路径
        """
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config/visitor_type_patterns.json')

        self.patterns = self._load_patterns(config_path)

    def _load_patterns(self, config_path: str) -> Dict:
        """加载游客类型模式"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        return {
            "family": {"keywords": ["孩子", "小孩", "儿童", "亲子", "带娃", "一家人"], "label": "亲子游"},
            "elderly": {"keywords": ["老人", "父母", "长辈", "老年人", "爷爷奶奶"], "label": "老年游"},
            "couple": {"keywords": ["情侣", "夫妻", "两人", "双人", "约会", "蜜月"], "label": "情侣游"},
            "solo": {"keywords": ["独自", "一个人", "单人", "独行", "独自旅行"], "label": "独自游"},
            "photographer": {"keywords": ["拍照", "摄影", "照片", "相机", "镜头", "拍摄"], "label": "摄影游"},
            "experienced": {"keywords": ["老登山友", "熟悉", "第二次", "多次", "再来"], "label": "经验丰富"},
            "beginner": {"keywords": ["第一次", "首次", "新手", "不知道"], "label": "新手"},
        }

    def classify(self, text: str) -> Dict[str, Any]:
        """
        从文本推断游客类型

        Args:
            text: 游记文本

        Returns:
            游客类型信息
        """
        scores = {vtype: 0 for vtype in self.patterns.keys()}
        evidence = {vtype: [] for vtype in self.patterns.keys()}

        for vtype, config in self.patterns.items():
            for keyword in config["keywords"]:
                if keyword in text:
                    scores[vtype] += 1
                    evidence[vtype].append(keyword)

        detected_types = [(t, s, evidence[t]) for t, s in scores.items() if s > 0]
        detected_types.sort(key=lambda x: x[1], reverse=True)

        primary_type = detected_types[0][0] if detected_types else "general"
        all_types = [t[0] for t in detected_types]

        return {
            "primary_type": primary_type,
            "primary_label": self.patterns.get(primary_type, {}).get("label", "一般游客"),
            "all_types": all_types,
            "scores": dict(scores),
            "evidence": {t[0]: t[2] for t in detected_types}
        }


# =============================================================================
# 4. 条件性建议提取器
# =============================================================================

class ConditionalAdviceExtractor:
    """条件性建议提取器"""

    def __init__(self):
        """初始化提取器"""
        self.pattern_matcher = ConditionPatternMatcher()
        self.condition_classifier = ConditionClassifier()
        self.visitor_classifier = VisitorTypeClassifier()
        self.strong_advice_markers = ["建议", "推荐", "最好", "可以", "不妨", "可考虑", "可选择", "不要", "别"]
        self.action_words = [
            "乘坐", "搭乘", "坐", "游览", "参观", "避开", "选择", "推荐",
            "前往", "走", "安排", "预订", "购买", "抢", "跟团", "入场", "提前", "记得",
        ]
        self.condition_markers = ["如果", "若是", "要是", "假如", "倘若", "对于", "针对", "的话", "时", "情况下"]
        self.fallback_action_markers = [
            "提前", "预订", "乘坐", "购买", "买票", "抢", "入场", "避开", "跟团", "规划", "早起", "自带", "走", "安排"
        ]
        self.condition_keywords = set()
        for config in self.condition_classifier.classification.values():
            self.condition_keywords.update(config.get("keywords", []))

    def extract_from_text(self, text: str, source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从文本中提取条件-建议对

        Args:
            text: 待处理的文本
            source_info: 来源信息（景区名称、游记编号等）

        Returns:
            条件-建议对列表
        """
        sentences = self._split_sentences(text)
        raw_results = []

        visitor_type_info = self.visitor_classifier.classify(text)

        for sentence in sentences:
            candidate_spans = self._generate_candidate_spans(sentence)
            for span in candidate_spans:
                matches = self.pattern_matcher.match(span)
                if not matches:
                    fallback_match = self._fallback_match(span)
                    if fallback_match:
                        matches = [fallback_match]

                for pattern_name, condition, advice, full_match in matches:
                    condition = self._clean_condition(condition)
                    cleaned_advice = self._clean_advice(advice if advice else full_match)

                    if not self._is_valid_extraction(condition, cleaned_advice, pattern_name):
                        continue

                    cond_type, normalized_cond = self.condition_classifier.classify(condition)
                    confidence = self._calculate_confidence(condition, cleaned_advice, pattern_name, cond_type)
                    action = self._extract_action(cleaned_advice)
                    target_entities = self._extract_target_entities(cleaned_advice)

                    raw_results.append({
                        "advice_id": "",
                        "scenic_spot": source_info['scenic_spot'],
                        "travelog_id": source_info['travelog_id'],
                        "visitor_type": visitor_type_info['primary_type'],
                        "condition": {
                            "text": condition,
                            "type": cond_type,
                            "type_label": self.condition_classifier.classification.get(cond_type, {}).get("label", cond_type),
                            "normalized": normalized_cond,
                        },
                        "advice": {
                            "text": cleaned_advice,
                            "action": action,
                            "target_entities": target_entities,
                        },
                        "pattern_type": pattern_name,
                        "sentence": sentence.strip(),
                        "evidence_span": span.strip(),
                        "confidence": round(confidence, 3),
                    })

        # 使用标准化 key 去重，避免同一句中被不同分句窗口重复抽取。
        dedup_map = {}
        sentence_advice_map = {}
        for item in raw_results:
            cond_key = self._canonical_text(item["condition"]["text"])
            advice_key = self._canonical_text(item["advice"]["text"])
            dedup_key = (cond_key, advice_key)
            sentence_advice_key = (self._canonical_text(item.get("sentence", "")), advice_key)

            # 同一句同建议，优先保留条件信号更强、条件文本更完整的版本。
            prev_sentence_item = sentence_advice_map.get(sentence_advice_key)
            if prev_sentence_item is not None:
                prev_key = (
                    self._canonical_text(prev_sentence_item["condition"]["text"]),
                    self._canonical_text(prev_sentence_item["advice"]["text"]),
                )
                prev_score = (
                    1 if self._has_condition_signal(prev_sentence_item["condition"]["text"]) else 0,
                    prev_sentence_item["confidence"],
                    len(prev_sentence_item["condition"]["text"]),
                )
                curr_score = (
                    1 if self._has_condition_signal(item["condition"]["text"]) else 0,
                    item["confidence"],
                    len(item["condition"]["text"]),
                )
                if curr_score > prev_score:
                    dedup_map.pop(prev_key, None)
                    sentence_advice_map[sentence_advice_key] = item
                else:
                    continue
            else:
                sentence_advice_map[sentence_advice_key] = item

            # 同一条件下，若建议文本互为前缀（长短版本），归并为同一条。
            merged_key = None
            for existing_key, existing_item in dedup_map.items():
                if existing_key[0] != cond_key:
                    continue
                existing_advice_key = self._canonical_text(existing_item["advice"]["text"])
                if advice_key.startswith(existing_advice_key) or existing_advice_key.startswith(advice_key):
                    merged_key = existing_key
                    break

            if merged_key is not None:
                dedup_key = merged_key

            prev = dedup_map.get(dedup_key)
            if prev is None:
                dedup_map[dedup_key] = item
                continue

            prev_score = (prev["confidence"], len(prev["advice"]["text"]))
            curr_score = (item["confidence"], len(item["advice"]["text"]))
            if curr_score > prev_score:
                dedup_map[dedup_key] = item

        results = []
        for idx, item in enumerate(dedup_map.values(), start=1):
            item["advice_id"] = f"{source_info['travelog_id']}_adv_{idx:04d}"
            results.append(item)

        return results

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子，兼容中英文标点并保护小数。"""
        if not text:
            return []

        normalized_text = re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()
        protected = re.sub(r"(\d)\.(\d)", r"\1<DECIMAL>\2", normalized_text)
        pieces = re.split(r"(?<=[。！？!?；;.])\s*|\n+", protected)

        sentences = []
        for piece in pieces:
            sentence = piece.replace("<DECIMAL>", ".").strip()
            if len(sentence) >= 4:
                sentences.append(sentence)

        return sentences

    def _generate_candidate_spans(self, sentence: str) -> List[str]:
        """生成候选片段：原句 + 分句 + 相邻分句组合。"""
        cleaned = sentence.strip()
        candidates = [cleaned]

        clauses = [c.strip(" ，,") for c in re.split(r"[，,]", cleaned) if c.strip(" ，,")]
        for clause in clauses:
            if len(clause) >= 4 and self._contains_advice_signal(clause):
                candidates.append(clause)

        for idx in range(len(clauses) - 1):
            merged = f"{clauses[idx]}，{clauses[idx + 1]}"
            if len(merged) >= 6 and self._contains_advice_signal(merged):
                candidates.append(merged)

        for idx in range(len(clauses) - 2):
            merged = f"{clauses[idx]}，{clauses[idx + 1]}，{clauses[idx + 2]}"
            if len(merged) >= 8 and self._contains_advice_signal(merged):
                candidates.append(merged)

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            clipped = candidate[:360]
            if clipped and clipped not in seen:
                seen.add(clipped)
                unique_candidates.append(clipped)

        return unique_candidates

    def _contains_advice_signal(self, text: str) -> bool:
        """判断候选片段是否包含建议线索。"""
        advice_cues = ("建议", "推荐", "最好", "可以", "不要", "别", "可考虑", "可选择", "不妨")
        return any(cue in text for cue in advice_cues)

    def _contains_conditional_signal(self, text: str) -> bool:
        """判断候选片段是否同时包含条件/建议线索。"""
        condition_cues = ("如果", "若是", "要是", "假如", "倘若", "的话", "的时候", "情况下", "时")
        advice_cues = ("建议", "推荐", "最好", "可以", "不要", "别", "可考虑", "可选择")
        return any(cue in text for cue in condition_cues) and any(cue in text for cue in advice_cues)

    def _fallback_match(self, text: str) -> Optional[Tuple[str, str, str, str]]:
        """当规则未命中时的保守回退抽取。"""
        marker_pattern = r"(建议|推荐|最好|不妨|可考虑|可选择|可以)"
        marker_match = re.search(marker_pattern, text)
        if not marker_match:
            return None

        marker = marker_match.group(1)
        advice = text[marker_match.start():].strip()
        # “可以”触发词噪声高，要求建议体内出现动作线索。
        if marker == "可以" and not any(action in advice for action in self.fallback_action_markers):
            return None

        pre_text = text[:marker_match.start()].strip(" ，,。；;:：")
        if len(pre_text) > 50:
            pre_text = pre_text[-50:]
        condition = self._infer_condition(pre_text)
        if not condition:
            condition = self._infer_condition_from_advice(advice)
        if not condition:
            return None

        return ("fallback", condition, advice, text)

    def _infer_condition(self, pre_text: str) -> str:
        """从建议前文推断条件部分。"""
        if not pre_text:
            return ""

        explicit = re.search(r"(?:如果|若是|要是|假如|倘若)([^，。；:：!?]{1,45})$", pre_text)
        if explicit:
            return explicit.group(1).strip()

        segments = [seg.strip() for seg in re.split(r"[，,；;。:：]", pre_text) if seg.strip()]
        if not segments:
            return ""

        # 优先选择携带条件关键词的片段，避免拿到“强烈”这类噪声词。
        signaled_segments = [seg for seg in segments if self._has_condition_signal(seg)]
        if signaled_segments:
            candidate = signaled_segments[-1]
        else:
            candidate = max(segments, key=len)

        if len(candidate) > 50:
            candidate = candidate[-50:]
        if len(candidate) < 2:
            return ""
        return candidate

    def _infer_condition_from_advice(self, advice: str) -> str:
        """当建议在句首时，从建议体内部回推条件。"""
        if not advice:
            return ""

        body = re.sub(r"^(强烈)?(建议大家|建议|推荐|最好|可以|不妨|可考虑|可选择)", "", advice).strip(" ，,。；;:：")

        if not body:
            return ""

        first_clause = re.split(r"[，,。；;:：]", body)[0].strip()
        if self._has_condition_signal(first_clause):
            return first_clause

        # 从建议体中寻找已知条件关键词附近的短片段
        sorted_keywords = sorted([kw for kw in self.condition_keywords if kw], key=len, reverse=True)
        for keyword in sorted_keywords:
            idx = body.find(keyword)
            if idx >= 0:
                start = max(0, idx - 6)
                end = min(len(body), idx + len(keyword) + 8)
                snippet = body[start:end].strip(" ，,。；;:：")
                if len(snippet) >= 2:
                    return snippet

        if 2 <= len(first_clause) <= 20:
            return first_clause

        return ""

    def _clean_condition(self, condition: str) -> str:
        """清洗条件文本，去掉触发词和噪声标点。"""
        if not condition:
            return ""

        condition = re.sub(r"\s+", "", condition)
        condition = condition.strip("，,.。！？；;:：\"'“”‘’()（）[]【】")
        condition = re.sub(r"^(如果|若是|要是|假如|倘若|对于|针对|在)", "", condition)
        condition = re.sub(r"^(大家|游客|我们|你们|请|一定要|尽量|记得)", "", condition)
        condition = re.sub(r"(的话|的时候|情况下|期间|时)$", "", condition)
        if condition.startswith("是") and len(condition) > 2:
            condition = condition[1:]
        if len(condition) > 60:
            condition = condition[:60]
        return condition

    def _clean_advice(self, advice: str) -> str:
        """清洗建议文本"""
        if not advice:
            return ""

        advice = re.sub(r'\s+', '', advice)
        advice = advice.strip('，。！？、；：""\'\'（）【】《》')

        marker = re.search(r"(建议|推荐|最好|可以|不妨|可考虑|可选择|不要|别)", advice)
        if marker and marker.start() > 0:
            advice = advice[marker.start():]

        advice = re.split(r"[。\\.！？；;]", advice)[0]
        advice = advice.strip("，,:： ")
        if len(advice) > 120:
            advice = advice[:120]

        return advice

    def _canonical_text(self, text: str) -> str:
        """用于去重的轻量标准化。"""
        return re.sub(r"[\\s，,。；;:：!?！？\"'“”‘’()（）\\-—\\.]+", "", text)

    def _extract_action(self, advice: str) -> str:
        """提取建议的动作部分"""
        if not advice:
            return ""

        action_patterns = [
            r'(建议|推荐|最好|可以|不妨|可考虑|可选择)([^，。；!?]{1,18})',
            r'(乘坐|搭乘|坐|游览|参观|前往|避开|选择|安排|预订|购买|抢|跟团)([^，。；!?]{0,14})',
        ]

        for pattern in action_patterns:
            match = re.search(pattern, advice)
            if match:
                return match.group(0)[:20]

        return advice[:10] if len(advice) > 10 else advice

    def _extract_target_entities(self, advice: str) -> List[str]:
        """提取建议中的目标实体"""
        entities = []

        entity_patterns = [
            r'(缆车|索道|观景车|游船|竹筏|地铁|公交|大巴)',
            r'(景区|景点|展馆|宫殿|庙宇|入口|出口|路线)',
            r'(路线|线路|攻略|顺序|东门|西门|南门|北门)',
            r'(时间|时段|早上|下午|晚上|清晨|第一天|第二天)',
            r'(门票|票|票务|预约|抢票|余票)',
            r'(登山杖|手套|鞋套|雨衣|背包)',
        ]

        for pattern in entity_patterns:
            matches = re.findall(pattern, advice)
            entities.extend(matches)

        return list(set(entities))

    def _has_condition_signal(self, condition: str) -> bool:
        """判断条件文本是否具有条件性线索。"""
        if any(marker in condition for marker in self.condition_markers):
            return True
        return any(keyword in condition for keyword in self.condition_keywords if keyword)

    def _looks_like_advice(self, advice: str) -> bool:
        """判断文本是否像建议。"""
        if any(marker in advice for marker in self.strong_advice_markers):
            return True
        return any(word in advice for word in self.action_words)

    def _is_valid_extraction(self, condition: str, advice: str, pattern_name: str) -> bool:
        """过滤边界错误和叙述性误提取。"""
        if not condition or not advice:
            return False

        if len(condition) < 2 or len(condition) > 60:
            return False
        if len(advice) < 3 or len(advice) > 140:
            return False
        if condition == advice:
            return False
        if len(condition) <= 4 and condition.endswith("也"):
            return False
        if advice.endswith(":") and len(advice) <= 10:
            return False
        if advice.startswith(("建议)", "推荐)", "最好)")):
            return False
        if "--" in advice and len(advice) > 45:
            return False

        if not self._looks_like_advice(advice):
            return False

        # “可以看到xxx”通常是叙述，不是建议
        if advice.startswith(("可以看到", "可以看见", "可以感受", "可以发现")):
            behavior_markers = ["选择", "乘坐", "预订", "抢票", "购买", "入场", "避开", "安排", "跟团", "前往", "步行"]
            if not any(marker in advice for marker in behavior_markers):
                return False

        if re.search(r"(刷卡\\d|\\d+毛|\\d+元)", advice):
            monetary_actions = ["购买", "买票", "抢票", "乘坐", "预订", "入场", "支付"]
            if not any(action in advice for action in monetary_actions):
                return False

        canonical_cond = self._canonical_text(condition)
        canonical_advice = self._canonical_text(advice)
        if canonical_cond and canonical_advice.startswith(canonical_cond) and len(canonical_cond) >= 10:
            return False

        if pattern_name == "fallback" and not self._has_condition_signal(condition):
            if len(condition) < 4:
                return False
            if not any(marker in advice for marker in self.fallback_action_markers):
                return False

        return True

    def _calculate_confidence(self, condition: str, advice: str, pattern: str, cond_type: str) -> float:
        """计算置信度"""
        confidence = 0.45

        if 2 <= len(condition) <= 35:
            confidence += 0.1

        if 4 <= len(advice) <= 45:
            confidence += 0.1

        if pattern in {"if_then", "if_not_then", "condition_suffix_then", "for_group_then", "desire_then"}:
            confidence += 0.15

        if self._has_condition_signal(condition):
            confidence += 0.1

        if cond_type != "other":
            confidence += 0.1

        if any(word in advice for word in self.action_words):
            confidence += 0.05

        return min(confidence, 1.0)


# =============================================================================
# 5. 数据加载器
# =============================================================================

class DataLoader:
    """数据加载器"""

    @staticmethod
    def load_travelogs(data_path: str) -> Dict[str, Any]:
        """
        加载游记数据

        Args:
            data_path: 数据文件路径

        Returns:
            包含游记数据的字典
        """
        df = pd.read_excel(data_path)

        data = {
            "scenic_spots": [],
            "travelogs": []
        }

        for _, row in df.iterrows():
            scenic_spot = row.get('景区名称', '')
            if scenic_spot and scenic_spot not in data["scenic_spots"]:
                data["scenic_spots"].append(scenic_spot)

            for i in range(1, 6):
                travelog_col = f'游客游记{i}'
                if travelog_col in row and pd.notna(row[travelog_col]):
                    content = str(row[travelog_col])
                    if content.strip():
                        data["travelogs"].append({
                            "scenic_spot": scenic_spot,
                            "travelog_id": f"{scenic_spot}_travelog_{i}",
                            "travelog_number": i,
                            "content": content
                        })

        return data


# =============================================================================
# 6. 主处理流程
# =============================================================================

def process_all_data(data_path: str, output_dir: str) -> Dict[str, Any]:
    """
    处理所有数据的主流程

    Args:
        data_path: 输入数据文件路径
        output_dir: 输出目录路径

    Returns:
        处理结果统计
    """
    print("=" * 60)
    print("任务5：条件性游览建议的抽取 - 数据处理")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/annotated", exist_ok=True)

    print("\n[步骤 1/4] 加载游记数据...")
    data_loader = DataLoader()
    data = data_loader.load_travelogs(data_path)
    print(f"  共加载 {len(data['travelogs'])} 篇游记")
    print(f"  景区: {', '.join(data['scenic_spots'])}")

    print("\n[步骤 2/4] 提取条件-建议对...")
    extractor = ConditionalAdviceExtractor()
    all_advice = []

    for travelog in data['travelogs']:
        advices = extractor.extract_from_text(
            travelog['content'],
            {
                'scenic_spot': travelog['scenic_spot'],
                'travelog_id': travelog['travelog_id']
            }
        )
        all_advice.extend(advices)
        print(f"  {travelog['scenic_spot']} - 游记{travelog['travelog_number']}: 找到 {len(advices)} 条建议")

    print(f"\n  总共找到 {len(all_advice)} 条条件性建议")

    print("\n[步骤 3/4] 构建条件-建议映射...")

    condition_mapping = defaultdict(lambda: defaultdict(list))
    for advice in all_advice:
        cond_type = advice['condition']['type']
        cond_text = advice['condition']['normalized']
        condition_mapping[cond_type][cond_text].append({
            'advice_id': advice['advice_id'],
            'advice_text': advice['advice']['text'],
            'action': advice['advice']['action'],
            'scenic_spot': advice['scenic_spot'],
            'travelog_id': advice['travelog_id'],
            'confidence': advice['confidence'],
            'condition_raw': advice['condition']['text'],
            'evidence_sentence': advice.get('evidence_span') or advice.get('sentence', ''),
        })

    condition_mapping_final = {}
    for cond_type, conditions in condition_mapping.items():
        condition_mapping_final[cond_type] = {}
        cond_label = extractor.condition_classifier.classification.get(cond_type, {}).get("label", cond_type)

        for cond_text, records in conditions.items():
            advice_counter = Counter(item['advice_text'] for item in records)
            raw_conditions = list(dict.fromkeys(item['condition_raw'] for item in records if item['condition_raw']))[:3]
            top_records = sorted(records, key=lambda x: x['confidence'], reverse=True)[:8]

            condition_mapping_final[cond_type][cond_text] = {
                "condition_type": cond_type,
                "condition_label": cond_label,
                "condition_raw_examples": raw_conditions,
                "advice_count": len(records),
                "unique_advice_count": len(advice_counter),
                "advice_frequency": [
                    {"advice_text": text, "count": count}
                    for text, count in advice_counter.most_common(5)
                ],
                "record_examples": [
                    {
                        "advice_id": item['advice_id'],
                        "advice_text": item['advice_text'],
                        "action": item['action'],
                        "scenic_spot": item['scenic_spot'],
                        "travelog_id": item['travelog_id'],
                        "confidence": item['confidence'],
                        "evidence_sentence": item['evidence_sentence'],
                    }
                    for item in top_records
                ],
            }

    print("\n[步骤 4/4] 保存结果...")

    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source_file": data_path,
            "total_records": len(data['travelogs']),
            "total_advice": len(all_advice),
            "scenic_spots": data['scenic_spots']
        },
        "conditional_advice": all_advice,
        "condition_mapping": condition_mapping_final,
    }

    advice_output_path = f"{output_dir}/conditional_advice.json"
    with open(advice_output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {advice_output_path}")

    mapping_output_path = f"{output_dir}/condition_mapping.json"
    with open(mapping_output_path, 'w', encoding='utf-8') as f:
        json.dump(condition_mapping_final, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {mapping_output_path}")

    stats = generate_statistics(all_advice, data['travelogs'])

    stats_output_path = f"{output_dir}/statistics_report.json"
    with open(stats_output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {stats_output_path}")

    print("\n" + "=" * 60)
    print("数据处理完成！")
    print("=" * 60)

    return {
        "total_advice": len(all_advice),
        "statistics": stats
    }


def generate_statistics(advice_list: List[Dict], travelogs: List[Dict]) -> Dict[str, Any]:
    """
    生成统计报告

    Args:
        advice_list: 提取的建议列表
        travelogs: 游记列表

    Returns:
        统计报告
    """
    stats = {
        "total_advice": len(advice_list),
        "total_travelogs": len(travelogs),
        "avg_advice_per_travelog": round(len(advice_list) / len(travelogs), 2) if travelogs else 0,
        "by_condition_type": Counter(),
        "by_scenic_spot": Counter(),
        "by_visitor_type": Counter(),
        "pattern_distribution": Counter(),
        "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
    }

    for advice in advice_list:
        stats['by_condition_type'][advice['condition']['type']] += 1
        stats['by_scenic_spot'][advice['scenic_spot']] += 1
        stats['by_visitor_type'][advice.get('visitor_type', 'unknown')] += 1
        stats['pattern_distribution'][advice['pattern_type']] += 1

        conf = advice['confidence']
        if conf >= 0.7:
            stats['confidence_distribution']['high'] += 1
        elif conf >= 0.5:
            stats['confidence_distribution']['medium'] += 1
        else:
            stats['confidence_distribution']['low'] += 1

    stats['by_condition_type'] = dict(stats['by_condition_type'])
    stats['by_scenic_spot'] = dict(stats['by_scenic_spot'])
    stats['by_visitor_type'] = dict(stats['by_visitor_type'])
    stats['pattern_distribution'] = dict(stats['pattern_distribution'])

    return stats


# =============================================================================
# 7. 创建标注模板
# =============================================================================

def create_annotation_template(output_dir: str):
    """
    创建手工标注模板

    Args:
        output_dir: 输出目录
    """
    template_data = {
        'advice_id': [],
        'scenic_spot': [],
        'sentence': [],
        'condition_text': [],
        'condition_type': [],
        'advice_text': [],
        'is_valid': [],
        'confidence': [],
        'manual_correction': [],
        'notes': []
    }

    df = pd.DataFrame(template_data)
    output_path = f"{output_dir}/annotation_template.xlsx"
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"  已创建标注模板: {output_path}")


# =============================================================================
# 8. 主程序
# =============================================================================

if __name__ == '__main__':
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, '../task1_data_collection/data/data_cleaned.xlsx')
    output_dir = os.path.join(current_dir, 'output')

    if not os.path.exists(data_path):
        print(f"错误: 数据文件不存在: {data_path}")
        print("请确保 task1_data_collection/data/data_cleaned.xlsx 存在")
        sys.exit(1)

    results = process_all_data(data_path, output_dir)
    create_annotation_template(output_dir)

    print("\n处理完成！")
    print(f"总共提取 {results['total_advice']} 条条件性建议")
