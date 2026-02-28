from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.spider_instance import spider_manager
from app.tvbox_parser import TVBoxConfigParser
import json
import os
import shutil

router = APIRouter()

class ImportTVBoxConfigRequest(BaseModel):
    config_url: str

class AddPythonSpiderRequest(BaseModel):
    key: str
    script_url: str
    name: Optional[str] = None

# 视频详情页参数映射模板
VIDEO_DETAIL_FIELDS = {
    'vod_id': '视频唯一标识符',
    'vod_name': '视频标题/名称',
    'vod_pic': '封面图片URL',
    'vod_director': '导演/上传者',
    'vod_actor': '演员/主演',
    'vod_remarks': '备注/时长',
    'vod_content': '视频简介/描述',
    'vod_play_from': '播放源名称（如：线路1、线路2）',
    'vod_play_url': '播放链接（支持多种格式：直接链接、名称$链接、链接1#链接2#...）',
    'type_name': '分类名称',
    'vod_year': '年份',
    'vod_area': '地区',
    'episodes_names': '集数名称列表（如：["第1集", "第2集"]）',
    'episodes': '集数播放链接列表（与episodes_names一一对应）'
}

def normalize_video_detail(video_detail: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化视频详情数据，确保所有必需的字段都存在
    
    参数说明：
    - vod_id: 视频唯一标识符
    - vod_name: 视频标题/名称
    - vod_pic: 封面图片URL
    - vod_director: 导演/上传者
    - vod_actor: 演员/主演
    - vod_remarks: 备注/时长
    - vod_content: 视频简介/描述
    - vod_play_from: 播放源名称（如：线路1、线路2）
    - vod_play_url: 播放链接（支持多种格式）
    - type_name: 分类名称
    - vod_year: 年份
    - vod_area: 地区
    """
    normalized = {
        'vod_id': video_detail.get('vod_id', ''),
        'vod_name': video_detail.get('vod_name', ''),
        'vod_pic': video_detail.get('vod_pic', ''),
        'vod_director': video_detail.get('vod_director', ''),
        'vod_actor': video_detail.get('vod_actor', ''),
        'vod_remarks': video_detail.get('vod_remarks', ''),
        'vod_content': video_detail.get('vod_content', ''),
        'vod_play_from': video_detail.get('vod_play_from', ''),
        'vod_play_url': video_detail.get('vod_play_url', ''),
        'type_name': video_detail.get('type_name', ''),
        'vod_year': video_detail.get('vod_year', ''),
        'vod_area': video_detail.get('vod_area', ''),
        'episodes_names': video_detail.get('episodes_names', []),
        'episodes': video_detail.get('episodes', [])
    }
    
    # 处理播放链接格式标准化
    if isinstance(normalized['vod_play_url'], list):
        normalized['vod_play_url'] = '#'.join(normalized['vod_play_url'])
    
    return normalized

@router.get("/classify")
async def get_classify():
    """获取分类列表"""
    try:
        spiders = spider_manager.get_all_spiders()
        result = []
        
        for key, spider_info in spiders.items():
            spider = spider_info['instance']
            classify_list = spider.homeVideoContent().get('class', [])
            for cls in classify_list:
                cls['key'] = key  # 添加爬虫标识
            result.extend(classify_list)
        
        return {
            "code": 0,
            "msg": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos")
async def get_videos(t: str = Query(..., description="分类ID"), pg: int = Query(1, description="页码")):
    """获取分类下的视频列表"""
    try:
        # 这里需要解析t参数获取爬虫key和分类ID
        spider_key = t.split('_')[0] if '_' in t else t
        cate_id = t
        
        spider_info = spider_manager.get_spider(spider_key)
        if not spider_info:
            raise HTTPException(status_code=404, detail="Spider not found")
        
        spider = spider_info['instance']
        result = spider.categoryContent(cate_id, str(pg), False, "")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail")
async def get_detail(id: str = Query(..., description="视频ID")):
    """获取视频详情"""
    try:
        # 解析ID获取爬虫key和视频ID
        parts = id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid video ID format")
        
        spider_key, video_id = parts
        
        spider_info = spider_manager.get_spider(spider_key)
        if not spider_info:
            raise HTTPException(status_code=404, detail="Spider not found")
        
        spider = spider_info['instance']
        result = spider.detailContent([video_id])
        
        # 标准化视频详情
        if result.get('list'):
            normalized_data = normalize_video_detail(result['list'][0])
            result['list'][0] = normalized_data
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/playurl")
async def get_play_url(flag: str = Query(..., description="播放源"), id: str = Query(..., description="视频链接")):
    """获取播放地址"""
    try:
        # 解析ID获取爬虫key和播放链接
        parts = id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid video ID format")
        
        spider_key, play_url = parts
        
        spider_info = spider_manager.get_spider(spider_key)
        if not spider_info:
            raise HTTPException(status_code=404, detail="Spider not found")
        
        spider = spider_info['instance']
        result = spider.playerContent(flag, play_url, [])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search(kw: str = Query(..., description="搜索关键词"), pg: int = Query(1, description="页码")):
    """搜索视频"""
    try:
        result = {"code": 0, "msg": "success", "data": []}
        
        # 在所有爬虫中搜索
        spiders = spider_manager.get_all_spiders()
        for key, spider_info in spiders.items():
            spider = spider_info['instance']
            try:
                search_result = spider.searchContent(kw, str(pg))
                
                # 如果搜索结果不为空，添加到最终结果中
                if search_result and search_result.get('list'):
                    for video in search_result['list']:
                        # 为视频ID添加爬虫标识前缀
                        if 'vod_id' in video:
                            video['vod_id'] = f"{key}_{video['vod_id']}"
                        result['data'].append(video)
            except:
                # 如果某个爬虫搜索失败，继续下一个
                continue
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-tvbox-config")
async def import_tvbox_config(request: ImportTVBoxConfigRequest):
    """导入 TVBox 配置"""
    try:
        parser = TVBoxConfigParser()
        config = parser.load_config(request.config_url)
        
        # 将配置中的爬虫添加到管理器
        for key, spider_config in config.items():
            if spider_config.get('type') == 'python':
                spider_manager.add_python_spider(key, spider_config['script_url'])
        
        return {"code": 0, "msg": "success", "data": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-python-spider")
async def add_python_spider(request: AddPythonSpiderRequest):
    """添加 Python 爬虫"""
    try:
        spider_manager.add_python_spider(request.key, request.script_url, request.name)
        return {"code": 0, "msg": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/spiders/upload")
async def upload_python_spider(key: str = Query(..., description="爬虫标识"), name: str = Query(None, description="爬虫名称"), file: UploadFile = File(..., description="Python爬虫文件")):
    """上传 Python 爬虫文件"""
    try:
        # 检查文件类型
        if not file.filename.endswith('.py'):
            raise HTTPException(status_code=400, detail="文件必须是 .py 格式")
        
        # 读取文件内容
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # 保存文件到spiders目录
        spiders_dir = os.path.join(os.path.dirname(__file__), "spiders")
        if not os.path.exists(spiders_dir):
            os.makedirs(spiders_dir)
        
        file_path = os.path.join(spiders_dir, f"{key}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        # 添加爬虫到管理器
        spider_manager.add_local_spider(key, file_path, name)
        
        return {"code": 0, "msg": "success", "data": {"key": key, "filename": file.filename}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateSpiderRequest(BaseModel):
    new_key: Optional[str] = None
    new_name: Optional[str] = None


@router.put("/spiders/{key}")
async def update_spider(key: str, request: UpdateSpiderRequest):
    """更新爬虫信息"""
    try:
        updated_key = spider_manager.update_spider(key, request.new_key, request.new_name)
        return {"code": 0, "msg": "success", "data": {"key": updated_key}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spider/{key}")
async def spider_api(
    key: str, 
    act: str = Query(None), 
    t: str = Query(None), 
    pg: str = Query("1"), 
    wd: str = Query(None),
    fl: str = Query(None),  # 筛选参数 (旧格式，向后兼容)
    extend: str = Query(None),  # 筛选参数 (TVBox标准格式)
    flag: str = Query("")  # 播放源标识
):
    """
    单个爬虫API端点，兼容TVBox协议
    :param key: 爬虫标识
    :param act: 操作类型 (home/vod/detail/search/play)
    :param t: 分类ID或视频ID或播放ID
    :param pg: 页码
    :param wd: 搜索关键词
    :param fl: 筛选参数 (旧格式，向后兼容)
    :param extend: 筛选参数 (TVBox标准格式)
    :param flag: 播放源标识
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        spider = spider_info['instance']
        
        # 根据不同操作类型调用相应方法
        if act == "home":
            # 首页数据（分类列表）
            result = spider.homeContent(True)  # 启用筛选
            return result
        elif act == "homev2":
            # 首页数据（新版）
            result = spider.homeContent(False)  # 不启用筛选
            return result
        elif act == "category":
            # 分类视频列表
            if t is None:
                raise HTTPException(status_code=400, detail="缺少分类ID参数t")
            
            # 处理筛选参数 (优先使用extend参数，向后兼容fl参数)
            extend_params = {}
            filter_param = extend or fl  # 优先使用extend参数
            if filter_param:
                try:
                    import json
                    extend_params = json.loads(filter_param)
                except:
                    # 如果fl不是JSON格式，则当作普通参数处理
                    extend_params = {'fl': fl}
            
            result = spider.categoryContent(t, pg, False, extend_params)
            return result
        elif act == "detail":
            # 视频详情
            if t is None:
                raise HTTPException(status_code=400, detail="缺少视频ID参数t")
            result = spider.detailContent([t])
            return result
        elif act == "search":
            # 搜索
            if wd is None:
                raise HTTPException(status_code=400, detail="缺少搜索关键词参数wd")
            result = spider.searchContent(wd, '', pg)
            return result
        elif act == "play":
            # 播放地址
            if t is None:
                raise HTTPException(status_code=400, detail="缺少播放ID参数t")
            result = spider.playerContent(flag, t, [])
            return result
        else:
            # 默认行为，可能是首页数据
            result = spider.homeContent(True)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/spiders/{key}")
async def delete_spider(key: str):
    """
    删除爬虫
    :param key: 爬虫标识
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        # 检查是否为本地爬虫，如果是则删除文件
        if spider_info.get('type') == 'local' and 'file_path' in spider_info:
            file_path = spider_info['file_path']
            try:
                import os
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"删除爬虫文件失败 {file_path}: {str(e)}")
        
        # 从管理器中移除爬虫
        spider_manager.remove_spider(key)
        
        return {"code": 0, "msg": "success", "data": {"key": key}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spiders/{key}/reload")
async def reload_spider(key: str):
    """
    重新加载爬虫
    :param key: 爬虫标识
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        # 检查是否为本地爬虫
        if spider_info.get('type') == 'local' and 'file_path' in spider_info:
            file_path = spider_info['file_path']
            
            # 重新加载爬虫
            spider_manager.remove_spider(key)
            spider_manager.add_local_spider(key, file_path)
            
            return {"code": 0, "msg": "success", "data": {"key": key}}
        else:
            raise HTTPException(status_code=400, detail="只能重新加载本地爬虫")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spiders")
async def list_spiders():
    """列出所有爬虫"""
    try:
        spiders = spider_manager.get_all_spiders()
        result = []
        for key, spider_info in spiders.items():
            result.append({
                "key": key,
                "name": spider_info['name'],
                "enabled": spider_info['enabled'],
                "type": spider_info.get('type', 'unknown')  # 添加类型信息
            })
        return {"code": 0, "msg": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spider/{key}/proxy")
async def spider_proxy(key: str, url: str = Query(..., description="图片URL")):
    """
    图片代理端点，用于获取爬虫返回的图片
    :param key: 爬虫标识
    :param url: 图片URL
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        spider = spider_info['instance']
        
        # 调用爬虫的localProxy方法
        param = {'url': url}
        result = spider.localProxy(param)
        
        # 返回图片数据
        if result and len(result) >= 3:
            status_code, content_type, data = result[0], result[1], result[2]
            return Response(content=data, media_type=content_type, status_code=status_code)
        else:
            raise HTTPException(status_code=500, detail="Invalid proxy response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))