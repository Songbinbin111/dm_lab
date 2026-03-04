#!/usr/bin/env python3
"""
任务6：多源程序性知识的融合与可视化 - 主入口文件

功能：
1. 数据加载（task2/3/5输出）
2. 知识融合（官方路线+游客POI+条件建议）
3. 知识图谱构建
4. 可视化输出

使用方法:
    python3 main.py              # 运行完整流程
    python3 main.py --fusion     # 仅执行知识融合
    python3 main.py --build      # 仅构建知识图谱
    python3 main.py --visualize  # 仅生成可视化
    python3 main.py --spot 九寨沟  # 处理指定景区
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='任务6：多源程序性知识的融合与可视化',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    python3 main.py              # 运行完整流程
    python3 main.py --fusion     # 仅执行知识融合
    python3 main.py --build      # 仅构建知识图谱
    python3 main.py --visualize  # 仅生成可视化
    python3 main.py --spot 九寨沟  # 处理指定景区
        '''
    )

    parser.add_argument('--fusion', action='store_true', help='仅执行知识融合')
    parser.add_argument('--build', action='store_true', help='仅构建知识图谱')
    parser.add_argument('--visualize', action='store_true', help='仅生成可视化')
    parser.add_argument('--spot', type=str, help='指定景区名称（九寨沟/故宫/黄山）')
    parser.add_argument('--all', action='store_true', help='运行完整流程（默认）')

    args = parser.parse_args()

    current_dir = Path(__file__).parent.absolute()
    project_root = current_dir.parent
    output_dir = current_dir / 'output'
    graph_output_dir = output_dir / 'knowledge_graph'
    viz_output_dir = output_dir / 'visualizations'

    graph_output_dir.mkdir(parents=True, exist_ok=True)
    viz_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import networkx  # noqa: F401
    except ImportError:
        print("错误: 需要安装 networkx")
        print("安装命令: pip install networkx")
        sys.exit(1)

    run_all = not (args.fusion or args.build or args.visualize)

    print("=" * 60)
    print("任务6：多源程序性知识的融合与可视化")
    print("=" * 60)

    if args.spot:
        spots = [args.spot]
        print(f"\n处理指定景区: {args.spot}")
    else:
        spots = ['九寨沟', '故宫', '黄山']
        print(f"\n处理所有景区: {', '.join(spots)}")

    from data_loader import MultiSourceDataLoader
    from knowledge_fusion import KnowledgeFusionEngine
    from graph_builder import KnowledgeGraphBuilder
    from visualizer import KnowledgeGraphVisualizer

    loader = MultiSourceDataLoader(str(project_root))

    available_spots = loader.get_available_spots()
    print(f"可用的景区: {', '.join(available_spots)}")

    valid_spots = [s for s in spots if s in available_spots]
    if not valid_spots:
        print("\n错误: 没有可处理的景区")
        print("请确保task2、task3、task5的输出文件存在")
        sys.exit(1)

    invalid_spots = set(spots) - set(valid_spots)
    if invalid_spots:
        print(f"警告: 跳过无效景区: {', '.join(invalid_spots)}")

    for spot in valid_spots:
        print(f"\n{'=' * 60}")
        print(f"处理景区: {spot}")
        print(f"{'=' * 60}")

        fused_data = None
        graph = None
        graph_stats = None

        print("\n[阶段 1/4] 数据加载...")
        spot_data = loader.load_scenic_spot(spot)

        if 'error' in spot_data:
            print(f"  错误: {spot_data['error']}")
            continue

        validation = loader.validate_data(spot_data)
        print(f"  官方路线: {'✓' if validation['has_official_routes'] else '✗'}")
        print(f"  游客POI: {'✓' if validation['has_visitor_pois'] else '✗'} ({spot_data['metadata']['visitor_poi_count']})")
        print(f"  条件建议: {'✓' if validation['has_advice'] else '✗'} ({spot_data['metadata']['advice_count']})")

        if run_all or args.fusion:
            print("\n[阶段 2/4] 知识融合...")

            fusion_engine = KnowledgeFusionEngine(spot)
            fused_data = fusion_engine.build_composite_knowledge(spot_data)

            stats = fused_data['statistics']
            route_report = fused_data.get('route_normalization_report', {})
            print(f"  官方POI数: {stats['official_poi_count']}")
            print(f"  游客POI数: {stats['visitor_poi_count']}")
            print(f"  融合POI数: {stats['fused_poi_count']}")
            print(f"  游客补充: {stats['visitor_supplemented_count']}")
            print(f"  建议关联: {stats['advice_matched_count']}")
            print(f"  统一路线边数: {route_report.get('normalized_route_count', 0)}")
            print(f"  推荐路线: {fused_data.get('recommended_route', {}).get('route_id', '')}")

            fusion_output = graph_output_dir / f'{spot}_fused.json'
            with open(fusion_output, 'w', encoding='utf-8') as f:
                export_data = {
                    'scenic_spot': fused_data['scenic_spot'],
                    'fused_pois': fused_data['fused_pois'],
                    'poi_weights': fused_data['poi_weights'],
                    'statistics': fused_data['statistics'],
                    'time_periods': fused_data['time_periods'],
                    'normalized_routes': fused_data.get('normalized_routes', []),
                    'route_normalization_report': fused_data.get('route_normalization_report', {}),
                    'recommended_route': fused_data.get('recommended_route', {}),
                    'visitor_supplemented': fused_data.get('visitor_supplemented', []),
                    'visitor_supplemented_details': fused_data.get('visitor_supplemented_details', []),
                    'condition_cleaning_report': fused_data.get('condition_cleaning_report', {})
                }
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print(f"  已保存: {fusion_output.name}")

        if run_all or args.build or args.visualize:
            if fused_data is None:
                fusion_engine = KnowledgeFusionEngine(spot)
                fused_data = fusion_engine.build_composite_knowledge(spot_data)

            print("\n[阶段 3/4] 构建知识图谱...")

            graph_builder = KnowledgeGraphBuilder()
            graph = graph_builder.build_graph(fused_data)

            graph_stats = graph_builder.get_graph_statistics(graph)
            print(f"  节点数: {graph_stats['total_nodes']}")
            print(f"  边数: {graph_stats['total_edges']}")
            print(f"  节点类型: {', '.join(f'{k}({v})' for k, v in graph_stats['node_types'].items())}")
            print(f"  边类型: {', '.join(f'{k}({v})' for k, v in graph_stats['edge_types'].items())}")

            graph_output = graph_output_dir / f'{spot}_graph.json'
            graph_builder.export_graph(graph, str(graph_output))
            print(f"  已保存: {graph_output.name}")

            quality_report_output = graph_output_dir / f'{spot}_quality_report.json'
            quality_report = {
                'scenic_spot': spot,
                'generated_at': datetime.now().isoformat(),
                'fusion_statistics': fused_data.get('statistics', {}),
                'route_normalization_report': fused_data.get('route_normalization_report', {}),
                'recommended_route': fused_data.get('recommended_route', {}),
                'visitor_supplemented': fused_data.get('visitor_supplemented', []),
                'visitor_supplemented_details': fused_data.get('visitor_supplemented_details', []),
                'condition_cleaning_report': fused_data.get('condition_cleaning_report', {}),
                'graph_statistics': graph_stats,
                'condition_advice_samples': graph.graph.get('condition_advice_table', [])[:20]
            }
            with open(quality_report_output, 'w', encoding='utf-8') as f:
                json.dump(quality_report, f, ensure_ascii=False, indent=2)
            print(f"  已保存: {quality_report_output.name}")

        if run_all or args.visualize:
            if graph is None:
                print("  错误: 图谱对象不存在，请先运行 --build")
                continue

            print("\n[阶段 4/4] 生成可视化...")

            visualizer = KnowledgeGraphVisualizer()
            viz_path = viz_output_dir / f'{spot}_knowledge_graph.png'

            viz_outputs = visualizer.visualize_knowledge_graph(
                graph,
                str(viz_path),
                mode='layered',
                export_main=False,
                export_condition=False
            )

            print(f"  已保存: {viz_path.name}")

    print(f"\n{'=' * 60}")
    print("任务6完成！")
    print(f"{'=' * 60}")

    print("\n输出文件:")
    print(f"  知识图谱数据: {graph_output_dir}/")
    print(f"  可视化图表: {viz_output_dir}/")
    print("\n")


if __name__ == '__main__':
    main()
