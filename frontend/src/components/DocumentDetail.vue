<template>
  <div class="document-detail">
    <button class="back-to-list" @click="$emit('back')">
      <span class="back-icon">←</span>
      <span class="back-text">返回列表</span>
    </button>
    <div class="document-header">
      <h1 class="document-title">{{ document.title }}</h1>
      <div class="document-info">
        <span>发布时间：<span class="publish-time">{{ formatTime(document.created_at) }}</span></span>
        <span>发布部门：<span class="publish-unit">{{ document.category_name || '未分类' }}</span></span>
        <span>发布者：<span class="owner">{{ document.owner_name || '未知' }}</span></span>
      </div>
    </div>
    
    <div class="document-content">
      <div class="content-text">{{ document.content }}</div>
    </div>

    <div class="document-attachments" v-if="document.attachments && document.attachments.length > 0">
      <h3 class="attachment-title">附件列表</h3>
      <ul class="attachment-list">
        <li v-for="(attachment, index) in document.attachments" :key="index" class="attachment-item">
          <span class="attachment-icon">📎</span>
          <div class="attachment-info">
            <div class="attachment-name">{{ attachment.filename || attachment }}</div>
            <div class="attachment-meta">{{ attachment.file_type || 'PDF文件' }}</div>
          </div>
          <button class="attachment-download" @click="downloadFile(attachment.filename || attachment)">下载</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    document: Object
  },
  methods: {
    formatTime(time) {
      if (!time) return '未知';
      return new Date(time).toLocaleDateString('zh-CN');
    },
    downloadFile(filename) {
      const link = document.createElement('a');
      link.href = `/api/documents/attachment/${filename}`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }
};
</script>

<style scoped>
.document-detail {
  padding: 20px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.back-to-list {
  display: flex;
  align-items: center;
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
  padding: 0;
  margin-bottom: 20px;
  font-size: 14px;
}

.back-icon {
  margin-right: 5px;
}

.document-header {
  margin-bottom: 20px;
  border-bottom: 1px solid #e8e8e8;
  padding-bottom: 15px;
}

.document-title {
  margin: 0 0 10px 0;
  font-size: 24px;
  color: #333;
}

.document-info {
  display: flex;
  gap: 20px;
  color: #666;
  font-size: 14px;
}

.publish-time, .publish-unit {
  color: #333;
  font-weight: 500;
}

.document-content {
  margin: 20px 0;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
}

.content-text {
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
}

.document-attachments {
  margin-top: 20px;
  border-top: 1px solid #e8e8e8;
  padding-top: 20px;
}

.attachment-title {
  margin: 0 0 15px 0;
  font-size: 18px;
  color: #333;
}

.attachment-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.attachment-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  margin-bottom: 10px;
}

.attachment-icon {
  font-size: 24px;
  margin-right: 15px;
}

.attachment-info {
  flex: 1;
}

.attachment-name {
  font-weight: 500;
  margin-bottom: 5px;
}

.attachment-meta {
  font-size: 12px;
  color: #666;
}

.attachment-download {
  padding: 5px 10px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 10px;
}

.attachment-download:hover {
  background: #40a9ff;
}
</style>
