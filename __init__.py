from .load_file_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
import os
import sys

# 注册web目录
WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")

# 导入API以注册路由
try:
    from . import upload_api
    # 确保ComfyUI的PromptServer实例可用
    if hasattr(sys.modules['__main__'], 'PromptServer'):
        PromptServer = sys.modules['__main__'].PromptServer
        # 检查PromptServer实例是否已经创建
        if PromptServer.instance:
            # 手动注册路由
            from .upload_api import FileUploadAPI
            api_instance = FileUploadAPI()
            for route in api_instance.routes:
                PromptServer.instance.app.router.add_route(
                    route.method, route.path, route.handler
                )
            print("LoadFile插件: API路由已手动注册")
        else:
            print("LoadFile插件: PromptServer实例未找到，API路由未注册")
    else:
        print("LoadFile插件: __main__中未找到PromptServer，API路由未注册")
    print("LoadFile插件: API模块已导入")
except Exception as e:
    print(f"LoadFile插件: API注册失败 - {e}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
