#!/usr/bin/env python3
"""
任务5：条件性游览建议的抽取 - 评估模块

功能：
1. 对比自动提取结果与手工标注
2. 计算精确率、召回率、F1值
3. 按条件句式类型分析准确率
4. 生成评估报告（JSON + Excel）
"""

import os
import json
import pandas as pd
from typing import Dict, List, Any, Tuple
from collections import defaultdict


# =============================================================================
# 1. 条件性建议评估器
# =============================================================================

class ConditionalAdviceEvaluator:
    """条件性建议评估器"""

    def __init__(self, manual_path: str, auto_path: str):
        """
        初始化评估器

        Args:
            manual_path: 手工标注数据路径
            auto_path: 自动提取结果路径
        """
        with open(manual_path, 'r', encoding='utf-8') as f:
            self.manual_data = json.load(f)

        with open(auto_path, 'r', encoding='utf-8') as f:
            auto_data = json.load(f)
            self.auto_list = auto_data.get('conditional_advice', [])

        self.manual_list = self.manual_data.get('annotations', [])

    def evaluate(self) -> Dict[str, Any]:
        """
        执行评估

        Returns:
            评估结果
        """
        print("\n[评估分析]")

        # 构建手工标注的映射
        manual_by_id = {item['advice_id']: item for item in self.manual_list}

        # 统计
        total_manual = len(self.manual_list)
        total_auto = len(self.auto_list)

        # 匹配统计
        correct = 0
        incorrect = 0
        partial = 0
        not_found = []

        # 按类型统计
        by_condition_type = defaultdict(lambda: {'correct': 0, 'total': 0})
        by_pattern_type = defaultdict(lambda: {'correct': 0, 'total': 0})

        # 错误分析
        error_types = defaultdict(int)
        error_examples = []

        for manual_item in self.manual_list:
            advice_id = manual_item['advice_id']
            is_valid = manual_item.get('is_valid', 'yes')

            if is_valid == 'no':
                continue

            cond_type = manual_item.get('condition_type', 'other')
            pattern_type = manual_item.get('pattern_type', 'unknown')

            by_condition_type[cond_type]['total'] += 1
            by_pattern_type[pattern_type]['total'] += 1

            # 查找对应的自动提取结果
            auto_item = None
            for item in self.auto_list:
                if item['advice_id'] == advice_id:
                    auto_item = item
                    break

            if auto_item is None:
                not_found.append(advice_id)
                continue

            # 比较结果
            comparison = self._compare_advice(manual_item, auto_item)

            if comparison['is_correct']:
                correct += 1
                by_condition_type[cond_type]['correct'] += 1
                by_pattern_type[pattern_type]['correct'] += 1
            elif comparison['is_partial']:
                partial += 1
                error_types['partial'] += 1
            else:
                incorrect += 1
                error_types[comparison['error_type']] += 1

                if len(error_examples) < 10:
                    error_examples.append({
                        'advice_id': advice_id,
                        'manual_condition': manual_item.get('condition_text', ''),
                        'auto_condition': auto_item['condition']['text'],
                        'manual_advice': manual_item.get('advice_text', ''),
                        'auto_advice': auto_item['advice']['text'],
                        'error_type': comparison['error_type']
                    })

        # 计算指标
        total_evaluated = correct + incorrect + partial
        precision = correct / total_auto if total_auto > 0 else 0
        recall = correct / total_manual if total_manual > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # 按类型计算准确率
        type_accuracy = {}
        for cond_type, stats in by_condition_type.items():
            if stats['total'] > 0:
                type_accuracy[cond_type] = {
                    'accuracy': round(stats['correct'] / stats['total'] * 100, 1),
                    'correct': stats['correct'],
                    'total': stats['total']
                }

        pattern_accuracy = {}
        for pattern_type, stats in by_pattern_type.items():
            if stats['total'] > 0:
                pattern_accuracy[pattern_type] = {
                    'accuracy': round(stats['correct'] / stats['total'] * 100, 1),
                    'correct': stats['correct'],
                    'total': stats['total']
                }

        result = {
            'overall_metrics': {
                'total_manual_annotations': total_manual,
                'total_auto_extracted': total_auto,
                'correct': correct,
                'incorrect': incorrect,
                'partial': partial,
                'not_found': len(not_found),
                'precision': round(precision * 100, 1),
                'recall': round(recall * 100, 1),
                'f1_score': round(f1_score * 100, 1)
            },
            'by_condition_type': type_accuracy,
            'by_pattern_type': pattern_accuracy,
            'error_analysis': {
                'error_types': dict(error_types),
                'error_examples': error_examples
            }
        }

        return result

    def _compare_advice(self, manual: Dict, auto: Dict) -> Dict[str, Any]:
        """
        比较手工标注和自动提取结果

        Args:
            manual: 手工标注数据
            auto: 自动提取数据

        Returns:
            比较结果
        """
        manual_cond = manual.get('condition_text', '').strip()
        auto_cond = auto['condition']['text'].strip()

        manual_adv = manual.get('advice_text', '').strip()
        auto_adv = auto['advice']['text'].strip()

        # 检查条件类型是否匹配
        manual_type = manual.get('condition_type', '')
        auto_type = auto['condition']['type']

        # 完全匹配
        if (manual_cond == auto_cond or manual_cond in auto_cond or auto_cond in manual_cond) and \
           (manual_adv == auto_adv or manual_adv in auto_adv or auto_adv in manual_adv):
            return {'is_correct': True, 'is_partial': False, 'error_type': None}

        # 部分匹配
        if manual_type == auto_type:
            return {'is_correct': False, 'is_partial': True, 'error_type': 'partial_match'}

        # 错误类型分析
        if manual_type != auto_type:
            return {'is_correct': False, 'is_partial': False, 'error_type': 'condition_type_mismatch'}
        elif manual_adv not in auto_adv and auto_adv not in manual_adv:
            return {'is_correct': False, 'is_partial': False, 'error_type': 'advice_mismatch'}
        else:
            return {'is_correct': False, 'is_partial': False, 'error_type': 'other'}

    def generate_report(self, output_path: str):
        """
        生成评估报告

        Args:
            output_path: 输出文件路径
        """
        result = self.evaluate()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"  已保存评估报告: {output_path}")

        # 打印摘要
        print("\n[评估摘要]")
        metrics = result['overall_metrics']
        print(f"  精确率: {metrics['precision']}%")
        print(f"  召回率: {metrics['recall']}%")
        print(f"  F1分数: {metrics['f1_score']}%")
        print(f"  正确: {metrics['correct']}, 错误: {metrics['incorrect']}, 部分: {metrics['partial']}")

    def export_to_excel(self, output_path: str):
        """
        导出评估报告到Excel

        Args:
            output_path: 输出文件路径
        """
        result = self.evaluate()

        # 创建Excel文件
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 总体指标
            overall_df = pd.DataFrame([result['overall_metrics']])
            overall_df.to_excel(writer, sheet_name='总体指标', index=False)

            # 按条件类型
            if result['by_condition_type']:
                condition_df = pd.DataFrame(result['by_condition_type']).T
                condition_df.to_excel(writer, sheet_name='按条件类型')

            # 按句式模式
            if result['by_pattern_type']:
                pattern_df = pd.DataFrame(result['by_pattern_type']).T
                pattern_df.to_excel(writer, sheet_name='按句式模式')

            # 错误分析
            if result['error_analysis']['error_examples']:
                error_df = pd.DataFrame(result['error_analysis']['error_examples'])
                error_df.to_excel(writer, sheet_name='错误示例', index=False)

            # 错误类型统计
            error_types_df = pd.DataFrame([result['error_analysis']['error_types']]).T
            error_types_df.columns = ['数量']
            error_types_df.to_excel(writer, sheet_name='错误类型统计')

        print(f"  已保存Excel报告: {output_path}")


# =============================================================================
# 2. 创建评估模板
# =============================================================================

def create_evaluation_template(auto_data_path: str, output_path: str):
    """
    创建评估模板

    Args:
        auto_data_path: 自动提取结果路径
        output_path: 输出模板路径
    """
    with open(auto_data_path, 'r', encoding='utf-8') as f:
        auto_data = json.load(f)

    advice_list = auto_data.get('conditional_advice', [])

    # 构建模板数据
    template_data = []
    for advice in advice_list:
        template_data.append({
            'advice_id': advice['advice_id'],
            'scenic_spot': advice['scenic_spot'],
            'sentence': advice['sentence'],
            'condition_text': advice['condition']['text'],
            'condition_type': advice['condition']['type'],
            'advice_text': advice['advice']['text'],
            'is_valid': '',  # 待填写: yes/no/partial
            'manual_condition': '',  # 待填写
            'manual_advice': '',  # 待填写
            'confidence': advice['confidence'],
            'notes': ''
        })

    df = pd.DataFrame(template_data)
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"  已创建评估模板: {output_path}")


# =============================================================================
# 3. 主程序
# =============================================================================

if __name__ == '__main__':
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 默认路径
    auto_path = os.path.join(current_dir, 'output/conditional_advice.json')
    manual_path = os.path.join(current_dir, 'output/annotated/manual_annotations.json')
    report_path = os.path.join(current_dir, 'output/evaluation_report.json')
    excel_path = os.path.join(current_dir, 'output/evaluation_report.xlsx')

    # 检查自动提取结果是否存在
    if not os.path.exists(auto_path):
        print(f"错误: 自动提取结果不存在: {auto_path}")
        print("请先运行处理器")
        sys.exit(1)

    # 如果没有手工标注，创建模板
    if not os.path.exists(manual_path):
        print("手工标注不存在，创建评估模板...")
        template_path = os.path.join(current_dir, 'output/annotation_template.xlsx')
        create_evaluation_template(auto_path, template_path)
        print("\n请填写 annotation_template.xlsx 进行手工标注后，")
        print("将其保存为 output/annotated/manual_annotations.json 后再运行评估")
    else:
        # 执行评估
        print("=" * 60)
        print("任务5：条件性游览建议的抽取 - 评估分析")
        print("=" * 60)

        evaluator = ConditionalAdviceEvaluator(manual_path, auto_path)
        evaluator.generate_report(report_path)
        evaluator.export_to_excel(excel_path)

        print("\n评估完成！")
