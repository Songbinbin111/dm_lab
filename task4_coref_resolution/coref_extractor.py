#!/usr/bin/env python3
"""
任务4：程序性知识的共指消解 - 代词提取与标注模块

功能：
1. 从游记中找出包含代词（"它"/"这里"/"该景点"等）的句子
2. 手工标注代词所指代的实体
3. 使用简单规则（最近名词匹配）实现自动指代消解
"""

import re
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import pandas as pd

try:
    import jieba
    import jieba.posseg as pseg
except ImportError:
    print("请安装 jieba: pip install jieba")


# =============================================================================
# 1. 代词定义词典
# =============================================================================

class PronounDictionary:
    """代词词典 - 定义需要处理的指代词"""

    # 人称代词（指代地点/景点）
    PERSONAL_PRONOUNS = ['它', '它们', '他', '她', '他们', '她们']

    # 指示代词（地点/方位）
    DEMONSTRATIVE_PRONOUNS = ['这里', '这里', '那儿', '那里', '此处', '彼处']

    # 指示短语
    DEMONSTRATIVE_PHRASES = ['该景点', '该景区', '这个景点', '这个景区', '这个地方',
                            '那个景点', '那个景区', '那个地方',
                            '此地', '景区内', '园内', '宫内', '沟内']

    # 疑问代词（用于句式识别，如"这里有什么"）
    INTERROGATIVE_PRONOUNS = ['哪里', '哪儿', '何处']

    @classmethod
    def get_all_pronouns(cls) -> List[str]:
        """获取所有需要处理的代词"""
        return (cls.PERSONAL_PRONOUNS +
                cls.DEMONSTRATIVE_PRONOUNS +
                cls.DEMONSTRATIVE_PHRASES)

    @classmethod
    def get_pronoun_patterns(cls) -> List[str]:
        """获取正则匹配模式"""
        patterns = []
        for pronoun in cls.get_all_pronouns():
            # 转义特殊字符
            escaped = re.escape(pronoun)
            patterns.append(escaped)
        return patterns


# =============================================================================
# 2. 句子分割器
# =============================================================================

class SentenceSplitter:
    """句子分割器 - 将文本分割为句子"""

    # 句子结束标记
    SENTENCE_ENDINGS = ['。', '！', '？', '！', '？', '\n']

    @staticmethod
    def split(text: str) -> List[str]:
        """
        将文本分割为句子

        Args:
            text: 待分割的文本

        Returns:
            句子列表
        """
        if not text or pd.isna(text):
            return []

        # 标准化文本
        text = str(text).strip()

        # 按句子结束符分割
        sentences = []
        current = ""

        for char in text:
            current += char
            if char in SentenceSplitter.SENTENCE_ENDINGS:
                sentence = current.strip()
                if sentence and len(sentence) > 3:  # 过滤太短的句子
                    sentences.append(sentence)
                current = ""

        # 处理最后一个句子
        if current.strip():
            sentence = current.strip()
            if sentence and len(sentence) > 3:
                sentences.append(sentence)

        return sentences


# =============================================================================
# 3. 代词句子提取器
# =============================================================================

class PronounSentenceExtractor:
    """代词句子提取器 - 提取包含代词的句子"""

    def __init__(self):
        self.pronoun_dict = PronounDictionary()
        self.pronoun_patterns = self.pronoun_dict.get_pronoun_patterns()

    def contains_pronoun(self, sentence: str) -> bool:
        """
        检查句子是否包含代词

        Args:
            sentence: 待检查的句子

        Returns:
            是否包含代词
        """
        for pattern in self.pronoun_patterns:
            if pattern in sentence:
                return True
        return False

    def extract_pronouns(self, sentence: str) -> List[Dict[str, Any]]:
        """
        提取句子中的代词及其位置

        Args:
            sentence: 待处理的句子

        Returns:
            代词信息列表：[{"pronoun": "它", "position": 10, "type": "personal"}]
        """
        results = []

        for pronoun in self.pronoun_dict.PERSONAL_PRONOUNS:
            for match in re.finditer(re.escape(pronoun), sentence):
                results.append({
                    "pronoun": pronoun,
                    "position": match.start(),
                    "type": "personal"
                })

        for pronoun in self.pronoun_dict.DEMONSTRATIVE_PRONOUNS:
            for match in re.finditer(re.escape(pronoun), sentence):
                results.append({
                    "pronoun": pronoun,
                    "position": match.start(),
                    "type": "demonstrative_location"
                })

        for phrase in self.pronoun_dict.DEMONSTRATIVE_PHRASES:
            for match in re.finditer(re.escape(phrase), sentence):
                results.append({
                    "pronoun": phrase,
                    "position": match.start(),
                    "type": "demonstrative_phrase"
                })

        # 按位置排序
        results.sort(key=lambda x: x["position"])
        return results

    def extract_from_text(self, text: str, source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从文本中提取包含代词的句子

        Args:
            text: 待处理的文本
            source_info: 来源信息（景区名称、游记编号等）

        Returns:
            包含代词的句子列表
        """
        sentences = SentenceSplitter.split(text)
        results = []
        
        # 保存最近的句子作为上下文
        context_window_size = 3

        for sent_idx, sentence in enumerate(sentences):
            pronouns = self.extract_pronouns(sentence)
            
            # 获取上下文（前N个句子）
            start_idx = max(0, sent_idx - context_window_size)
            context_sentences = sentences[start_idx:sent_idx]
            context_text = " ".join(context_sentences)
            
            if pronouns:
                results.append({
                    "sentence_id": f"{source_info['scenic_spot']}_{source_info['travelog_id']}_{sent_idx}",
                    "scenic_spot": source_info['scenic_spot'],
                    "travelog_id": source_info['travelog_id'],
                    "sentence_index": sent_idx,
                    "sentence": sentence,
                    "context": context_text,  # 添加上下文
                    "pronouns": pronouns,
                    "manual_annotation": None,  # 待手工标注
                    "auto_resolution": None    # 待自动消解
                })

        return results


# =============================================================================
# 4. 上下文提取器 - 用于指代消解
# =============================================================================

class ContextExtractor:
    """上下文提取器 - 提取代词前后的上下文"""

    @staticmethod
    def extract_candidate_entities(text: str, pronoun_position: int,
                                    window_size: int = 100) -> List[Dict[str, Any]]:
        """
        提取代词前后的候选实体（名词/景点）

        Args:
            text: 完整文本
            pronoun_position: 代词在文本中的位置
            window_size: 向前查找的窗口大小

        Returns:
            候选实体列表
        """
        # 获取代词前的文本
        start_pos = max(0, pronoun_position - window_size)
        context_text = text[start_pos:pronoun_position]

        # 使用jieba分词提取名词
        words = pseg.cut(context_text)
        candidates = []

        # 常见景点后缀
        poi_suffixes = ['海', '池', '宫', '殿', '门', '峰', '阁', '寺', '松',
                       '沟', '山', '区', '湖', '瀑', '滩', '寨', '瀑布']

        for word, flag in words:
            # 名词或地名
            if flag in ['n', 'nr', 'ns', 'nt', 'nz']:
                if 2 <= len(word) <= 6:
                    # 检查是否是景点类名词
                    is_poi = any(word.endswith(suffix) for suffix in poi_suffixes)
                    candidates.append({
                        "entity": word,
                        "pos_flag": flag,
                        "is_poi": is_poi,
                        "distance_from_pronoun": pronoun_position - start_pos - context_text.rfind(word)
                    })

        # 过滤噪声词
        noise_words = {'热门', '门票', '区域', '时间', '路线', '攻略'}
        candidates = [c for c in candidates if c["entity"] not in noise_words]

        # 按距离排序（最近的在前）
        candidates.sort(key=lambda x: x["distance_from_pronoun"])

        return candidates


# =============================================================================
# 5. 最近名词匹配指代消解器
# =============================================================================

class NearestNounResolver:
    """最近名词匹配指代消解器 - 使用简单规则进行指代消解"""

    def __init__(self):
        self.context_extractor = ContextExtractor()

        # 加载POI词典（用于判断是否是景点）
        self._load_poi_dicts()

    def _load_poi_dicts(self):
        """加载POI词典"""
        self.poi_dicts = set()
        dict_dir = '../task2_entity_recognition/custom_dicts/poi'

        for spot in ['jiuzhaigou', 'gugong', 'huangshan']:
            dict_path = os.path.join(dict_dir, f'{spot}.txt')
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            self.poi_dicts.add(parts[0])
                            jieba.add_word(parts[0], 10000, 'n')

    def resolve(self, sentence: str, context: str, pronoun_info: Dict[str, Any],
                scenic_spot: str) -> Dict[str, Any]:
        """
        使用增强的规则进行指代消解

        Args:
            sentence: 包含代词的句子
            context: 上下文（前几个句子）
            pronoun_info: 代词信息
            scenic_spot: 景区名称

        Returns:
            消解结果
        """
        pronoun = pronoun_info['pronoun']
        pronoun_type = pronoun_info.get('type', 'unknown')
        position_in_sentence = pronoun_info['position']

        # 1. 提取当前句子中代词前的部分
        sentence_before = sentence[:position_in_sentence]
        
        # 2. 提取候选实体（包括当前句和上下文）
        # 提取当前句的名词（倒序，最近的优先）
        candidates_current = self._extract_nouns_from_text(sentence_before)
        # 提取上下文的名词（倒序，最近的优先）
        candidates_context = self._extract_nouns_from_text(context) if context else []
        
        # 合并候选列表，优先当前句
        all_candidates = candidates_current + candidates_context

        # 策略1：针对地点代词（这里/那儿/该景点）
        if pronoun_type in ['demonstrative_location', 'demonstrative_phrase'] or pronoun in ['这里', '那儿', '该景点', '此地']:
            # 1.1 优先匹配POI词典中的景点
            poi_candidates = [c for c in all_candidates if c['entity'] in self.poi_dicts]
            if poi_candidates:
                best_match = poi_candidates[0]
                return {
                    "pronoun": pronoun,
                    "antecedent": best_match['entity'],
                    "resolution_method": "nearest_poi_in_context",
                    "confidence": "high",
                    "reason": f"在上下文中找到最近的POI景点: {best_match['entity']}"
                }
            
            # 1.2 其次匹配地名（ns）
            loc_candidates = [c for c in all_candidates if c['pos_flag'] == 'ns']
            if loc_candidates:
                best_match = loc_candidates[0]
                return {
                    "pronoun": pronoun,
                    "antecedent": best_match['entity'],
                    "resolution_method": "nearest_location_in_context",
                    "confidence": "medium",
                    "reason": f"在上下文中找到最近的地名: {best_match['entity']}"
                }
                
            # 1.3 再次匹配以地点后缀结尾的名词
            loc_suffixes = ['亭', '台', '楼', '阁', '殿', '堂', '门', '宫', '祠', '庙', '寺', '观', '山', '河', '湖', '海', '沟', '寨', '园', '区']
            suffix_candidates = [c for c in all_candidates if any(c['entity'].endswith(s) for s in loc_suffixes)]
            if suffix_candidates:
                best_match = suffix_candidates[0]
                return {
                    "pronoun": pronoun,
                    "antecedent": best_match['entity'],
                    "resolution_method": "nearest_loc_noun_in_context",
                    "confidence": "medium",
                    "reason": f"在上下文中找到最近的地点名词: {best_match['entity']}"
                }

        # 策略2：针对人称代词（他/她）优先匹配人名/称谓
        if pronoun in ['他', '她', '他们', '她们']:
            # 2.1 匹配人名（nr）
            person_candidates = [c for c in all_candidates if c['pos_flag'] == 'nr']
            if person_candidates:
                best_match = person_candidates[0]
                return {
                    "pronoun": pronoun,
                    "antecedent": best_match['entity'],
                    "resolution_method": "nearest_person_name_in_context",
                    "confidence": "high",
                    "reason": f"在上下文中找到最近的人名: {best_match['entity']}"
                }
            
            # 2.2 匹配特定称谓
            titles = ['游客', '导游', '师傅', '司机', '朋友', '家人', '皇帝', '妃子', '太子', '阿哥', '格格', '大臣', '诗人', '画家', '记者', '工作组']
            title_candidates = [c for c in all_candidates if any(t in c['entity'] for t in titles)]
            if title_candidates:
                best_match = title_candidates[0]
                return {
                    "pronoun": pronoun,
                    "antecedent": best_match['entity'],
                    "resolution_method": "nearest_person_title_in_context",
                    "confidence": "high",
                    "reason": f"在上下文中找到最近的人物称谓: {best_match['entity']}"
                }

        # 策略3：针对“它”，优先匹配非人非地点名词
        if pronoun in ['它', '它们']:
             # 排除明显的人物（nr）和时间（t）
            obj_candidates = [c for c in all_candidates 
                             if c['pos_flag'] not in ['nr', 't'] 
                             and c['entity'] not in self.poi_dicts  # 尽量不指代POI（通常用这里）
                             and not self._is_noise_word(c['entity'])]
            if obj_candidates:
                best_match = obj_candidates[0]
                return {
                    "pronoun": pronoun,
                    "antecedent": best_match['entity'],
                    "resolution_method": "nearest_object_in_context",
                    "confidence": "medium",
                    "reason": f"在上下文中找到最近的物体/名词: {best_match['entity']}"
                }

        # 策略4：通用回退策略 - 最近的名词
        if all_candidates:
            # 过滤明显的非实体词
            filtered = [c for c in all_candidates
                       if not self._is_noise_word(c['entity'])]
            if filtered:
                best_match = filtered[0]
                return {
                    "pronoun": pronoun,
                    "antecedent": best_match['entity'],
                    "resolution_method": "nearest_noun_fallback",
                    "confidence": "low",
                    "reason": f"在上下文中找到最近的名词: {best_match['entity']}"
                }

        # 策略5：如果都找不到，返回无法消解
        return {
            "pronoun": pronoun,
            "antecedent": None,
            "resolution_method": "no_candidate",
            "confidence": "low",
            "reason": "在上下文内未找到合适的先行词"
        }

    def _extract_nouns_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取名词"""
        words = list(pseg.cut(text))
        nouns = []

        for word, flag in reversed(words):  # 从后往前找
            if flag in ['n', 'nr', 'ns', 'nt', 'nz'] and len(word) >= 2:
                nouns.append({
                    "entity": word,
                    "pos_flag": flag
                })

        return nouns

    def _is_noise_word(self, word: str) -> bool:
        """判断是否是噪声词"""
        noise_words = {'热门', '门票', '时间', '小时', '分钟', '路程',
                      '路线', '攻略', '游客', '人们', '大家'}
        return word in noise_words


# =============================================================================
# 6. 数据加载器
# =============================================================================

class DataLoader:
    """数据加载器"""

    @staticmethod
    def load_travelogs(data_path: str = '../task1_data_collection/data/data_cleaned.xlsx') -> Dict[str, Any]:
        """
        加载游记数据

        Args:
            data_path: 数据文件路径

        Returns:
            数据字典
        """
        df = pd.read_excel(data_path)
        data = {
            "scenic_spots": [],
            "travelogs": []
        }

        for idx, row in df.iterrows():
            scenic_spot = row['景区名称']
            data["scenic_spots"].append(scenic_spot)

            # 提取每个景区的游客游记
            for i in range(1, 6):
                travelog_col = f'游客游记{i}'
                if travelog_col in row and pd.notna(row[travelog_col]):
                    data["travelogs"].append({
                        "scenic_spot": scenic_spot,
                        "travelog_id": f"{scenic_spot}_travelog_{i}",
                        "travelog_number": i,
                        "content": str(row[travelog_col])
                    })

        return data


# =============================================================================
# 7. 主处理流程
# =============================================================================

def process_all_data(data_path: str, output_dir: str) -> Dict[str, Any]:
    """
    处理所有数据的主流程

    Args:
        data_path: 数据文件路径
        output_dir: 输出目录

    Returns:
        处理结果汇总
    """
    print("=" * 60)
    print("任务4：程序性知识的共指消解")
    print("=" * 60)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/annotated", exist_ok=True)

    # 1. 加载数据
    print("\n[1/4] 加载游记数据...")
    data_loader = DataLoader()
    data = data_loader.load_travelogs(data_path)
    print(f"  共加载 {len(data['travelogs'])} 篇游记")

    # 2. 提取包含代词的句子
    print("\n[2/4] 提取包含代词的句子...")
    extractor = PronounSentenceExtractor()
    all_sentences = []

    for travelog in data['travelogs']:
        sentences = extractor.extract_from_text(
            travelog['content'],
            {
                'scenic_spot': travelog['scenic_spot'],
                'travelog_id': travelog['travelog_id']
            }
        )
        all_sentences.extend(sentences)
        print(f"  {travelog['scenic_spot']} - 游记{travelog['travelog_number']}: "
              f"找到 {len(sentences)} 个包含代词的句子")

    print(f"\n  总共找到 {len(all_sentences)} 个包含代词的句子")

    # 3. 保存原始提取结果
    output_path = f"{output_dir}/pronoun_sentences.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "total_sentences": len(all_sentences),
                "scenic_spots": list(set([s['scenic_spot'] for s in all_sentences])),
                "pronoun_types": PronounDictionary().get_all_pronouns()
            },
            "sentences": all_sentences
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  已保存: {output_path}")

    # 4. 自动指代消解
    print("\n[3/4] 进行自动指代消解...")
    resolver = NearestNounResolver()

    for sentence_data in all_sentences:
        auto_results = []
        for pronoun in sentence_data['pronouns']:
            result = resolver.resolve(
                sentence_data['sentence'],
                sentence_data.get('context', ''),  # 使用上下文
                pronoun,
                sentence_data['scenic_spot']
            )
            auto_results.append(result)

        sentence_data['auto_resolution'] = auto_results

    # 统计自动消解结果
    resolved_count = sum(1 for s in all_sentences
                        if any(r['antecedent'] for r in s.get('auto_resolution', [])))
    print(f"  成功消解: {resolved_count}/{len(all_sentences)} 个句子")

    # 5. 保存自动消解结果
    auto_output_path = f"{output_dir}/auto_resolution_results.json"
    with open(auto_output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "total_sentences": len(all_sentences),
                "resolved_count": resolved_count,
                "resolution_rate": f"{resolved_count/len(all_sentences)*100:.1f}%"
            },
            "sentences": all_sentences
        }, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {auto_output_path}")

    # 6. 生成统计报告
    print("\n[4/4] 生成统计报告...")
    stats = generate_statistics(all_sentences)

    stats_output_path = f"{output_dir}/statistics_report.json"
    with open(stats_output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {stats_output_path}")

    print("\n" + "=" * 60)
    print("处理完成！")
    print("=" * 60)

    return {
        "total_sentences": len(all_sentences),
        "resolved_count": resolved_count,
        "statistics": stats
    }


def generate_statistics(sentences: List[Dict]) -> Dict[str, Any]:
    """生成统计报告"""
    stats = {
        "pronoun_frequency": defaultdict(int),
        "pronoun_by_scenic_spot": defaultdict(lambda: defaultdict(int)),
        "resolution_success_rate": {},
        "sample_sentences": {}
    }

    # 统计代词频率
    for sentence in sentences:
        spot = sentence['scenic_spot']
        for pronoun in sentence.get('pronouns', []):
            pronoun_text = pronoun['pronoun']
            stats['pronoun_frequency'][pronoun_text] += 1
            stats['pronoun_by_scenic_spot'][spot][pronoun_text] += 1

    # 统计消解成功率
    total = len(sentences)
    resolved = sum(1 for s in sentences
                  if any(r.get('antecedent') for r in s.get('auto_resolution', [])))

    stats['resolution_success_rate'] = {
        "total": total,
        "resolved": resolved,
        "rate": f"{resolved/total*100:.1f}%" if total > 0 else "N/A"
    }

    # 选取示例句子
    for spot in ['九寨沟', '故宫', '黄山']:
        spot_sentences = [s for s in sentences if s['scenic_spot'] == spot]
        if spot_sentences:
            stats['sample_sentences'][spot] = spot_sentences[:3]  # 取前3个作为示例

    return {k: dict(v) if isinstance(v, dict) else v for k, v in stats.items()}


# =============================================================================
# 8. 手工标注模块
# =============================================================================

def create_annotation_template(output_dir: str):
    """
    创建手工标注模板

    生成一个Excel文件，方便手工标注
    """
    import pandas as pd

    # 读取提取结果
    with open(f'{output_dir}/pronoun_sentences.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 构建标注表格
    annotation_data = []

    for sentence in data['sentences']:
        for pronoun in sentence['pronouns']:
            annotation_data.append({
                'sentence_id': sentence['sentence_id'],
                'scenic_spot': sentence['scenic_spot'],
                'travelog_id': sentence['travelog_id'],
                'sentence': sentence['sentence'],
                'pronoun': pronoun['pronoun'],
                'pronoun_type': pronoun['type'],
                'manual_antecedent': '',  # 手工标注：先行词
                'confidence': '',         # 手工标注：置信度（high/medium/low）
                'notes': ''               # 手工标注：备注
            })

    # 保存为Excel
    df = pd.DataFrame(annotation_data)
    output_path = f'{output_dir}/annotation_template.xlsx'
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"\n  已生成手工标注模板: {output_path}")
    print(f"  请在该Excel文件中进行手工标注")

    return output_path


# =============================================================================
# 主程序入口
# =============================================================================

if __name__ == '__main__':
    import sys

    # 设置路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, '../task1_data_collection/data/data_cleaned.xlsx')
    output_dir = os.path.join(current_dir, 'output')

    # 执行主流程
    results = process_all_data(data_path, output_dir)

    # 创建手工标注模板
    print("\n生成手工标注模板...")
    create_annotation_template(output_dir)
