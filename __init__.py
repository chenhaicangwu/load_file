from .load_file_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
import os

# 注册web目录
WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")

# 导入API以注册路由
try:
    from . import upload_api
    print("LoadFile插件: API路由已注册")
except Exception as e:
    print(f"LoadFile插件: API注册失败 - {e}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
