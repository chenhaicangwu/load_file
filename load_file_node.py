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

class LoadFileWithButton:
    """
    通用文件加载节点 - 支持文件上传功能
    模仿ComfyUI LoadImage节点的实现方式
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # 获取input目录中的所有文件
        input_dir = folder_paths.get_input_directory()
        files = []
        
        if os.path.exists(input_dir):
            for f in os.listdir(input_dir):
                if os.path.isfile(os.path.join(input_dir, f)):
                    files.append(f)
        
        return {
            "required": {
                "file": (sorted(files), {"image_upload": True}),
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
        # 获取文件完整路径
        input_dir = folder_paths.get_input_directory()
        file_path = os.path.join(input_dir, file)
        
        if not os.path.exists(file_path):
            # 返回默认值
            empty_image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            empty_mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            return (
                {"error": "文件不存在", "status": "file_not_found"},
                json.dumps({"status": "文件不存在"}, ensure_ascii=False),
                empty_image,
                empty_mask
            )
        
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
                    "file_path": file_path,
                    "note": "未知格式的模型文件"
                }
            
            return file_data
        except Exception as e:
            raise Exception(f"无法加载模型: {e}")
    
    def _load_text(self, file_path):
        """加载文本文件"""
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
            content = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise Exception("无法解码文本文件")
            
            file_data = {
                "type": "text",
                "content": content,
                "encoding": used_encoding,
                "length": len(content),
                "lines": len(content.splitlines())
            }
            
            return file_data
        except Exception as e:
            raise Exception(f"无法加载文本文件: {e}")
    
    def _load_binary(self, file_path):
        """加载二进制文件"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # 生成文件哈希
            file_hash = hashlib.md5(data).hexdigest()
            
            file_data = {
                "type": "binary",
                "size": len(data),
                "hash": file_hash,
                "preview": data[:100].hex() if len(data) > 0 else "",  # 前100字节的十六进制预览
                "note": "二进制文件，显示前100字节的十六进制预览"
            }
            
            return file_data
        except Exception as e:
            raise Exception(f"无法加载二进制文件: {e}")
    
    def _load_generic(self, file_path):
        """通用文件加载"""
        try:
            stat = os.stat(file_path)
            file_data = {
                "type": "generic",
                "file_path": file_path,
                "size": stat.st_size,
                "note": "通用文件，仅提供基本信息"
            }
            return file_data
        except Exception as e:
            raise Exception(f"无法加载文件: {e}")
    
    @classmethod
    def IS_CHANGED(cls, file, load_mode):
        """检查文件是否发生变化"""
        input_dir = folder_paths.get_input_directory()
        file_path = os.path.join(input_dir, file)
        
        if not os.path.exists(file_path):
            return float("NaN")
        
        # 使用文件修改时间和大小作为变化检测
        stat = os.stat(file_path)
        return f"{stat.st_mtime}_{stat.st_size}"
    
    @classmethod
    def VALIDATE_INPUTS(cls, file, load_mode):
        """验证输入参数"""
        input_dir = folder_paths.get_input_directory()
        file_path = os.path.join(input_dir, file)
        
        if not os.path.exists(file_path):
            return f"文件不存在: {file}"
        
        return True

# 节点注册
NODE_CLASS_MAPPINGS = {
    "LoadFileWithButton": LoadFileWithButton
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadFileWithButton": "Load File (Upload)"
}
