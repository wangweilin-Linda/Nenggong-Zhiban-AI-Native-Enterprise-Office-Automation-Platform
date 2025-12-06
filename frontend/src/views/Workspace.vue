<template>
  <div class="workspace-container">
    <!-- 左侧导航栏 -->
    <aside class="sidebar">
      <div class="logo">
        <h1>OA系统</h1>
      </div>
      <nav class="nav-menu">
        <router-link to="/dashboard" class="nav-item">
          <i class="icon dashboard-icon"></i>
          <span>控制台</span>
        </router-link>
        <router-link to="/workspace/todo" class="nav-item">
          <i class="icon todo-icon"></i>
          <span>待办事项</span>
        </router-link>
        <router-link to="/workspace/email" class="nav-item">
          <i class="icon email-icon"></i>
          <span>邮件系统</span>
        </router-link>
        <router-link to="/workspace/approval" class="nav-item">
          <i class="icon approval-icon"></i>
          <span>审批中心</span>
        </router-link>
      </nav>
      <div class="user-panel">
        <div class="user-info">
          <img src="https://via.placeholder.com/40" alt="用户头像" class="avatar">
          <div class="user-details">
            <span class="username">{{ username }}</span>
            <router-link to="/workspace/profile" class="profile-link">个人资料</router-link>
          </div>
        </div>
        <button @click="logout" class="logout-btn">退出登录</button>
      </div>
    </aside>

    <!-- 主内容区域 -->
    <main class="main-content">
      <header class="top-bar">
        <div class="breadcrumb">
          <span>{{ getCurrentRouteName() }}</span>
        </div>
        <div class="top-actions">
          <button class="notification-btn">
            <i class="icon notification-icon"></i>
            <span class="badge" v-if="notifications.length">{{ notifications.length }}</span>
          </button>
        </div>
      </header>
      
      <!-- 子路由渲染区域 -->
      <div class="content-area">
        <router-view></router-view>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'Workspace',
  data() {
    return {
      username: '未登录',
      notifications: []
    };
  },
  mounted() {
    this.loadUserInfo();
  },
  methods: {
    loadUserInfo() {
      // 从localStorage获取用户信息
      const userStr = localStorage.getItem('user');
      if (userStr) {
        try {
          const user = JSON.parse(userStr);
          this.username = user.username || user.full_name || '用户';
        } catch (e) {
          console.error('解析用户信息失败:', e);
          this.username = '用户';
        }
      }
    },
    getCurrentRouteName() {
      // 获取当前路由名称，用于面包屑导航
      const route = this.$route;
      if (route.name === 'TodoList') return '待办事项';
      if (route.name === 'EmailSystem') return '邮件系统';
      if (route.name === 'ApprovalCenter') return '审批中心';
      if (route.name === 'UserProfile') return '个人资料';
      return '工作区';
    },
    logout() {
      // 清除登录信息
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // 跳转到登录页
      this.$router.push('/login');
    }
  }
};
</script>

<style scoped>
.workspace-container {
  display: flex;
  min-height: 100vh;
  background-color: #f0f2f5;
}

.sidebar {
  width: 250px;
  background-color: #001529;
  color: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
}

.logo {
  padding: 16px;
  text-align: center;
  border-bottom: 1px solid #002140;
}

.logo h1 {
  color: white;
  font-size: 20px;
  margin: 0;
}

.nav-menu {
  padding: 16px 0;
  flex-grow: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  color: rgba(255, 255, 255, 0.65);
  text-decoration: none;
  transition: all 0.3s;
}

.nav-item:hover,
.nav-item.router-link-active {
  color: #fff;
  background-color: #1890ff;
}

.icon {
  margin-right: 10px;
  width: 16px;
  height: 16px;
  display: inline-block;
}

.user-panel {
  padding: 16px;
  border-top: 1px solid #002140;
}

.user-info {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 12px;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: bold;
  margin-bottom: 4px;
}

.profile-link {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  text-decoration: none;
}

.profile-link:hover {
  color: #1890ff;
}

.logout-btn {
  width: 100%;
  background-color: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: rgba(255, 255, 255, 0.65);
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.logout-btn:hover {
  color: #fff;
  border-color: #fff;
}

.main-content {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.top-bar {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.breadcrumb {
  font-size: 16px;
  font-weight: bold;
}

.top-actions {
  display: flex;
  align-items: center;
}

.notification-btn {
  background: none;
  border: none;
  cursor: pointer;
  position: relative;
  padding: 8px;
}

.badge {
  position: absolute;
  top: 0;
  right: 0;
  background-color: #f5222d;
  color: white;
  border-radius: 10px;
  padding: 0 5px;
  font-size: 12px;
  line-height: 16px;
  min-width: 16px;
  text-align: center;
}

.content-area {
  padding: 24px;
  height: calc(100vh - 64px);
  overflow-y: auto;
}
</style> 