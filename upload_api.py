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
    
    # 在FileUploadAPI类中添加新的处理方法
    async def upload_file(self, request):
        """处理文件上传"""
        try:
            # 检查请求类型
            content_type = request.headers.get('Content-Type', '')
            
            if 'multipart/form-data' in content_type:
                # 处理FormData上传
                reader = await request.multipart()
                
                # 获取文件字段
                field = await reader.next()
                if field.name == 'file':
                    filename = field.filename
                    # 读取文件内容
                    file_data = b''
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        file_data += chunk
                    
                    # 保存文件逻辑...
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
                
                return web.json_response({'error': '未找到文件字段'}, status=400)
            else:
                # 原有的JSON处理逻辑
                # ... 保持不变 ...
        
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

# 注册API路由
api_instance = FileUploadAPI()
for route in api_instance.routes:
    PromptServer.instance.app.router.add_route(route.method, route.path, route.handler)
