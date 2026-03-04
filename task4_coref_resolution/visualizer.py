#!/usr/bin/env python3
"""
任务4：共指消解可视化模块

功能：
1. 生成代词分布统计图
2. 生成综合评估报告图
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from typing import Dict, List
from collections import Counter
from matplotlib.font_manager import FontProperties


# 设置中文字体（参考task3的配置）
def setup_matplotlib_font():
    """设置matplotlib中文字体"""
    import platform
    from matplotlib import font_manager
    system = platform.system()

    # 常见中文字体路径
    font_paths = []
    if system == 'Darwin':  # macOS
        font_paths = ['/System/Library/Fonts/PingFang.ttc', '/Library/Fonts/Arial Unicode.ttf']
    elif system == 'Windows':
        font_paths = ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']
    else:  # Linux
        font_paths = ['/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']

    found_font = False
    for path in font_paths:
        if os.path.exists(path):
            try:
                # 显式注册字体文件
                font_manager.fontManager.addfont(path)
                # 获取该字体文件对应的家族名称
                prop = font_manager.FontProperties(fname=path)
                font_name = prop.get_name()
                
                # 设置为默认字体
                matplotlib.rcParams['font.sans-serif'] = [font_name, 'SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
                matplotlib.rcParams['font.family'] = 'sans-serif'
                found_font = True
                break
            except Exception as e:
                print(f"警告: 无法加载字体 {path}: {e}")

    if not found_font:
        # 最后的兜底方案：尝试常见的系统字体名称
        matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'STHeiti']

    matplotlib.rcParams['axes.unicode_minus'] = False


def get_chinese_font():
    """获取中文字体路径（用于FontProperties）"""
    import platform
    system = platform.system()

    if system == 'Darwin':  # macOS
        fonts = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/Library/Fonts/Arial Unicode.ttf'
        ]
    elif system == 'Windows':
        fonts = [
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttc',
        ]
    else:  # Linux
        fonts = [
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        ]

    for font in fonts:
        if os.path.exists(font):
            return font
    return None


setup_matplotlib_font()


class CoreferenceVisualizer:
    """共指消解可视化器"""

    def __init__(self, stats_path: str, eval_report_path: str):
        """
        初始化可视化器

        Args:
            stats_path: 统计报告文件路径
            eval_report_path: 评估报告文件路径
        """
        with open(stats_path, 'r', encoding='utf-8') as f:
            self.stats = json.load(f)

        with open(eval_report_path, 'r', encoding='utf-8') as f:
            self.eval_report = json.load(f)

    def create_all_visualizations(self, output_dir: str):
        """
        生成所有可视化图表

        Args:
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. 综合评估报告图（包含所有核心信息）
        self.plot_evaluation_summary(f"{output_dir}/evaluation_summary.png")

        # 2. 代词频率分布图
        self.plot_pronoun_frequency(f"{output_dir}/pronoun_frequency.png")

        print(f"\n可视化图表已保存到: {output_dir}")

    def plot_pronoun_frequency(self, output_path: str):
        """绘制代词频率分布图"""
        freq = self.stats['pronoun_frequency']

        # 按频率排序，只显示前10个
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]

        pronouns = [item[0] for item in sorted_freq]
        counts = [item[1] for item in sorted_freq]

        fig, ax = plt.subplots(figsize=(12, 6))

        bars = ax.bar(pronouns, counts, color='steelblue', edgecolor='black', alpha=0.7)

        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom', fontsize=11)

        ax.set_xlabel('代词', fontsize=12)
        ax.set_ylabel('出现次数', fontsize=12)
        ax.set_title('代词频率分布统计（Top 10）', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        plt.xticks(rotation=0, fontsize=11)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def plot_evaluation_summary(self, output_path: str):
        """绘制综合评估报告图"""
        fig = plt.figure(figsize=(16, 10))

        # 创建子图布局
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 1. 总体结果饼图
        ax1 = fig.add_subplot(gs[0, 0])
        summary = self.eval_report['summary']
        sizes = [summary['correct'], summary['incorrect'], summary['not_resolved']]
        labels = [f'正确 ({summary["correct"]})', f'错误 ({summary["incorrect"]})',
                 f'未消解 ({summary["not_resolved"]})']
        colors = ['#4CAF50', '#F44336', '#FFC107']
        explode = (0.05, 0.05, 0.05)

        ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
               shadow=True, startangle=90, textprops={'fontsize': 11})
        ax1.set_title('总体消解结果分布', fontsize=13, fontweight='bold')

        # 2. 按代词类型的准确率
        ax2 = fig.add_subplot(gs[0, 1])
        by_type = self.eval_report['by_pronoun_type']
        types = list(by_type.keys())
        accuracies = [by_type[t]['accuracy'] * 100 for t in types]
        totals = [by_type[t]['total'] for t in types]

        colors = plt.cm.Set3(np.linspace(0, 1, len(types)))
        bars = ax2.bar(types, accuracies, color=colors, edgecolor='black', alpha=0.7)

        for bar, acc, tot in zip(bars, accuracies, totals):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{acc:.0f}%\n(n={tot})', ha='center', va='bottom', fontsize=10)

        ax2.set_ylabel('准确率 (%)', fontsize=11)
        ax2.set_xlabel('代词类型', fontsize=11)
        ax2.set_title('按代词类型的准确率', fontsize=13, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. 按先行词类型的准确率
        ax3 = fig.add_subplot(gs[1, 0])
        by_ant = self.eval_report['by_antecedent_type']
        ant_types = list(by_ant.keys())
        ant_accs = [by_ant[t]['accuracy'] * 100 for t in ant_types]
        ant_totals = [by_ant[t]['total'] for t in ant_types]

        colors = plt.cm.Pastel1(np.linspace(0, 1, len(ant_types)))
        bars = ax3.bar(ant_types, ant_accs, color=colors, edgecolor='black', alpha=0.7)

        for bar, acc, tot in zip(bars, ant_accs, ant_totals):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{acc:.0f}%\n(n={tot})', ha='center', va='bottom', fontsize=10)

        ax3.set_ylabel('准确率 (%)', fontsize=11)
        ax3.set_xlabel('先行词类型', fontsize=11)
        ax3.set_title('按先行词类型的准确率', fontsize=13, fontweight='bold')
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. 关键发现文字总结
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.axis('off')

        findings = []
        findings.append("共指消解评估关键发现")
        findings.append("=" * 35)
        findings.append(f"\n【总体表现】")
        findings.append(f"• 总准确率: {summary['accuracy']}")
        findings.append(f"• 正确案例: {summary['correct']}/{summary['total_cases']}")
        findings.append(f"• 错误案例: {summary['incorrect']}")

        findings.append(f"\n【按代词类型】")
        for ptype, stats in by_type.items():
            findings.append(f"• {ptype}: {stats['correct']}/{stats['total']} "
                          f"({stats['accuracy']*100:.1f}%)")

        findings.append(f"\n【主要挑战】")
        findings.append("• 跨句指代消解准确率较低")
        findings.append("• '这里'类指代词消解难度大")
        findings.append("• 需要上下文理解的指代关系")

        findings.append(f"\n【改进建议】")
        findings.append("• 引入更复杂的上下文模型")
        findings.append("• 考虑句法依存关系")
        findings.append("• 使用预训练语言模型")

        text = '\n'.join(findings)
        ax4.text(0.05, 0.95, text, transform=ax4.transAxes,
                fontsize=10, verticalalignment='top', family='sans-serif',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

        fig.suptitle('共指消解综合评估报告', fontsize=16, fontweight='bold', y=0.98)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()


def main():
    """主函数"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    stats_path = os.path.join(current_dir, 'output/statistics_report.json')
    eval_path = os.path.join(current_dir, 'output/evaluation_report.json')
    output_dir = os.path.join(current_dir, 'output/visualizations')

    visualizer = CoreferenceVisualizer(stats_path, eval_path)
    visualizer.create_all_visualizations(output_dir)


if __name__ == '__main__':
    main()
