#!/usr/bin/env python3
"""
任务6：多源程序性知识的融合与可视化 - 数据加载模块

功能：
1. 加载task2的实体提取结果
2. 加载task3的路线层级结构
3. 加载task5的条件性建议
4. 统一输出格式
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None


class MultiSourceDataLoader:
    """多源数据加载器"""

    # 景区名称映射（标准化）
    SPOT_NAME_MAP = {
        '九寨沟': 'jiuzhaigou',
        '故宫': 'gugong',
        '黄山': 'huangshan'
    }

    # 英文名到中文名映射
    SPOT_EN_TO_CN = {
        'jiuzhaigou': '九寨沟',
        'gugong': '故宫',
        'huangshan': '黄山'
    }

    def __init__(self, project_root: str = None):
        """
        初始化数据加载器

        Args:
            project_root: 项目根目录路径
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)

        # 定义数据路径
        self.data_paths = {
            'entity': self.project_root / 'task2_entity_recognition' / 'entity_results.json',
            'hierarchy': self.project_root / 'task3_route_hierarchy' / 'hierarchies',
            'advice': self.project_root / 'task5_conditional_advice' / 'output' / 'conditional_advice.json',
            'travelogs': self.project_root / 'task1_data_collection' / 'data' / 'data_cleaned.xlsx'
        }

    def _load_json(self, path: Path) -> Optional[Dict]:
        """
        加载JSON文件

        Args:
            path: 文件路径

        Returns:
            JSON数据，如果文件不存在返回None
        """
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_entity_results(self) -> Optional[Dict]:
        """
        加载实体提取结果（task2）

        Returns:
            实体结果字典
        """
        return self._load_json(self.data_paths['entity'])

    def load_hierarchy(self, spot_name: str) -> Optional[Dict]:
        """
        加载单个景区的层级结构（task3）

        Args:
            spot_name: 景区名称（中文）

        Returns:
            层级结构字典
        """
        en_name = self.SPOT_NAME_MAP.get(spot_name, spot_name)
        hierarchy_path = self.data_paths['hierarchy'] / f'{spot_name}_hierarchy.json'
        return self._load_json(hierarchy_path)

    def load_all_hierarchies(self) -> Dict[str, Dict]:
        """
        加载所有景区的层级结构

        Returns:
            {景区名: 层级结构}
        """
        hierarchies = {}
        for spot_cn, spot_en in self.SPOT_NAME_MAP.items():
            hierarchy_path = self.data_paths['hierarchy'] / f'{spot_cn}_hierarchy.json'
            data = self._load_json(hierarchy_path)
            if data:
                hierarchies[spot_cn] = data
        return hierarchies

    def load_conditional_advice(self) -> Optional[Dict]:
        """
        加载条件性建议（task5）

        Returns:
            条件性建议字典
        """
        return self._load_json(self.data_paths['advice'])

    def _compute_visitor_poi_frequency(
        self,
        spot_name: str,
        visitor_pois: List[str]
    ) -> Dict[str, int]:
        """
        基于 task1 游记按“文档频次”统计游客 POI 频率（1~5）。
        如果无法读取游记数据，则回退为出现即记 1。
        """
        if not visitor_pois:
            return {}

        fallback = {poi: 1 for poi in visitor_pois if poi}
        travelog_path = self.data_paths.get('travelogs')

        if not HAS_PANDAS or not travelog_path or not travelog_path.exists():
            return fallback

        try:
            df = pd.read_excel(travelog_path)
        except Exception:
            return fallback

        spot_rows = df[df.get('景区名称') == spot_name]
        if spot_rows.empty:
            return fallback

        row = spot_rows.iloc[0]
        travelog_texts = []
        for idx in range(1, 6):
            col = f'游客游记{idx}'
            if col in row and pd.notna(row[col]):
                content = str(row[col]).strip()
                if content:
                    travelog_texts.append(content)

        if not travelog_texts:
            return fallback

        poi_freq = {}
        for poi in visitor_pois:
            if not poi:
                continue
            doc_count = sum(1 for text in travelog_texts if poi in text)
            poi_freq[poi] = doc_count if doc_count > 0 else 1

        return poi_freq

    def load_scenic_spot(self, spot_name: str) -> Dict[str, Any]:
        """
        加载单个景区的所有数据

        Args:
            spot_name: 景区名称（中文）：九寨沟/故宫/黄山

        Returns:
            {
                'scenic_spot': '九寨沟',
                'official_routes': {...},      # from task3
                'visitor_pois': [...],         # from task2
                'visitor_poi_freq': {...},     # POI频率统计
                'conditional_advice': [...],   # from task5
                'spot_advice': [...],          # 该景区的建议
                'metadata': {...}
            }
        """
        # 1. 加载层级结构
        official_routes = self.load_hierarchy(spot_name)
        if not official_routes:
            return {'error': f'未找到景区 {spot_name} 的层级结构数据'}

        # 2. 加载实体结果
        entity_results = self.load_entity_results()
        visitor_pois = []
        visitor_poi_freq = {}

        if entity_results and 'results' in entity_results:
            for result in entity_results['results']:
                if result.get('scenic_spot') == spot_name:
                    # 获取游客提到的POI（非官方）
                    visitor_pois = result.get('poi', [])
                    # 基于 task1 游记计算 POI 文档频次（高频景点更可靠）
                    visitor_poi_freq = self._compute_visitor_poi_frequency(spot_name, visitor_pois)
                    break

        # 3. 加载条件性建议
        conditional_advice = []
        spot_advice = []
        advice_data = self.load_conditional_advice()

        if advice_data and 'conditional_advice' in advice_data:
            conditional_advice = advice_data['conditional_advice']
            # 筛选该景区的建议
            spot_advice = [
                adv for adv in conditional_advice
                if adv.get('scenic_spot') == spot_name
            ]

        return {
            'scenic_spot': spot_name,
            'official_routes': official_routes,
            'visitor_pois': visitor_pois,
            'visitor_poi_freq': visitor_poi_freq,
            'conditional_advice': conditional_advice,
            'spot_advice': spot_advice,
            'metadata': {
                'spot_name': spot_name,
                'en_name': self.SPOT_NAME_MAP.get(spot_name, spot_name),
                'has_official_routes': bool(official_routes),
                'visitor_poi_count': len(visitor_pois),
                'advice_count': len(spot_advice)
            }
        }

    def load_all_scenic_spots(self) -> Dict[str, Dict]:
        """
        加载所有景区的数据

        Returns:
            {景区名: 数据字典}
        """
        all_spots = {}
        for spot_name in self.SPOT_NAME_MAP.keys():
            spot_data = self.load_scenic_spot(spot_name)
            if 'error' not in spot_data:
                all_spots[spot_name] = spot_data
        return all_spots

    def get_available_spots(self) -> List[str]:
        """
        获取可用的景区列表

        Returns:
            景区名称列表
        """
        available = []
        for spot_name in self.SPOT_NAME_MAP.keys():
            hierarchy_path = self.data_paths['hierarchy'] / f'{spot_name}_hierarchy.json'
            if hierarchy_path.exists():
                available.append(spot_name)
        return available

    def validate_data(self, data: Dict) -> Dict[str, bool]:
        """
        验证数据完整性

        Args:
            data: load_scenic_spot返回的数据

        Returns:
            {验证项: 是否通过}
        """
        validation = {
            'has_official_routes': bool(data.get('official_routes')),
            'has_visitor_pois': len(data.get('visitor_pois', [])) > 0,
            'has_advice': len(data.get('spot_advice', [])) > 0,
            'routes_has_parsed': False,
            'routes_has_hierarchy': False
        }

        if data.get('official_routes'):
            validation['routes_has_parsed'] = 'parsed' in data['official_routes']
            validation['routes_has_hierarchy'] = 'hierarchy' in data['official_routes']

        return validation


# =============================================================================
# 便捷函数
# =============================================================================

def load_spot_data(spot_name: str, project_root: str = None) -> Dict[str, Any]:
    """
    便捷函数：加载单个景区数据

    Args:
        spot_name: 景区名称
        project_root: 项目根目录

    Returns:
        景区数据
    """
    loader = MultiSourceDataLoader(project_root)
    return loader.load_scenic_spot(spot_name)


def load_all_spots(project_root: str = None) -> Dict[str, Dict]:
    """
    便捷函数：加载所有景区数据

    Args:
        project_root: 项目根目录

    Returns:
        {景区名: 数据}
    """
    loader = MultiSourceDataLoader(project_root)
    return loader.load_all_scenic_spots()


if __name__ == '__main__':
    # 测试代码
    loader = MultiSourceDataLoader()
    print("可用的景区:", loader.get_available_spots())

    # 加载单个景区
    spot_data = loader.load_scenic_spot('九寨沟')
    print("\n九寨沟数据验证:")
    validation = loader.validate_data(spot_data)
    for key, value in validation.items():
        print(f"  {key}: {value}")
