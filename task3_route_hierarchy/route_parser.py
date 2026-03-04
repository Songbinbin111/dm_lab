#!/usr/bin/env python3
"""
路线解析器 - 解析不同格式的官方游览路线
支持三种格式：
1. 九寨沟格式：箭头连接 + 时间范围
2. 故宫格式：编号列表
3. 黄山格式：多线路选择
"""

import re
import json
from typing import Dict, List, Any, Optional


def get_time_period(time_str: str) -> str:
    """将时间字符串映射到时段（上午/中午/下午/晚上）"""
    # 提取小时数
    hour_match = re.search(r'(\d{1,2}):', time_str)
    if hour_match:
        hour = int(hour_match.group(1))
        if 5 <= hour < 9:
            return "清晨"
        elif 9 <= hour < 11:
            return "上午"
        elif 11 <= hour < 13:
            return "中午"
        elif 13 <= hour < 17:
            return "下午"
        elif 17 <= hour < 19:
            return "傍晚"
        else:
            return "晚上"
    return "未知时段"


def parse_arrow_route(text: str, spot_name: str) -> Dict[str, Any]:
    """
    通用解析器：解析带有箭头和详细信息的路线
    格式：[上午]A(详情)→B(详情) B→C(详情) ...
    """
    routes = []
    
    # 1. 移除时间段标记 [上午] 等，以免干扰，但可以保留作为上下文（这里暂不处理上下文）
    # 或者我们可以按时间段分割
    
    # 简单的正则匹配： 节点A(详情A)→节点B(详情B)
    # 考虑到节点B可能是下一个的起点，我们采用查找所有 A->B 关系的策略
    
    # 正则策略：
    # 寻找 X→Y(...) 模式
    # X 可能包含 (详情) 也可能不包含
    # Y 必须紧跟 (详情)
    
    # 预处理：将中文括号转为英文括号，方便正则
    text = text.replace('（', '(').replace('）', ')')
    
    # 匹配模式：
    # part1: ([^→\s\[\]：:.,，。]+(?:[(][^)]+[)])?)  -- 起点，排除标点和括号
    # arrow: →
    # part2: ([^→\s\[\]：:.,，。(]+) -- 终点
    # details: \(([^)]+)\) -- 括号内的详情
    
    # 但实际数据中，起点也可能有括号，如 "午门(8:30 入园)"
    # 且 "午门(8:30 入园)→太和门"
    # 所以起点是 "箭头前的所有内容" (在该段内)
    
    # 更好的方法是先按箭头分割，然后处理每一段
    # A(..) → B(..) B → C(..)
    # 这其实是 A(..) → B(..) 和 B → C(..) 的混合
    # 注意观察数据： "午门(...)→太和门(...)太和门→太和殿(...)"
    # 它们是连在一起的。
    # 可以用 split('→') 吗？
    # "午门(...) ", "太和门(...)太和门", "太和殿(...)太和殿", ...
    # 这种分割会把 "太和门(...)太和门" 放在一起，很难分清哪里是上一段的结尾，哪里是下一段的开始。
    
    # 观察数据特点： "...)太和门→"
    # 也就是说，下一段的起点紧跟在上一段详情的右括号后面。
    # 我们可以用正则找 `→`，然后向前找终点，向后找终点。
    
    # 迭代查找 "A→B(details)"
    # A 可以是 "午门(8:30 入园)" 或者 "太和门"
    # B 是 "太和门"
    # details 是 "(...)"
    
    # 正则：
    # (?P<start>.+?)→(?P<end>[^(]+)\((?P<details>[^)]+)\)
    # 但是 start 可能会匹配过多。
    # 限制 start 的边界：
    # start 不能包含 '→'
    # start 可能紧跟在上一段的 ')' 后面
    
    matches = list(re.finditer(r'([^→\s\[\]：:.,，。]+(?:[(][^)]+[)])?)\s*→\s*([^→\s\[\]：:.,，。(]+)\(([^)]+)\)', text))
    
    for i, match in enumerate(matches):
        start_node = match.group(1).strip()
        end_node = match.group(2).strip()
        details = match.group(3).strip()
        
        # 清理 start_node，如果它包含上一段的残留（虽然正则[^→]应该避免了，但为了保险）
        # 实际上 start_node 可能是 "太和门" 或 "午门(8:30 入园)"
        # 如果有括号，提取纯名
        start_pure = re.sub(r'\(.*?\)', '', start_node).strip()
        
        # 提取时间
        time_range = ""
        period = "未知时段"
        time_match = re.search(r'(\d{1,2}:\d{2}-\d{1,2}:\d{2})', details)
        if time_match:
            time_range = time_match.group(1)
            # Use start time to guess period
            start_time = time_range.split('-')[0]
            period = get_time_period(start_time)
        elif "上午" in text:
            period = "上午" # Crude fallback
            
        # 提取时长
        duration = ""
        dur_match = re.search(r'游览时间\s*(\d+\s*分钟|\d+\s*小时)', details)
        if dur_match:
            duration = dur_match.group(1)
            
        routes.append({
            "from_poi": start_pure,
            "to_poi": end_node,
            "poi": end_node,
            "time_range": time_range,
            "period": period,
            "duration": duration,
            "details": details,
            "full_text": match.group(0)
        })
        
    # 提取所有 POI
    all_pois = set()
    if routes:
        all_pois.add(routes[0]['from_poi'])
    for r in routes:
        all_pois.add(r['to_poi'])
        
    sorted_pois = sorted(list(all_pois)) # 简单排序
    
    return {
        "scenic_spot": spot_name,
        "route_format": "arrow_text",
        "total_pois": len(all_pois),
        "pois": sorted_pois,
        "routes": routes
    }

def parse_jiuzhaigou_route(text: str) -> Dict[str, Any]:
    return parse_arrow_route(text, "九寨沟")

def parse_gugong_route(text: str) -> Dict[str, Any]:
    return parse_arrow_route(text, "故宫")

def parse_huangshan_route(text: str) -> Dict[str, Any]:
    return parse_arrow_route(text, "黄山")


class RouteParser:
    """路线解析器 - 统一接口"""

    @staticmethod
    def parse(scenic_spot: str, route_text: str) -> Dict[str, Any]:
        """根据景区类型解析路线"""
        if scenic_spot == "九寨沟":
            return parse_jiuzhaigou_route(route_text)
        elif scenic_spot == "故宫":
            return parse_gugong_route(route_text)
        elif scenic_spot == "黄山":
            return parse_huangshan_route(route_text)
        else:
            return {
                "scenic_spot": scenic_spot,
                "route_format": "unknown",
                "error": "Unsupported scenic spot"
            }


class TimeHierarchyBuilder:
    """时间层级结构构建器"""

    @staticmethod
    def build_hierarchy(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建时间维度的游览层级结构"""
        scenic_spot = parsed_data.get("scenic_spot", "")
        route_format = parsed_data.get("route_format", "")

        if scenic_spot == "九寨沟" and route_format == "arrow_text":
            return TimeHierarchyBuilder._build_jiuzhaigou_hierarchy(parsed_data)
        elif scenic_spot == "故宫" and (route_format == "numbered_list" or route_format == "arrow_text"):
            return TimeHierarchyBuilder._build_gugong_hierarchy(parsed_data)
        elif scenic_spot == "黄山":
            if route_format == "multi_route_selection":
                return TimeHierarchyBuilder._build_huangshan_hierarchy(parsed_data)
            elif route_format == "arrow_text":
                 return TimeHierarchyBuilder._build_huangshan_arrow_hierarchy(parsed_data)
            else:
                return {"error": f"Unsupported format: {scenic_spot} - {route_format}"}
        
        return {"error": f"Unsupported format: {scenic_spot} - {route_format}"}

    @staticmethod
    def _build_huangshan_arrow_hierarchy(data: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap single arrow route into Huangshan hierarchy structure"""
        hierarchy = {
            "scenic_spot": "黄山",
            "structure_type": "route_selection_based",
            "hierarchy": {
                "可选线路": {
                    "推荐线路": {
                        "nodes": [r["poi"] for r in data.get("routes", [])],
                        "total_nodes": len(data.get("routes", []))
                    }
                }
            }
        }
        return hierarchy

    @staticmethod
    def _build_jiuzhaigou_hierarchy(data: Dict[str, Any]) -> Dict[str, Any]:
        """构建九寨沟的时间层级结构"""
        hierarchy = {
            "scenic_spot": "九寨沟",
            "structure_type": "time_based",
            "hierarchy": {}
        }

        # 按时段分组
        periods = {}
        for route in data.get("routes", []):
            period = route.get("period", "未知时段")
            if period not in periods:
                periods[period] = []

            periods[period].append({
                "poi": route.get("poi", ""),
                "time_start": route.get("time_start", ""),
                "time_end": route.get("time_end", ""),
                "transport": route.get("transport", ""),
                "duration": route.get("duration", ""),
                "details": route.get("details", "")
            })

        # 构建层级结构
        period_order = ["清晨", "上午", "中午", "下午", "傍晚", "晚上"]
        for period in period_order:
            if period in periods:
                hierarchy["hierarchy"][period] = {
                    "time_range": TimeHierarchyBuilder._get_period_range(period),
                    "activities": periods[period],
                    "activity_count": len(periods[period])
                }

        return hierarchy

    @staticmethod
    def _build_gugong_hierarchy(data: Dict[str, Any]) -> Dict[str, Any]:
        """构建故宫的层级结构（基于编号顺序）"""
        hierarchy = {
            "scenic_spot": "故宫",
            "structure_type": "sequence_based",
            "hierarchy": {
                "游览路线": {
                    "sections": []
                }
            }
        }

        # 将路线分组（前、中、后）
        routes = data.get("routes", [])
        total = len(routes)
        
        # Determine full sequence
        full_sequence = []
        if routes:
            # If format is arrow_text, routes are segments (from_poi -> to_poi)
            # We should include the start point of the first segment
            if "from_poi" in routes[0]:
                full_sequence.append(routes[0]["from_poi"])
            
            # Add all destination points
            full_sequence.extend([r["poi"] for r in routes])
        else:
            full_sequence = []

        total = len(full_sequence)

        # 分为三个部分
        if total > 0:
            third = total // 3
            hierarchy["hierarchy"]["游览路线"]["sections"] = [
                {
                    "name": "前部（外朝）",
                    "pois": full_sequence[:third]
                },
                {
                    "name": "中部（内廷）",
                    "pois": full_sequence[third:2 * third]
                },
                {
                    "name": "后部（御花园等）",
                    "pois": full_sequence[2 * third:]
                }
            ]

        hierarchy["hierarchy"]["游览路线"]["total_pois"] = total
        hierarchy["hierarchy"]["游览路线"]["full_sequence"] = full_sequence

        return hierarchy

    @staticmethod
    def _build_huangshan_hierarchy(data: Dict[str, Any]) -> Dict[str, Any]:
        """构建黄山的层级结构（基于线路选择）"""
        hierarchy = {
            "scenic_spot": "黄山",
            "structure_type": "route_selection_based",
            "hierarchy": {
                "可选线路": {}
            }
        }

        for route in data.get("routes", []):
            route_name = route.get("route_name", "")
            hierarchy["hierarchy"]["可选线路"][route_name] = {
                "entrance": route.get("entrance", ""),
                "cableway": route.get("cableway", ""),
                "nodes": route.get("nodes", []),
                "total_nodes": route.get("total_nodes", 0)
            }

        # 统计所有景点的出现频率
        poi_freq = data.get("poi_frequency", {})
        hierarchy["common_pois"] = {
            "high_frequency": [poi for poi, freq in poi_freq.items() if freq >= 3],
            "medium_frequency": [poi for poi, freq in poi_freq.items() if freq == 2],
            "low_frequency": [poi for poi, freq in poi_freq.items() if freq == 1]
        }

        return hierarchy

    @staticmethod
    def _get_period_range(period: str) -> str:
        """获取时段的时间范围"""
        ranges = {
            "清晨": "5:00-9:00",
            "上午": "9:00-11:00",
            "中午": "11:00-13:00",
            "下午": "13:00-17:00",
            "傍晚": "17:00-19:00",
            "晚上": "19:00-23:00"
        }
        return ranges.get(period, "")


def main():
    """测试函数"""
    import pandas as pd

    print("=" * 60)
    print("路线解析测试")
    print("=" * 60)

    # 读取数据
    df = pd.read_excel('../task1_data_collection/data/data_cleaned.xlsx')

    for idx, row in df.iterrows():
        scenic_spot = row['景区名称']
        route_text = row['官方游览路线']

        if pd.isna(route_text):
            continue

        print(f"\n{'='*60}")
        print(f"解析 {scenic_spot} 官方路线")
        print(f"{'='*60}")

        # 解析路线
        parsed = RouteParser.parse(scenic_spot, route_text)

        # 构建层级结构
        hierarchy = TimeHierarchyBuilder.build_hierarchy(parsed)

        print(f"\n路线格式: {parsed.get('route_format', 'unknown')}")
        print(f"景点数量: {parsed.get('total_pois', 0)}")
        print(f"\n前10个景点: {parsed.get('pois', [])[:10]}")

        print(f"\n层级结构类型: {hierarchy.get('structure_type', 'unknown')}")

        # 保存结果
        with open(f'route_hierarchy/{scenic_spot}_hierarchy.json', 'w', encoding='utf-8') as f:
            json.dump({
                "parsed": parsed,
                "hierarchy": hierarchy
            }, f, ensure_ascii=False, indent=2)

        print(f"\n已保存: route_hierarchy/{scenic_spot}_hierarchy.json")


if __name__ == '__main__':
    # 创建输出目录
    import os
    if not os.path.exists('route_hierarchy'):
        os.makedirs('route_hierarchy')

    main()
