<template>
  <div class="personal-kb">
    <div class="kb-header">
      <h2>个人知识库</h2>
      <button class="upload-btn" @click="showUploadDialog">
        <span>+</span> 上传文档
      </button>
    </div>
    
    <div class="kb-list">
      <div v-for="doc in documents" :key="doc.id" class="kb-item">
        <div class="doc-info">
          <span class="doc-icon">📄</span>
          <div class="doc-details">
            <div class="doc-name">{{ doc.name }}</div>
            <div class="doc-meta">上传时间：{{ doc.uploadTime }}</div>
          </div>
        </div>
        <button class="delete-btn" @click="deleteDocument(doc.id)">删除</button>
      </div>
    </div>

    <!-- 上传对话框 -->
    <div v-if="showDialog" class="upload-dialog">
      <div class="dialog-content">
        <h3>上传文档</h3>
        <input type="file" @change="handleFileSelect" accept=".pdf,.doc,.docx">
        <div class="dialog-buttons">
          <button @click="uploadFile">确认</button>
          <button @click="showDialog = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PersonalKnowledgeBase',
  data() {
    return {
      documents: [],
      showDialog: false,
      selectedFile: null
    }
  },
  methods: {
    showUploadDialog() {
      this.showDialog = true
    },
    handleFileSelect(event) {
      this.selectedFile = event.target.files[0]
    },
    async uploadFile() {
      if (!this.selectedFile) return
      
      const formData = new FormData()
      formData.append('file', this.selectedFile)
      
      try {
        // TODO: 实现文件上传API
        this.showDialog = false
        this.selectedFile = null
      } catch (error) {
        console.error('上传失败:', error)
      }
    },
    async deleteDocument(docId) {
      // TODO: 实现删除文档API
    }
  }
}
</script>

<style scoped>
.personal-kb {
  padding: 20px;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.upload-btn {
  padding: 8px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.kb-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #e8e8e8;
  margin-bottom: 8px;
  border-radius: 4px;
}

.doc-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.delete-btn {
  padding: 4px 8px;
  color: #ff4d4f;
  border: 1px solid #ff4d4f;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.upload-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.dialog-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  min-width: 300px;
}

.dialog-buttons {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>