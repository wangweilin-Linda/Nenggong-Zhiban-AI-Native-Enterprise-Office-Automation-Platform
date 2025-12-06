<template>
  <div class="todo-list-container">
    <h1 class="page-title">待办事项</h1>
    
    <!-- 添加新任务 -->
    <div class="add-task">
      <input 
        type="text" 
        v-model="newTask" 
        @keyup.enter="addTask" 
        placeholder="输入新任务，按回车添加" 
        class="task-input"
      />
      <button @click="addTask" class="add-btn">添加</button>
    </div>
    
    <!-- 过滤选项 -->
    <div class="filters">
      <button 
        @click="currentFilter = 'all'" 
        :class="['filter-btn', { active: currentFilter === 'all' }]"
      >
        全部
      </button>
      <button 
        @click="currentFilter = 'active'" 
        :class="['filter-btn', { active: currentFilter === 'active' }]"
      >
        未完成
      </button>
      <button 
        @click="currentFilter = 'completed'" 
        :class="['filter-btn', { active: currentFilter === 'completed' }]"
      >
        已完成
      </button>
    </div>
    
    <!-- 任务列表 -->
    <div class="tasks-container">
      <div v-if="filteredTasks.length === 0" class="empty-tasks">
        当前没有{{ currentFilter === 'completed' ? '已完成' : currentFilter === 'active' ? '未完成' : '' }}任务
      </div>
      
      <ul class="task-list" v-else>
        <li 
          v-for="(task, index) in filteredTasks" 
          :key="index" 
          :class="['task-item', { completed: task.completed }]"
        >
          <div class="task-content">
            <input 
              type="checkbox" 
              :checked="task.completed" 
              @change="toggleTask(index)"
              class="task-checkbox"
            />
            <span 
              class="task-text" 
              :class="{ 'completed-text': task.completed }"
            >
              {{ task.text }}
            </span>
          </div>
          
          <div class="task-actions">
            <span class="task-date">{{ formatDate(task.date) }}</span>
            <button @click="deleteTask(index)" class="delete-btn">删除</button>
          </div>
        </li>
      </ul>
    </div>
    
    <!-- 统计信息 -->
    <div class="task-stats">
      <span>总计: {{ tasks.length }}</span>
      <span>完成: {{ tasks.filter(t => t.completed).length }}</span>
      <span>未完成: {{ tasks.filter(t => !t.completed).length }}</span>
      
      <button 
        v-if="tasks.some(t => t.completed)"
        @click="clearCompleted" 
        class="clear-btn"
      >
        清除已完成
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TodoList',
  data() {
    return {
      tasks: [],
      newTask: '',
      currentFilter: 'all'
    };
  },
  computed: {
    filteredTasks() {
      if (this.currentFilter === 'all') return this.tasks;
      if (this.currentFilter === 'active') return this.tasks.filter(task => !task.completed);
      if (this.currentFilter === 'completed') return this.tasks.filter(task => task.completed);
      return this.tasks;
    }
  },
  mounted() {
    this.loadTasks();
  },
  methods: {
    loadTasks() {
      // 从localStorage加载任务
      const savedTasks = localStorage.getItem('tasks');
      if (savedTasks) {
        try {
          this.tasks = JSON.parse(savedTasks);
        } catch (e) {
          console.error('解析任务数据失败:', e);
          this.tasks = [];
        }
      }
      
      // 如果没有任务，添加示例任务
      if (!this.tasks || !this.tasks.length) {
        this.tasks = [
          { text: '完成OA系统前端开发', completed: false, date: new Date() },
          { text: '编写API文档', completed: false, date: new Date() },
          { text: '准备周会演示', completed: false, date: new Date() }
        ];
        this.saveTasks();
      }
    },
    saveTasks() {
      // 保存任务到localStorage
      localStorage.setItem('tasks', JSON.stringify(this.tasks));
    },
    addTask() {
      if (!this.newTask.trim()) return;
      
      this.tasks.unshift({
        text: this.newTask,
        completed: false,
        date: new Date()
      });
      
      this.newTask = '';
      this.saveTasks();
    },
    toggleTask(index) {
      const realIndex = this.tasks.indexOf(this.filteredTasks[index]);
      if (realIndex !== -1) {
        this.tasks[realIndex].completed = !this.tasks[realIndex].completed;
        this.saveTasks();
      }
    },
    deleteTask(index) {
      const realIndex = this.tasks.indexOf(this.filteredTasks[index]);
      if (realIndex !== -1) {
        this.tasks.splice(realIndex, 1);
        this.saveTasks();
      }
    },
    clearCompleted() {
      this.tasks = this.tasks.filter(task => !task.completed);
      this.saveTasks();
    },
    formatDate(date) {
      if (!date) return '';
      
      const d = new Date(date);
      if (isNaN(d.getTime())) return '';
      
      return d.toLocaleDateString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  }
};
</script>

<style scoped>
.todo-list-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.page-title {
  font-size: 24px;
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

.add-task {
  display: flex;
  margin-bottom: 20px;
}

.task-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px 0 0 4px;
  font-size: 14px;
}

.add-btn {
  padding: 10px 16px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
}

.filters {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.filter-btn {
  padding: 6px 12px;
  margin: 0 5px;
  background-color: transparent;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  cursor: pointer;
}

.filter-btn.active {
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

.tasks-container {
  margin-bottom: 20px;
}

.empty-tasks {
  text-align: center;
  color: #999;
  padding: 30px 0;
}

.task-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.3s;
}

.task-item:hover {
  background-color: #f9f9f9;
}

.task-content {
  display: flex;
  align-items: center;
}

.task-checkbox {
  margin-right: 10px;
}

.task-text {
  font-size: 14px;
}

.completed-text {
  text-decoration: line-through;
  color: #999;
}

.task-actions {
  display: flex;
  align-items: center;
}

.task-date {
  font-size: 12px;
  color: #999;
  margin-right: 10px;
}

.delete-btn {
  background-color: transparent;
  border: none;
  color: #ff4d4f;
  cursor: pointer;
  font-size: 12px;
}

.task-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
  font-size: 12px;
  color: #666;
}

.clear-btn {
  background-color: transparent;
  border: none;
  color: #1890ff;
  cursor: pointer;
}
</style> 