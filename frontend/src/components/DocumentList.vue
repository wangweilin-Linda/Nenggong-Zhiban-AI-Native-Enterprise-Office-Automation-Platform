<template>
  <div class="document-list">
    <div
      v-for="doc in documents"
      :key="doc.id"
      class="document-item"
      @click="$emit('select-document', doc)"
    >
      <h3>{{ doc.title }}</h3>
      <div class="document-meta">
        <span class="publish-time">发布时间：{{ formatTime(doc.created_at) }}</span>
        <span class="publish-unit">发布部门：{{ doc.category_name || '未分类' }}</span>
        <span class="owner">发布者：{{ doc.owner_name || '未知' }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    documents: {
      type: Array,
      required: true
    }
  },
  methods: {
    fetchDocuments() {
      this.$emit('fetch-documents');
    },
    formatTime(time) {
      if (!time) return '未知';
      return new Date(time).toLocaleDateString('zh-CN');
    }
  }
};
</script>

<style scoped>
.document-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 10px;
}

.document-item {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 15px;
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  cursor: pointer;
}

.document-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.document-item h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #333;
  font-size: 18px;
}

.document-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 14px;
  color: #666;
}

.publish-time {
  color: #1890ff;
  font-weight: 500;
}

.publish-unit {
  color: #52c41a;
}

.owner {
  color: #722ed1;
}
</style>