import os
import hashlib
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import json
import mimetypes
from pathlib import Path

class LoadFile:
    """
    通用文件加载节点 - 支持图片、视频、模型文件等多种格式
    兼容ComfyUI多个版本
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # 获取输入目录中的所有文件
        input_dir = folder_paths.get_input_directory()
        files = []
        
        # 支持的文件扩展名
        supported_extensions = {
            # 图片格式
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
            # 视频格式
            '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv',
            # 模型文件
            '.pt', '.pth', '.safetensors', '.ckpt', '.bin',
            # 其他文件
            '.txt', '.json', '.yaml', '.yml', '.xml', '.csv'
        }
        
        # 递归搜索支持的文件
        for root, dirs, filenames in os.walk(input_dir):
            for filename in filenames:
                file_ext = Path(filename).suffix.lower()
                if file_ext in supported_extensions:
                    # 获取相对路径
                    rel_path = os.path.relpath(os.path.join(root, filename), input_dir)
                    files.append(rel_path)
        
        return {
            "required": {
                "file": (sorted(files), {
                    "image_upload": True,  # 启用上传功能
                    "tooltip": "选择要加载的文件或上传新文件"
                }),
            },
            "optional": {
                "load_mode": (["auto", "image", "video", "model", "text", "binary"], {
                    "default": "auto",
                    "tooltip": "文件加载模式，auto为自动检测"
                }),
            }
        }
    
    RETURN_TYPES = ("FILE_DATA", "STRING", "IMAGE", "MASK")
    RETURN_NAMES = ("file_data", "file_info", "image", "mask")
    FUNCTION = "load_file"
    CATEGORY = "loaders"
    
    def load_file(self, file, load_mode="auto"):
        # 获取完整文件路径
        file_path = folder_paths.get_annotated_filepath(file)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文件信息
        file_info = self._get_file_info(file_path)
        
        # 根据模式加载文件
        if load_mode == "auto":
            load_mode = self._detect_file_type(file_path)
        
        file_data = None
        image = None
        mask = None
        
        try:
            if load_mode == "image":
                file_data, image, mask = self._load_image(file_path)
            elif load_mode == "video":
                file_data = self._load_video(file_path)
            elif load_mode == "model":
                file_data = self._load_model(file_path)
            elif load_mode == "text":
                file_data = self._load_text(file_path)
            elif load_mode == "binary":
                file_data = self._load_binary(file_path)
            else:
                file_data = self._load_generic(file_path)
                
        except Exception as e:
            print(f"加载文件时出错: {e}")
            file_data = {"error": str(e), "file_path": file_path}
        
        # 确保返回值不为None
        if image is None:
            # 创建一个空的图像张量
            image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
        if mask is None:
            # 创建一个空的mask张量
            mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            
        return (file_data, json.dumps(file_info, indent=2), image, mask)
    
    def _get_file_info(self, file_path):
        """获取文件基本信息"""
        stat = os.stat(file_path)
        file_ext = Path(file_path).suffix.lower()
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return {
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "file_size": stat.st_size,
            "file_extension": file_ext,
            "mime_type": mime_type,
            "modified_time": stat.st_mtime,
        }
    
    def _detect_file_type(self, file_path):
        """自动检测文件类型"""
        file_ext = Path(file_path).suffix.lower()
        
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        model_exts = {'.pt', '.pth', '.safetensors', '.ckpt', '.bin'}
        text_exts = {'.txt', '.json', '.yaml', '.yml', '.xml', '.csv'}
        
        if file_ext in image_exts:
            return "image"
        elif file_ext in video_exts:
            return "video"
        elif file_ext in model_exts:
            return "model"
        elif file_ext in text_exts:
            return "text"
        else:
            return "binary"
    
    def _load_image(self, file_path):
        """加载图片文件 - 参考ComfyUI LoadImage实现"""
        try:
            i = Image.open(file_path)
            i = ImageOps.exif_transpose(i)
            image = i.convert("RGB")
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            
            # 处理alpha通道作为mask
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((image.shape[1], image.shape[2]), dtype=torch.float32)
            
            file_data = {
                "type": "image",
                "width": i.size[0],
                "height": i.size[1],
                "mode": i.mode,
                "format": i.format,
                "has_alpha": 'A' in i.getbands()
            }
            
            return file_data, image, mask.unsqueeze(0)
            
        except Exception as e:
            raise Exception(f"无法加载图片: {e}")
    
    def _load_video(self, file_path):
        """加载视频文件信息"""
        try:
            # 这里只返回视频文件的基本信息
            # 实际的视频处理可能需要额外的库如opencv-python
            file_data = {
                "type": "video",
                "file_path": file_path,
                "note": "视频文件已加载，需要额外的视频处理节点来解析帧"
            }
            return file_data
        except Exception as e:
            raise Exception(f"无法加载视频: {e}")
    
    def _load_model(self, file_path):
        """加载模型文件"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.safetensors':
                # 对于safetensors文件，只返回文件信息
                # 实际加载需要safetensors库
                file_data = {
                    "type": "model",
                    "format": "safetensors",
                    "file_path": file_path,
                    "note": "SafeTensors模型文件，需要专门的模型加载器"
                }
            elif file_ext in ['.pt', '.pth', '.ckpt']:
                # 对于PyTorch模型文件
                file_data = {
                    "type": "model",
                    "format": "pytorch",
                    "file_path": file_path,
                    "note": "PyTorch模型文件，需要专门的模型加载器"
                }
            else:
                file_data = {
                    "type": "model",
                    "format": "unknown",
                    "file_path": file_path
                }
            
            return file_data
        except Exception as e:
            raise Exception(f"无法加载模型: {e}")
    
    def _load_text(self, file_path):
        """加载文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_data = {
                "type": "text",
                "content": content,
                "length": len(content),
                "lines": len(content.splitlines())
            }
            return file_data
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                file_data = {
                    "type": "text",
                    "content": content,
                    "encoding": "gbk",
                    "length": len(content),
                    "lines": len(content.splitlines())
                }
                return file_data
            except Exception as e:
                raise Exception(f"无法读取文本文件: {e}")
    
    def _load_binary(self, file_path):
        """加载二进制文件"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            file_data = {
                "type": "binary",
                "size": len(content),
                "content_preview": content[:100].hex() if len(content) > 0 else "",
                "note": "二进制文件内容，显示前100字节的十六进制表示"
            }
            return file_data
        except Exception as e:
            raise Exception(f"无法加载二进制文件: {e}")
    
    def _load_generic(self, file_path):
        """通用文件加载"""
        return {
            "type": "generic",
            "file_path": file_path,
            "note": "通用文件类型，请选择合适的加载模式"
        }
    
    @classmethod
    def IS_CHANGED(cls, file, load_mode="auto"):
        """检查文件是否发生变化"""
        try:
            file_path = folder_paths.get_annotated_filepath(file)
            if os.path.exists(file_path):
                # 使用文件的修改时间和大小作为变化检测
                stat = os.stat(file_path)
                return f"{stat.st_mtime}_{stat.st_size}"
            return "file_not_found"
        except:
            return "error"
    
    @classmethod
    def VALIDATE_INPUTS(cls, file, load_mode="auto"):
        """验证输入参数"""
        if not folder_paths.exists_annotated_filepath(file):
            return f"文件不存在: {file}"
        return True

# 节点注册
NODE_CLASS_MAPPINGS = {
    "LoadFile": LoadFile
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadFile": "Load File (Universal)"
}
