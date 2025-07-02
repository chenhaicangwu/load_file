import os
import hashlib
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import json
import mimetypes
from pathlib import Path
import shutil
import tempfile

class LoadFileWithButton:
    """
    通用文件加载节点 - 支持通过按钮选择本地文件
    兼容ComfyUI 2024年12月版本
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "choose_file_button": ("BUTTON", {
                    "default": "选择文件",
                    "tooltip": "点击选择本地文件"
                }),
            },
            "optional": {
                "file_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "选中的文件路径（自动填充）"
                }),
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
    
    def load_file(self, choose_file_button, file_path="", load_mode="auto"):
        if not file_path or not os.path.exists(file_path):
            # 返回默认值
            empty_image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            empty_mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            return (
                {"error": "请先选择文件", "status": "no_file"},
                json.dumps({"status": "请点击按钮选择文件"}, ensure_ascii=False),
                empty_image,
                empty_mask
            )
        
        # 复制文件到ComfyUI的input目录
        input_dir = folder_paths.get_input_directory()
        filename = os.path.basename(file_path)
        dest_path = os.path.join(input_dir, filename)
        
        # 如果文件不存在于input目录，则复制过去
        if not os.path.exists(dest_path) or os.path.getmtime(file_path) > os.path.getmtime(dest_path):
            try:
                shutil.copy2(file_path, dest_path)
                print(f"文件已复制到: {dest_path}")
            except Exception as e:
                print(f"复制文件失败: {e}")
                dest_path = file_path  # 使用原始路径
        
        # 获取文件信息
        file_info = self._get_file_info(dest_path)
        
        # 根据模式加载文件
        if load_mode == "auto":
            load_mode = self._detect_file_type(dest_path)
        
        file_data = None
        image = None
        mask = None
        
        try:
            if load_mode == "image":
                file_data, image, mask = self._load_image(dest_path)
            elif load_mode == "video":
                file_data = self._load_video(dest_path)
            elif load_mode == "model":
                file_data = self._load_model(dest_path)
            elif load_mode == "text":
                file_data = self._load_text(dest_path)
            elif load_mode == "binary":
                file_data = self._load_binary(dest_path)
            else:
                file_data = self._load_generic(dest_path)
                
        except Exception as e:
            print(f"加载文件时出错: {e}")
            file_data = {"error": str(e), "file_path": dest_path}
        
        # 确保返回值不为None
        if image is None:
            image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
        if mask is None:
            mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            
        return (file_data, json.dumps(file_info, indent=2, ensure_ascii=False), image, mask)
    
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
                file_data = {
                    "type": "model",
                    "format": "safetensors",
                    "file_path": file_path,
                    "note": "SafeTensors模型文件，需要专门的模型加载器"
                }
            elif file_ext in ['.pt', '.pth', '.ckpt']:
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

# 节点注册
NODE_CLASS_MAPPINGS = {
    "LoadFileWithButton": LoadFileWithButton
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadFileWithButton": "Load File (Button)"
}
