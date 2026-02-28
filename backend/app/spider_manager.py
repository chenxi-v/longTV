import importlib.util
import json
import os
import sys
import tempfile
import requests
from urllib.parse import urlparse
from typing import Dict, Any, Optional
from .base.spider import Spider


class SpiderManager:
    """
    爬虫管理器，负责管理多个爬虫实例
    """
    
    def __init__(self):
        self.spiders: Dict[str, Dict[str, Any]] = {}
        self._remote_spiders_file = os.path.join(os.path.dirname(__file__), "remote_spiders.json")
        self._local_spiders_file = os.path.join(os.path.dirname(__file__), "local_spiders.json")
        self._load_existing_spiders()
        self._load_remote_spiders()
        self._load_local_spiders_name()
    
    def _load_local_spiders_name(self):
        """
        加载本地爬虫的自定义名称
        """
        local_spiders_name = {}
        
        if os.path.exists(self._local_spiders_file):
            try:
                with open(self._local_spiders_file, 'r', encoding='utf-8') as f:
                    local_spiders_name = json.load(f)
            except Exception as e:
                print(f"加载本地爬虫名称失败: {str(e)}")
        
        for key, name in local_spiders_name.items():
            if key in self.spiders:
                self.spiders[key]['name'] = name
    
    def _load_existing_spiders(self):
        """
        加载spiders目录中现有的爬虫文件
        """
        spiders_dir = os.path.join(os.path.dirname(__file__), "spiders")
        if os.path.exists(spiders_dir):
            for filename in os.listdir(spiders_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    key = filename[:-3]
                    file_path = os.path.join(spiders_dir, filename)
                    try:
                        self.add_local_spider(key, file_path)
                        print(f"自动加载爬虫: {key} from {filename}")
                    except Exception as e:
                        print(f"加载爬虫 {filename} 失败: {str(e)}")
    
    def _load_remote_spiders(self):
        """
        加载远程爬虫配置
        """
        remote_spiders = {}
        
        if os.path.exists(self._remote_spiders_file):
            try:
                with open(self._remote_spiders_file, 'r', encoding='utf-8') as f:
                    remote_spiders = json.load(f)
            except Exception as e:
                print(f"加载远程爬虫配置失败: {str(e)}")
        
        for key, config in remote_spiders.items():
            try:
                self.add_python_spider(key, config['script_url'], config.get('name'))
                print(f"自动加载远程爬虫: {key}")
            except Exception as e:
                print(f"加载远程爬虫 {key} 失败: {str(e)}")
    
    def _save_remote_spiders(self):
        """
        保存远程爬虫配置
        """
        remote_spiders = {}
        for key, spider_info in self.spiders.items():
            if spider_info.get('type') == 'remote' and 'script_url' in spider_info:
                remote_spiders[key] = {
                    'script_url': spider_info['script_url'],
                    'name': spider_info.get('name', key)
                }
        
        try:
            with open(self._remote_spiders_file, 'w', encoding='utf-8') as f:
                json.dump(remote_spiders, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存远程爬虫配置失败: {str(e)}")
    
    def _save_local_spiders_name(self):
        """
        保存本地爬虫的自定义名称
        """
        local_spiders_name = {}
        for key, spider_info in self.spiders.items():
            if spider_info.get('type') == 'local' and spider_info.get('name') != key:
                local_spiders_name[key] = spider_info['name']
        
        try:
            with open(self._local_spiders_file, 'w', encoding='utf-8') as f:
                json.dump(local_spiders_name, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存本地爬虫名称失败: {str(e)}")
    
    def add_python_spider(self, key: str, script_url: str, custom_name: str = None):
        """
        添加 Python 爬虫
        """
        try:
            response = requests.get(script_url)
            response.raise_for_status()
            script_content = response.content
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.py', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_file_path = temp_file.name
            
            app_dir = os.path.dirname(os.path.abspath(__file__))
            
            current_dir = os.path.dirname(os.path.abspath(temp_file_path))
            parent_dir = os.path.dirname(current_dir)
            sys.path.insert(0, app_dir)
            sys.path.insert(0, current_dir)
            
            try:
                spec = importlib.util.spec_from_file_location(f"spider_{key}", temp_file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"spider_{key}"] = module
                spec.loader.exec_module(module)
            finally:
                if app_dir in sys.path:
                    sys.path.remove(app_dir)
                if current_dir in sys.path:
                    sys.path.remove(current_dir)
            
            spider_class = getattr(module, 'Spider', None)
            if spider_class is None:
                raise ValueError("脚本中未找到Spider类")
                
            spider_instance = spider_class()
            spider_instance.init()
            
            spider_name = custom_name if custom_name else key
            if not custom_name:
                if hasattr(spider_instance, 'getName') and callable(getattr(spider_instance, 'getName')):
                    name_result = spider_instance.getName()
                    if name_result and name_result != 'Spider':
                        spider_name = name_result
            self.spiders[key] = {
                'instance': spider_instance,
                'name': spider_name,
                'enabled': True,
                'type': 'remote',
                'script_url': script_url,
                'temp_file': temp_file_path
            }
            
            self._save_remote_spiders()
            
        except Exception as e:
            if 'temp_file_path' in locals():
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            raise e
    
    def remove_spider(self, key: str):
        """
        移除爬虫
        """
        if key in self.spiders:
            spider_info = self.spiders[key]
            
            if hasattr(spider_info['instance'], 'destroy'):
                spider_info['instance'].destroy()
            
            if 'temp_file' in spider_info:
                try:
                    os.unlink(spider_info['temp_file'])
                except:
                    pass
            
            del self.spiders[key]
            
            self._save_remote_spiders()
            self._save_local_spiders_name()
    
    def get_spider(self, key: str) -> Optional[Dict[str, Any]]:
        return self.spiders.get(key)
    
    def get_all_spiders(self) -> Dict[str, Dict[str, Any]]:
        return self.spiders.copy()
    
    def reload_spider(self, key: str):
        if key not in self.spiders:
            return
            
        spider_info = self.spiders[key]
        script_url = spider_info['script_url']
        
        self.remove_spider(key)
        self.add_python_spider(key, script_url)
    
    def enable_spider(self, key: str):
        if key in self.spiders:
            self.spiders[key]['enabled'] = True
    
    def disable_spider(self, key: str):
        if key in self.spiders:
            self.spiders[key]['enabled'] = False
    
    def update_spider(self, old_key: str, new_key: str = None, new_name: str = None):
        if old_key not in self.spiders:
            raise ValueError(f"爬虫 '{old_key}' 不存在")
        
        spider_info = self.spiders[old_key]
        
        if new_name is not None:
            spider_info['name'] = new_name
        
        if new_key is not None and new_key != old_key:
            if new_key in self.spiders:
                raise ValueError(f"爬虫标识 '{new_key}' 已存在")
            
            spider_info['key'] = new_key
            self.spiders[new_key] = spider_info
            del self.spiders[old_key]
        
        self._save_remote_spiders()
        self._save_local_spiders_name()
        
        if new_key is not None and new_key != old_key:
            return new_key
        
        return old_key
    
    def add_local_spider(self, key: str, file_path: str, custom_name: str = None):
        try:
            current_dir = os.path.dirname(os.path.abspath(file_path))
            parent_dir = os.path.dirname(current_dir)
            sys.path.insert(0, parent_dir)
            sys.path.insert(0, current_dir)
            
            try:
                spec = importlib.util.spec_from_file_location(f"spider_{key}", file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"spider_{key}"] = module
                spec.loader.exec_module(module)
            finally:
                if parent_dir in sys.path:
                    sys.path.remove(parent_dir)
                if current_dir in sys.path:
                    sys.path.remove(current_dir)
            
            spider_class = getattr(module, 'Spider', None)
            if spider_class is None:
                raise ValueError("脚本中未找到Spider类")
                
            spider_instance = spider_class()
            spider_instance.init()
            
            spider_name = custom_name if custom_name else key
            if not custom_name:
                if hasattr(spider_instance, 'getName') and callable(getattr(spider_instance, 'getName')):
                    name_result = spider_instance.getName()
                    if name_result and name_result != 'Spider':
                        spider_name = name_result
            
            if os.path.exists(self._local_spiders_file):
                try:
                    with open(self._local_spiders_file, 'r', encoding='utf-8') as f:
                        local_spiders_name = json.load(f)
                    if key in local_spiders_name:
                        spider_name = local_spiders_name[key]
                except Exception as e:
                    print(f"读取本地爬虫名称失败: {str(e)}")
            
            self.spiders[key] = {
                'instance': spider_instance,
                'name': spider_name,
                'enabled': True,
                'type': 'local',
                'file_path': file_path
            }
            
        except Exception as e:
            raise e


spider_manager = SpiderManager()
