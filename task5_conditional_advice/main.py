#!/usr/bin/env python3
"""
任务5：条件性游览建议的抽取 - 主入口文件

功能：
1. 从游记中提取条件-建议对
2. 分析条件类型和游客类型
3. 生成可视化报告
4. 评估提取结果

使用方法:
    python3 main.py              # 运行完整流程
    python3 main.py --extract    # 仅提取条件建议
    python3 main.py --analyze    # 仅分析结果
    python3 main.py --visualize  # 仅生成可视化
    python3 main.py --evaluate   # 仅评估结果
"""

import os
import sys
import argparse


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='任务5：条件性游览建议的抽取',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    python3 main.py              # 运行完整流程
    python3 main.py --extract    # 仅提取条件建议
    python3 main.py --analyze    # 仅分析结果
    python3 main.py --visualize  # 仅生成可视化
    python3 main.py --evaluate   # 仅评估结果
        '''
    )

    parser.add_argument('--extract', action='store_true', help='仅提取条件建议')
    parser.add_argument('--analyze', action='store_true', help='仅分析结果')
    parser.add_argument('--visualize', action='store_true', help='仅生成可视化')
    parser.add_argument('--evaluate', action='store_true', help='仅评估结果')
    parser.add_argument('--all', action='store_true', help='运行完整流程（默认）')

    args = parser.parse_args()

    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, '../task1_data_collection/data/data_cleaned.xlsx')
    output_dir = os.path.join(current_dir, 'output')

    # 检查数据文件是否存在
    if not os.path.exists(data_path):
        print(f"错误: 数据文件不存在: {data_path}")
        print("请确保 task1_data_collection/data/data_cleaned.xlsx 存在")
        sys.exit(1)

    # 如果没有指定任何选项，运行完整流程
    run_all = not (args.extract or args.analyze or args.visualize or args.evaluate)

    print("=" * 60)
    print("任务5：条件性游览建议的抽取")
    print("=" * 60)

    # 1. 提取条件建议
    if run_all or args.extract:
        from processor import process_all_data, create_annotation_template

        print("\n[阶段 1/4] 提取条件性建议...")
        results = process_all_data(data_path, output_dir)

        # 创建标注模板
        create_annotation_template(output_dir)

    # 2. 分析结果
    if run_all or args.analyze:
        from analyzer import analyze_all_data

        print("\n[阶段 2/4] 分析提取结果...")
        analyze_all_data(output_dir, output_dir)

    # 3. 生成可视化
    if run_all or args.visualize:
        # 检查必要的文件是否存在
        stats_path = f"{output_dir}/statistics_report.json"
        visitor_path = f"{output_dir}/visitor_analysis.json"

        if not os.path.exists(stats_path) or not os.path.exists(visitor_path):
            print("  跳过可视化（缺少分析数据，请先运行 --analyze）")
        else:
            from visualizer import ConditionalAdviceVisualizer

            print("\n[阶段 3/4] 生成可视化图表...")
            viz_output_dir = f"{output_dir}/visualizations"
            os.makedirs(viz_output_dir, exist_ok=True)

            visualizer = ConditionalAdviceVisualizer(stats_path, visitor_path)
            visualizer.create_all_visualizations(viz_output_dir)

    # 4. 评估结果
    if run_all or args.evaluate:
        from evaluator import ConditionalAdviceEvaluator, create_evaluation_template

        print("\n[阶段 4/4] 评估提取结果...")

        auto_path = f"{output_dir}/conditional_advice.json"
        manual_path = f"{output_dir}/annotated/manual_annotations.json"
        report_path = f"{output_dir}/evaluation_report.json"
        excel_path = f"{output_dir}/evaluation_report.xlsx"

        if not os.path.exists(auto_path):
            print("  跳过评估（缺少提取数据，请先运行 --extract）")
        elif not os.path.exists(manual_path):
            print("  手工标注不存在，创建评估模板...")
            template_path = f"{output_dir}/annotation_template.xlsx"
            create_evaluation_template(auto_path, template_path)
            print("\n  请填写 annotation_template.xlsx 进行手工标注")
            print("  标注完成后，将其保存为 output/annotated/manual_annotations.json")
            print("  然后运行: python3 main.py --evaluate")
        else:
            evaluator = ConditionalAdviceEvaluator(manual_path, auto_path)
            evaluator.generate_report(report_path)
            evaluator.export_to_excel(excel_path)

    print("\n" + "=" * 60)
    print("任务5完成！")
    print("=" * 60)

    print("\n输出文件:")
    print("  - output/conditional_advice.json     : 提取的条件性建议")
    print("  - output/condition_mapping.json     : 条件→建议映射表")
    print("  - output/visitor_analysis.json      : 游客类型分析")
    print("  - output/statistics_report.json     : 统计报告")
    print("  - output/visualizations/            : 可视化图表")

    if os.path.exists(f"{output_dir}/evaluation_report.json"):
        print("  - output/evaluation_report.json    : 评估报告")
        print("  - output/evaluation_report.xlsx    : Excel评估报告")

    print("\n")


if __name__ == '__main__':
    main()
