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

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']




但这个错误与我们的文件上传功能无关，它是关于日志系统的连接问题。

要解决文件上传按钮不显示的问题，我建议：

1. **检查浏览器控制台日志**：打开浏览器开发者工具（F12），查看控制台是否有JavaScript错误。

2. **检查ComfyUI的主日志**：查看ComfyUI启动时的日志输出，看是否有关于我们插件加载的错误信息。

3. **确认前端扩展是否正确加载**：
   - 我们已经确认`loadfile_extension.js`文件位于正确的位置（`web/extensions/`目录下）
   - 但ComfyUI可能没有正确加载这个扩展

4. **修改__init__.py文件**：确保添加了注册web目录的代码：
```python
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