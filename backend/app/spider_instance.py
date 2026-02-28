from typing import Dict, Any, Optional
from .base.spider import Spider


class SpiderInstance:
    """
    爬虫实例包装器
    """
    
    def __init__(self, spider: Spider, config: Dict[str, Any]):
        self.spider = spider
        self.config = config
        self.last_used = None
        self.usage_count = 0
        
    def execute_home_content(self, filter_param=None):
        """执行首页内容获取"""
        self._before_execute()
        result = self.spider.homeContent(filter_param)
        self._after_execute()
        return result
    
    def execute_home_video_content(self):
        """执行首页视频内容获取"""
        self._before_execute()
        result = self.spider.homeVideoContent()
        self._after_execute()
        return result
    
    def execute_category_content(self, tid, pg, filter_param, extend):
        """执行分类内容获取"""
        self._before_execute()
        result = self.spider.categoryContent(tid, pg, filter_param, extend)
        self._after_execute()
        return result
    
    def execute_detail_content(self, ids):
        """执行详情内容获取"""
        self._before_execute()
        result = self.spider.detailContent(ids)
        self._after_execute()
        return result
    
    def execute_search_content(self, key, quick):
        """执行搜索内容获取"""
        self._before_execute()
        result = self.spider.searchContent(key, quick)
        self._after_execute()
        return result
    
    def execute_player_content(self, flag, id, vip_flags):
        """执行播放内容获取"""
        self._before_execute()
        result = self.spider.playerContent(flag, id, vip_flags)
        self._after_execute()
        return result
    
    def _before_execute(self):
        """执行前的准备工作"""
        self.last_used = __import__('time').time()
        self.usage_count += 1
    
    def _after_execute(self):
        """执行后的清理工作"""
        pass


# 保留向后兼容性
from .spider_manager import spider_manager