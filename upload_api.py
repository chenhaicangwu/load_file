import os
import base64
from aiohttp import web
import folder_paths

class FileUploadAPI:
    def __init__(self):
        pass
    
    async def upload_file(self, request):
        """处理文件上传"""
        try:
            # 只处理FormData上传，简化逻辑
            if not request.content_type.startswith('multipart/form-data'):
                return web.json_response({'error': '只支持multipart/form-data格式'}, status=400)
            
            reader = await request.multipart()
            field = await reader.next()
            
            if field.name != 'file':
                return web.json_response({'error': '未找到文件字段'}, status=400)
            
            filename = field.filename
            if not filename:
                return web.json_response({'error': '文件名为空'}, status=400)
            
            # 读取文件内容
            file_data = await field.read()
            
            # 保存文件
            input_dir = folder_paths.get_input_directory()
            file_path = os.path.join(input_dir, filename)
            
            # 如果文件已存在，添加数字后缀
            counter = 1
            original_path = file_path
            while os.path.exists(file_path):
                name, ext = os.path.splitext(original_path)
                file_path = f"{name}_{counter}{ext}"
                counter += 1
            
            # 写入文件
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            return web.json_response({
                'success': True,
                'filename': os.path.basename(file_path),
                'path': file_path,
                'size': len(file_data)
            })
            
        except Exception as e:
            print(f"文件上传异常: {str(e)}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def list_files(self, request):
        """列出input目录中的所有文件"""
        try:
            input_dir = folder_paths.get_input_directory()
            files = []
            
            if os.path.exists(input_dir):
                for f in os.listdir(input_dir):
                    file_path = os.path.join(input_dir, f)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        files.append({
                            'name': f,
                            'size': stat.st_size,
                            'modified': stat.st_mtime
                        })
            
            return web.json_response({'files': files})
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
