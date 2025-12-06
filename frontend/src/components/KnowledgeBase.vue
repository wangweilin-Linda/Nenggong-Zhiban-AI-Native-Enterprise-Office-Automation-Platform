<template>
  <div class="knowledge-base">
    <!-- 知识库列表视图 -->
    <div v-if="!showDetail">
      <div class="kb-header">
        <h2>个人知识库</h2>
        <div class="header-right">
          <div class="search-bar">
            <button class="search-btn">
              <i class="search-icon">搜索</i>
            </button>
            <input type="text" v-model="searchQuery" placeholder="搜索知识库..." />
            <select v-model="selectedCategory">
              <option value="">所有分类</option>
              <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
        </div>
      </div>

      <div class="kb-content">
        <div class="knowledge-grid">
          <div v-for="item in filteredItems" 
               :key="item.id" 
               class="knowledge-card"
               @click="openDetail(item)">
            <div class="card-content">
              <h3>{{ item.title }}</h3>
              <p class="category">{{ item.category }}</p>
            </div>
          </div>

          <!-- 新增知识库卡片 -->
          <div class="knowledge-card add-card" @click="createNewKnowledge">
            <div class="add-content">
              <span class="add-icon">+</span>
              <span>新增知识库</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 知识库详情视图 -->
    <div v-else>
      <knowledge-detail 
        v-if="currentItem && !isEditing"
        :item="currentItem"
        @close="closeDetail"
        @edit="editKnowledge"
        @delete="deleteKnowledge" />
      
      <knowledge-form 
        v-else
        :item="editingItem"
        @close="closeDetail"
        @save="saveKnowledge" />
    </div>
  </div>
</template>

<script>
import KnowledgeForm from './KnowledgeForm.vue';
import KnowledgeDetail from './KnowledgeDetail.vue';

export default {
  components: {
    KnowledgeForm,
    KnowledgeDetail
  },
  data() {
    return {
      searchQuery: '',
      selectedCategory: '',
      tagFilter: '',
      showDetail: false,
      currentItem: null,
      isCreating: false,
      isEditing: false,
      editingItem: null,
      items: [], // 知识条目列表
      categories: ['技术文档', '工作笔记', '学习资料', '项目文档'],
    };
  },
  computed: {
    filteredItems() {
      return this.items.filter(item => {
        const matchSearch = item.title.toLowerCase().includes(this.searchQuery.toLowerCase());
        const matchCategory = !this.selectedCategory || item.category === this.selectedCategory;
        const matchTags = !this.tagFilter || item.tags.some(tag => 
          tag.toLowerCase().includes(this.tagFilter.toLowerCase())
        );
        return matchSearch && matchCategory && matchTags;
      });
    }
  },
  methods: {
    formatDate(date) {
      return new Date(date).toLocaleDateString();
    },
    openDetail(item) {
      this.currentItem = item;
      this.showDetail = true;
    },
    createNewKnowledge() {
      this.currentItem = null;
      this.showDetail = true;
    },
    closeDetail() {
      this.showDetail = false;
      this.currentItem = null;
      this.isEditing = false;
      this.editingItem = null;
    },
    editKnowledge(item) {
      this.isEditing = true;
      this.editingItem = { ...item }; // 复制一份，避免直接修改原对象
      this.showDetail = true;
    },
    async saveKnowledge(knowledge) {
      try {
        // 如果是编辑现有知识
        if (knowledge.id) {
          const index = this.items.findIndex(item => item.id === knowledge.id);
          if (index !== -1) {
            this.items[index] = { ...knowledge };
          }
        } else {
          // 如果是新增知识
          const newKnowledge = {
            ...knowledge,
            id: Date.now(), // 临时ID，实际应该由后端生成
            createdAt: new Date().toISOString()
          };
          this.items.unshift(newKnowledge);
        }
        this.closeDetail();
      } catch (error) {
        console.error('保存知识失败:', error);
      }
    },
    deleteKnowledge(id) {
      const index = this.items.findIndex(item => item.id === id);
      if (index !== -1) {
        this.items.splice(index, 1);
      }
      this.closeDetail();
    }
  }
};
</script>

<style scoped>
.knowledge-base {
  padding: 20px;
  height: 100%;
  background: #fff;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header-right {
  display: flex;
  gap: 20px;
  align-items: center;
}

.search-bar {
  display: flex;
  gap: 10px;
}

.search-bar input,
.search-bar select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-width: 200px;
}

.knowledge-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 20px 0;
}

.knowledge-card {
  width: 300px;
  height: 150px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.knowledge-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.card-content {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-content h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
}

.category {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.add-card {
  border: 2px dashed #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}

.add-content {
  text-align: center;
  color: #666;
}

.add-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 10px;
}

/* 移除不需要的样式 */
.kb-sidebar {
  display: none;
}
</style>

<style scoped>
.knowledge-base {
  height: 100%;
  padding: 20px;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.search-bar {
  display: flex;
  gap: 10px;
}

.search-bar input,
.search-bar select {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.add-btn {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.kb-content {
  display: flex;
  height: calc(100% - 60px);
  gap: 20px;
}

.kb-sidebar {
  width: 250px;
  background: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
}

.kb-main {
  flex: 1;
  background: white;
  padding: 20px;
  border-radius: 4px;
  overflow-y: auto;
}

.knowledge-item {
  padding: 15px;
  border: 1px solid #eee;
  margin-bottom: 10px;
  border-radius: 4px;
  cursor: pointer;
}

.knowledge-item:hover {
  background: #f9f9f9;
}

.tag {
  background: #e0e0e0;
  padding: 2px 8px;
  border-radius: 12px;
  margin-right: 5px;
  font-size: 12px;
}

.item-tags {
  margin: 8px 0;
}

.item-meta {
  font-size: 12px;
  color: #666;
}
</style>