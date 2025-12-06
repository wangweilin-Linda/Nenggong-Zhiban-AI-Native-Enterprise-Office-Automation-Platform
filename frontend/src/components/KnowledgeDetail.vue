<template>
  <div class="knowledge-detail">
    <div class="detail-header">
      <h2>{{ item.title }}</h2>
      <div class="header-actions">
        <button @click="handleEdit">编辑</button>
        <button @click="handleDelete" class="delete-btn">删除</button>
        <button @click="$emit('close')" class="close-btn">返回</button>
      </div>
    </div>

    <div class="detail-meta">
      <span class="category">分类：{{ item.category }}</span>
      <br>
      <span class="date">创建时间：{{ formatDate(item.createdAt) }}</span>
    </div>

    <div class="detail-content">
      {{ item.content }}
    </div>

    <div class="detail-attachments" v-if="item.attachments && item.attachments.length">
      <h3>附件</h3>
      <ul>
        <li v-for="file in item.attachments" :key="file.id" class="attachment-item">
          <div class="file-info">
            <svg class="pdf-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512">
              <path d="M181.9 256.1c-5.1-9.2-9.3-21.4-9.3-34.6 0-28.9 11.7-50.5 49.8-50.5 21.9 0 34 5 49.8 13V180c-12.9-9.8-27.8-13.5-49.8-13.5-48 0-71.8 28-71.8 70.4 0 14.5 4.6 30.7 10.3 42.2.5.7 1.1 1.4 1.6 2.1-14.6 7.1-25.6 21.2-27.8 39.5-3.3 29.5 15.9 54.6 39.5 54.6 20.7 0 37.2-11.4 48.5-29H286v-44h-59.9z"/>
            </svg>
            <span>{{ getFileName(file) }}</span>
          </div>
          <div class="file-actions">
            <a :href="getFileUrl(file)" target="_blank" class="download-btn" @click.prevent="handlePreview(file)">
              预览
            </a>
            <a :href="getFileUrl(file)" class="download-btn" @click.prevent="handleDownload(file)">
              下载
            </a>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    item: {
      type: Object,
      required: true
    }
  },
  methods: {
    formatDate(date) {
      return new Date(date).toLocaleDateString();
    },
    handleEdit() {
      this.$emit('edit', this.item);
    },
    getFileName(file) {
      if (!file) return '未知文件';
      return file.originalName || file.displayName || file.name || '未知文件';
    },
    getFileUrl(file) {
      if (!file) {
        console.warn('文件对象未定义');
        return '#';
      }
      
      const fileId = file.id || file.path || file.name;
      
      if (!fileId) {
        console.warn('无效的文件标识符');
        return '#';
      }
      
      return `/api/files/download/${fileId}`;
    },
    async deleteAttachmentFile(fileId) {
      try {
        const response = await fetch(`/api/files/${fileId}`, {
          method: 'DELETE'
        });
        if (!response.ok) {
          console.error('删除文件失败:', fileId);
        }
      } catch (error) {
        console.error('删除文件请求失败:', error);
      }
    },

    async handleDelete() {
      if (confirm('确定要删除这条知识吗？')) {
        try {
          // 先删除所有附件文件
          if (this.item.attachments && this.item.attachments.length > 0) {
            for (const file of this.item.attachments) {
              await this.deleteAttachmentFile(file.id);
            }
          }
          
          // 删除知识条目
          this.$emit('delete', this.item.id);
        } catch (error) {
          console.error('删除知识及附件失败:', error);
          alert('删除失败，请重试');
        }
      }
    },
    async handlePreview(file) {
      try {
        const response = await fetch(this.getFileUrl(file));
        if (!response.ok) throw new Error('预览失败');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        window.open(url, '_blank');
        
        // 延迟释放 URL 对象
        setTimeout(() => {
          window.URL.revokeObjectURL(url);
        }, 1000);
      } catch (error) {
        console.error('文件预览失败:', error);
        alert('文件预览失败，请重试');
      }
    },

    async handleDownload(file) {
      try {
        const response = await fetch(this.getFileUrl(file));
        if (!response.ok) throw new Error('下载失败');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = this.getFileName(file);
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error('文件下载失败:', error);
        alert('文件下载失败，请重试');
      }
    }
  }
};
</script>

<style scoped>
.knowledge-detail {
  padding: 20px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.header-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.delete-btn {
  background: #ff4444;
  color: white;
}

.close-btn {
  background: #666;
  color: white;
}

.detail-meta {
  margin-bottom: 20px;
  color: #666;
}

.tag {
  background: #e0e0e0;
  padding: 2px 8px;
  border-radius: 12px;
  margin-right: 5px;
}

.detail-content {
  line-height: 1.6;
  margin: 20px 0;
  white-space: pre-wrap;
}

.detail-attachments {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.detail-attachments ul {
  list-style: none;
  padding: 0;
}

.attachment-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 4px;
}

.file-info {
  display: flex;
  align-items: center;
}

.pdf-icon {
  width: 20px;
  height: 20px;
  margin-right: 10px;
  fill: #e74c3c;
}

.file-actions {
  display: flex;
  gap: 10px;
}

.download-btn {
  color: #2196F3;
  text-decoration: none;
  background: #e3f2fd;
  padding: 5px 10px;
  border-radius: 4px;
}

.download-btn:hover {
  background: #bbdefb;
  text-decoration: none;
}
</style>