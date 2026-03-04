#!/usr/bin/env python3
"""
任务4：程序性知识的共指消解 - 主入口文件

功能：
1. 从游记中提取包含代词的句子
2. 进行自动指代消解
3. 评估消解结果
4. 生成可视化报告

使用方法:
    python3 main.py              # 运行完整流程
    python3 main.py --extract    # 仅提取代词
    python3 main.py --evaluate   # 仅评估结果
    python3 main.py --visualize  # 仅生成可视化
"""

import os
import sys
import argparse
from coref_extractor import process_all_data, create_annotation_template
from evaluator import CoreferenceEvaluator
from visualizer import CoreferenceVisualizer


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='任务4：程序性知识的共指消解')
    parser.add_argument('--extract', action='store_true', help='仅提取代词')
    parser.add_argument('--evaluate', action='store_true', help='仅评估结果')
    parser.add_argument('--visualize', action='store_true', help='仅生成可视化')
    parser.add_argument('--all', action='store_true', help='运行完整流程（默认）')

    args = parser.parse_args()

    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, '../task1_data_collection/data/data_cleaned.xlsx')
    output_dir = os.path.join(current_dir, 'output')

    # 如果没有指定任何选项，运行完整流程
    run_all = not (args.extract or args.evaluate or args.visualize)

    print("=" * 60)
    print("任务4：程序性知识的共指消解")
    print("=" * 60)

    # 1. 提取代词和自动消解
    if run_all or args.extract:
        print("\n[步骤 1/3] 提取代词并进行自动消解...")
        process_all_data(data_path, output_dir)

    # 2. 评估结果
    if run_all or args.evaluate:
        print("\n[步骤 2/3] 评估自动消解结果...")
        manual_path = os.path.join(current_dir, 'annotated/manual_annotations.json')
        auto_path = os.path.join(current_dir, 'output/auto_resolution_results.json')
        report_path = os.path.join(current_dir, 'output/evaluation_report.json')
        excel_path = os.path.join(current_dir, 'output/evaluation_report.xlsx')

        evaluator = CoreferenceEvaluator(manual_path, auto_path)
        evaluator.generate_report(report_path)
        evaluator.export_to_excel(excel_path)

    # 3. 生成可视化
    if run_all or args.visualize:
        print("\n[步骤 3/3] 生成可视化图表...")
        stats_path = os.path.join(current_dir, 'output/statistics_report.json')
        eval_path = os.path.join(current_dir, 'output/evaluation_report.json')
        viz_output_dir = os.path.join(current_dir, 'output/visualizations')

        visualizer = CoreferenceVisualizer(stats_path, eval_path)
        visualizer.create_all_visualizations(viz_output_dir)

    print("\n" + "=" * 60)
    print("任务4完成！")
    print("=" * 60)

    print("\n输出文件:")
    print("  - output/pronoun_sentences.json       : 提取的包含代词的句子")
    print("  - output/auto_resolution_results.json : 自动消解结果")
    print("  - output/statistics_report.json       : 统计报告")
    print("  - output/evaluation_report.json       : 评估报告")
    print("  - output/evaluation_report.xlsx       : Excel格式评估报告")
    print("  - output/visualizations/             : 可视化图表")
    print("\n")


if __name__ == '__main__':
    main()
