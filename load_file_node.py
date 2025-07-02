import os
import torch
import numpy as np
import hashlib
import traceback
from PIL import Image, ImageOps, ImageSequence, ImageFile
from safetensors.torch import load_file as load_safetensors

import folder_paths
import node_helpers
import comfy.utils

class LoadFile:
    """
    通用文件加载节点，支持多种文件类型，包括图像、视频、模型文件和潜在空间文件等。
    该节点可以自动检测文件类型，并根据文件类型调用相应的加载函数。
    
    功能特点:
    1. 自动检测文件类型，或允许用户手动指定
    2. 支持多种文件格式，包括图像、视频、模型文件、潜在空间文件和文本文件
    3. 根据文件类型返回不同的输出类型
    4. 提供详细的错误处理和日志记录
    """
    
    # 支持的文件类型及其扩展名
    IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif']
    MODEL_EXTENSIONS = ['.ckpt', '.pt', '.safetensors', '.pth', '.bin']
    LATENT_EXTENSIONS = ['.latent']
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.webm', '.mkv']
    TEXT_EXTENSIONS = ['.txt', '.json', '.yaml', '.yml']
    
    @classmethod
    def INPUT_TYPES(s):
        # 获取输入目录中的所有文件
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        
        return {
            "required": {
                "file": (sorted(files), {"file_upload": True, "tooltip": "要加载的文件"}),
                "file_type": (["auto", "image", "model", "latent", "video", "text"], 
                             {"default": "auto", "tooltip": "文件类型，选择'auto'将自动检测"})
            }
        }

    CATEGORY = "loaders"
    
    # 动态返回类型，将在运行时根据文件类型确定
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "load_file"
    
    def load_file(self, file, file_type):
        """
        加载文件并根据文件类型返回相应的数据
        
        参数:
            file (str): 文件名
            file_type (str): 文件类型，可以是'auto'、'image'、'model'、'latent'、'video'或'text'
            
        返回:
            根据文件类型返回不同的数据
        """
        try:
            # 获取文件路径
            file_path = folder_paths.get_annotated_filepath(file)
            
            print(f"正在加载文件: {file_path}")
            
            # 如果文件类型为'auto'，则自动检测文件类型
            detected_type = file_type
            if file_type == "auto":
                detected_type = self.detect_file_type(file_path)
                print(f"自动检测到文件类型: {detected_type}")
            
            # 根据文件类型调用相应的加载函数
            if detected_type == "image":
                return self.load_image(file_path)
            elif detected_type == "model":
                return self.load_model(file_path)
            elif detected_type == "latent":
                return self.load_latent(file_path)
            elif detected_type == "video":
                return self.load_video(file_path)
            elif detected_type == "text":
                return self.load_text(file_path)
            else:
                raise ValueError(f"不支持的文件类型: {detected_type}")
        except Exception as e:
            print(f"加载文件时出错: {e}")
            print(traceback.format_exc())
            raise RuntimeError(f"加载文件失败: {str(e)}")
    
    def detect_file_type(self, file_path):
        """
        根据文件扩展名和内容检测文件类型
        
        参数:
            file_path (str): 文件路径
            
        返回:
            str: 文件类型，可以是'image'、'model'、'latent'、'video'或'text'
        """
        # 获取文件扩展名（小写）
        ext = os.path.splitext(file_path)[1].lower()
        
        # 根据扩展名判断文件类型
        if ext in self.IMAGE_EXTENSIONS:
            print(f"通过扩展名 {ext} 识别为图像文件")
            return "image"
        elif ext in self.LATENT_EXTENSIONS:
            print(f"通过扩展名 {ext} 识别为潜在空间文件")
            return "latent"
        elif ext in self.VIDEO_EXTENSIONS:
            print(f"通过扩展名 {ext} 识别为视频文件")
            return "video"
        elif ext in self.TEXT_EXTENSIONS:
            print(f"通过扩展名 {ext} 识别为文本文件")
            return "text"
        elif ext in self.MODEL_EXTENSIONS:
            print(f"通过扩展名 {ext} 识别为模型文件")
            # 对于模型文件，尝试进一步检查文件内容以确定具体的模型类型
            try:
                # 使用安全的加载方式检查模型文件
                if ext == '.safetensors':
                    # 尝试加载元数据以检查模型类型
                    try:
                        metadata = comfy.utils.load_metadata_from_safetensors(file_path)
                        if metadata:
                            print(f"从safetensors元数据中检测到模型信息: {list(metadata.keys())[:10]}")
                            # 根据元数据判断模型类型
                            if any(key in metadata for key in ["sd_model_name", "ss_sd_model_name", "model_config"]):
                                return "model"
                            elif "vae" in metadata or "vae_config" in metadata:
                                return "model"  # VAE模型
                    except Exception as e:
                        print(f"加载safetensors元数据失败: {e}")
                
                # 如果没有明确的元数据或不是safetensors文件，尝试通过文件大小和名称判断
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
                file_name = os.path.basename(file_path).lower()
                
                print(f"文件大小: {file_size:.2f} MB")
                
                # 根据文件名中的关键词判断
                if any(keyword in file_name for keyword in ["vae", "autoencoder"]):
                    print(f"通过文件名关键词识别为VAE模型")
                    return "model"
                elif any(keyword in file_name for keyword in ["lora", "lycoris"]):
                    print(f"通过文件名关键词识别为LoRA模型")
                    return "model"
                elif any(keyword in file_name for keyword in ["clip", "text_encoder"]):
                    print(f"通过文件名关键词识别为CLIP模型")
                    return "model"
                elif any(keyword in file_name for keyword in ["unet", "diffusion"]):
                    print(f"通过文件名关键词识别为UNet模型")
                    return "model"
                
                # 如果无法通过文件名判断，则根据文件大小判断
                # 大多数完整模型文件大小超过1GB
                if file_size > 1000:
                    print(f"通过文件大小识别为完整模型")
                    return "model"
                # VAE模型通常在150-350MB之间
                elif 100 < file_size < 400:
                    print(f"通过文件大小识别可能为VAE模型")
                    return "model"
                # LoRA模型通常小于100MB
                elif file_size < 100:
                    print(f"通过文件大小识别可能为LoRA模型")
                    return "model"
                
                # 默认为模型文件
                return "model"
            except Exception as e:
                print(f"模型文件类型检测失败: {e}")
                # 如果检测失败，默认为模型文件
                return "model"
        else:
            # 对于未知扩展名的文件，尝试通过内容判断
            try:
                # 尝试作为图像打开
                Image.open(file_path)
                print(f"通过内容识别为图像文件")
                return "image"
            except Exception as e:
                print(f"尝试作为图像打开失败: {e}")
                # 检查文件大小
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
                if file_size > 100:  # 如果文件大于100MB，可能是模型文件
                    print(f"通过文件大小 {file_size:.2f} MB 推测可能为模型文件")
                    return "model"
                else:
                    print(f"默认识别为文本文件")
                    return "text"
    
    def load_image(self, image_path):
        """
        加载图像文件
        
        参数:
            image_path (str): 图像文件路径
            
        返回:
            tuple: (IMAGE, MASK)
        """
        # 使用与LoadImage节点相同的加载逻辑
        img = node_helpers.pillow(Image.open, image_path)
        
        output_images = []
        output_masks = []
        w, h = None, None
        
        excluded_formats = ['MPO']
        
        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)
            
            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")
            
            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]
            
            if image.size[0] != w or image.size[1] != h:
                continue
            
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            elif i.mode == 'P' and 'transparency' in i.info:
                mask = np.array(i.convert('RGBA').getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))
        
        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]
        
        return (output_image, output_mask)
    
    def load_latent(self, latent_path):
        """
        加载潜在空间文件
        
        参数:
            latent_path (str): 潜在空间文件路径
            
        返回:
            tuple: (LATENT,)
        """
        # 使用与LoadLatent节点相同的加载逻辑
        latent = load_safetensors(latent_path, device="cpu")
        multiplier = 1.0
        if "latent_format_version_0" not in latent:
            multiplier = 1.0 / 0.18215
        samples = {"samples": latent["latent_tensor"].float() * multiplier}
        return (samples,)
    
    def load_model(self, model_path):
        """
        加载模型文件
        
        参数:
            model_path (str): 模型文件路径
            
        返回:
            tuple: (MODEL, CLIP, VAE)
        """
        print(f"尝试加载模型文件: {model_path}")
        
        # 获取文件扩展名和文件名
        ext = os.path.splitext(model_path)[1].lower()
        file_name = os.path.basename(model_path).lower()
        
        # 检查文件名中的关键词，尝试确定模型类型
        is_vae = any(keyword in file_name for keyword in ["vae", "autoencoder"])
        is_lora = any(keyword in file_name for keyword in ["lora", "lycoris"])
        is_clip = any(keyword in file_name for keyword in ["clip", "text_encoder"])
        is_unet = any(keyword in file_name for keyword in ["unet", "diffusion"])
        
        # 首先尝试作为完整模型加载
        if not (is_vae or is_lora or is_clip or is_unet):
            try:
                print("尝试作为完整检查点加载...")
                out = comfy.sd.load_checkpoint_guess_config(
                    model_path, 
                    output_vae=True, 
                    output_clip=True, 
                    embedding_directory=folder_paths.get_folder_paths("embeddings")
                )
                print("成功加载完整检查点")
                return out[:3]  # 返回MODEL, CLIP, VAE
            except Exception as e:
                print(f"作为完整检查点加载失败: {e}")
        
        # 如果是VAE或者完整模型加载失败，尝试作为VAE加载
        if is_vae or True:
            try:
                print("尝试作为VAE模型加载...")
                sd = comfy.utils.load_torch_file(model_path)
                vae = comfy.sd.VAE(sd=sd)
                print("成功加载VAE模型")
                return (None, None, vae)  # 返回None, None, VAE
            except Exception as e:
                print(f"作为VAE模型加载失败: {e}")
        
        # 如果是CLIP或者前面的加载都失败了，尝试作为CLIP模型加载
        if is_clip or True:
            try:
                print("尝试作为CLIP模型加载...")
                clip = comfy.sd.load_clip(
                    ckpt_paths=[model_path], 
                    embedding_directory=folder_paths.get_folder_paths("embeddings")
                )
                print("成功加载CLIP模型")
                return (None, clip, None)  # 返回None, CLIP, None
            except Exception as e:
                print(f"作为CLIP模型加载失败: {e}")
        
        # 如果是LoRA或者前面的加载都失败了，尝试作为LoRA加载
        if is_lora or True:
            try:
                print("尝试作为LoRA模型加载...")
                # 由于LoRA需要应用到现有模型上，我们不能直接加载它
                # 这里只是验证文件是否可以作为LoRA加载
                lora = comfy.utils.load_torch_file(model_path, safe_load=True)
                print("成功验证LoRA模型格式")
                # 返回None，因为LoRA需要应用到现有模型上
                return (None, None, None)
            except Exception as e:
                print(f"作为LoRA模型加载失败: {e}")
        
        # 如果所有尝试都失败了
        raise ValueError(f"无法加载模型文件: {model_path}，尝试了所有可能的模型类型但都失败了")
    
    def load_video(self, video_path):
        """
        加载视频文件
        
        参数:
            video_path (str): 视频文件路径
            
        返回:
            tuple: (VIDEO,) 或 (IMAGE, MASK) 如果只提取第一帧
        """
        # 尝试使用OpenCV加载视频
        try:
            import cv2
            print(f"使用OpenCV加载视频: {video_path}")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
                
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            print(f"视频信息: {width}x{height}, {fps} FPS, {frame_count} 帧")
            
            # 为了避免内存问题，限制加载的帧数
            max_frames = min(frame_count, 300)  # 最多加载300帧
            frames = []
            
            for i in range(max_frames):
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # 转换BGR到RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 归一化到0-1范围
                frame = frame.astype(np.float32) / 255.0
                # 转换为PyTorch张量
                frame = torch.from_numpy(frame)
                frames.append(frame)
                
                # 每100帧打印一次进度
                if (i + 1) % 100 == 0:
                    print(f"已加载 {i + 1}/{max_frames} 帧")
            
            cap.release()
            
            # 如果没有帧，抛出异常
            if len(frames) == 0:
                raise ValueError(f"无法从视频中提取帧: {video_path}")
            
            # 将所有帧堆叠为一个批次
            video_tensor = torch.stack(frames, dim=0)
            print(f"成功加载视频，形状: {video_tensor.shape}")
            
            # 创建一个空的掩码
            mask = torch.zeros((video_tensor.shape[0], height, width), dtype=torch.float32)
            
            # 如果只有一帧，则作为图像返回
            if video_tensor.shape[0] == 1:
                print("视频只有一帧，作为图像返回")
                return (video_tensor.squeeze(0), mask.squeeze(0))
            
            return (video_tensor, mask)
            
        except ImportError:
            print("未安装OpenCV，尝试使用PIL加载视频的第一帧")
            # 如果没有OpenCV，尝试使用PIL加载视频的第一帧
            try:
                # 使用PIL加载视频的第一帧
                from PIL import ImageFile
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                
                img = Image.open(video_path)
                # 转换为RGB模式
                img = img.convert("RGB")
                # 转换为NumPy数组
                img_np = np.array(img).astype(np.float32) / 255.0
                # 转换为PyTorch张量
                img_tensor = torch.from_numpy(img_np)[None,]
                # 创建一个空的掩码
                mask = torch.zeros((img.height, img.width), dtype=torch.float32, device="cpu")
                
                print("成功加载视频的第一帧作为图像")
                return (img_tensor, mask)
            except Exception as e:
                print(f"使用PIL加载视频第一帧失败: {e}")
                raise ImportError("加载视频需要安装OpenCV库: pip install opencv-python")
    
    def load_text(self, text_path):
        """
        加载文本文件
        
        参数:
            text_path (str): 文本文件路径
            
        返回:
            tuple: (STRING,)
        """
        # 读取文本文件内容
        with open(text_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return (content,)
    
    @classmethod
    def IS_CHANGED(s, file, file_type):
        """
        检查文件是否已更改
        
        参数:
            file (str): 文件名
            file_type (str): 文件类型
            
        返回:
            str: 文件的哈希值
        """
        image_path = folder_paths.get_annotated_filepath(file)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()
    
    @classmethod
    def VALIDATE_INPUTS(s, file, file_type):
        """
        验证输入参数是否有效
        
        参数:
            file (str): 文件名
            file_type (str): 文件类型
            
        返回:
            bool or str: 如果输入有效，则返回True；否则返回错误消息
        """
        if not folder_paths.exists_annotated_filepath(file):
            return f"无效的文件: {file}"
        return True

    @classmethod
    def OUTPUT_NODE(s, file_type="auto"):
        """
        根据文件类型动态确定输出类型
        
        参数:
            file_type (str): 文件类型
            
        返回:
            tuple: 输出类型和名称
        """
        if file_type == "auto":
            # 对于自动检测，返回所有可能的输出类型
            return {
                "ui": {
                    "warning": "输出类型将根据检测到的文件类型动态确定"
                },
                "output": (
                    ("IMAGE", "MASK", "MODEL", "CLIP", "VAE", "LATENT", "VIDEO", "STRING"),
                    ("image", "mask", "model", "clip", "vae", "latent", "video", "text")
                )
            }
        elif file_type == "image":
            return {
                "output": (("IMAGE", "MASK"), ("image", "mask"))
            }
        elif file_type == "model":
            return {
                "output": (("MODEL", "CLIP", "VAE"), ("model", "clip", "vae"))
            }
        elif file_type == "latent":
            return {
                "output": (("LATENT",), ("latent",))
            }
        elif file_type == "video":
            return {
                "output": (("IMAGE", "MASK"), ("video_frames", "video_mask"))
            }
        elif file_type == "text":
            return {
                "output": (("STRING",), ("text",))
            }
        else:
            return {
                "output": (("*",), ("output",))
            }

# 注册节点
NODE_CLASS_MAPPINGS = {
    "LoadFile": LoadFile
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadFile": "Load File (通用)"
}

# 打印加载信息
print("\n加载通用文件加载节点 (LoadFile)...")
print("支持的文件类型:")
print("- 图像: " + ", ".join(LoadFile.IMAGE_EXTENSIONS))
print("- 模型: " + ", ".join(LoadFile.MODEL_EXTENSIONS))
print("- 潜在空间: " + ", ".join(LoadFile.LATENT_EXTENSIONS))
print("- 视频: " + ", ".join(LoadFile.VIDEO_EXTENSIONS))
print("- 文本: " + ", ".join(LoadFile.TEXT_EXTENSIONS))
print("使用方法: 选择文件，并将文件类型设置为'auto'或手动指定文件类型\n")
