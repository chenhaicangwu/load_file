import { app } from "/extensions/scripts/app.js";
import { api } from "/extensions/scripts/api.js";

// 文件上传工具类
class FileUploader {
    static async uploadFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const base64Data = e.target.result.split(',')[1];
                    const response = await api.fetchApi('/loadfile/upload', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            filename: file.name,
                            data: base64Data
                        })
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        resolve(result);
                    } else {
                        const error = await response.json();
                        reject(new Error(error.error || '上传失败'));
                    }
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = () => reject(new Error('文件读取失败'));
            reader.readAsDataURL(file);
        });
    }
    
    static async refreshFileList() {
        try {
            const response = await api.fetchApi('/loadfile/files');
            if (response.ok) {
                const result = await response.json();
                return result.files.map(f => f.name);
            }
        } catch (error) {
            console.error('获取文件列表失败:', error);
        }
        return [];
    }
}

// 注册节点扩展
app.registerExtension({
    name: "LoadFileWithButton.Upload",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoadFileWithButton") {
            // 保存原始方法
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                // 调用原始方法
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // 添加上传按钮
                this.addWidget("button", "📁 选择文件上传", null, () => {
                    this.selectAndUploadFile();
                });
                
                // 添加刷新按钮
                this.addWidget("button", "🔄 刷新文件列表", null, () => {
                    this.refreshFileList();
                });
            };
            
            // 文件选择和上传方法
            nodeType.prototype.selectAndUploadFile = function() {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = '*/*'; // 接受所有文件类型
                fileInput.style.display = 'none';
                
                fileInput.onchange = async (event) => {
                    const file = event.target.files[0];
                    if (!file) return;
                    
                    try {
                        // 显示上传进度
                        this.showUploadProgress(true);
                        
                        // 上传文件
                        const result = await FileUploader.uploadFile(file);
                        
                        // 更新文件选择器
                        await this.refreshFileList();
                        
                        // 自动选择刚上传的文件
                        const fileWidget = this.widgets.find(w => w.name === "file");
                        if (fileWidget) {
                            fileWidget.value = result.filename;
                        }
                        
                        // 触发节点更新
                        this.setDirtyCanvas(true, true);
                        
                        console.log('文件上传成功:', result.filename);
                        
                    } catch (error) {
                        console.error('文件上传失败:', error);
                        alert(`文件上传失败: ${error.message}`);
                    } finally {
                        this.showUploadProgress(false);
                        document.body.removeChild(fileInput);
                    }
                };
                
                document.body.appendChild(fileInput);
                fileInput.click();
            };
            
            // 刷新文件列表方法
            nodeType.prototype.refreshFileList = async function() {
                try {
                    const files = await FileUploader.refreshFileList();
                    const fileWidget = this.widgets.find(w => w.name === "file");
                    if (fileWidget) {
                        fileWidget.options.values = files;
                        // 如果当前选择的文件不在列表中，选择第一个
                        if (!files.includes(fileWidget.value) && files.length > 0) {
                            fileWidget.value = files[0];
                        }
                    }
                    this.setDirtyCanvas(true, true);
                } catch (error) {
                    console.error('刷新文件列表失败:', error);
                }
            };
            
            // 显示上传进度
            nodeType.prototype.showUploadProgress = function(show) {
                if (show) {
                    if (!this.uploadProgressWidget) {
                        this.uploadProgressWidget = this.addWidget("text", "上传状态", "正在上传...");
                    }
                    this.uploadProgressWidget.value = "正在上传...";
                } else {
                    if (this.uploadProgressWidget) {
                        this.removeWidget(this.uploadProgressWidget);
                        this.uploadProgressWidget = null;
                    }
                }
                this.setDirtyCanvas(true, true);
            };
        }
    }
});
