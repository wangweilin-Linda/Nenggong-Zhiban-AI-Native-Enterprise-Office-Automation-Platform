<template>
  <div class="admin-dashboard">
    <div class="dashboard-header">
      <h1>管理员控制台</h1>
      <div class="user-info">
        <span>欢迎，管理员</span>
        <button @click="logout" class="logout-btn">退出登录</button>
      </div>
    </div>

    <div class="dashboard-content">
      <div class="sidebar">
        <div 
          v-for="(item, index) in menuItems" 
          :key="index"
          :class="['menu-item', { active: activeMenu === item.key }]"
          @click="activeMenu = item.key"
        >
          {{ item.label }}
        </div>
      </div>

      <div class="main-content">
        <!-- 文档管理 -->
        <DocumentManagement v-if="activeMenu === 'documents'" />
        
        <!-- 审批流程设计器 -->
        <WorkflowDesigner v-if="activeMenu === 'workflows'" />
        
        <!-- 其他模块可以在这里添加 -->
        <div v-if="activeMenu === 'users'" class="placeholder-content">
          <h2>用户管理</h2>
          <p>用户管理功能正在开发中...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import DocumentManagement from './components/DocumentManagement.vue';
import WorkflowDesigner from './components/WorkflowDesigner.vue';

export default {
  components: {
    DocumentManagement,
    WorkflowDesigner
  },
  data() {
    return {
      activeMenu: 'workflows', // 默认显示审批流程设计器
      menuItems: [
        { key: 'documents', label: '文档管理' },
        { key: 'workflows', label: '审批流程' },
        { key: 'users', label: '用户管理' }
      ]
    };
  },
  methods: {
    logout() {
      // 清除登录信息
      localStorage.removeItem('adminToken');
      // 跳转到登录页
      this.$router.push('/admin/login');
    }
  }
};
</script>

<style scoped>
.admin-dashboard {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.dashboard-header {
  background-color: #001529;
  color: white;
  padding: 0 20px;
  height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logout-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.dashboard-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  background-color: #001529;
  color: white;
  padding: 20px 0;
}

.menu-item {
  padding: 12px 20px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.menu-item:hover {
  background-color: #1890ff;
}

.menu-item.active {
  background-color: #1890ff;
}

.main-content {
  flex: 1;
  overflow: auto;
  background-color: #f0f2f5;
}

.placeholder-content {
  padding: 20px;
  background: white;
  margin: 20px;
  border-radius: 4px;
}
</style>