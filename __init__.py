"""
LoadFile节点 - ComfyUI通用文件加载节点

该节点能够加载多种类型的文件，包括图像、视频、模型文件（特别是pt/safetensors格式）、
潜在空间文件和文本文件。节点会自动检测文件类型，并根据文件类型返回不同的输出。

作者: Reporter
版本: 1.0.0
"""

# 导入必要的模块
from .load_file_node import LoadFile, NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# 确保导出NODE_CLASS_MAPPINGS和NODE_DISPLAY_NAME_MAPPINGS
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

# 打印加载信息
print("\n正在初始化通用文件加载节点 (LoadFile)...")
print("支持的文件类型:")
print("- 图像: " + ", ".join(LoadFile.IMAGE_EXTENSIONS))
print("- 模型: " + ", ".join(LoadFile.MODEL_EXTENSIONS))
print("- 潜在空间: " + ", ".join(LoadFile.LATENT_EXTENSIONS))
print("- 视频: " + ", ".join(LoadFile.VIDEO_EXTENSIONS))
print("- 文本: " + ", ".join(LoadFile.TEXT_EXTENSIONS))
print("使用方法: 选择文件，并将文件类型设置为'auto'或手动指定文件类型\n")
