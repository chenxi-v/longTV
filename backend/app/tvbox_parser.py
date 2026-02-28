import json
import requests
from typing import Dict, Any, List


class TVBoxConfigParser:
    """
    TVBox 配置解析器，用于解析 TVBox 配置文件
    """
    
    def load_config(self, config_url: str) -> Dict[str, Any]:
        """
        从 URL 加载 TVBox 配置
        :param config_url: 配置文件URL
        :return: 解析后的配置字典
        """
        try:
            response = requests.get(config_url)
            response.raise_for_status()
            
            # 尝试解析 JSON
            try:
                config_data = response.json()
            except json.JSONDecodeError:
                # 如果不是标准JSON，尝试其他格式
                content = response.text.strip()
                # TVBox 配置通常是以 # 开头的注释行和配置项
                config_data = self._parse_text_config(content)
            
            return self._normalize_config(config_data)
        except Exception as e:
            raise ValueError(f"无法加载或解析配置: {str(e)}")
    
    def _parse_text_config(self, content: str) -> Dict[str, Any]:
        """
        解析文本格式的配置
        :param content: 配置内容
        :return: 解析后的配置字典
        """
        config = {"sites": []}
        
        lines = content.split('\n')
        current_site = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key.lower() == 'name':
                    # 新站点开始
                    if current_site is not None:
                        config["sites"].append(current_site)
                    current_site = {"key": value, "name": value}
                elif current_site is not None:
                    current_site[key.lower()] = value
        
        if current_site is not None:
            config["sites"].append(current_site)
        
        return config
    
    def _normalize_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化配置格式
        :param config_data: 原始配置数据
        :return: 标准化后的配置
        """
        normalized = {}
        
        if 'sites' in config_data:
            for site in config_data['sites']:
                if isinstance(site, dict):
                    key = site.get('key') or site.get('name') or len(normalized)
                    normalized[str(key)] = self._convert_site_to_spider_config(site)
        elif isinstance(config_data, dict):
            # 如果是键值对格式
            for key, value in config_data.items():
                if isinstance(value, dict):
                    normalized[key] = self._convert_site_to_spider_config(value)
                elif isinstance(value, str):
                    # 假设是URL，尝试识别类型
                    if value.endswith('.py'):
                        normalized[key] = {
                            'type': 'python',
                            'script_url': value
                        }
                    else:
                        normalized[key] = {
                            'type': 'generic',
                            'api_url': value
                        }
        
        return normalized
    
    def _convert_site_to_spider_config(self, site: Dict[str, Any]) -> Dict[str, Any]:
        """
        将站点配置转换为爬虫配置
        :param site: 站点配置
        :return: 爬虫配置
        """
        if site.get('type') == '3' or site.get('api', '').endswith('.py'):
            # 这是一个 Python 爬虫
            return {
                'type': 'python',
                'script_url': site.get('api', ''),
                'name': site.get('name', ''),
                'searchable': site.get('searchable', 1),
                'quickSearch': site.get('quickSearch', 1),
                'filterable': site.get('filterable', 1)
            }
        else:
            # 这是一个通用爬虫
            return {
                'type': 'generic',
                'api_url': site.get('api', ''),
                'name': site.get('name', ''),
                'searchable': site.get('searchable', 1),
                'quickSearch': site.get('quickSearch', 1),
                'filterable': site.get('filterable', 1)
            }


# 示例配置格式支持
EXAMPLE_CONFIG_FORMATS = {
    "json": {
        "sites": [
            {
                "key": "example1",
                "name": "示例站点1",
                "type": 3,
                "api": "https://example.com/spider.py",
                "searchable": 1,
                "quickSearch": 1,
                "filterable": 1
            }
        ]
    },
    "text": """
# 这是一个TVBox配置示例
name=example1
api=https://example.com/spider.py
type=3
searchable=1
quickSearch=1
filterable=1
"""
}