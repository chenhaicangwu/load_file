from .load_file_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
import os

# 注册web目录
WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")

# 导入并注册API路由
try:
    from server import PromptServer
    from .upload_api import FileUploadAPI
    
    # 创建API实例并注册路由
    api_instance = FileUploadAPI()
    
    # 注册路由到PromptServer
    @PromptServer.instance.routes.post('/loadfile/upload')
    async def upload_file_handler(request):
        return await api_instance.upload_file(request)
    
    @PromptServer.instance.routes.get('/loadfile/files')
    async def list_files_handler(request):
        return await api_instance.list_files(request)
    
    print("LoadFile插件: API路由注册成功")
except Exception as e:
    print(f"LoadFile插件: API注册失败 - {e}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
