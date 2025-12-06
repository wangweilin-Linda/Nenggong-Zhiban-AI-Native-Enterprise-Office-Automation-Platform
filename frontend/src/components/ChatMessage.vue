<template>
  <div class="chat-message">
    <div class="message-content">{{ message.answer }}</div>
    
    <!-- 添加来源信息显示 -->
    <div v-if="message.sources && message.sources.length" class="message-sources">
      <div class="sources-header">参考来源：</div>
      <div class="source-list">
        <button 
          v-for="(source, index) in message.sources" 
          :key="index"
          class="source-item"
          @click="openDocument(source)"
        >
          {{ source.filename }} (第{{ source.page }}页)
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    message: {
      type: Object,
      required: true
    }
  },
  methods: {
    openDocument(source) {
      // 触发事件，让父组件处理文档打开
      this.$emit('open-document', source);
    }
  }
}
</script>

<style scoped>
.message-sources {
  margin-top: 10px;
  border-top: 1px solid #eee;
  padding-top: 10px;
}

.sources-header {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-item {
  padding: 4px 12px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #1890ff;
}

.source-item:hover {
  background: #e6f7ff;
}
</style>