<template>
  <aside class="ai-assistant" :class="{ active: isActive }" :style="{ width: aiWidth + 'px' }">
    <div class="ai-header">
      <h3>AI助手</h3>
      <button class="close-ai" @click="closeAssistant">×</button>
    </div>
    <div class="chat-container">
      <div class="chat-messages" ref="chatMessages">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.type + '-message']"
        >
          <p v-html="formatMessage(msg.content)"></p>
          
          <!-- 添加操作建议按钮，但仅当消息内容中不包含链接时才显示 -->
          <div v-if="msg.type === 'ai' && msg.actionSuggestion && !containsMarkdownLink(msg.content)" class="action-suggestion">
            <button class="action-button" @click="executeAction(msg.actionSuggestion)">
              <i :class="getActionIcon(msg.actionSuggestion.type)"></i> 
              {{ getActionText(msg.actionSuggestion.type) }}
            </button>
          </div>
          
          <!-- 用户消息下方显示该消息的引用 -->
          <div v-if="msg.type === 'user' && msg.references && msg.references.length > 0" class="reference-files user-references">
            <div class="reference-header">引用文档:</div>
            <div class="reference-list">
              <div 
                v-for="(ref, refIndex) in msg.references" 
                :key="refIndex" 
                class="reference-item"
                @click="openReferenceFile(ref)"
              >
                <span class="file-icon"></span>
                <span class="file-name">{{ ref.title || '未命名文档' }}</span>
              </div>
            </div>
          </div>
          
          <!-- 在AI消息下方显示AI找到的引用上下文 -->
          <div v-if="msg.type === 'ai' && msg.references && msg.references.length > 0" class="reference-files">
            <div class="reference-header">引用上下文:</div>
            <div class="reference-list">
              <div 
                v-for="(ref, refIndex) in msg.references" 
                :key="refIndex" 
                class="reference-item"
                @click="openReferenceFile(ref)"
              >
                <span class="file-icon"></span>
                <span class="file-name">{{ ref.title || '未命名文档' }}</span>
                <span class="file-lines" v-if="ref.context">"{{ truncateContext(ref.context) }}"</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 加载状态指示器 -->
        <div v-if="loading" class="message ai-message">
          <div class="thinking">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>
      
      <!-- 已选择的引用文件和上传的附件 -->
      <div v-if="selectedReferences.length > 0 || uploadedFiles.length > 0" class="selected-files-container">
        <div v-if="selectedReferences.length > 0" class="selected-files">
          <div class="selected-files-header">已选择的引用:</div>
          <div class="selected-files-list">
            <div v-for="(ref, index) in selectedReferences" :key="index" class="selected-file">
              <span class="file-icon"></span>
              <span class="file-name">{{ ref.title }}</span>
              <button class="remove-file" @click="removeReference(index)">×</button>
            </div>
          </div>
        </div>
        
        <div v-if="uploadedFiles.length > 0" class="selected-files">
          <div class="selected-files-header">已上传的附件:</div>
          <div class="selected-files-list">
            <div v-for="(file, index) in uploadedFiles" :key="index" class="selected-file">
              <span class="file-icon"></span>
              <span class="file-name">{{ file.name }}</span>
              <button class="remove-file" @click="removeUploadedFile(index)">×</button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 使用transition组件包裹各选择器，添加过渡效果 -->
      <transition name="slide-fade">
      <!-- 引用选择器 -->
      <div v-if="showReferenceSelector" class="file-selector">
        <div class="selector-header">
          <h4>选择引用文件</h4>
            <button class="close-selector" @click="closeAllSelectors">×</button>
        </div>
        
        <div class="file-tabs">
          <button 
            :class="['tab-btn', referenceTab === 'public' ? 'active' : '']" 
            @click="referenceTab = 'public'"
          >
            公共知识库
          </button>
          <button 
            :class="['tab-btn', referenceTab === 'personal' ? 'active' : '']" 
            @click="referenceTab = 'personal'"
          >
            个人知识库
          </button>
        </div>
        
        <div class="file-list">
          <div 
            v-for="(file, index) in filteredReferenceFiles" 
            :key="index"
            :class="['file-item', isFileSelected(file) ? 'selected' : '']"
            @click="toggleReferenceFile(file)"
          >
            <span class="file-icon"></span>
            <span class="file-name">{{ file.title }}</span>
          </div>
          <div v-if="filteredReferenceFiles.length === 0" class="no-files">
            暂无可引用文件
          </div>
        </div>
        
        <div class="selector-footer">
          <button class="confirm-btn" @click="confirmReferenceSelection">确认选择</button>
        </div>
      </div>
      </transition>
      
      <transition name="slide-fade">
      <!-- 附件上传器 -->
      <div v-if="showAttachmentUploader" class="file-selector">
        <div class="selector-header">
          <h4>上传附件</h4>
            <button class="close-selector" @click="closeAllSelectors">×</button>
        </div>
        
        <div class="upload-area">
          <input 
            type="file" 
            ref="fileInput" 
            @change="handleFileChange" 
            multiple 
            accept=".pdf,.doc,.docx,.txt"
            style="display: none"
          />
          <div class="upload-drop-area" @click="triggerFileInput" @drop.prevent="handleFileDrop" @dragover.prevent>
            <div class="upload-icon">📁</div>
            <div class="upload-text">点击或拖拽文件到此处上传</div>
            <div class="upload-hint">只支持PDF文档格式</div>
          </div>
        </div>
        
        <div v-if="uploadQueue.length > 0" class="upload-queue">
          <div v-for="(file, index) in uploadQueue" :key="index" class="upload-item">
            <span class="file-icon"></span>
            <span class="file-name">{{ file.name }}</span>
            <span class="upload-status">{{ file.status }}</span>
          </div>
        </div>
        
        <div class="selector-footer">
          <button class="confirm-btn" @click="confirmAttachmentUpload" :disabled="uploadQueue.length === 0">
            确认上传
          </button>
        </div>
      </div>
      </transition>
      
      <div class="action-buttons">
          <button class="action-btn reference-btn" @click="handleReference">
          <span>引用文档</span>
          </button>
          <button class="action-btn attachment-btn" @click="handleAttachment">
          <span>上传附件</span>
          </button>
      </div>
      <div class="chat-input">
        <textarea v-model="input" placeholder="请输入您的问题..." @keyup.enter="sendMessage"></textarea>
        <button @click="sendMessage">发送</button>
      </div>
    </div>
  </aside>
</template>

<script>
import emitter from '../utils/eventBus';

export default {
  data() {
    return {
      isActive: false,
      aiWidth: 0, // 初始宽度设为0，表示完全关闭
      messages: [],
      input: '',
      selectedReferences: [],
      uploadedFiles: [],
      showReferenceSelector: false,
      showAttachmentUploader: false,
      referenceTab: 'public',
      uploadQueue: [],
      publicFiles: [],
      personalFiles: [],
      backendUrl: 'http://127.0.0.1:8000/api',
      pendingActionSuggestion: null, // 添加这一行
      loading: false, // 添加加载状态
      overlayTimeout: null // 添加超时机制
    };
  },
  computed: {
    filteredReferenceFiles() {
      return this.referenceTab === 'public' ? this.publicFiles : this.personalFiles;
    }
  },
  mounted() {
    // 添加全局事件监听器，用于在路由变化时清理过渡层和localStorage数据
    window.addEventListener('popstate', this.cleanupOnRouteChange);
    
    // 监听Vue Router的路由变化
    try {
      import('../router').then(({ default: router }) => {
        router.afterEach(() => {
          console.log('路由变化，清理过渡层和localStorage数据');
          this.cleanupOnRouteChange();
        });
      }).catch(err => {
        console.error('导入router模块失败:', err);
      });
    } catch (e) {
      console.error('监听路由变化失败:', e);
    }
    
    // 注册事件监听器
    emitter.on('toggle-ai', () => {
      this.toggle();
    });
    
    // 监听邮件模块点击事件
    this.setupEmailModuleListeners();
    
    // 监听AI生成的链接点击事件
    document.addEventListener('ai-link-click', this.handleAiLinkClick);
  },
  beforeUnmount() {
    // Vue 3 生命周期钩子，确保在Vue 3环境下也能正确清理
    emitter.off('toggle-ai-assistant');
    window.removeEventListener('popstate', this.cleanupOnRouteChange);
    
    this.removeTransitionOverlay();
    this.cleanupLocalStorage();
    
    console.log('AiAssistant组件卸载，已清理所有资源');
  },
  created() {
    // 监听toggle-ai-assistant事件
    emitter.on('toggle-ai-assistant', this.toggle);
    
    // 初始化数据
    this.fetchPublicFiles();
    this.fetchPersonalFiles();
    
    // 清理可能存在的localStorage数据
    this.cleanupLocalStorage();
  },
  methods: {
    truncateContext(context) {
      // 截断过长的上下文内容
      return context.length > 50 ? context.substring(0, 50) + '...' : context;
    },
    formatMessage(content) {
      if (!content) return '';
      
      // 首先移除所有<think>标签
      let formattedContent = content.replace(/<think>[\s\S]*?<\/think>/g, '');
      
      // 处理Markdown风格的链接 [文本](#链接) 或 [文本](/链接)
      // 但我们不再使用这种方式，因为现在使用按钮
      formattedContent = formattedContent.replace(
        /\[([^\]]+)\]\(([^)]+)\)/g, 
        (match, text, url) => {
          // 只保留文本部分，不生成链接
          return text;
        }
      );
      
      // 将URL转换为链接
      formattedContent = formattedContent.replace(
        /(https?:\/\/[^\s]+)/g, 
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
      );
      
      // 替换换行符为<br>标签
      formattedContent = formattedContent.replace(/\n/g, '<br>');
      
      // 确保内容的安全性，移除任何可能的恶意脚本
      formattedContent = formattedContent
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
      
      return formattedContent;
    },
    openReferenceFile(reference) {
      // 打开引用的文件
      if (!reference) {
        console.error('尝试打开无效的引用:', reference);
        return;
      }
      
      console.log('尝试打开引用:', reference);
      
      if (reference.id) {
        try {
          // 如果是公共信息文档，通过事件总线通知Workspace组件打开文档
          console.log('打开文档ID:', reference.id);
          emitter.emit('open-document', reference.id);
          
          // 创建过渡效果
          this.createTransitionOverlay('正在打开文档...');
          
          // 使用Vue Router导航，而不是直接修改window.location
          import('../router').then(({ default: router }) => {
            // 在跳转前设置一个标记，指示这是从AI助手引用的文件
            localStorage.setItem('highlight_document_id', reference.id);
            localStorage.setItem('ai_referenced_document', 'true');
            
            // 导航到文档详情页
            router.push(`/document/${reference.id}`).then(() => {
              // 导航成功后触发一个事件，通知文档详情组件高亮显示
              setTimeout(() => {
                // 发送事件指示高亮当前打开的文档
                window.dispatchEvent(new CustomEvent('highlight-document', {
                  detail: { documentId: reference.id }
                }));
                
                // 移除过渡层
                this.removeTransitionOverlay();
              }, 300);
            }).catch(navErr => {
              console.error('导航到文档页面失败:', navErr);
              this.removeTransitionOverlay();
            });
          }).catch(err => {
            console.error('导入router模块失败:', err);
            this.removeTransitionOverlay();
          });
        } catch (error) {
          console.error('打开文档失败:', error);
          this.removeTransitionOverlay();
          alert('无法打开文档: ' + error.message);
        }
      } else if (reference.path) {
        try {
          // 如果是知识库文件，可以通过路径打开
          const baseUrl = this.backendUrl.replace('/api', '');
          
          // 创建过渡效果
          this.createTransitionOverlay('正在打开文件...');
          
          // 确保路径格式正确
          let filePath = reference.path;
          if (!filePath.startsWith('knowledge/') && !filePath.startsWith('personal/')) {
            // 尝试从source推断正确的路径前缀
            if (reference.source && reference.source.includes('knowledge')) {
              filePath = 'knowledge/' + filePath;
            } else if (reference.source && reference.source.includes('personal')) {
              filePath = 'personal/' + filePath;
            }
          }
          
          const fileUrl = `${baseUrl}/files/${filePath}`;
          console.log('打开文件URL:', fileUrl);
          
          // 使用新标签页打开文件
          setTimeout(() => {
            window.open(fileUrl, '_blank');
            // 移除过渡层
            this.removeTransitionOverlay();
          }, 300);
        } catch (error) {
          console.error('打开文件失败:', error, reference);
          this.removeTransitionOverlay();
          alert('无法打开文件: ' + (reference.title || reference.path));
        }
      } else if (reference.title) {
        try {
          // 如果只有标题，尝试在知识库中查找
          console.log('尝试根据标题查找文档:', reference.title);
          emitter.emit('search-document', reference.title);
          
          // 创建过渡效果
          this.createTransitionOverlay('正在搜索文档...');
          
          // 使用Vue Router导航到知识库页面
          import('../router').then(({ default: router }) => {
            // 在跳转前设置一个标记，指示要搜索的文档标题
            localStorage.setItem('highlight_document_title', reference.title);
            localStorage.setItem('ai_referenced_search', 'true');
            
            router.push({
              path: '/knowledge',
              query: { search: reference.title }
            }).then(() => {
              // 导航成功后触发一个事件，通知知识库组件高亮显示搜索结果
              setTimeout(() => {
                // 发送事件指示高亮搜索结果
                window.dispatchEvent(new CustomEvent('highlight-search-result', {
                  detail: { searchTerm: reference.title }
                }));
                
                // 移除过渡层
                this.removeTransitionOverlay();
              }, 300);
            }).catch(navErr => {
              console.error('导航到知识库页面失败:', navErr);
              this.removeTransitionOverlay();
            });
          }).catch(err => {
            console.error('导入router模块失败:', err);
            this.removeTransitionOverlay();
          });
        } catch (error) {
          console.error('搜索文档失败:', error);
          this.removeTransitionOverlay();
          alert('无法搜索文档: ' + reference.title);
        }
      } else {
        console.error('无法识别的引用类型:', reference);
        alert('无法打开引用，缺少必要信息');
      }
    },
    
    // 创建过渡覆盖层
    createTransitionOverlay(message) {
      // 移除可能存在的过渡层
      this.removeTransitionOverlay();
      
      // 创建过渡层
      const transitionOverlay = document.createElement('div');
      transitionOverlay.id = 'transition-overlay';
      transitionOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.8);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
        transition: opacity 0.3s ease;
      `;
      
      const loadingContent = document.createElement('div');
      loadingContent.style.cssText = `
        text-align: center;
        background-color: white;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      `;
      
      loadingContent.innerHTML = `
        <div style="font-size: 16px; margin-bottom: 10px;">${message}</div>
        <div style="color: #666;">请稍候...</div>
      `;
      
      transitionOverlay.appendChild(loadingContent);
      document.body.appendChild(transitionOverlay);
      
      // 添加安全超时机制，确保过渡层不会永久存在
      this.overlayTimeout = setTimeout(() => {
        this.removeTransitionOverlay();
      }, 5000); // 5秒后自动移除
    },
    
    // 移除过渡覆盖层
    removeTransitionOverlay() {
      // 清除可能存在的超时
      if (this.overlayTimeout) {
        clearTimeout(this.overlayTimeout);
        this.overlayTimeout = null;
      }
      
      const overlay = document.getElementById('transition-overlay');
      if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
          if (document.body.contains(overlay)) {
            document.body.removeChild(overlay);
          }
        }, 300);
      }
    },
    toggle() {
      console.log("触发toggle方法，切换AI助手对话框状态");
      
      this.isActive = !this.isActive;
      
      // 更新宽度
      this.aiWidth = this.isActive ? 360 : 0;
      
      // 触发 toggle 事件，通知父组件对话框状态变化
      this.$emit('toggle', this.isActive);

      // 如果打开对话框且没有消息，添加欢迎语
      if (this.isActive && this.messages.length === 0) {
        console.log("新会话，添加欢迎消息");
        this.messages.push({
          type: 'ai',
          content: '您好！我是您的智能办公助手。我可以：\n\n• 查询和搜索公共文档库中的信息\n• 回答关于公文、流程和规章制度的问题\n• 分析和处理上传的PDF文件内容\n• 处理图片并提供相关建议\n• 协助您撰写专业邮件和回复\n• 为工作流程提供建议和优化方案\n\n您可以直接问我任何问题，也可以上传文件供我分析，或者从知识库中引用相关资料。\n\n请问今天有什么可以帮到您的？',
          references: []
        });
      }
      
      // 关闭所有选择器
      this.closeAllSelectors();
      
      console.log("AI助手对话框状态已切换:", this.isActive ? "打开" : "关闭");
    },
    async fetchPublicFiles() {
      try {
        // 获取文档
        console.log('开始获取公共文件...');
        const response = await fetch(`${this.backendUrl}/documents`);
        console.log('获取公共文件响应状态:', response.status);
        if (!response.ok) {
          const errorText = await response.text();
          console.error('获取公共文件失败, 状态码:', response.status, '错误信息:', errorText);
          throw new Error(`获取公共文件请求失败: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('获取公共文件响应数据:', data);
        
        // 处理后端返回的数据格式，支持documents或items字段
        const documentsList = data.documents || data.items || [];
        if (documentsList.length === 0) {
          console.error('公共文件响应缺少有效的文档数据:', data);
          this.publicFiles = [];
          return;
        }
        
        this.publicFiles = documentsList.map(doc => ({
          id: doc.id,
          path: null,
          title: doc.title,
          content: doc.content,
          type: 'file',
          source: 'documents'
        }));
        
        console.log('处理后的公共文件列表:', this.publicFiles);
        
        // 获取知识库文件夹下的文件
        const knowledgeResponse = await fetch(`${this.backendUrl}/files/list?folder=knowledge`);
        const knowledgeData = await knowledgeResponse.json();
        console.log('获取知识库文件夹数据:', knowledgeData);
        
        // 合并文件列表
        const knowledgeFiles = knowledgeData.files.map(file => ({
          id: null,
            path: `knowledge/${file.name}`,
            title: file.name,
            type: 'file',
            source: 'knowledge'
        }));
        
        this.publicFiles = [...this.publicFiles, ...knowledgeFiles];
        console.log('最终公共文件列表数量:', this.publicFiles.length);
      } catch (error) {
        console.error('获取公共文件失败:', error);
        this.publicFiles = []; // 确保在出错时至少有一个空数组而不是undefined
      }
    },
    
    async fetchPersonalFiles() {
      try {
        // 获取个人知识库文件
        console.log('开始获取个人文件...');
        const response = await fetch(`${this.backendUrl}/files/list?folder=personal`);
        
        if (!response.ok) {
          console.error('获取个人文件响应失败:', response.status);
          return;
        }
        
        const data = await response.json();
        console.log('获取个人文件响应数据:', data);
        
        this.personalFiles = data.files.map(file => ({
          id: null,
          path: `personal/${file.name}`,
          title: file.name,
          type: 'file',
          source: 'personal'
        }));
        
        console.log('处理后的个人文件列表:', this.personalFiles);
      } catch (error) {
        console.error('获取个人文件失败:', error);
        this.personalFiles = [];
      }
    },
    handleReference() {
      // 关闭其他选择器，切换引用选择器的状态
      this.showAttachmentUploader = false;
      this.showReferenceSelector = !this.showReferenceSelector;
      
      // 当打开引用选择器时刷新文件列表
      if (this.showReferenceSelector) {
        Promise.all([
        this.fetchPublicFiles(),
        this.fetchPersonalFiles()
      ]);
      }
    },
    handleAttachment() {
      // 关闭其他选择器，切换附件选择器的状态
      this.showReferenceSelector = false;
      this.showAttachmentUploader = !this.showAttachmentUploader;
    },
    triggerFileInput() {
      // 触发文件选择对话框
      this.$refs.fileInput.click();
    },
    handleFileChange(event) {
      // 处理文件选择
      const files = Array.from(event.target.files);
      this.addFilesToUploadQueue(files);
    },
    handleFileDrop(event) {
      // 处理文件拖放
      event.preventDefault();
      const files = Array.from(event.dataTransfer.files);
      this.addFilesToUploadQueue(files);
    },
    addFilesToUploadQueue(files) {
      // 添加文件到上传队列
      for (const file of files) {
        // 检查文件类型
        const validTypes = ['.pdf'];
        const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        
        if (!validTypes.includes(fileExt)) {
          alert(`不支持的文件类型: ${fileExt}。请上传PDF文件。`);
          continue;
        }
        
        // 添加到上传队列
        this.uploadQueue.push({
          file,
          name: file.name,
          status: '等待上传'
        });
      }
    },
    async confirmAttachmentUpload() {
      // 上传文件到服务器
      for (let i = 0; i < this.uploadQueue.length; i++) {
        const item = this.uploadQueue[i];
        item.status = '上传中...';
        
        try {
          const formData = new FormData();
          formData.append('file', item.file);
          
          const response = await fetch(`${this.backendUrl}/files/upload`, {
            method: 'POST',
            body: formData
          });
          
          if (!response.ok) {
            throw new Error('上传失败');
          }
          
          const data = await response.json();
          
          // 更新状态
          item.status = '上传成功';
          
          // 添加到已上传文件列表
          this.uploadedFiles.push({
            name: item.name,
            path: `personal/${data.name}`,  // 使用返回的相对路径
            type: 'file',
            source: 'uploaded'
          });
        } catch (error) {
          console.error('文件上传失败:', error);
          item.status = '上传失败';
        }
      }
      
      // 清空上传队列
      setTimeout(() => {
        this.uploadQueue = [];
        this.showAttachmentUploader = false;
      }, 1500);
    },
    removeUploadedFile(index) {
      // 从已上传列表中移除文件
      this.uploadedFiles.splice(index, 1);
    },
    isFileSelected(file) {
      // 检查逻辑，同时考虑ID和path两种情况
      const isSelected = this.selectedReferences.some(ref => 
        (file.id && ref.id === file.id) || 
        (file.path && ref.path === file.path)
      );
      
      return isSelected;
    },
    toggleReferenceFile(file) {
      // 切换文件的选中状态
      const index = this.selectedReferences.findIndex(ref => 
        (file.id && ref.id === file.id) || 
        (file.path && ref.path === file.path)
      );
      
      if (index === -1) {
        // 添加到选中列表，确保ID和path有效
        const newRef = {...file};
        console.log('添加文件到引用列表:', newRef);
        this.selectedReferences.push(newRef);
      } else {
        // 从选中列表中移除
        this.selectedReferences.splice(index, 1);
      }
    },
    confirmReferenceSelection() {
      console.log('确认选择的引用文件:', this.selectedReferences);
      this.showReferenceSelector = false;
    },
    removeReference(index) {
      console.log('移除引用:', this.selectedReferences[index]);
      this.selectedReferences.splice(index, 1);
    },
    async sendMessage() {
      // 如果输入为空或正在加载，则不发送
      if (!this.input.trim() || this.loading) return;
      
      // 记录用户消息
      const userMessage = this.input.trim();
      this.messages.push({
        type: 'user',
        content: userMessage,
        references: this.selectedReferences.map(ref => ({ ...ref }))
      });
      
      // 清空输入框
      this.input = '';
      
      // 显示思考状态
      this.loading = true;
      
      try {
        // 检查是否是邮件请求
        const isEmailReq = this.isEmailRequest(userMessage);
        
        // 准备请求数据
        const requestData = {
          query: userMessage,
          references: this.selectedReferences.map(ref => ({
            id: ref.id,
            path: ref.path,
            source: ref.source || '用户选择'
          })),
          attachments: this.uploadedFiles.map(file => ({
              name: file.name,
              path: file.path,
            type: file.type || 'file'
          })),
          isEmailRequest: isEmailReq // 设置是否为邮件请求
        };
        
        console.log("发送聊天请求:", requestData);
        
        // 使用fetch API发送POST请求，但以流的方式处理响应
        const response = await fetch(`${this.backendUrl}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestData)
        });
        
        console.log("收到响应状态:", response.status);

        if (!response.ok) {
          throw new Error(`请求失败: ${response.status}`);
        }

        // 创建一个新的AI消息对象，但先不添加到消息列表
        const aiMessage = {
          type: 'ai',
          content: '',
          references: []
        };
        
        // 添加空消息到列表，后续会更新内容
        this.messages.push(aiMessage);
        
        // 使用ReadableStream API处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // 用于处理邮件JSON数据
        let collectingEmailJson = false;
        let emailJsonData = '';
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log("流读取完成");
            break;
          }

          // 解码二进制数据为文本
          const chunk = decoder.decode(value, { stream: true });
          console.log("接收到数据块:", chunk);
          
          // 处理SSE格式的数据
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.substring(6).trim();
              
              // 检查是否是结束标记
              if (data === '[DONE]') {
                console.log("接收到结束标记");
                continue; 
              } 
              
              // 处理邮件JSON数据开始标记
              if (data === 'EMAIL_JSON_START') {
                console.log("开始收集邮件JSON数据");
                collectingEmailJson = true;
                emailJsonData = '';
                continue;
              }
              
              // 处理邮件JSON数据结束标记
              if (data === 'EMAIL_JSON_END') {
                console.log("邮件JSON数据收集完成");
                collectingEmailJson = false;
                
                try {
                  // 解析收集到的邮件JSON数据
                  const emailData = JSON.parse(emailJsonData);
                  console.log("解析的邮件JSON数据:", emailData);
                  
                  // 更新AI消息内容为完整邮件
                  aiMessage.content = emailData.full_content || emailData.content;
                  
                  // 触发邮件编辑器打开
                  this.openEmailEditor(emailData);
                } catch (jsonError) {
                  console.error("解析邮件JSON数据失败:", jsonError);
                  aiMessage.content = "解析邮件数据失败，请重试。";
                }
                continue;
              }
              
              // 如果正在收集邮件JSON数据
              if (collectingEmailJson) {
                emailJsonData += data;
                continue;
              }
              
              try {
                // 尝试解析普通JSON数据
                const parsedData = JSON.parse(data);
                console.log("解析的JSON数据:", parsedData);
                
                // 更新AI消息内容
                if (parsedData.content) {
                  aiMessage.content = parsedData.content;
              }
              
                // 更新引用信息
                if (parsedData.references) {
                  aiMessage.references = parsedData.references;
                }
                
                // 处理智能代理结果
                if (parsedData.agent_result && parsedData.agent_result.action) {
                  console.log("检测到智能代理结果:", parsedData.agent_result);
                      
                  // 将智能代理的建议添加到消息中
                  aiMessage.actionSuggestion = {
                    type: parsedData.agent_result.action,
                    form_data: parsedData.agent_result.form_data || {}
                    };
                    
                  console.log("添加的操作建议:", aiMessage.actionSuggestion);
            }
              } catch (error) {
                // 如果不是JSON，则作为普通文本追加到消息内容中
                console.log("接收到普通文本数据:", data);
                aiMessage.content += data;
              }
            }
          }
        }
      } catch (error) {
        console.error("聊天请求失败:", error);
        // 添加错误消息
        this.messages.push({
          type: 'ai',
          content: `抱歉，处理您的请求时出错: ${error.message}`
        });
      } finally {
        // 无论成功失败，都关闭加载状态
        this.loading = false;
        
        // 重置选择状态
        this.selectedReferences = [];
        this.uploadedFiles = [];
        
        // 滚动到最新消息
        this.$nextTick(() => {
          if (this.$refs.chatMessages) {
            this.$refs.chatMessages.scrollTop = this.$refs.chatMessages.scrollHeight;
          }
        });
      }
    },
    
    // 打开邮件编辑器
    openEmailEditor(emailData) {
      console.log("打开邮件编辑器，数据:", emailData);
      
      try {
        // 使用事件总线触发写邮件事件
        emitter.emit('open-compose-email', {
          recipient: emailData.recipient || '',
          subject: emailData.subject || '',
          content: emailData.content || ''
        });
        
        // 显示成功消息
        this.messages.push({
          type: 'ai',
          content: '已为您生成邮件内容并打开邮件编辑器。'
        });
      } catch (error) {
        console.error("打开邮件编辑器失败:", error);
      }
    },
    isEmailRequest(query) {
      // 匹配邮件相关关键词
      const emailKeywords = [
        '写一封邮件', '写邮件', '发邮件', '帮我写一封', '生成邮件',
        '写一个邮件', '邮件模板', '商务邮件', '创建邮件'
      ];
      
      // 检查是否包含邮件关键词
      const lowercaseQuery = query.toLowerCase();
      const containsEmailKeyword = emailKeywords.some(keyword => 
        lowercaseQuery.includes(keyword)
      );
      
      // 使用正则表达式检查更复杂的模式
      const emailPatterns = [
        /给.*?(?:发|写).*?(?:邮件|信)/,
        /写给.*?的.*?邮件/,
        /关于.*?的邮件/,
        /收件人.*?主题/
      ];
      
      const matchesPattern = emailPatterns.some(pattern => 
        pattern.test(query)
      );
      
      console.log('邮件请求检测:', {
        containsEmailKeyword,
        matchesPattern,
        query: query.substring(0, 30) + '...'
      });
      
      return containsEmailKeyword || matchesPattern;
    },
    
    // 新增：检测是否是工作流创建请求
    isWorkflowCreationRequest(query) {
      // 匹配工作流创建相关关键词
      const workflowKeywords = [
        '创建工作流', '设计工作流', '创建审批流程', '设计审批流程', 
        '新建流程', '制作审批', '设计流程', '创建审批', '流程设计',
        '审批设计', '工作流设计', '审批流程设计'
      ];
      
      // 检查是否包含工作流创建关键词
      const lowercaseQuery = query.toLowerCase();
      const containsWorkflowKeyword = workflowKeywords.some(keyword => 
        lowercaseQuery.includes(keyword)
      );
      
      // 使用正则表达式检查更复杂的模式
      const workflowPatterns = [
        /设计.*?(?:审批|流程)/,
        /创建.*?(?:审批|流程)/,
        /新建.*?(?:审批|流程)/,
        /制作.*?(?:审批|流程)/
      ];
      
      const matchesPattern = workflowPatterns.some(pattern => 
        pattern.test(lowercaseQuery)
      );
      
      console.log('工作流创建请求检测:', {
        containsWorkflowKeyword,
        matchesPattern,
        query: query.substring(0, 30) + '...'
      });
      
      return containsWorkflowKeyword || matchesPattern;
    },
    
    // 新增：检测是否是用户账号创建请求
    isUserCreationRequest(query) {
      // 匹配用户创建相关关键词
      const userKeywords = [
        '新增用户', '创建用户', '添加用户', '新建用户', 
        '新增账号', '创建账号', '添加账号', '新建账号',
        '新增一个账号', '创建一个账号', '添加一个账号', '新建一个账号',
        '新增一个用户', '创建一个用户', '添加一个用户', '新建一个用户'
      ];
      
      // 检查是否包含用户创建关键词
      const lowercaseQuery = query.toLowerCase();
      const containsUserKeyword = userKeywords.some(keyword => 
        lowercaseQuery.includes(keyword)
      );
      
      // 使用正则表达式检查更复杂的模式
      const userPatterns = [
        /(?:新增|创建|添加|新建).*?(?:用户|账号)/,
        /(?:新增|创建|添加|新建).*?(?:部门).*?(?:用户|账号)/,
        /(?:为|给).*?(?:部门).*?(?:新增|创建|添加|新建).*?(?:用户|账号)/
      ];
      
      const matchesPattern = userPatterns.some(pattern => 
        pattern.test(lowercaseQuery)
      );
      
      console.log('用户创建请求检测:', {
        containsUserKeyword,
        matchesPattern,
        query: query.substring(0, 30) + '...'
      });
      
      return containsUserKeyword || matchesPattern;
    },
    
    // 新增：打开用户管理页面并创建新用户
    openUserManagement(query) {
      try {
        console.log('打开用户管理页面，准备创建新用户，基于提示:', query);
        
        // 从查询中提取可能的部门名称
        let departmentName = '';
        const deptMatch = query.match(/(?:新增|创建|添加|新建)([^，。,.!?！？]*)(?:部门).*?(?:用户|账号)/);
        if (deptMatch && deptMatch[1] && deptMatch[1].trim().length > 0) {
          departmentName = deptMatch[1].trim();
        } else {
          // 尝试其他模式
          const deptMatch2 = query.match(/(?:为|给)([^，。,.!?！？]*)(?:部门).*?(?:新增|创建|添加|新建)/);
          if (deptMatch2 && deptMatch2[1] && deptMatch2[1].trim().length > 0) {
            departmentName = deptMatch2[1].trim();
          }
        }
        
        // 随机生成用户信息
        const randomUsername = 'user_' + Math.floor(Math.random() * 10000);
        const randomPassword = 'pwd_' + Math.floor(Math.random() * 10000);
        
        // 创建用户数据
        const userData = {
          username: randomUsername,
          password: randomPassword,
          department: departmentName || '未指定',
          action: 'create_user'
        };
        
        // 将用户数据存储到localStorage
        localStorage.setItem('user_creation_data', JSON.stringify(userData));
        
        // 判断是否已在用户管理页面
        const currentPath = window.location.pathname;
        if (currentPath.includes('/admin') && currentPath.includes('/user')) {
          // 如果已在用户管理页面，触发事件
          window.dispatchEvent(new CustomEvent('user-create-request', { 
            detail: userData 
          }));
          return `我已为您准备创建新用户，用户名: ${randomUsername}，密码: ${randomPassword}。`;
        } else {
          // 创建过渡层
          this.createTransitionOverlay('正在打开用户管理页面');
          
          // 使用Vue Router导航，优化导航机制
          sessionStorage.setItem('ai_triggered_navigation', 'true');
          sessionStorage.setItem('ai_user_data', JSON.stringify(userData));
          
          // 添加特殊标记表示直接渲染用户管理组件
          localStorage.setItem('direct_render_user_management', 'true');
          
          import('../router').then(({ default: router }) => {
            // 直接导航到用户管理页面，并传递查询参数
            router.push({
              path: '/admin/user',
              query: { 
                create: 'true',
                auto: 'true',
                timestamp: Date.now()
              }
            }).then(() => {
              // 导航完成后，触发创建用户事件
              setTimeout(() => {
                window.dispatchEvent(new CustomEvent('user-create-request', {
                  detail: userData
                }));
                
                // 短暂延迟后移除过渡层，确保页面可见
                setTimeout(() => {
                  this.removeTransitionOverlay();
                }, 300);
              }, 200);
            }).catch(navErr => {
              console.error('导航到用户管理页面失败:', navErr);
              this.removeTransitionOverlay();
            });
          }).catch(err => {
            console.error('导入router模块失败:', err);
            this.removeTransitionOverlay();
            throw err;
          });
        }
        
        // 返回响应消息
        return `我已为您准备创建新用户，用户名: ${randomUsername}，密码: ${randomPassword}。正在打开用户管理页面...`;
      } catch (error) {
        console.error('打开用户管理页面失败:', error);
        this.removeTransitionOverlay();
        return '抱歉，无法打开用户管理页面: ' + error.message;
      }
    },
    
    // 新增：打开工作流设计器
    openWorkflowDesigner(query) {
      try {
        console.log('打开工作流设计器，带入提示词:', query);
        
        // 从查询中提取可能的流程名称
        let workflowName = '新建审批流程';
        const nameMatch = query.match(/(?:创建|设计|新建|制作)([^，。,.!?！？]*)(?:流程|审批|工作流)/);
        if (nameMatch && nameMatch[1] && nameMatch[1].trim().length > 0) {
          workflowName = nameMatch[1].trim();
          // 如果提取的名称太长，则截断
          if (workflowName.length > 15) {
            workflowName = workflowName.substring(0, 15);
          }
          // 确保名称以"流程"结尾
          if (!workflowName.endsWith('流程') && !workflowName.endsWith('审批')) {
            workflowName = workflowName + '审批流程';
          }
        }
        
        // 创建设计数据
        const designData = {
          name: workflowName,
          description: '根据AI助手提示自动创建的工作流',
          prompt: query
        };
        
        // 将设计数据存储到localStorage，供设计器页面加载时使用
        localStorage.setItem('workflow_design_data', JSON.stringify(designData));
        sessionStorage.setItem('ai_triggered_workflow', 'true');
        
        // 判断是否已在工作流设计器页面
        const currentPath = window.location.pathname;
        if (currentPath === '/workflow-designer') {
          // 通过事件传递数据到设计器组件
          window.dispatchEvent(new CustomEvent('workflow-create-request', { 
            detail: designData 
          }));
          
          return '已将设计提示填充到工作流设计器...';
        } else {
          // 创建过渡层
          this.createTransitionOverlay('正在打开工作流设计器');

          // 使用Vue Router导航，优化导航机制
          import('../router').then(({ default: router }) => {
            // 添加特殊标记表示直接渲染设计器组件
            localStorage.setItem('direct_render_workflow', 'true');
            
            // 直接导航到工作流设计器，并传递查询参数
            router.push({
              path: '/workflow-designer',
              query: { 
                create: 'true',
                name: encodeURIComponent(workflowName),
                timestamp: Date.now()
              }
            }).then(() => {
              // 导航完成后，显示工作流页面并传递事件
              setTimeout(() => {
                window.dispatchEvent(new CustomEvent('workflow-create-request', {
                  detail: designData
                }));
                
                // 短暂延迟后移除过渡层，确保页面可见
                setTimeout(() => {
                  this.removeTransitionOverlay();
                }, 300);
              }, 200);
            }).catch(navErr => {
              console.error('导航到工作流设计器失败:', navErr);
              this.removeTransitionOverlay();
            });
          }).catch(err => {
            console.error('导入router模块失败:', err);
            this.removeTransitionOverlay();
            throw err;
          });
        }
        
        // 返回响应消息
        return '正在为您打开工作流设计器并自动填充设计提示...';
      } catch (error) {
        console.error('打开工作流设计器失败:', error);
        this.removeTransitionOverlay();
        return '抱歉，无法打开工作流设计器: ' + error.message;
      }
    },
    // 处理引用数据
    processReferenceData(references) {
      if (!references || !Array.isArray(references)) {
        console.error('无效的引用数据格式:', references);
        return [];
      }
      
      return references.map(ref => {
        // 确保引用项有标题
        if (!ref.title && ref.path) {
          ref.title = this.extractFilenameFromPath(ref.path);
        }
        return ref;
      });
    },
    // 从路径中提取文件名
    extractFilenameFromPath(path) {
      if (!path) return '未命名文档';
      const parts = path.split('/');
      return parts[parts.length - 1];
    },
    // 滚动到聊天窗口底部
    scrollToBottom() {
      const chatContainer = this.$refs.chatMessages;
      if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }
    },
    // 添加一个方法，用于关闭所有选择器
    closeAllSelectors() {
      const hadOpenSelectors = this.showReferenceSelector || this.showAttachmentUploader;
      
      this.showReferenceSelector = false;
      this.showAttachmentUploader = false;
      
      if (hadOpenSelectors) {
        console.log("已关闭所有打开的选择器");
      }
    },
    closeAssistant() {
      console.log("点击关闭按钮");
      this.isActive = false;
      this.aiWidth = 0; // 确保宽度为0
      this.$emit('toggle', false);
      this.closeAllSelectors();
      console.log("AI助手对话框已关闭");
    },
    cleanThinkingContent(content) {
      if (!content) return '';
      
      // 移除各种思考标记和分析内容
      let cleanedContent = content;
      
      // 移除<think>标签
      cleanedContent = cleanedContent.replace(/<think>[\s\S]*?<\/think>/g, '');
      cleanedContent = cleanedContent.replace(/<th\s*ink>[\s\S]*?<\/th\s*ink>/g, '');
      
      // 移除其他思考标记
      cleanedContent = cleanedContent.replace(/【思考[:：][\s\S]*?】/g, '');
      cleanedContent = cleanedContent.replace(/\[思考[:：][\s\S]*?\]/g, '');
      cleanedContent = cleanedContent.replace(/（思考[:：][\s\S]*？）/g, '');
      cleanedContent = cleanedContent.replace(/\(思考[:：][\s\S]*?\)/g, '');
      
      // 移除解析/思路等标记
      cleanedContent = cleanedContent.replace(/AI分析[:：][\s\S]*?(?=\n\n)/g, '');
      cleanedContent = cleanedContent.replace(/思路[:：][\s\S]*?(?=\n\n)/g, '');
      cleanedContent = cleanedContent.replace(/让我来[:：][\s\S]*?(?=\n\n)/g, '');
      
      // 移除常见引导词
      cleanedContent = cleanedContent.replace(/接下来[我|我们|开始|将]/g, '');
      cleanedContent = cleanedContent.replace(/首先[，|,]?我[需要|会|将]/g, '');
      
      // 移除可能的markdown格式标记
      cleanedContent = cleanedContent.replace(/```[\s\S]*?```/g, '');
      
      return cleanedContent.trim();
    },
    // 添加一个针对邮件内容的特殊处理函数
    extractEmailComponents(content) {
      if (!content) return { recipient: '', subject: '', content: '' };

      const cleanedContent = this.cleanThinkingContent(content);
      
      // 提取收件人
      let recipient = '';
      const recipientPatterns = [
        /收件人[：:\s]*([^\n\r]*)/i,
        /[收信][人员][：:\s]*([^\n\r]*)/i,
        /[邮箱地址|邮件地址][：:\s]*([^\n\r]*)/i,
        /[TO:|To:|to:]\s*([^\n\r]*)/i,
        /发[送给][：:\s]*([^\n\r]*)/i
      ];
      
      // 试用每个模式提取收件人
      for (const pattern of recipientPatterns) {
        const match = cleanedContent.match(pattern);
        if (match && match[1] && match[1].trim()) {
          recipient = match[1].trim();
          break;
        }
      }
      
      // 尝试提取电子邮箱地址作为最后手段
      if (!recipient) {
        const emailMatch = cleanedContent.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
        if (emailMatch) {
          recipient = emailMatch[1];
        }
      }
      
      // 提取主题
      let subject = '';
      const subjectPatterns = [
        /主题[：:\s]*([^\n\r]*)/i,
        /标题[：:\s]*([^\n\r]*)/i,
        /[SUBJECT:|Subject:|subject:]\s*([^\n\r]*)/i,
        /邮件主题[：:\s]*([^\n\r]*)/i
      ];
      
      // 试用每个模式提取主题
      for (const pattern of subjectPatterns) {
        const match = cleanedContent.match(pattern);
        if (match && match[1] && match[1].trim()) {
          subject = match[1].trim();
          break;
        }
      }
      
      // 提取内容
      let emailContent = '';
      const contentPatterns = [
        /内容[：:\s]*([\s\S]*)/i,
        /正文[：:\s]*([\s\S]*)/i,
        /邮件内容[：:\s]*([\s\S]*)/i,
        /邮件正文[：:\s]*([\s\S]*)/i
      ];
      
      // 试用每个模式提取内容
      for (const pattern of contentPatterns) {
        const match = cleanedContent.match(pattern);
        if (match && match[1] && match[1].trim()) {
          emailContent = match[1].trim();
          break;
        }
      }
      
      // 如果没有找到正文，但找到了收件人和主题
      if (!emailContent && (recipient || subject)) {
        // 移除收件人和主题行，剩下的当作正文
        let remainingContent = cleanedContent;
        
        recipientPatterns.forEach(pattern => {
          remainingContent = remainingContent.replace(pattern, '');
        });
        
        subjectPatterns.forEach(pattern => {
          remainingContent = remainingContent.replace(pattern, '');
        });
        
        emailContent = remainingContent.trim();
      }
      
      // 如果仍然没有找到正文，使用整个清理后的内容
      if (!emailContent) {
        emailContent = cleanedContent;
      }
      
      return {
        recipient,
        subject,
        content: emailContent
      };
    },
    // 新增方法：设置邮件模块点击监听器
    setupEmailModuleListeners() {
        // 监听所有邮件相关链接的点击
        document.addEventListener('click', (event) => {
            const target = event.target.closest('a, button, .clickable-item, .menu-item');
            if (!target) return;
            
            // 检查是否是邮件相关导航
            const href = target.getAttribute('href') || '';
            const text = target.textContent ? target.textContent.toLowerCase() : '';
            
            // 检查是否包含图标
            const hasMailIcon = target.querySelector('.fa-inbox, .fa-paper-plane, .fa-cog, .fa-file');
            
            const isEmailLink = 
                href.includes('/mail') || 
                href.includes('/email') || 
                href.includes('personal-office') ||
                hasMailIcon ||
                ['收件箱', '发件箱', '邮件设置', '草稿箱', 'inbox', 'outbox', 'mail', 'email', 'drafts', 'settings'].some(
                    keyword => text.includes(keyword)
                );
                
            if (isEmailLink) {
                // 阻止默认行为
                event.preventDefault();
                event.stopPropagation();
                
                console.log('检测到邮件模块点击:', text || (hasMailIcon ? '邮件图标' : '未知邮件链接'));
                
                // 根据点击内容决定跳转到哪个邮件模块
                let targetTab = 'inbox';
                if (text.includes('收件箱') || text.includes('inbox')) {
                    targetTab = 'inbox';
                } else if (text.includes('发件箱') || text.includes('outbox')) {
                    targetTab = 'outbox';
                } else if (text.includes('设置')) {
                    targetTab = 'settings';
                } else if (text.includes('草稿') || text.includes('drafts')) {
                    targetTab = 'drafts';
                }
                
                // 触发模块切换事件
                emitter.emit('module-changed', 'personal-office');
                
                // 优先直接分发事件到EmailSystem组件
                const emailTabEvent = new CustomEvent('switch-email-tab', { 
                    detail: { tab: targetTab },
                    bubbles: true 
                });
                document.dispatchEvent(emailTabEvent);
                
                // 不再使用window.location.href导航，而是使用Vue Router
                // 确保emailSystem组件有足够的时间处理事件
                setTimeout(() => {
                    // 检查当前路由是否已经是个人办公模块
                    if (window.location.hash !== '#/workspace/email') {
                        import('../router').then(({ default: router }) => {
                            router.push('/workspace/email?tab=' + targetTab);
                        }).catch(err => {
                            console.error('导入router模块失败:', err);
                        });
                    }
                }, 50);
                
                console.log('已触发邮件标签切换:', targetTab);
            }
        });
    },
    getActionIcon(actionType) {
        switch (actionType) {
            case 'create_approval':
                return 'fas fa-calendar-check';
            case 'compose_email':
                return 'fas fa-envelope';
            case 'create_user':
                return 'fas fa-user-plus';
            case 'create_workflow':
                return 'fas fa-project-diagram';
            default:
                return 'fas fa-check';
        }
    },
    
    getActionText(actionType) {
        switch (actionType) {
            case 'create_approval':
                return '发起审批';
            case 'compose_email':
                return '写邮件';
            case 'create_user':
                return '创建用户';
            case 'create_workflow':
                return '设计流程';
            default:
                return '执行操作';
        }
    },
    
    executeAction(actionSuggestion) {
        console.log('执行操作:', actionSuggestion);
        
        if (actionSuggestion.type === 'create_approval') {
            // 获取表单数据，确保使用正确的属性名
            const data = actionSuggestion.form_data || {};
            console.log('审批数据:', data);
            
            // 使用与邮件相同的填充逻辑
            const processType = data.process_type || '请假';
            const days = data.days || 1;
            const reason = data.reason || '家里有事';
            
            // 关闭AI助手面板
            this.closeAssistant();
            
            // 使用DocumentProcess组件的方法打开审批表单
            this.$nextTick(() => {
                // 获取DocumentProcess组件实例
                const docProcess = this.getDocumentProcessComponent();
                if (docProcess) {
                    if (processType === '请假') {
                        // 调用请假专用方法
                        if (typeof docProcess.handleExternalLeaveApprovalRequest === 'function') {
                            console.log('调用handleExternalLeaveApprovalRequest方法');
                            // 先设置表单数据
                            docProcess.presetApprovalData = {
                                days: days,
                                reason: reason
                            };
                            docProcess.handleExternalLeaveApprovalRequest();
                        } else {
                            console.error('DocumentProcess组件中找不到handleExternalLeaveApprovalRequest方法');
                            this.fallbackToRouterNavigation(processType, days, reason);
                        }
                    } else {
                        // 其他类型审批
                        console.log('调用openNewApprovalForm方法');
                        // 先设置表单数据
                        docProcess.presetApprovalData = {
                            type: processType,
                            days: days,
                            reason: reason
                        };
                        docProcess.openNewApprovalForm();
                    }
                } else {
                    console.error('未找到DocumentProcess组件实例');
                    this.fallbackToRouterNavigation(processType, days, reason);
                }
            });
        } else if (actionSuggestion.type === 'compose_email') {
            // 获取邮件数据
            const data = actionSuggestion.form_data || {};
            console.log('邮件数据:', data);
            
            // 使用事件总线触发写邮件事件，而不是尝试导航
            emitter.emit('open-compose-email', {
                    recipient: data.recipient || '',
                subject: data.subject || '',
                content: data.content || ''
            });
            
            // 关闭AI助手面板
            this.closeAssistant();
        } else if (actionSuggestion.type === 'create_user') {
            // 获取用户数据
            const data = actionSuggestion.form_data || {};
            console.log('用户创建数据:', data);
            
            // 创建用户数据对象
            const userData = {
                username: data.username || ('user_' + Math.floor(Math.random() * 10000)),
                password: data.password || ('pwd_' + Math.floor(Math.random() * 10000)),
                department: data.department || '未指定',
                role: data.role || '普通用户',
                action: 'create_user'
            };
            
            console.log('准备创建用户，完整数据:', userData);
            
            // 将用户数据存储到localStorage
            localStorage.setItem('user_creation_data', JSON.stringify(userData));
            console.log('已将用户创建数据保存到localStorage');
            
            // 关闭AI助手面板
            this.closeAssistant();
            
            // 判断是否已在用户管理页面
            const currentPath = window.location.pathname;
            console.log('当前路径:', currentPath);
            
            if (currentPath.includes('/admin') && currentPath.includes('/user')) {
                // 如果已在用户管理页面，触发事件
                console.log('当前已在用户管理页面，直接触发事件');
                window.dispatchEvent(new CustomEvent('user-create-request', { 
                    detail: userData 
                }));
            } else {
                // 创建过渡层
                console.log('准备导航到用户管理页面');
                this.createTransitionOverlay('正在打开用户管理页面');
                
                // 使用Vue Router导航
                import('../router').then(({ default: router }) => {
                    // 添加特殊标记表示直接渲染用户管理组件
                    localStorage.setItem('direct_render_user_management', 'true');
                    console.log('已设置direct_render_user_management标记');
                    
                    // 直接导航到用户管理页面
                    console.log('开始导航到用户管理页面');
                    router.push({
                        path: '/admin/user',
                        query: { 
                            create: 'true',
                            auto: 'true',
                            timestamp: Date.now()
                        }
                    }).then(() => {
                        // 导航完成后，触发创建用户事件
                        console.log('导航完成，准备触发事件');
                        setTimeout(() => {
                            console.log('触发user-create-request事件，数据:', userData);
                            window.dispatchEvent(new CustomEvent('user-create-request', {
                                detail: userData
                            }));
                            
                            // 短暂延迟后移除过渡层，确保页面可见
                            setTimeout(() => {
                                this.removeTransitionOverlay();
                            }, 300);
                        }, 200);
                    }).catch(navErr => {
                        console.error('导航到用户管理页面失败:', navErr);
                        this.removeTransitionOverlay();
                    });
                }).catch(err => {
                    console.error('导入router模块失败:', err);
                    this.removeTransitionOverlay();
                });
            }
        } else if (actionSuggestion.type === 'create_workflow') {
            // 获取工作流数据
            const data = actionSuggestion.form_data || {};
            console.log('工作流创建数据:', data);
            
            // 创建工作流设计数据
            const workflowName = data.name || '新建审批流程';
            const designData = {
                name: workflowName,
                description: data.description || '根据AI助手提示自动创建的工作流',
                prompt: data.prompt || actionSuggestion.message || '创建工作流'
            };
            
            // 将设计数据存储到localStorage，供设计器页面加载时使用
            localStorage.setItem('workflow_design_data', JSON.stringify(designData));
            sessionStorage.setItem('ai_triggered_workflow', 'true');
            
            // 关闭AI助手面板
            this.closeAssistant();
            
            // 判断是否已在工作流设计器页面
            const currentPath = window.location.pathname;
            if (currentPath === '/workflow-designer') {
                // 通过事件传递数据到设计器组件
                window.dispatchEvent(new CustomEvent('workflow-create-request', { 
                    detail: designData 
                }));
            } else {
                // 创建过渡层
                this.createTransitionOverlay('正在打开工作流设计器');

                // 使用Vue Router导航
                import('../router').then(({ default: router }) => {
                    // 添加特殊标记表示直接渲染设计器组件
                    localStorage.setItem('direct_render_workflow', 'true');
                    
                    // 直接导航到工作流设计器
                    router.push({
                        path: '/workflow-designer',
                        query: { 
                            create: 'true',
                            name: encodeURIComponent(workflowName),
                            timestamp: Date.now()
                        }
                    }).then(() => {
                        // 导航完成后，显示工作流页面并传递事件
                        setTimeout(() => {
                            window.dispatchEvent(new CustomEvent('workflow-create-request', {
                                detail: designData
                            }));
                            
                            // 短暂延迟后移除过渡层，确保页面可见
                            setTimeout(() => {
                                this.removeTransitionOverlay();
                            }, 300);
                        }, 200);
                    }).catch(navErr => {
                        console.error('导航到工作流设计器失败:', navErr);
                        this.removeTransitionOverlay();
                    });
                }).catch(err => {
                    console.error('导入router模块失败:', err);
                    this.removeTransitionOverlay();
                });
            }
        }
    },
    handleAiLinkClick(event) {
      // 处理AI生成的链接点击事件
      console.log('AI链接点击事件:', event.detail);
      
      try {
        const routeInfo = event.detail.route;
        if (!routeInfo) return;
        
        // 解析路由路径和查询参数
        let path = routeInfo;
        let query = {};
        
        if (routeInfo.includes('?')) {
          const [routePath, queryString] = routeInfo.split('?');
          path = routePath;
          
          // 解析查询参数
          const searchParams = new URLSearchParams(queryString);
          searchParams.forEach((value, key) => {
            query[key] = value;
          });
        }
        
        console.log('导航到路径:', path, '查询参数:', query);
        
        // 特殊处理审批创建路径
        if (path === 'approval/create') {
          // 确保查询参数正确
          if (query.type === undefined) query.type = '请假';
          if (query.days === undefined) query.days = 1;
          if (query.reason === undefined) query.reason = '家里有事';
          
          console.log('导航到审批创建页面:', path, query);
        }
        
        // 使用Vue Router导航
        this.$router.push({ path: '/' + path, query });
        
        // 关闭AI助手面板
        this.closeAssistant();
      } catch (error) {
        console.error('处理AI链接点击事件失败:', error);
      }
    },
    containsMarkdownLink(content) {
      // 我们不再检查Markdown链接，始终返回false以显示操作按钮
      return false;
    },
    // 获取DocumentProcess组件实例
    getDocumentProcessComponent() {
      // 尝试从父组件中获取DocumentProcess组件
      if (this.$parent && this.$parent.$refs && this.$parent.$refs.documentProcess) {
        return this.$parent.$refs.documentProcess;
      }
      
      // 尝试从根组件中获取
      if (this.$root && this.$root.$refs && this.$root.$refs.documentProcess) {
        return this.$root.$refs.documentProcess;
      }
      
      // 尝试通过DOM查找组件
      const workspaceComponent = document.querySelector('.workspace');
      if (workspaceComponent && workspaceComponent.__vue__) {
        return workspaceComponent.__vue__.$refs.documentProcess;
      }
      
      // 查找全局注册的DocumentProcess组件实例
      if (window.$workspaceInstance && window.$workspaceInstance.$refs.documentProcess) {
        return window.$workspaceInstance.$refs.documentProcess;
      }
      
      return null;
    },
    
    // 回退到路由导航方式
    fallbackToRouterNavigation(processType, days, reason) {
      console.log('使用路由导航方式打开审批表单');
      
      // 保存审批数据到localStorage，以便审批页面可以读取
      localStorage.setItem('presetApprovalData', JSON.stringify({
        type: processType,
        days: days,
        reason: reason
      }));
      
      // 使用路由导航到审批中心
      this.$router.push({
        path: '/workspace/approval',
        query: {
          action: 'create',
          type: processType,
          days: days,
          reason: reason
        }
      });
    },
    // 处理AI助手发起的邮件请求
    handleAIEmailRequest(data) {
      console.log('收到AI助手邮件请求:', data);
      
      // 检查数据有效性
      if (!data) {
        console.error('邮件数据为空');
        return;
      }
      
      try {
        // 确保数据格式正确
        let emailData = data;
        
        // 如果数据是字符串，尝试解析为JSON
        if (typeof data === 'string') {
          try {
            emailData = JSON.parse(data);
          } catch (e) {
            console.error('解析邮件JSON数据失败:', e);
            // 如果解析失败，尝试作为纯文本处理
            emailData = {
              content: data,
              subject: '自动生成的邮件',
              recipient: ''
            };
          }
        }
        
        console.log('处理的邮件数据:', emailData);
        
        // 添加时间戳，用于后续判断数据是否过期
        emailData.timestamp = Date.now();
        emailData.from = 'ai_assistant'; // 标记来源
        
        // 关闭AI助手面板
        this.closeAssistant();
        
        // 尝试获取EmailSystem组件
        const emailSystem = this.getEmailSystemComponent();
        
        if (emailSystem) {
          console.log('找到EmailSystem组件，直接调用方法');
          // 直接调用EmailSystem组件的方法
          let methodCalled = false;
          
          if (typeof emailSystem.handleAIEmailRequest === 'function') {
            emailSystem.handleAIEmailRequest(emailData);
            methodCalled = true;
          } else if (typeof emailSystem.openEmailWithData === 'function') {
            emailSystem.openEmailWithData(emailData);
            methodCalled = true;
          } else if (typeof emailSystem.openComposeModal === 'function') {
            emailSystem.openComposeModal(emailData);
            methodCalled = true;
          }
          
          if (!methodCalled) {
            console.error('EmailSystem组件中找不到合适的方法');
            this.fallbackToEmailEvent(emailData);
          }
        } else {
          console.log('未找到EmailSystem组件，使用事件触发');
          this.fallbackToEmailEvent(emailData);
        }
        
        // 设置一个超时，如果在指定时间内没有被处理，则清理localStorage
        setTimeout(() => {
          // 检查是否已经被处理（如果已经被处理，localStorage中的数据应该已经被移除）
          if (localStorage.getItem('pending_email_data')) {
            console.log('邮件数据在10秒内未被处理，清理localStorage');
            localStorage.removeItem('pending_email_data');
            localStorage.removeItem('ai_generated_email');
          }
        }, 10000); // 10秒后清理
      } catch (error) {
        console.error('处理AI邮件请求失败:', error);
        // 尝试使用备用方法
        try {
          this.fallbackToEmailEvent(data);
        } catch (fallbackError) {
          console.error('备用方法也失败:', fallbackError);
          // 确保清理所有数据
          localStorage.removeItem('pending_email_data');
          localStorage.removeItem('ai_generated_email');
        }
      }
    },
    
    // 获取EmailSystem组件
    getEmailSystemComponent() {
      // 尝试从父组件中获取EmailSystem组件
      if (this.$parent && this.$parent.$refs && this.$parent.$refs.emailSystem) {
        return this.$parent.$refs.emailSystem;
      }
      
      // 尝试从根组件中获取
      if (this.$root && this.$root.$refs && this.$root.$refs.emailSystem) {
        return this.$root.$refs.emailSystem;
      }
      
      // 尝试通过DOM查找组件
      const emailSystemEl = document.querySelector('.email-system');
      if (emailSystemEl && emailSystemEl.__vue__) {
        return emailSystemEl.__vue__;
      }
      
      return null;
    },
    
    // 备用方法：使用事件总线触发邮件事件
    fallbackToEmailEvent(emailData) {
      console.log('使用事件总线触发邮件事件');
      
      try {
        // 确保数据格式正确
        if (typeof emailData === 'string') {
          try {
            emailData = JSON.parse(emailData);
          } catch (e) {
            emailData = { content: emailData };
          }
        }
        
        // 添加时间戳，用于后续判断数据是否过期
        emailData.timestamp = Date.now();
        
        // 保存到localStorage，以便EmailSystem组件可以读取
        localStorage.setItem('pending_email_data', JSON.stringify(emailData));
        
        // 设置一个标志，表示这是由AI助手触发的邮件
        localStorage.setItem('ai_generated_email', 'true');
        
        // 使用多种方式触发事件，确保能被捕获
        emitter.emit('open-compose-email', emailData);
        
        // 使用自定义事件
        const emailEvent = new CustomEvent('open-compose-email', {
          detail: emailData,
          bubbles: true
        });
        document.dispatchEvent(emailEvent);
        window.dispatchEvent(emailEvent);
        
        // 设置一个超时，如果在指定时间内没有被处理，则清理localStorage
        setTimeout(() => {
          // 检查是否已经被处理（如果已经被处理，localStorage中的数据应该已经被移除）
          if (localStorage.getItem('pending_email_data')) {
            console.log('邮件数据在10秒内未被处理，清理localStorage');
            localStorage.removeItem('pending_email_data');
            localStorage.removeItem('ai_generated_email');
          }
        }, 10000); // 10秒后清理
        
        // 导航到邮件系统
        this.$nextTick(() => {
          // 关闭AI助手面板
          this.closeAssistant();
          
          // 使用Vue Router导航到邮件页面
          try {
            import('../router').then(({ default: router }) => {
              // 检查当前路由，避免重复导航
              if (router.currentRoute.value && router.currentRoute.value.path !== '/workspace/email') {
                router.push('/workspace/email?compose=true');
              }
            }).catch(err => {
              console.error('导入router模块失败:', err);
            });
          } catch (routerError) {
            console.error('导航到邮件系统失败:', routerError);
          }
        });
      } catch (error) {
        console.error('处理邮件事件失败:', error);
        // 确保清理所有数据
        localStorage.removeItem('pending_email_data');
        localStorage.removeItem('ai_generated_email');
      }
    },
    cleanupLocalStorage() {
      // 清理可能存在的localStorage数据
      try {
        localStorage.removeItem('ai_generated_email');
        localStorage.removeItem('pending_email_data');
        localStorage.removeItem('force_open_email');
      } catch (e) {
        console.error('清理localStorage数据失败:', e);
      }
    },
    cleanupOnRouteChange() {
      // 清理过渡层和localStorage数据
      this.removeTransitionOverlay();
      this.cleanupLocalStorage();
    }
  },
  beforeDestroy() {
    // 移除事件监听器
    emitter.off('toggle-ai-assistant');
    window.removeEventListener('popstate', this.cleanupOnRouteChange);
    
    // 清理可能存在的过渡层
    this.removeTransitionOverlay();
    
    // 清理localStorage中可能存在的临时数据
    this.cleanupLocalStorage();
    
    console.log('AiAssistant组件销毁，已清理所有资源');
  },
};
</script>

<style scoped>
/* 原有样式 */
.ai-assistant {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: 0;
  background-color: white;
  box-shadow: -2px 0 5px rgba(0,0,0,0.1);
  transition: width 0.3s ease;
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ai-assistant.active {
  width: 360px;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
}

.chat-input {
  display: flex;
  padding: 10px;
  border-top: 1px solid #eee;
  background-color: white;
}

.chat-input textarea {
  flex: 1;
  min-height: 40px;
  max-height: 120px;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 8px;
  margin-right: 10px;
  resize: none;
  font-size: 14px;
}

.chat-input button {
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0 15px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.chat-input button:hover {
  background-color: #40a9ff;
}

.message {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  line-height: 1.5;
  max-width: 85%;
  position: relative;
  box-shadow: none;
  border: 1px solid transparent;
  animation: none;
}

.user-message {
  background-color: #dcf3ff;
  border-radius: 12px 12px 0 12px;
  margin-left: auto;
  margin-right: 8px;
  border-color: #c6e9fe;
}

.ai-message {
  background-color: #f5f5f5;
  border-radius: 12px 12px 12px 0;
  margin-right: auto;
  margin-left: 8px;
  border-color: #e8e8e8;
}

.message p {
  margin: 0;
  padding: 0;
  word-break: break-word;
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  border-bottom: 1px solid #eee;
  background-color: #f8f9fa;
}

.ai-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.close-ai {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
}

.close-ai:hover {
  color: #666;
}

/* 动作按钮 */
.action-buttons {
  display: flex;
  justify-content: space-around;
  padding: 5px 10px;
  border-top: 1px solid #eee;
  margin-top: auto;
}

.action-btn {
  background: none;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
  color: #666;
  transition: background-color 0.2s;
}

.action-btn:hover {
  background-color: #f5f5f5;
}

/* 文件选择器 */
.file-selector {
  position: absolute;
  bottom: 80px;
  left: 10px;
  right: 10px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 12px;
  z-index: 10;
  max-height: 60vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.selector-header h4 {
  margin: 0;
  font-size: 14px;
}

.close-selector {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #555;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.close-selector:hover {
  background-color: #f0f0f0;
}

.file-tabs {
  display: flex;
  margin-bottom: 10px;
}

.tab-btn {
  flex: 1;
  padding: 6px 10px;
  background: none;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-right: 5px;
  cursor: pointer;
  font-size: 12px;
}

.tab-btn.active {
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

.file-list {
  margin-bottom: 10px;
  max-height: 200px;
  overflow-y: auto;
}

.file-item {
  padding: 8px 10px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background-color 0.2s, transform 0.2s;
  display: flex;
  align-items: center;
}

.file-item:hover {
  background-color: #f5f8ff;
  transform: translateX(2px);
}

.file-item.selected {
  background-color: #e8f0fe;
  border-left: 3px solid #4285f4;
}

.file-icon {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  background-color: #ddd;
  border-radius: 2px;
}

.file-name {
  flex: 1;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.selector-footer {
  display: flex;
  justify-content: flex-end;
}

.confirm-btn {
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.2s;
}

.confirm-btn:hover {
  background-color: #40a9ff;
}

.confirm-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 4px;
  padding: 20px;
  text-align: center;
  margin-bottom: 10px;
  transition: border-color 0.3s, background-color 0.3s;
}

.upload-area:hover {
  border-color: #1890ff;
  background-color: #f0f7ff;
}

.upload-icon {
  font-size: 30px;
  margin-bottom: 10px;
  color: #999;
}

.upload-text {
  font-size: 14px;
  margin-bottom: 5px;
  color: #333;
}

.upload-hint {
  font-size: 12px;
  color: #999;
}

.upload-queue {
  margin: 10px 0;
  max-height: 120px;
  overflow-y: auto;
}

.upload-item {
  display: flex;
  align-items: center;
  padding: 5px 8px;
  border-bottom: 1px solid #eee;
}

.upload-status {
  margin-left: auto;
  font-size: 12px;
  color: #999;
}

/* 已选择文件显示 */
.selected-files-container {
  padding: 8px 10px;
  background-color: #f9f9f9;
  border-top: 1px solid #eee;
  border-bottom: 1px solid #eee;
  max-height: 150px;
  overflow-y: auto;
}

.selected-files {
  margin-bottom: 8px;
}

.selected-files:last-child {
  margin-bottom: 0;
}

.selected-files-header {
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.selected-files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.selected-file {
  display: flex;
  align-items: center;
  background-color: #e6f7ff;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
}

.remove-file {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  margin-left: 5px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  font-size: 14px;
}

.remove-file:hover {
  color: #f56c6c;
}

.no-files {
  color: #999;
  font-size: 13px;
  padding: 10px;
  text-align: center;
}

/* 引用文件显示 */
.reference-files {
  margin-top: 6px;
  padding: 8px 10px;
  background-color: #f9f9fa;
  border-radius: 6px;
  border-left: 2px solid #52c41a;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  font-size: 12px;
}

.user-references {
  background-color: #f0f7ff;
  border-left: 2px solid #1890ff;
}

.reference-header {
  font-size: 12px;
  font-weight: 500;
  color: #595959;
  margin-bottom: 6px;
}

.reference-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.reference-item {
  display: flex;
  align-items: center;
  padding: 5px 8px;
  margin-bottom: 2px;
  border-radius: 4px;
  background-color: rgba(255,255,255,0.7);
  border: 1px solid #e6e6e6;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 1px rgba(0,0,0,0.02);
}

.reference-item:hover {
  background-color: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  transform: translateX(1px);
}

.file-icon {
  min-width: 14px;
  height: 14px;
  margin-right: 6px;
  background-color: #1890ff;
  border-radius: 2px;
  display: inline-block;
  position: relative;
}

.file-icon:after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  right: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 1px;
}

.file-name {
  flex: 1;
  font-size: 12px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-lines {
  font-size: 11px;
  color: #666;
  font-style: italic;
  margin-top: 2px;
  padding-left: 20px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  display: block;
}

/* 添加过渡动画样式 */
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: all 0.3s ease;
}
.slide-fade-enter-from, .slide-fade-leave-to {
  transform: translateY(10px);
  opacity: 0;
}

/* 添加消息区域动画 */
.message {
  animation: none;
}

@keyframes message-appear {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 优化按钮和交互元素的响应式反馈 */
.action-btn, .confirm-btn, .tab-btn {
  transition: all 0.2s ease;
}

.action-btn:hover, .confirm-btn:hover, .tab-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.action-btn:active, .confirm-btn:active, .tab-btn:active {
  transform: translateY(1px);
  box-shadow: none;
}

/* 滚动条样式 */
.chat-messages::-webkit-scrollbar,
.file-list::-webkit-scrollbar,
.selected-files-container::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track,
.file-list::-webkit-scrollbar-track,
.selected-files-container::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.chat-messages::-webkit-scrollbar-thumb,
.file-list::-webkit-scrollbar-thumb,
.selected-files-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover,
.file-list::-webkit-scrollbar-thumb:hover,
.selected-files-container::-webkit-scrollbar-thumb:hover {
  background: #a0a0a0;
}

/* 阴影效果 */
.ai-assistant {
  box-shadow: -5px 0 15px rgba(0, 0, 0, 0.1);
}

.message {
  box-shadow: none;
}

.file-selector {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

/* 为用户引用添加特定样式 */
.user-references {
  background-color: #e6f7ff;
  border-left: 3px solid #1890ff;
}

/* 提高对比度和整洁度 */
.ai-header {
  background-color: #f0f2f5;
  border-bottom: 2px solid #e8e8e8;
  padding: 12px 16px;
}

.ai-header h3 {
  color: #1a1a1a;
  font-weight: 600;
}

/* 改善消息区域 */
.message {
  margin-bottom: 16px;
  padding: 12px 14px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
  line-height: 1.5;
  max-width: 85%;
  position: relative;
}

.user-message {
  background-color: #dcf3ff;
  border-radius: 12px 12px 0 12px;
  margin-left: auto;
  margin-right: 8px;
}

.ai-message {
  background-color: #f5f5f5;
  border-radius: 12px 12px 12px 0;
  margin-right: auto;
  margin-left: 8px;
}

/* 改善输入区域 */
.chat-input {
  padding: 12px 16px;
  border-top: 2px solid #e8e8e8;
  background-color: #f9f9f9;
}

.chat-input textarea {
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #d9d9d9;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
  transition: all 0.3s;
}

.chat-input textarea:focus {
  border-color: #40a9ff;
  box-shadow: 0 0 0 2px rgba(24,144,255,0.2);
  outline: none;
}

.chat-input button {
  font-weight: 500;
  padding: 0 18px;
  height: 36px;
  border-radius: 6px;
}

/* 优化动作按钮 */
.action-buttons {
  padding: 10px 16px;
  border-top: 1px solid #f0f0f0;
  justify-content: center;
  gap: 12px;
}

.action-btn {
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 90px;
  transition: all 0.3s;
  color: #595959;
}

.action-btn:hover {
  color: #1890ff;
  border-color: #1890ff;
  background-color: #f0f7ff;
}

/* 引用文件样式优化 */
.reference-files {
  margin-top: 10px;
  padding: 10px 12px;
  background-color: #f9f9fa;
  border-radius: 8px;
  border-left: 3px solid #52c41a;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.user-references {
  background-color: #f0f7ff;
  border-left: 3px solid #1890ff;
}

.reference-header {
  font-size: 13px;
  font-weight: 500;
  color: #595959;
  margin-bottom: 8px;
}

.reference-item {
  padding: 6px 10px;
  margin-bottom: 4px;
  border-radius: 4px;
  background-color: rgba(255,255,255,0.7);
  border: 1px solid #e8e8e8;
}

.reference-item:hover {
  background-color: white;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

/* 改善选择器外观 */
.file-selector {
  bottom: 90px;
  box-shadow: 0 6px 16px rgba(0,0,0,0.15);
  border-radius: 10px;
  border: 1px solid #e8e8e8;
}

.selector-header {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.selector-header h4 {
  font-size: 15px;
  font-weight: 500;
}

.reference-section {
  background-color: #f9f9f9;
  border-radius: 10px;
  border: 1px solid #eaeaea;
  margin-top: 15px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.reference-title {
  font-size: 14px;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.reference-title .icon {
  margin-right: 6px;
  color: #4a5568;
}

.reference-list {
  max-height: 300px;
  overflow-y: auto;
  padding-right: 5px;
}

.reference-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  background-color: white;
  border-radius: 8px;
  border: 1px solid #e6e6e6;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  position: relative;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.reference-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
  border-color: #d1d5db;
  background-color: #f8fafc;
}

.reference-item:active {
  transform: translateY(0);
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}

.reference-item .file-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background-color: #ebf5ff;
  margin-right: 12px;
  color: #3b82f6;
}

.reference-item .file-content {
  flex-grow: 1;
  overflow: hidden;
}

.reference-item .file-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reference-item .file-lines {
  font-size: 12px;
  color: #64748b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}

.reference-item .preview-button {
  position: absolute;
  right: 8px;
  top: 8px;
  opacity: 0;
  transition: opacity 0.2s ease;
  background-color: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  color: #64748b;
}

.reference-item:hover .preview-button {
  opacity: 1;
}

.reference-item .preview-button:hover {
  background-color: #e2e8f0;
  color: #334155;
}

.action-suggestion {
    margin-top: 10px;
    display: flex;
    justify-content: flex-start;
}

.action-button {
    background-color: #1976d2;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    transition: background-color 0.3s;
    margin-top: 10px;
    width: auto;
    max-width: 150px;
    text-align: center;
    justify-content: center;
}

.action-button:hover {
    background-color: #1565c0;
}

/* 添加Markdown链接样式 */
:deep(.markdown-link) {
  display: inline-block;
  background-color: #1890ff;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  text-decoration: none;
  margin: 5px 0;
  transition: background-color 0.3s;
}

:deep(.markdown-link:hover) {
  background-color: #40a9ff;
  text-decoration: none;
}

/* 添加加载中状态样式 */
.thinking {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 5px 0;
}

.thinking .dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #1890ff;
  margin: 0 3px;
  animation: dotPulse 1.4s infinite ease-in-out both;
}

.thinking .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.thinking .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes dotPulse {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>