import os
import hashlib
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import json
import mimetypes
from pathlib import Path

class LoadFileWithButton:
    """
    通用文件加载节点 - 支持任意文件类型上传
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # 动态获取input目录中的所有文件
        input_dir = folder_paths.get_input_directory()
        files = []
        
        if os.path.exists(input_dir):
            for f in os.listdir(input_dir):
                if os.path.isfile(os.path.join(input_dir, f)):
                    files.append(f)
        
        # 如果没有文件，提供一个默认选项
        if not files:
            files = ["请先上传文件"]
        
        return {
            "required": {
                "file": (sorted(files), {}),
                "load_mode": (["auto", "image", "video", "model", "text", "binary"], {
                    "default": "auto",
                    "tooltip": "文件加载模式，auto为自动检测"
                }),
            }
        }
    
    RETURN_TYPES = ("*", "STRING", "IMAGE", "MASK")
    RETURN_NAMES = ("file_data", "file_info", "image", "mask")
    FUNCTION = "load_file"
    CATEGORY = "loaders"
    OUTPUT_NODE = False
    
    def load_file(self, file, load_mode="auto"):
        # 检查是否为默认提示文本
        if file == "请先上传文件":
            empty_image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            empty_mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            return (
                {"error": "请先上传文件", "status": "no_file"},
                json.dumps({"status": "请使用上传按钮选择文件"}, ensure_ascii=False),
                empty_image,
                empty_mask
            )
        
        # 获取文件完整路径
        input_dir = folder_paths.get_input_directory()
        file_path = os.path.join(input_dir, file)
        
        if not os.path.exists(file_path):
            empty_image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            empty_mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            return (
                {"error": "文件不存在", "status": "file_not_found"},
                json.dumps({"status": "文件不存在，请重新上传"}, ensure_ascii=False),
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
        text_exts = {'.txt', '.json', '.yaml', '.yml', '.xml', '.csv', '.md'}
        
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
        """加载图片文件"""
        try:
            i = Image.open(file_path)
            i = ImageOps.exif_transpose(i)
            image = i.convert("RGB")
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            
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
        return {
            "type": "video",
            "file_path": file_path,
            "note": "视频文件已加载，需要额外的视频处理节点来解析帧"
        }
    
    def _load_model(self, file_path):
        """加载模型文件"""
        file_ext = Path(file_path).suffix.lower()
        return {
            "type": "model",
            "format": file_ext[1:],  # 去掉点号
            "file_path": file_path,
            "note": f"{file_ext}模型文件，需要专门的模型加载器"
        }
    
    def _load_text(self, file_path):
        """加载文本文件"""
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
        
        return {
            "type": "text",
            "content": content,
            "encoding": used_encoding,
            "length": len(content),
            "lines": len(content.splitlines())
        }
    
    def _load_binary(self, file_path):
        """加载二进制文件"""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        file_hash = hashlib.md5(data).hexdigest()
        
        return {
            "type": "binary",
            "size": len(data),
            "hash": file_hash,
            "preview": data[:100].hex() if len(data) > 0 else "",
            "note": "二进制文件，显示前100字节的十六进制预览"
        }
    
    def _load_generic(self, file_path):
        """通用文件加载"""
        stat = os.stat(file_path)
        return {
            "type": "generic",
            "file_path": file_path,
            "size": stat.st_size,
            "note": "通用文件，仅提供基本信息"
        }
    
    @classmethod
    def IS_CHANGED(cls, file, load_mode):
        """检查文件是否发生变化"""
        if file == "请先上传文件":
            return float("NaN")
            
        input_dir = folder_paths.get_input_directory()
        file_path = os.path.join(input_dir, file)
        
        if not os.path.exists(file_path):
            return float("NaN")
        
        stat = os.stat(file_path)
        return f"{stat.st_mtime}_{stat.st_size}"

# 节点注册
NODE_CLASS_MAPPINGS = {
    "LoadFileWithButton": LoadFileWithButton
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadFileWithButton": "Load File (Any Type)"
}