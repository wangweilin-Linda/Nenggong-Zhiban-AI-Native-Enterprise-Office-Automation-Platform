<template>
  <nav class="sidebar">
    <div class="logo">
      <h2>OA系统</h2>
    </div>
    <ul class="nav-menu">
      <li class="nav-item" :class="{ active: activeModule === 'public-info' }">
        <a href="#" @click.prevent="setModule('public-info')">
          <span class="icon">📢</span>
          <span class="text">公共信息</span>
        </a>
      </li>
      <li class="nav-item" :class="{ active: activeModule === 'personal-office' }">
        <a href="#" @click.prevent="setModule('personal-office')">
          <span class="icon">👨</span>
          <span class="text">个人办公</span>
        </a>
      </li>
      <li class="nav-item" :class="{ active: activeModule === 'document-process' }">
        <a href="#" @click.prevent="setModule('document-process')">
          <span class="icon">📝</span>
          <span class="text">公文办理</span>
        </a>
      </li>
      <li class="nav-item" :class="{ active: activeModule === 'knowledge-base' }">
        <a href="#" @click.prevent="setModule('knowledge-base')">
          <span class="icon">📚</span>
          <span class="text">个人知识库</span>
        </a>
      </li>
      <li class="nav-item" :class="{ active: activeModule === 'sandbox' }">
        <a href="#" @click.prevent="handleSandboxClick">
          <span class="icon">📊</span>
          <span class="text">数据分析沙盒</span>
        </a>
      </li>
      
      <!-- 管理员功能区 -->
      <div v-if="isAdmin" class="admin-section">
        <div class="section-title">管理员功能</div>
        <li class="nav-item" :class="{ active: activeModule === 'admin-workflow' }">
          <a href="#" @click.prevent="setModule('admin-workflow')">
            <span class="icon">⚙️</span>
            <span class="text">工作流管理</span>
          </a>
        </li>
        <li class="nav-item" :class="{ active: activeModule === 'admin-users' }">
          <a href="#" @click.prevent="setModule('admin-users')">
            <span class="icon">👥</span>
            <span class="text">用户管理</span>
          </a>
        </li>
      </div>
    </ul>
  </nav>
</template>

<script>
import emitter from '../utils/eventBus';

export default {
  data() {
    return {
      activeModule: 'public-info',
      isAdmin: false,
      adminCheckInterval: null
    };
  },
  created() {
    // 检查用户是否为管理员
    setTimeout(() => {
      this.checkAdmin();
    }, 100);
    
    // 监听登录状态变化
    emitter.on('user-login', (userData) => {
      console.log('监听到用户登录事件，用户数据:', userData);
      // 如果直接从事件获取到用户信息，优先使用
      if (userData && (userData.isAdmin === true || (userData.user && userData.user.is_admin))) {
        this.isAdmin = true;
        console.log('从登录事件确认管理员身份');
      } else {
        setTimeout(() => {
          this.checkAdmin();
        }, 100);
      }
      // 强制刷新侧边栏
      this.$forceUpdate();
    });
    
    // 添加DOM事件监听器
    document.addEventListener('user-login', this.handleDomUserLogin);
    
    // 监听存储变化
    window.addEventListener('storage', this.handleStorageChange);
    
    // 监听邮件事件
    emitter.on('compose-email', this.handleComposeEmail);
    window.addEventListener('compose-email', this.handleDomComposeEmail);
    
    emitter.on('user-logout', () => {
      this.isAdmin = false;
      this.$forceUpdate();
    });
    
    // 不使用定时器，避免频繁调用可能引起错误
    // this.adminCheckInterval = setInterval(() => {
    //   this.checkAdmin();
    // }, 5000);
  },
  beforeUnmount() {
    emitter.off('user-login');
    emitter.off('user-logout');
    emitter.off('compose-email');
    
    // 移除DOM事件监听器
    document.removeEventListener('user-login', this.handleDomUserLogin);
    window.removeEventListener('storage', this.handleStorageChange);
    window.removeEventListener('compose-email', this.handleDomComposeEmail);
    
    // 清除定时器
    if (this.adminCheckInterval) {
      clearInterval(this.adminCheckInterval);
    }
  },
  methods: {
    setModule(module) {
      this.activeModule = module;
      emitter.emit('module-changed', module);
      emitter.emit('workspace-module-changed', module);
    },
    handleSandboxClick() {
      this.setModule('sandbox');
      this.$router.push('/sandbox');
    },
    // 处理DOM事件的监听函数
    handleDomUserLogin(e) {
      if (e.detail) {
        console.log('收到DOM user-login事件:', e.detail);
        if (e.detail.isAdmin === true || (e.detail.user && e.detail.user.is_admin)) {
          this.isAdmin = true;
          console.log('从DOM事件确认管理员身份');
        } else {
          this.checkAdmin();
        }
        // 强制刷新侧边栏
        this.$forceUpdate();
      }
    },
    // 处理存储变化的监听函数
    handleStorageChange(e) {
      if (e.key === 'token' || e.key === 'user' || e.key === 'user_role' || e.key === 'mock_admin_token') {
        console.log('检测到存储变化，重新检查管理员状态');
        this.checkAdmin();
      }
    },
    checkAdmin() {
      try {
        console.log('检查管理员权限...');
        
        // 使用一个更安全的检查方法
        const safeCheckIncludes = (str, searchValue) => {
          return typeof str === 'string' && str.includes(searchValue);
        };
        
        // 检查token是否存在
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (!token) {
          console.log('未找到token，设置为非管理员');
          this.isAdmin = false;
          return;
        }
        
        console.log('当前token:', token);
        
        // 首先检查是否是普通用户或经理的模拟token
        if (safeCheckIncludes(token, 'mock_user_token') || safeCheckIncludes(token, 'mock_manager_token')) {
          console.log('检测到普通用户或经理token，明确设置为非管理员');
          this.isAdmin = false;
          // 确保没有错误设置的管理员标记
          localStorage.removeItem('mock_admin_token');
          this.$forceUpdate();
          return;
        }
        
        // 检查用户角色
        const userRole = localStorage.getItem('user_role') || sessionStorage.getItem('user_role');
        if (userRole === 'admin') {
          console.log('从user_role确认管理员身份');
          this.isAdmin = true;
          
          // 强制刷新一次视图
          this.$forceUpdate();
          return;
        }
        
        // 特殊标记直接检查
        const adminUsername = localStorage.getItem('adminUsername');
        if (adminUsername === 'admin') {
          console.log('特殊标记确认管理员身份');
          this.isAdmin = true;
          this.$forceUpdate();
          return;
        }
        
        // 检查模拟管理员token
        if (safeCheckIncludes(token, 'mock_admin_token')) {
          console.log('检测到管理员token');
          this.isAdmin = true;
          localStorage.setItem('mock_admin_token', 'true');
          this.$forceUpdate();
          return;
        }
        
        // 从localStorage或sessionStorage获取用户对象
        let user = null;
        try {
          const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
          if (userStr && userStr !== 'undefined' && userStr !== 'null') {
            user = JSON.parse(userStr);
          }
        } catch (e) {
          console.error('解析user对象失败:', e);
        }
        
        // 确保user不为null且有必要的属性，避免"Cannot read properties of null"错误
        if (user && typeof user === 'object') {
          const isAdminUser = user.is_admin === true || user.role === 'admin';
          if (isAdminUser) {
            console.log('从user对象确认管理员身份');
            this.isAdmin = true;
            this.$forceUpdate();
            return;
          } else {
            // 明确不是管理员的情况
            console.log('从user对象确认非管理员身份');
            this.isAdmin = false;
            this.$forceUpdate();
            return;
          }
        }
        
        // 默认情况，设置为非管理员
        console.log('无法确认管理员身份，设置为非管理员');
        this.isAdmin = false;
        this.$forceUpdate();
      } catch (error) {
        // 出错时默认为非管理员，确保安全
        console.error('检查管理员权限时发生错误:', error);
        this.isAdmin = false;
        this.$forceUpdate();
      }
    },
    // 处理邮件撰写事件
    handleComposeEmail(emailData) {
      console.log('Sidebar: 通过事件总线收到compose-email事件');
      // 切换到个人办公模块
      this.setModule('personal-office');
    },
    // 处理DOM邮件事件
    handleDomComposeEmail(event) {
      console.log('Sidebar: 通过DOM事件收到compose-email事件');
      // 切换到个人办公模块
      this.setModule('personal-office');
    }
  }
};
</script>

<style scoped>
.sidebar {
  width: 220px;
  height: 100%;
  background-color: #001529;
  color: white;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
}

.logo {
  padding: 0 20px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 20px;
}

.logo h2 {
  margin: 0;
  color: #1890ff;
  font-size: 20px;
}

.nav-menu {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  padding: 0;
  margin: 4px 0;
}

.nav-item a {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: rgba(255, 255, 255, 0.65);
  text-decoration: none;
  transition: all 0.3s;
}

.nav-item.active a, .nav-item a:hover {
  color: white;
  background-color: #1890ff;
}

.icon {
  margin-right: 10px;
  font-size: 18px;
}

.admin-section {
  margin-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 10px;
}

.section-title {
  padding: 10px 20px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
</style>