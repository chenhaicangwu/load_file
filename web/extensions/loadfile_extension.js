import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// 文件上传工具类
class FileUploader {
    static async uploadFile(file) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            
            api.fetchApi('/loadfile/upload', {
                method: 'POST',
                body: formData
            }).then(async response => {
                if (response.ok) {
                    const result = await response.json();
                    resolve(result);
                } else {
                    const error = await response.text();
                    reject(new Error(error || '上传失败'));
                }
            }).catch(error => {
                reject(error);
            });
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
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                this.addWidget("button", "📁 选择文件上传", null, () => {
                    this.selectAndUploadFile();
                });
                
                this.addWidget("button", "🔄 刷新文件列表", null, () => {
                    this.refreshFileList();
                });
            };
            
            nodeType.prototype.selectAndUploadFile = function() {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = '*/*';
                fileInput.style.display = 'none';
                
                fileInput.onchange = async (event) => {
                    const file = event.target.files[0];
                    if (!file) return;
                    
                    try {
                        this.showUploadProgress(true);
                        
                        const result = await FileUploader.uploadFile(file);
                        
                        await this.refreshFileList();
                        
                        const fileWidget = this.widgets.find(w => w.name === "file");
                        if (fileWidget) {
                            fileWidget.value = result.filename;
                        }
                        
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
            
            nodeType.prototype.refreshFileList = async function() {
                try {
                    const files = await FileUploader.refreshFileList();
                    const fileWidget = this.widgets.find(w => w.name === "file");
                    if (fileWidget) {
                        fileWidget.options.values = files;
                        if (!files.includes(fileWidget.value) && files.length > 0) {
                            fileWidget.value = files[0];
                        }
                    }
                    this.setDirtyCanvas(true, true);
                } catch (error) {
                    console.error('刷新文件列表失败:', error);
                }
            };
            
            // 修复上传进度显示方法
            nodeType.prototype.showUploadProgress = function(show) {
                if (show) {
                    if (!this.uploadProgressWidget) {
                        this.uploadProgressWidget = this.addWidget("text", "上传状态", "正在上传...");
                    }
                    this.uploadProgressWidget.value = "正在上传...";
                } else {
                    if (this.uploadProgressWidget) {
                        // 使用正确的方法移除widget
                        const index = this.widgets.indexOf(this.uploadProgressWidget);
                        if (index > -1) {
                            this.widgets.splice(index, 1);
                        }
                        this.uploadProgressWidget = null;
                    }
                }
                this.setDirtyCanvas(true, true);
            };
        }
    }
});
