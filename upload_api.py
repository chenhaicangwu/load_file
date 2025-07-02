import os
import json
import base64
from aiohttp import web
import folder_paths
from server import PromptServer

class FileUploadAPI:
    def __init__(self):
        self.routes = [
            web.post('/loadfile/upload', self.upload_file),
            web.get('/loadfile/files', self.list_files)
        ]
    
    async def upload_file(self, request):
        """处理文件上传"""
        try:
            # 获取上传的文件数据
            data = await request.json()
            filename = data.get('filename')
            file_data = data.get('data')  # base64编码的文件数据
            
            if not filename or not file_data:
                return web.json_response({'error': '缺少文件名或文件数据'}, status=400)
            
            # 解码base64数据
            try:
                file_bytes = base64.b64decode(file_data)
            except Exception as e:
                return web.json_response({'error': f'文件数据解码失败: {str(e)}'}, status=400)
            
            # 保存到input目录
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
                f.write(file_bytes)
            
            return web.json_response({
                'success': True,
                'filename': os.path.basename(file_path),
                'path': file_path,
                'size': len(file_bytes)
            })
            
        except Exception as e:
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

# 注册API路由
api_instance = FileUploadAPI()
for route in api_instance.routes:
    PromptServer.instance.app.router.add_route(route.method, route.path, route.handler)