import json
import re
import sys
import threading
import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse
import requests
from pyquery import PyQuery as pq


class Spider(ABC):
    """
    爬虫基类，定义了 TVBox 爬虫的接口规范
    """
    
    def __init__(self):
        self.siteUrl = ""
        self.cookie = ""
        self.header = {}
        self.extend = {}
        
    @abstractmethod
    def init(self, extend=""):
        """
        爬虫初始化
        :param extend: 扩展参数，通常是json字符串
        """
        pass
    
    @abstractmethod
    def homeContent(self, filter=None):
        """
        首页内容
        :param filter: 是否启用筛选
        :return: 包含分类信息的字典
        """
        pass
    
    @abstractmethod
    def homeVideoContent(self):
        """
        首页视频内容
        :return: 包含推荐视频的字典
        """
        pass
    
    @abstractmethod
    def categoryContent(self, tid, pg, filter, extend):
        """
        分类内容
        :param tid: 分类ID
        :param pg: 页码
        :param filter: 是否启用筛选
        :param extend: 扩展参数
        :return: 包含分类视频列表的字典
        """
        pass
    
    @abstractmethod
    def detailContent(self, ids):
        """
        视频详情
        :param ids: 视频ID列表
        :return: 包含视频详细信息的字典
        """
        pass
    
    @abstractmethod
    def searchContent(self, key, quick):
        """
        搜索内容
        :param key: 搜索关键词
        :param quick: 是否快速搜索
        :return: 包含搜索结果的字典
        """
        pass
    
    @abstractmethod
    def playerContent(self, flag, id, vipFlags):
        """
        播放内容
        :param flag: 播放源标识
        :param id: 播放ID
        :param vipFlags: VIP标识列表
        :return: 包含播放地址的字典
        """
        pass
    
    def getName(self):
        """
        获取爬虫名称
        :return: 爬虫名称
        """
        return self.__class__.__name__
    
    def isVideoFormat(self, url):
        """
        判断URL是否为视频格式
        :param url: URL地址
        :return: 是否为视频格式
        """
        video_extensions = ['.m3u8', '.mp4', '.flv', '.avi', '.mkv', '.mov', '.wmv', '.rmvb', '.ts', '.f4v']
        return any(ext in url.lower() for ext in video_extensions)
    
    def manualVideoCheck(self):
        """
        手动视频检测
        :return: 是否需要手动检测
        """
        return False
    
    def destroy(self):
        """
        销毁爬虫实例
        """
        pass
    
    def getCache(self, key):
        """
        获取缓存
        :param key: 缓存键
        :return: 缓存值
        """
        # TODO: 实现缓存功能
        return None
    
    def setCache(self, key, value):
        """
        设置缓存
        :param key: 缓存键
        :param value: 缓存值
        """
        # TODO: 实现缓存功能
        pass

    def fetch(self, url, headers=None, timeout=10, params=None):
        """
        发送HTTP请求
        :param url: 请求URL
        :param headers: 请求头
        :param timeout: 超时时间
        :param params: URL参数
        :return: 响应内容
        """
        if headers is None:
            headers = self.header
            
        try:
            response = requests.get(url, headers=headers, timeout=timeout, params=params)
            response.encoding = response.apparent_encoding
            # 返回完整的response对象以便调用方可以访问.json()等方法
            return response
        except Exception as e:
            print(f"请求失败: {url}, 错误: {str(e)}")
            # 返回一个模拟的response对象
            class MockResponse:
                def __init__(self):
                    self.status_code = 500
                    self.text = ""
                    self.headers = {}
                def json(self):
                    raise Exception("Mock error")
                def raise_for_status(self):
                    raise Exception("Mock error")
            return MockResponse()

    def post(self, url, data=None, headers=None, timeout=10, **kwargs):
        """
        发送POST请求
        :param url: 请求URL
        :param data: POST数据
        :param headers: 请求头
        :param timeout: 超时时间
        :param kwargs: 其他参数，如json等
        :return: 响应内容
        """
        if headers is None:
            headers = self.header
            
        try:
            response = requests.post(url, data=data, headers=headers, timeout=timeout, **kwargs)
            response.encoding = response.apparent_encoding
            # 检查是否需要返回完整response对象还是文本内容
            # 如果有其他代码需要访问response对象属性，则需返回response
            return response
        except Exception as e:
            print(f"POST请求失败: {url}, 错误: {str(e)}")
            # 返回一个模拟的response对象
            class MockResponse:
                def __init__(self):
                    self.status_code = 500
                    self.text = ""
                    self.headers = {}
                def raise_for_status(self):
                    raise Exception("Mock error")
            return MockResponse()