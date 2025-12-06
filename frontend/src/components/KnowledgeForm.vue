<template>
  <div class="knowledge-form">
    <h2>{{ isEdit ? '编辑知识' : '新增知识' }}</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label>标题</label>
        <input type="text" v-model="form.title" required />
      </div>
      
      <div class="form-group">
        <label>内容</label>
        <textarea v-model="form.content" rows="10" required></textarea>
      </div>
      
      <div class="form-group">
        <label>分类</label>
        <select v-model="form.category" required>
          <option value="">请选择分类</option>
          <option v-for="cat in categories" :key="cat" :value="cat">
            {{ cat }}
          </option>
        </select>
      </div>
      
      
      <div class="form-group">
        <label>文件上传 (仅支持PDF文件)</label>
        <input type="file" @change="handleFileUpload" multiple accept=".pdf" />
        <p v-if="uploadStatus" :class="['upload-status', uploadStatus.includes('成功') ? 'success' : uploadStatus.includes('失败') ? 'error' : '']">
          {{ uploadStatus }}
        </p>
        <div v-if="form.attachments && form.attachments.length" class="attachment-list">
          <h4>已上传文件:</h4>
          <ul>
            <li v-for="file in form.attachments" :key="file.id">
              {{ file.name }}
              <button type="button" class="remove-file" @click="removeAttachment(file)">×</button>
            </li>
          </ul>
        </div>
      </div>
      
      <div class="form-actions">
        <button type="submit">保存</button>
        <button type="button" @click="handleCancel">取消</button>
      </div>
    </form>
  </div>
</template>

<script>
export default {
  props: {
    item: {
      type: Object,
      default: () => null  // 修改默认值的返回方式
    }
  },
  data() {
    return {
      form: {
        title: '',
        content: '',
        category: '',
        tags: [],
        url: '',
        attachments: []  // 确保初始化 attachments 数组
      },
      originalAttachments: [], // 新增：保存原始附件列表
      tagInput: '',
      uploadStatus: '',
      categories: ['技术文档', '工作笔记', '学习资料', '项目文档']
    };
  },
  computed: {
    isEdit() {
      return Boolean(this.item);  // 修改计算属性的实现
    }
  },

  methods: {
    addTag() {
      if (this.tagInput && !this.form.tags.includes(this.tagInput)) {
        this.form.tags.push(this.tagInput);
      }
      this.tagInput = '';
    },
    removeTag(tag) {
      this.form.tags = this.form.tags.filter(t => t !== tag);
    },
    async handleFileUpload(event) {
      const files = event.target.files;
      if (!files.length) return;

      this.uploadStatus = '文件上传中...';

      for (let file of files) {
        // 检查文件类型
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          this.uploadStatus = '只能上传PDF文件!';
          event.target.value = '';
          return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
          const response = await fetch('/api/files/upload', {
            method: 'POST',
            body: formData
          });

          if (response.ok) {
            const result = await response.json();
            this.form.attachments.push({
              id: result.id,
              name: result.name,
              url: result.url
            });
            this.uploadStatus = '文件上传成功！';
          } else {
            const error = await response.json();
            this.uploadStatus = `上传失败: ${error.detail}`;
          }
        } catch (error) {
          console.error('文件上传失败:', error);
          this.uploadStatus = '文件上传失败，请重试！';
        }
      }

      event.target.value = '';  // 修改这里，使用event.target而不是this.$refs.fileInput
    },
    removeAttachment(file) {
      // 从附件列表中移除
      this.form.attachments = this.form.attachments.filter(f => f.id !== file.id);
    },
    handleSubmit() {
      this.$emit('save', this.form);
    },
    async deleteUploadedFile(fileId) {
      try {
        const response = await fetch(`http://localhost:8000/api/files/${fileId}`, {
          method: 'DELETE'
        });
        if (!response.ok) {
          console.error('删除文件失败:', fileId);
        }
      } catch (error) {
        console.error('删除文件请求失败:', error);
      }
    },

    async handleCancel() {
      if (this.form.attachments && this.form.attachments.length > 0) {
        // 找出新上传的文件（不在原始附件列表中的文件）
        const newAttachments = this.form.attachments.filter(
          file => !this.originalAttachments.some(orig => orig.id === file.id)
        );
        
        // 只删除新上传的文件
        for (const file of newAttachments) {
          await this.deleteUploadedFile(file.id);
        }
      }
      // 发送关闭事件
      this.$emit('close');
    }
  },

  created() {
    if (this.item) {
      // 深拷贝确保不会直接修改原对象
      this.form = JSON.parse(JSON.stringify(this.item));
      
      // 保存原始附件列表的副本
      this.originalAttachments = JSON.parse(JSON.stringify(this.item.attachments || []));
      
      // 确保tags是数组
      if (!this.form.tags) {
        this.form.tags = [];
      }
    }
  }
};
</script>

<style scoped>
.knowledge-form {
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.tags {
  margin-top: 10px;
}

.tag {
  background: #e0e0e0;
  padding: 2px 8px;
  border-radius: 12px;
  margin-right: 5px;
  cursor: pointer;
}

.form-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button[type="submit"] {
  background: #4CAF50;
  color: white;
}

button[type="button"] {
  background: #f5f5f5;
}

.upload-status {
  margin-top: 5px;
  font-size: 0.9em;
}

.upload-status.success {
  color: green;
}

.upload-status.error {
  color: red;
}

.attachment-list {
  margin-top: 10px;
}

.attachment-list ul {
  list-style: none;
  padding: 0;
}

.attachment-list li {
  background: #f5f5f5;
  padding: 5px 10px;
  margin: 5px 0;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.remove-file {
  background: #ff4444;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}
</style>