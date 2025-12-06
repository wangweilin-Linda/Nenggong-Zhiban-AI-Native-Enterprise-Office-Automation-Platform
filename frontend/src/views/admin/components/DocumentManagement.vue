<template>
  <div class="document-management">
    <div class="header">
      <h2>文档管理</h2>
      <button @click="showAddDoc = true">添加文档</button>
    </div>

    <table class="doc-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>标题</th>
          <th>发布时间</th>
          <th>发布单位</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="doc in documents" :key="doc.id">
          <td>{{ doc.id }}</td>
          <td>{{ doc.title }}</td>
          <td>{{ doc.publish_time }}</td>
          <td>{{ doc.publish_unit }}</td>
          <td>
            <button @click="editDoc(doc)">编辑</button>
            <button @click="deleteDoc(doc.id)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 添加/编辑文档弹窗 -->
    <div v-if="showAddDoc" class="modal">
      <div class="modal-content">
        <h3>{{ editingDoc ? '编辑文档' : '添加文档' }}</h3>
        <input v-model="docForm.title" placeholder="标题">
        <input v-model="docForm.publish_unit" placeholder="发布单位">
        <textarea v-model="docForm.content" placeholder="文档内容"></textarea>
        <div class="modal-footer">
          <button @click="saveDoc">保存</button>
          <button @click="showAddDoc = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      documents: [],
      showAddDoc: false,
      editingDoc: null,
      docForm: {
        title: '',
        publish_unit: '',
        content: ''
      }
    }
  },
  mounted() {
    this.fetchDocuments()
  },
  methods: {
    async fetchDocuments() {
      try {
        const response = await fetch('/api/admin/documents', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
          }
        })
        if (response.ok) {
          this.documents = await response.json()
        }
      } catch (error) {
        console.error('获取文档列表失败:', error)
      }
    },
    editDoc(doc) {
      this.editingDoc = doc
      this.docForm = { ...doc }
      this.showAddDoc = true
    },
    async saveDoc() {
      try {
        const url = this.editingDoc 
          ? `/api/admin/documents/${this.editingDoc.id}`
          : '/api/admin/documents'
        
        const response = await fetch(url, {
          method: this.editingDoc ? 'PUT' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
          },
          body: JSON.stringify(this.docForm)
        })

        if (response.ok) {
          this.showAddDoc = false
          this.fetchDocuments()
          this.docForm = { title: '', publish_unit: '', content: '' }
          this.editingDoc = null
        }
      } catch (error) {
        console.error('保存文档失败:', error)
      }
    },
    async deleteDoc(id) {
      if (!confirm('确定要删除该文档吗？')) return

      try {
        const response = await fetch(`/api/admin/documents/${id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
          }
        })

        if (response.ok) {
          this.fetchDocuments()
        }
      } catch (error) {
        console.error('删除文档失败:', error)
      }
    }
  }
}
</script>

<style scoped>
.document-management {
  padding: 24px;
  background: white;
  border-radius: 8px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
}

.doc-table th,
.doc-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background: white;
  padding: 24px;
  border-radius: 8px;
  width: 500px;
}

.modal-content input,
.modal-content textarea {
  width: 100%;
  margin-bottom: 16px;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.modal-content textarea {
  height: 200px;
  resize: vertical;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

button {
  padding: 8px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background: #40a9ff;
}
</style>