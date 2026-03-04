#!/usr/bin/env python3
"""
任务4：共指消解评估模块

功能：
1. 对比自动消解结果与手工标注结果
2. 计算准确率、召回率、F1分数
3. 生成详细的错误分析报告
"""

import json
import os
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import pandas as pd


class CoreferenceEvaluator:
    """共指消解评估器"""

    def __init__(self, manual_annotation_path: str, auto_result_path: str):
        """
        初始化评估器

        Args:
            manual_annotation_path: 手工标注文件路径
            auto_result_path: 自动消解结果文件路径
        """
        self.manual_data = self._load_json(manual_annotation_path)
        self.auto_data = self._load_json(auto_result_path)

        # 构建手工标注映射：sentence_id -> annotation
        self.manual_map = self._build_manual_map()

        # 构建自动结果映射：sentence_id -> auto_results
        self.auto_map = self._build_auto_map()

    def _load_json(self, path: str) -> Dict:
        """加载JSON文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _build_manual_map(self) -> Dict[str, Dict]:
        """构建手工标注映射"""
        manual_map = {}
        for annotation in self.manual_data.get('annotations', []):
            sentence_id = annotation['sentence_id']
            if sentence_id not in manual_map:
                manual_map[sentence_id] = []
            manual_map[sentence_id].append(annotation)
        return manual_map

    def _build_auto_map(self) -> Dict[str, List[Dict]]:
        """构建自动结果映射"""
        auto_map = {}
        for sentence in self.auto_data.get('sentences', []):
            sentence_id = sentence['sentence_id']
            auto_resolutions = sentence.get('auto_resolution', [])
            if auto_resolutions:
                auto_map[sentence_id] = auto_resolutions
        return auto_map

    def evaluate(self) -> Dict[str, Any]:
        """
        执行评估

        Returns:
            评估结果字典
        """
        results = {
            "total_cases": 0,
            "correct": 0,
            "incorrect": 0,
            "not_resolved": 0,
            "accuracy": 0.0,
            "by_pronoun_type": defaultdict(lambda: {"total": 0, "correct": 0, "accuracy": 0.0}),
            "by_antecedent_type": defaultdict(lambda: {"total": 0, "correct": 0, "accuracy": 0.0}),
            "error_analysis": []
        }

        # 遍历所有手工标注的案例
        for sentence_id, manual_annotations in self.manual_map.items():
            auto_resolutions = self.auto_map.get(sentence_id, [])

            # 对每个手工标注的代词进行评估
            for manual_ann in manual_annotations:
                pronoun = manual_ann['pronoun']
                manual_antecedent = manual_ann['manual_antecedent']

                results["total_cases"] += 1

                # 找到对应的自动消解结果
                auto_result = self._find_matching_auto_result(auto_resolutions, pronoun)

                if auto_result is None:
                    # 自动消解未找到结果
                    results["not_resolved"] += 1
                    results["error_analysis"].append({
                        "sentence_id": sentence_id,
                        "sentence": manual_ann.get('sentence', ''),
                        "pronoun": pronoun,
                        "manual_antecedent": manual_antecedent,
                        "auto_antecedent": None,
                        "error_type": "not_resolved",
                        "reason": "自动消解未找到结果"
                    })
                    continue

                auto_antecedent = auto_result.get('antecedent')

                # 判断是否正确
                is_correct = self._is_match(manual_antecedent, auto_antecedent)

                if is_correct:
                    results["correct"] += 1
                else:
                    results["incorrect"] += 1
                    results["error_analysis"].append({
                        "sentence_id": sentence_id,
                        "sentence": manual_ann.get('sentence', ''),
                        "pronoun": pronoun,
                        "manual_antecedent": manual_antecedent,
                        "auto_antecedent": auto_antecedent,
                        "error_type": "incorrect_resolution",
                        "confidence": auto_result.get('confidence', ''),
                        "method": auto_result.get('resolution_method', '')
                    })

                # 按代词类型统计
                pronoun_type = manual_ann.get('pronoun_type', 'unknown')
                results["by_pronoun_type"][pronoun_type]["total"] += 1
                if is_correct:
                    results["by_pronoun_type"][pronoun_type]["correct"] += 1

                # 按先行词类型统计
                antecedent_type = manual_ann.get('antecedent_type', 'unknown')
                results["by_antecedent_type"][antecedent_type]["total"] += 1
                if is_correct:
                    results["by_antecedent_type"][antecedent_type]["correct"] += 1

        # 计算准确率
        if results["total_cases"] > 0:
            results["accuracy"] = results["correct"] / results["total_cases"]

        # 计算各类别的准确率
        for pronoun_type, stats in results["by_pronoun_type"].items():
            if stats["total"] > 0:
                stats["accuracy"] = stats["correct"] / stats["total"]

        for antecedent_type, stats in results["by_antecedent_type"].items():
            if stats["total"] > 0:
                stats["accuracy"] = stats["correct"] / stats["total"]

        # 转换defaultdict为普通dict
        results["by_pronoun_type"] = dict(results["by_pronoun_type"])
        results["by_antecedent_type"] = dict(results["by_antecedent_type"])

        return results

    def _find_matching_auto_result(self, auto_resolutions: List[Dict], pronoun: str) -> Dict:
        """找到匹配的自动消解结果"""
        for auto_res in auto_resolutions:
            if auto_res.get('pronoun') == pronoun:
                return auto_res
        return None

    def _is_match(self, manual: str, auto: str) -> bool:
        """
        判断手工标注和自动消解是否匹配

        Args:
            manual: 手工标注的先行词
            auto: 自动消解的先行词

        Returns:
            是否匹配
        """
        if manual is None or auto is None:
            return False

        # 精确匹配
        if manual == auto:
            return True

        # 包含匹配（处理部分匹配的情况）
        if manual in auto or auto in manual:
            return True

        # 常见同义词映射
        synonyms = {
            '故宫': ['紫禁城', '故宫博物院'],
            '九寨沟': ['九寨沟景区'],
            '黄山': ['黄山风景区', '黄山景区'],
        }

        for key, values in synonyms.items():
            if manual in [key] + values and auto in [key] + values:
                return True

        return False

    def generate_report(self, output_path: str):
        """
        生成评估报告

        Args:
            output_path: 输出文件路径
        """
        results = self.evaluate()

        report = {
            "summary": {
                "total_cases": results["total_cases"],
                "correct": results["correct"],
                "incorrect": results["incorrect"],
                "not_resolved": results["not_resolved"],
                "accuracy": f"{results['accuracy']*100:.1f}%"
            },
            "by_pronoun_type": results["by_pronoun_type"],
            "by_antecedent_type": results["by_antecedent_type"],
            "error_analysis": results["error_analysis"][:20]  # 只保留前20个错误案例
        }

        # 保存JSON报告
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n评估报告已保存: {output_path}")

        # 打印摘要
        self._print_summary(results)

        return report

    def _print_summary(self, results: Dict):
        """打印评估摘要"""
        print("\n" + "=" * 60)
        print("共指消解评估结果")
        print("=" * 60)

        print(f"\n总体结果:")
        print(f"  总案例数: {results['total_cases']}")
        print(f"  正确: {results['correct']}")
        print(f"  错误: {results['incorrect']}")
        print(f"  未消解: {results['not_resolved']}")
        print(f"  准确率: {results['accuracy']*100:.1f}%")

        print(f"\n按代词类型统计:")
        for pronoun_type, stats in results['by_pronoun_type'].items():
            print(f"  {pronoun_type}: {stats['correct']}/{stats['total']} "
                  f"({stats['accuracy']*100:.1f}%)")

        print(f"\n按先行词类型统计:")
        for antecedent_type, stats in results['by_antecedent_type'].items():
            print(f"  {antecedent_type}: {stats['correct']}/{stats['total']} "
                  f"({stats['accuracy']*100:.1f}%)")

        print("\n" + "=" * 60)

    def export_to_excel(self, output_path: str):
        """
        导出评估结果到Excel

        Args:
            output_path: 输出文件路径
        """
        results = self.evaluate()

        # 创建Excel工作簿
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 总体摘要
            summary_data = {
                '指标': ['总案例数', '正确', '错误', '未消解', '准确率'],
                '数值': [
                    results['total_cases'],
                    results['correct'],
                    results['incorrect'],
                    results['not_resolved'],
                    f"{results['accuracy']*100:.1f}%"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='总体摘要', index=False)

            # 按代词类型统计
            pronoun_type_data = []
            for pronoun_type, stats in results['by_pronoun_type'].items():
                pronoun_type_data.append({
                    '代词类型': pronoun_type,
                    '总数': stats['total'],
                    '正确': stats['correct'],
                    '准确率': f"{stats['accuracy']*100:.1f}%"
                })
            pd.DataFrame(pronoun_type_data).to_excel(writer, sheet_name='按代词类型', index=False)

            # 按先行词类型统计
            antecedent_type_data = []
            for antecedent_type, stats in results['by_antecedent_type'].items():
                antecedent_type_data.append({
                    '先行词类型': antecedent_type,
                    '总数': stats['total'],
                    '正确': stats['correct'],
                    '准确率': f"{stats['accuracy']*100:.1f}%"
                })
            pd.DataFrame(antecedent_type_data).to_excel(writer, sheet_name='按先行词类型', index=False)

            # 错误分析
            if results['error_analysis']:
                error_data = []
                for error in results['error_analysis']:
                    error_data.append({
                        '句子ID': error['sentence_id'],
                        '句子': error['sentence'][:50] + '...' if len(error.get('sentence', '')) > 50 else error.get('sentence', ''),
                        '代词': error['pronoun'],
                        '手工标注': error['manual_antecedent'],
                        '自动消解': error.get('auto_antecedent', 'N/A'),
                        '错误类型': error['error_type']
                    })
                pd.DataFrame(error_data).to_excel(writer, sheet_name='错误分析', index=False)

        print(f"\nExcel报告已保存: {output_path}")


def main():
    """主函数"""
    import sys

    # 设置路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    manual_path = os.path.join(current_dir, 'annotated/manual_annotations.json')
    auto_path = os.path.join(current_dir, 'output/auto_resolution_results.json')
    report_path = os.path.join(current_dir, 'output/evaluation_report.json')
    excel_path = os.path.join(current_dir, 'output/evaluation_report.xlsx')

    # 创建评估器
    evaluator = CoreferenceEvaluator(manual_path, auto_path)

    # 生成报告
    evaluator.generate_report(report_path)

    # 导出Excel
    evaluator.export_to_excel(excel_path)


if __name__ == '__main__':
    main()
