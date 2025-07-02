import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// 注册自定义节点扩展
app.registerExtension({
    name: "LoadFileWithButton",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoadFileWithButton") {
            // 保存原始的onNodeCreated方法
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                // 调用原始方法
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // 添加文件选择按钮的处理逻辑
                this.addWidget("button", "选择文件", null, () => {
                    this.selectFile();
                });
            };
            
            // 添加文件选择方法
            nodeType.prototype.selectFile = function() {
                // 创建文件输入元素
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = '.png,.jpg,.jpeg,.gif,.bmp,.tiff,.webp,.mp4,.avi,.mov,.mkv,.webm,.flv,.pt,.pth,.safetensors,.ckpt,.bin,.txt,.json,.yaml,.yml,.xml,.csv';
                
                // 处理文件选择
                fileInput.onchange = (event) => {
                    const file = event.target.files[0];
                    if (file) {
                        // 更新file_path输入框
                        const filePathWidget = this.widgets.find(w => w.name === "file_path");
                        if (filePathWidget) {
                            filePathWidget.value = file.path || file.name;
                        }
                        
                        // 如果是Web环境，需要处理文件上传
                        if (!file.path) {
                            this.handleWebFile(file);
                        }
                        
                        // 触发节点更新
                        this.setDirtyCanvas(true, true);
                    }
                };
                
                // 触发文件选择对话框
                fileInput.click();
            };
            
            // 处理Web环境下的文件
            nodeType.prototype.handleWebFile = function(file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    // 创建临时文件路径
                    const tempPath = `/tmp/${file.name}`;
                    
                    // 发送文件数据到后端
                    api.fetchApi('/upload/file', {
                        method: 'POST',
                        body: JSON.stringify({
                            filename: file.name,
                            data: e.target.result.split(',')[1], // base64数据
                            path: tempPath
                        }),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }).then(response => {
                        if (response.ok) {
                            // 更新file_path
                            const filePathWidget = this.widgets.find(w => w.name === "file_path");
                            if (filePathWidget) {
                                filePathWidget.value = tempPath;
                            }
                        }
                    }).catch(err => {
                        console.error('文件上传失败:', err);
                    });
                };
                reader.readAsDataURL(file);
            };
        }
    }
});