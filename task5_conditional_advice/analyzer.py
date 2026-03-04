#!/usr/bin/env python3
"""
任务5：条件性游览建议的抽取 - 分析模块

功能：
1. 分析条件类型分布统计
2. 分析不同游客类型的建议差异
3. 生成游客类型对比分析
"""

import os
import json
import pandas as pd
from typing import Dict, List, Any
from collections import Counter, defaultdict


# =============================================================================
# 1. 条件统计分析器
# =============================================================================

class ConditionStatisticsAnalyzer:
    """条件统计分析器"""

    def __init__(self, advice_data_path: str):
        """
        初始化分析器

        Args:
            advice_data_path: 条件建议数据文件路径
        """
        with open(advice_data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.advice_list = self.data.get('conditional_advice', [])
        self.condition_mapping = self.data.get('condition_mapping', {})

    def analyze_by_condition_type(self) -> Dict[str, Any]:
        """
        按条件类型分析

        Returns:
            条件类型分析结果
        """
        type_stats = defaultdict(lambda: {
            'count': 0,
            'conditions': {},
            'advice_examples': []
        })

        for advice in self.advice_list:
            cond_type = advice['condition']['type']
            cond_text = advice['condition']['normalized']
            advice_text = advice['advice']['text']

            type_stats[cond_type]['count'] += 1

            if cond_text not in type_stats[cond_type]['conditions']:
                type_stats[cond_type]['conditions'][cond_text] = {
                    'count': 0,
                    'advice_list': []
                }

            type_stats[cond_type]['conditions'][cond_text]['count'] += 1
            type_stats[cond_type]['conditions'][cond_text]['advice_list'].append(advice_text)

            # 保存示例（最多3个）
            if len(type_stats[cond_type]['advice_examples']) < 3:
                type_stats[cond_type]['advice_examples'].append({
                    'condition': cond_text,
                    'advice': advice_text,
                    'sentence': advice['sentence']
                })

        # 转换为普通字典并排序
        result = {}
        for cond_type, stats in sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            # 对条件按数量排序
            sorted_conditions = dict(sorted(
                stats['conditions'].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            ))
            result[cond_type] = {
                'count': stats['count'],
                'conditions': sorted_conditions,
                'advice_examples': stats['advice_examples']
            }

        return result

    def analyze_by_scenic_spot(self) -> Dict[str, Any]:
        """
        按景区分析

        Returns:
            景区分析结果
        """
        spot_stats = defaultdict(lambda: {
            'total_advice': 0,
            'condition_types': defaultdict(int),
            'top_conditions': []
        })

        for advice in self.advice_list:
            spot = advice['scenic_spot']
            cond_type = advice['condition']['type']
            cond_text = advice['condition']['normalized']

            spot_stats[spot]['total_advice'] += 1
            spot_stats[spot]['condition_types'][cond_type] += 1

            # 收集条件文本
            spot_stats[spot]['top_conditions'].append(cond_text)

        # 处理每个景区的数据
        result = {}
        for spot, stats in spot_stats.items():
            # 统计最常见的条件
            condition_counter = Counter(stats['top_conditions'])

            result[spot] = {
                'total_advice': stats['total_advice'],
                'condition_types': dict(stats['condition_types']),
                'top_conditions': condition_counter.most_common(10)
            }

        return result

    def analyze_pattern_distribution(self) -> Dict[str, Any]:
        """
        分析句式模式分布

        Returns:
            句式模式分析结果
        """
        pattern_stats = defaultdict(lambda: {
            'count': 0,
            'condition_types': defaultdict(int),
            'examples': []
        })

        for advice in self.advice_list:
            pattern = advice['pattern_type']
            cond_type = advice['condition']['type']

            pattern_stats[pattern]['count'] += 1
            pattern_stats[pattern]['condition_types'][cond_type] += 1

            # 保存示例
            if len(pattern_stats[pattern]['examples']) < 3:
                pattern_stats[pattern]['examples'].append({
                    'condition': advice['condition']['text'],
                    'advice': advice['advice']['text'],
                    'sentence': advice['sentence']
                })

        result = {}
        for pattern, stats in sorted(pattern_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            result[pattern] = {
                'count': stats['count'],
                'condition_types': dict(stats['condition_types']),
                'examples': stats['examples']
            }

        return result


# =============================================================================
# 2. 游客类型分析器
# =============================================================================

class VisitorTypeAnalyzer:
    """游客类型分析器"""

    def __init__(self, advice_data_path: str):
        """
        初始化分析器

        Args:
            advice_data_path: 条件建议数据文件路径
        """
        with open(advice_data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.advice_list = self.data.get('conditional_advice', [])

    def analyze_by_visitor_type(self) -> Dict[str, Any]:
        """
        按游客类型分析

        Returns:
            游客类型分析结果
        """
        type_stats = defaultdict(lambda: {
            'count': 0,
            'conditions': [],
            'advices': [],
            'scenic_spots': defaultdict(int),
            'examples': []
        })

        for advice in self.advice_list:
            visitor_type = advice.get('visitor_type', 'general')
            cond_text = advice['condition']['normalized']
            cond_type = advice['condition']['type']
            advice_text = advice['advice']['text']
            spot = advice['scenic_spot']

            type_stats[visitor_type]['count'] += 1
            type_stats[visitor_type]['conditions'].append(cond_text)
            type_stats[visitor_type]['advices'].append(advice_text)
            type_stats[visitor_type]['scenic_spots'][spot] += 1

            # 保存示例
            if len(type_stats[visitor_type]['examples']) < 5:
                type_stats[visitor_type]['examples'].append({
                    'condition': cond_text,
                    'advice': advice_text,
                    'sentence': advice['sentence']
                })

        # 统计最常见的条件和建议
        result = {}
        for vtype, stats in sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            condition_counter = Counter(stats['conditions'])
            advice_counter = Counter(stats['advices'])

            # 提取高频条件类型
            condition_types = defaultdict(int)
            for advice in self.advice_list:
                if advice.get('visitor_type') == vtype:
                    condition_types[advice['condition']['type']] += 1

            result[vtype] = {
                'count': stats['count'],
                'common_conditions': [c for c, _ in condition_counter.most_common(10)],
                'common_advices': [a for a, _ in advice_counter.most_common(10)],
                'condition_type_distribution': dict(condition_types),
                'scenic_spot_distribution': dict(stats['scenic_spots']),
                'examples': stats['examples']
            }

        # 任务重点类型：亲子/老人/情侣。即使样本为0也保留，便于横向比较。
        focus_types = ['family', 'elderly', 'couple']
        for vtype in focus_types:
            if vtype not in result:
                result[vtype] = {
                    'count': 0,
                    'common_conditions': [],
                    'common_advices': [],
                    'condition_type_distribution': {},
                    'scenic_spot_distribution': {},
                    'examples': []
                }

        return result

    def compare_visitor_types(self) -> Dict[str, Any]:
        """
        对比不同游客类型

        Returns:
            游客类型对比结果
        """
        type_analysis = self.analyze_by_visitor_type()

        # 获取主要游客类型：优先亲子/老人/情侣，再补充高频类型
        preferred_types = ['family', 'elderly', 'couple']
        main_types = [t for t in preferred_types if t in type_analysis]

        extra_types = [t for t in type_analysis.keys() if t not in main_types and t != 'general']
        main_types.extend(extra_types[:max(0, 4 - len(main_types))])

        if len(main_types) < 2 and 'general' in type_analysis:
            main_types.append('general')

        comparisons = {}

        # 两两对比
        for i, type1 in enumerate(main_types):
            for type2 in main_types[i+1:]:
                comparison_key = f"{type1}_vs_{type2}"

                advices1 = set(type_analysis[type1]['common_advices'])
                advices2 = set(type_analysis[type2]['common_advices'])

                shared = list(advices1 & advices2)
                unique_to_1 = list(advices1 - advices2)
                unique_to_2 = list(advices2 - advices1)

                comparisons[comparison_key] = {
                    'type1': type1,
                    'type2': type2,
                    'shared_advice': shared[:10],  # 最多10个
                    'unique_to_type1': unique_to_1[:10],
                    'unique_to_type2': unique_to_2[:10]
                }

        # 按条件类型对比
        condition_type_comparison = {}
        all_condition_types = sorted({
            cond_type
            for stats in type_analysis.values()
            for cond_type in stats.get('condition_type_distribution', {}).keys()
        })
        if not all_condition_types:
            all_condition_types = ['time', 'weather', 'crowd', 'physical', 'budget']

        for cond_type in all_condition_types:
            condition_type_comparison[cond_type] = {}
            for vtype in main_types:
                count = type_analysis[vtype]['condition_type_distribution'].get(cond_type, 0)
                total = type_analysis[vtype]['count']
                percentage = round(count / total * 100, 1) if total > 0 else 0
                condition_type_comparison[cond_type][vtype] = {
                    'count': count,
                    'percentage': percentage
                }

        return {
            'pairwise_comparisons': comparisons,
            'condition_type_comparison': condition_type_comparison,
            'main_types': main_types
        }


# =============================================================================
# 3. 主分析流程
# =============================================================================

def analyze_all_data(input_dir: str, output_dir: str) -> Dict[str, Any]:
    """
    运行所有分析

    Args:
        input_dir: 输入目录（包含 conditional_advice.json）
        output_dir: 输出目录

    Returns:
        分析结果
    """
    print("=" * 60)
    print("任务5：条件性游览建议的抽取 - 数据分析")
    print("=" * 60)

    advice_data_path = f"{input_dir}/conditional_advice.json"

    if not os.path.exists(advice_data_path):
        print(f"错误: 数据文件不存在: {advice_data_path}")
        print("请先运行处理器生成数据")
        return {}

    # 1. 条件统计分析
    print("\n[步骤 1/3] 条件统计分析...")
    condition_analyzer = ConditionStatisticsAnalyzer(advice_data_path)

    by_condition = condition_analyzer.analyze_by_condition_type()
    by_spot = condition_analyzer.analyze_by_scenic_spot()
    pattern_dist = condition_analyzer.analyze_pattern_distribution()

    print(f"  找到 {len(by_condition)} 种条件类型")
    for cond_type, stats in by_condition.items():
        print(f"    - {cond_type}: {stats['count']} 条")

    # 2. 游客类型分析
    print("\n[步骤 2/3] 游客类型分析...")
    visitor_analyzer = VisitorTypeAnalyzer(advice_data_path)

    visitor_analysis = visitor_analyzer.analyze_by_visitor_type()
    visitor_comparison = visitor_analyzer.compare_visitor_types()

    print(f"  找到 {len(visitor_analysis)} 种游客类型")
    for vtype, stats in visitor_analysis.items():
        print(f"    - {vtype}: {stats['count']} 条建议")

    # 3. 保存结果
    print("\n[步骤 3/3] 保存分析结果...")

    # 构建完整的分析报告
    analysis_report = {
        "condition_analysis": {
            "by_type": by_condition,
            "by_scenic_spot": by_spot,
            "pattern_distribution": pattern_dist
        },
        "visitor_type_analysis": {
            "by_type": visitor_analysis,
            "comparison": visitor_comparison
        },
        "summary": {
            "total_condition_types": len(by_condition),
            "total_visitor_types": len(visitor_analysis),
            "main_visitor_types": visitor_comparison.get('main_types', [])
        }
    }

    # 保存游客分析结果
    visitor_output_path = f"{output_dir}/visitor_analysis.json"
    with open(visitor_output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {visitor_output_path}")

    print("\n" + "=" * 60)
    print("数据分析完成！")
    print("=" * 60)

    return analysis_report


# =============================================================================
# 4. 主程序
# =============================================================================

if __name__ == '__main__':
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(current_dir, 'output')
    output_dir = input_dir

    results = analyze_all_data(input_dir, output_dir)

    if results:
        print("\n分析完成！")
        print(f"游客类型: {', '.join(results['visitor_type_analysis']['comparison'].get('main_types', []))}")
