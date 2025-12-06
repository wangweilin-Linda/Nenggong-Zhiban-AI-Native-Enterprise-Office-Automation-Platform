<template>
  <div class="container">
    <Sidebar v-if="!appError" @user-login="checkUserInfo" @user-logout="handleLogout" />
    <Workspace v-if="!appError" ref="workspace" />
    <Resizer v-if="!appError" />
    <AiAssistant v-if="!appError" ref="aiAssistant" @toggle="handleAiToggle" />
    <button v-if="!isAiVisible && !appError" class="ai-toggle" @click="toggleAiAssistant">
      <span class="ai-icon">🤖</span>
    </button>
    <DocumentList v-if="!appError" :documents="documents" @select-document="handleSelectDocument" @update-documents="handleUpdateDocuments" />
    
    <!-- 错误提示 -->
    <div v-if="appError" class="app-error">
      <h2>应用加载错误</h2>
      <p>{{ appError }}</p>
      <button @click="reloadApp">重新加载</button>
    </div>
    
    <!-- 用户信息和登录/退出按钮区域 -->
    <div v-if="!appError" class="auth-area">
      <!-- 已登录状态显示用户信息和退出按钮 -->
      <div v-if="userInfo && !appError" class="user-info">
        <div class="user-avatar">{{ userInfo.username ? userInfo.username.charAt(0).toUpperCase() : 'U' }}</div>
        <span class="username">{{ userInfo.real_name || userInfo.username }}</span>
        <button class="logout-btn" @click="handleLogout">
          <LogoutOutlined />
          <span>退出</span>
        </button>
      </div>
      <!-- 未登录状态显示登录按钮 -->
      <button v-else-if="!userInfo && !appError" class="login-btn" @click="showLoginModal = true">
        <LoginOutlined />
        <span>登录</span>
      </button>
    </div>

    <!-- 登录弹窗 -->
    <div v-if="showLoginModal" class="login-modal">
      <div class="login-content">
        <div class="login-header">
          <h3>用户登录</h3>
          <button class="close-modal-btn" @click="showLoginModal = false">×</button>
        </div>
        
        <div v-if="loginError" class="login-error">
          {{ loginError }}
        </div>
        
        <div class="form-group">
          <label for="username">用户名</label>
          <a-input
            id="username"
            v-model:value="loginForm.username"
            placeholder="请输入用户名"
            :maxLength="20"
            @keydown.enter="handleLogin"
          >
            <template #prefix>
              <UserOutlined />
            </template>
          </a-input>
        </div>
        
        <div class="form-group password-group">
          <label for="password">密码</label>
          <a-input-password
            id="password"
            v-model:value="loginForm.password"
            placeholder="请输入密码"
            :maxLength="20"
            @keydown.enter="handleLogin"
          >
            <template #prefix>
              <LockOutlined />
            </template>
          </a-input-password>
        </div>
        
        <div class="login-actions">
          <a-checkbox v-model:checked="loginForm.rememberMe">记住我</a-checkbox>
          <div class="login-buttons">
            <a-button type="primary" :loading="loggingIn" @click="handleLogin">登录</a-button>
            <a-button @click="showLoginModal = false">取消</a-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 通知组件 -->
    <div v-if="notification.show" 
      :class="['notification', notification.type]">
      <span>{{ notification.message }}</span>
      <button @click="dismissNotification" class="notification-close">×</button>
    </div>
  </div>
</template>

<script>
import Sidebar from './components/Sidebar.vue';
import Workspace from './components/Workspace.vue';
import Resizer from './components/Resizer.vue';
import AiAssistant from './components/AiAssistant.vue';
import DocumentList from './components/DocumentList.vue';
import emitter from './utils/eventBus';
import { useUserStore } from './stores/user';
import axios from 'axios';
import { ref, onMounted, onBeforeUnmount } from 'vue';
import Login from './views/Login.vue';
import { message, Modal } from 'ant-design-vue';
import { LogoutOutlined, LoginOutlined, UserOutlined, LockOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons-vue';
import router from './router';
// 直接引入登录方法
import * as userApi from './api/user';

export default {
  components: {
    Sidebar,
    Workspace,
    Resizer,
    AiAssistant,
    DocumentList,
    Login,
    LogoutOutlined,
    LoginOutlined,
    UserOutlined,
    LockOutlined,
    EyeOutlined,
    EyeInvisibleOutlined
  },
  setup() {
    const isLoggedIn = ref(false);
    const sidebarWidth = 220;
    const workspaceWidth = ref(window.innerWidth - sidebarWidth);
    
    const checkLoginStatus = () => {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token');
      isLoggedIn.value = !!token;
      console.log('检查登录状态:', isLoggedIn.value);
    };
    
    const handleUserLogin = (userData) => {
      console.log('接收到用户登录事件', userData);
      isLoggedIn.value = true;
    };
    
    const handleUserLogout = () => {
      console.log('接收到用户登出事件');
      isLoggedIn.value = false;
    };
    
    const handleResize = () => {
      workspaceWidth.value = window.innerWidth - sidebarWidth;
    };
    
    onMounted(() => {
      // 检查登录状态
      checkLoginStatus();
      
      // 初始化本地存储 - 确保数据持久化
      import('./utils/api').then(apiModule => {
        console.log('初始化本地存储数据');
        apiModule.default.initApprovalData();
        apiModule.default.initUserData();
        
        // 确保数据持久化
        localStorage.setItem('persist_approvals', 'true');
        localStorage.setItem('persist_users', 'true');
        localStorage.setItem('persist_workflows', 'true');
        
        // 标记使用本地数据
        localStorage.setItem('using_local_approvals', 'true');
        localStorage.setItem('using_local_users', 'true');
        localStorage.setItem('using_local_workflows', 'true');
      }).catch(err => {
        console.error('初始化本地存储失败:', err);
      });
      
      // 监听窗口大小变化
      window.addEventListener('resize', handleResize);
      
      // 监听登录状态变化
      emitter.on('user-login', handleUserLogin);
      emitter.on('user-logout', handleUserLogout);
      
      // 检查localStorage中的模拟用户
      try {
        const mockUsersStr = localStorage.getItem('mock_users');
        console.log('应用启动时检查localStorage中的mock_users:', mockUsersStr);
        
        if (mockUsersStr) {
          const mockUsers = JSON.parse(mockUsersStr);
          console.log('应用启动时已保存的模拟用户列表:', mockUsers);
        }
      } catch (e) {
        console.error('检查模拟用户失败:', e);
      }
    });
    
    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize);
      emitter.off('user-login', handleUserLogin);
      emitter.off('user-logout', handleUserLogout);
    });
    
    return {
      isLoggedIn,
      workspaceWidth,
      sidebarWidth
    };
  },
  data() {
    return {
      isAiVisible: false,
      documents: [],
      showLoginModal: false,
      loginForm: {
        username: '',
        password: '',
        rememberMe: false
      },
      loginError: '',
      loggingIn: false,
      appError: null,
      showPassword: false,
      userInfo: null,
      lastLogoutTime: 0,
      notification: {
        show: false,
        type: '',
        message: ''
      }
    };
  },
  computed: {
    userStore() {
      try {
        return useUserStore();
      } catch (error) {
        this.appError = 'Pinia store加载失败: ' + error.message;
        return {
          isLoggedIn: false,
          isAdmin: false,
          user: null
        };
      }
    },
    currentUser() {
      try {
        return this.userStore.user;
      } catch (error) {
        return null;
      }
    },
    isAdmin() {
      return this.userInfo && (
        this.userInfo.role === 'admin' || 
        localStorage.getItem('mock_admin_token') || 
        sessionStorage.getItem('mock_admin_token')
      );
    }
  },
  methods: {
    toggleAiAssistant() {
      try {
        this.$refs.aiAssistant.toggle();
      } catch (error) {
        this.appError = 'AI助手组件错误: ' + error.message;
      }
    },
    handleAiToggle(isVisible) {
      this.isAiVisible = isVisible;
    },
    handleSelectDocument(doc) {
      // 处理文档选择
    },
    handleUpdateDocuments(updatedDocuments) {
      this.documents = updatedDocuments;
    },
    async fetchDocuments() {
      try {
        const response = await axios.get('/api/documents');
        if (response.data && Array.isArray(response.data)) {
          this.documents = response.data;
        }
      } catch (error) {
        console.error('获取文档列表失败:', error);
      }
    },
    openLoginModal() {
      this.showLoginModal = true;
      this.loginError = '';
    },
    async handleLogin() {
      try {
        this.loginError = '';
        this.loggingIn = true;
        
        if (!this.loginForm.username || !this.loginForm.password) {
          this.loginError = '请输入用户名和密码';
          return;
        }
        
        // 移除前后空格
        const username = this.loginForm.username.trim();
        const password = this.loginForm.password.trim();
        
        // 测试账号逻辑
        let success = false;
        let user = null;
        
        if (username === 'admin' && password === 'admin123') {
          // 管理员登录
          const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6NTUxNjIzOTAyMn0.Cwr_GwNnGQ9XhRNWk8RVzH_9x2nVzhjujDwKTXA9T5Y';
          
          if (this.loginForm.rememberMe) {
            localStorage.setItem('token', token);
            localStorage.setItem('mock_admin_token', 'true');
            localStorage.setItem('user_role', 'admin');
          } else {
            sessionStorage.setItem('token', token);
            sessionStorage.setItem('mock_admin_token', 'true');
            sessionStorage.setItem('user_role', 'admin');
          }
          
          user = {
            id: 'admin-1',
            username: 'admin',
            real_name: '系统管理员',
            role: 'admin',
            is_admin: true
          };
          success = true;
          
          if (this.loginForm.rememberMe) {
            localStorage.setItem('user', JSON.stringify(user));
          } else {
            sessionStorage.setItem('user', JSON.stringify(user));
          }
          
          message.success(`欢迎回来，${user.real_name}！`);
          
          // 触发登录成功事件
          emitter.emit('user-login', { user, isAdmin: true });
          document.dispatchEvent(new CustomEvent('user-login', { detail: { user, isAdmin: true } }));
          
        } else if (username === 'user' && password === 'user123') {
          // 普通用户登录
          const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiZXhwIjo1NTE2MjM5MDIyfQ.xWLh8TqJpTiKM-U5eYNf6Qn06TcvMAdXCpTNWYkCoks';
          
          if (this.loginForm.rememberMe) {
            localStorage.setItem('token', token);
            localStorage.setItem('user_role', 'user');
          } else {
            sessionStorage.setItem('token', token);
            sessionStorage.setItem('user_role', 'user');
          }
          
          user = {
            id: 'user-1',
            username: 'user',
            real_name: '普通用户',
            role: 'user',
            is_admin: false
          };
          success = true;
          
          if (this.loginForm.rememberMe) {
            localStorage.setItem('user', JSON.stringify(user));
          } else {
            sessionStorage.setItem('user', JSON.stringify(user));
          }
          
          message.success(`欢迎回来，${user.real_name}！`);
          
          // 触发登录成功事件
          emitter.emit('user-login', { user, isAdmin: false });
          document.dispatchEvent(new CustomEvent('user-login', { detail: { user, isAdmin: false } }));
          
        } else if (username === 'manager' && password === 'manager123') {
          // 经理登录
          const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYW5hZ2VyIiwiZXhwIjo1NTE2MjM5MDIyfQ.pChIbOCfL6r1Bg4cbXXEcErwDp4NQHbX-XVvfF9Ua8M';
          
          if (this.loginForm.rememberMe) {
            localStorage.setItem('token', token);
            localStorage.setItem('user_role', 'manager');
          } else {
            sessionStorage.setItem('token', token);
            sessionStorage.setItem('user_role', 'manager');
          }
          
          user = {
            id: 'manager-1',
            username: 'manager',
            real_name: '部门经理',
            role: 'manager',
            is_admin: false
          };
          success = true;
          
          if (this.loginForm.rememberMe) {
            localStorage.setItem('user', JSON.stringify(user));
          } else {
            sessionStorage.setItem('user', JSON.stringify(user));
          }
          
          message.success(`欢迎回来，${user.real_name}！`);
          
          // 触发登录成功事件
          emitter.emit('user-login', { user, isAdmin: false });
          document.dispatchEvent(new CustomEvent('user-login', { detail: { user, isAdmin: false } }));
          
        } else {
          // 检查从UserManagement组件中创建的用户
          try {
            // 获取保存的模拟用户
            const mockUsersStr = localStorage.getItem('mock_users');
            console.log('检查模拟用户列表:', mockUsersStr);
            
            if (mockUsersStr) {
              let mockUsers = [];
              try {
                mockUsers = JSON.parse(mockUsersStr);
                console.log('尝试用户名:', username, '密码:', password);
                console.log('可用的模拟用户:', mockUsers);
                
                // 查找匹配的用户
                const foundUser = mockUsers.find(u => 
                  u.username === username && u.password === password
                );
                
                if (foundUser) {
                  console.log('找到匹配的模拟用户:', foundUser);
                  // 用户找到，创建token和用户信息
                  const userJwtToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIke2ZvdW5kVXNlci51c2VybmFtZX0iLCJleHAiOjU1MTYyMzkwMjJ9.DFEpix7bLlqFl0qcasEVzRdkl5ZKIQHJbl-VWWq4lsM`;
                  const token = userJwtToken.replace('${foundUser.username}', foundUser.username);
                  
                  if (this.loginForm.rememberMe) {
                    localStorage.setItem('token', token);
                    localStorage.setItem('user_role', foundUser.role || 'user');
                  } else {
                    sessionStorage.setItem('token', token);
                    sessionStorage.setItem('user_role', foundUser.role || 'user');
                  }
                  
                  user = {
                    id: 'user-' + (mockUsers.indexOf(foundUser) + 100),
                    username: foundUser.username,
                    real_name: foundUser.full_name,
                    role: foundUser.role || 'user',
                    is_admin: foundUser.is_admin || false
                  };
                  success = true;
                  
                  if (this.loginForm.rememberMe) {
                    localStorage.setItem('user', JSON.stringify(user));
                  } else {
                    sessionStorage.setItem('user', JSON.stringify(user));
                  }
                  
                  message.success(`欢迎回来，${user.real_name || user.username}！`);
                  
                  // 触发登录成功事件
                  emitter.emit('user-login', { user, isAdmin: user.is_admin });
                  document.dispatchEvent(new CustomEvent('user-login', { 
                    detail: { user, isAdmin: user.is_admin } 
                  }));
                } else {
                  console.log('未找到匹配的模拟用户');
                }
              } catch (parseError) {
                console.error('解析mock_users数据失败:', parseError);
              }
            } else {
              console.log('未找到模拟用户列表');
            }
          } catch (e) {
            console.error('检查模拟用户时出错:', e);
          }
          
          // 如果没有找到模拟用户，尝试调用后端登录API
          if (!success) {
            try {
              const response = await userApi.login(username, password);
              
              if (response && response.data && response.data.success) {
                // 后端登录成功
                const apiUser = response.data.user;
                const apiToken = response.data.token;
                
                if (this.loginForm.rememberMe) {
                  localStorage.setItem('token', apiToken);
                  localStorage.setItem('user', JSON.stringify(apiUser));
                  localStorage.setItem('user_role', apiUser.role || 'user');
                } else {
                  sessionStorage.setItem('token', apiToken);
                  sessionStorage.setItem('user', JSON.stringify(apiUser));
                  sessionStorage.setItem('user_role', apiUser.role || 'user');
                }
                
                user = apiUser;
                success = true;
                
                message.success(`欢迎回来，${apiUser.real_name || apiUser.username}！`);
                
                // 触发登录成功事件
                emitter.emit('user-login', { 
                  user: apiUser, 
                  isAdmin: apiUser.role === 'admin' || apiUser.is_admin
                });
                document.dispatchEvent(new CustomEvent('user-login', { 
                  detail: { 
                    user: apiUser, 
                    isAdmin: apiUser.role === 'admin' || apiUser.is_admin 
                  } 
                }));
              } else {
                this.loginError = '用户名或密码不正确';
              }
            } catch (error) {
              console.error('API登录失败:', error);
              this.loginError = '登录服务暂时不可用，请稍后再试';
            }
          }
        }
        
        if (success) {
          // 登录成功后关闭窗口
          this.showLoginModal = false;
          this.loginForm = { username: '', password: '', rememberMe: false };
          this.userInfo = user;
          
          // 更新状态并刷新页面显示
          this.checkUserInfo();
          
          // 强制更新视图
          this.$forceUpdate();
          
          // 如果用户在登录页面，则跳转到首页
          if (this.$route && this.$route.path === '/login') {
            this.$router.push('/');
          }
          
          // 延迟一下以确保状态更新
          setTimeout(() => {
            window.dispatchEvent(new Event('storage'));
          }, 100);
        }
      } catch (error) {
        console.error('登录失败:', error);
        this.loginError = '登录过程中发生错误，请重试';
      } finally {
        this.loggingIn = false;
      }
    },
    handleLogout() {
      // 防止频繁退出
      const now = Date.now();
      if (now - this.lastLogoutTime < 1000) {
        return;
      }
      this.lastLogoutTime = now;
      
      // 清除登录信息
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('mock_admin_token');
      localStorage.removeItem('user_role');
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('user');
      sessionStorage.removeItem('mock_admin_token');
      sessionStorage.removeItem('user_role');
      
      // 重置用户状态
      this.userInfo = null;
      
      // 发送退出登录事件
      emitter.emit('user-logout');
      
      // 显示消息
      message.success('已成功退出登录');
      
      // 如果需要跳转到登录页面
      // this.$router.push('/login');
    },
    checkUserInfo() {
      try {
        const storage = this.loginForm.rememberMe ? localStorage : sessionStorage;
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        
        if (token) {
          // 从本地存储获取用户信息
          const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
          if (userStr) {
            try {
              this.userInfo = JSON.parse(userStr);
              console.log('已从本地存储恢复用户信息:', this.userInfo);
            } catch (e) {
              console.error('解析用户信息失败:', e);
              this.userInfo = null;
            }
          } else {
            console.log('未找到本地存储的用户信息');
            this.userInfo = null;
          }
        } else {
          this.userInfo = null;
        }
      } catch (error) {
        console.error('检查用户信息时出错:', error);
        this.userInfo = null;
      }
    },
    reloadApp() {
      window.location.reload();
    },
    handleWorkflowUpdate(event) {
      try {
        console.log('App收到工作流更新事件，重新获取工作流数据');
        // 这里可以添加重新获取工作流数据的逻辑
      } catch (error) {
        console.error('处理工作流更新事件失败:', error);
      }
    },
    dismissNotification() {
      this.notification.show = false;
    }
  },
  mounted() {
    try {
      // 初始化检查登录状态
      this.checkUserInfo();
      // 获取文档列表
      this.fetchDocuments();
      
      // 添加工作流更新事件监听
      try {
        window.addEventListener('workflow-updated', this.handleWorkflowUpdate);
      } catch (error) {
        console.error('添加工作流更新事件监听失败:', error);
      }
  
      // 检查是否需要登录
      if (!this.userInfo && this.$route.path !== '/login') {
        this.showLoginModal = true;
      }
      
      // 使用 emitter 监听模块变化
      emitter.on('module-changed', (module) => {
        emitter.emit('workspace-module-changed', module);
      });
      
      // 监听显示登录窗口的事件
      emitter.on('show-login', () => {
        this.openLoginModal();
      });
      
      // 监听用户登录和登出事件
      emitter.on('user-login', (userData) => {
        console.log('检测到用户登录事件');
        // 更新用户信息
        this.checkUserInfo();
        
        // 清除任何可能存在的错误状态
        this.appError = null;
      });
      
      emitter.on('user-logout', () => {
        console.log('检测到用户登出事件');
        this.userInfo = null;
      });
      
      // 监听会话过期事件
      emitter.on('session-expired', () => {
        // 防止频繁提示
        const now = Date.now();
        if (now - this.lastLogoutTime < 5000) {
          return;
        }
        this.lastLogoutTime = now;
        
        // 显示会话过期提示
        Modal.warning({
          title: '登录提示',
          content: '您的登录会话可能已过期，请重新登录以继续操作。',
          okText: '重新登录',
          onOk: () => {
            // 显示登录窗口而不是强制登出
            setTimeout(() => {
              this.showLoginModal = true;
            }, 100);
          }
        });
      });
    } catch (error) {
      console.error('应用初始化失败:', error);
      this.appError = '应用初始化失败: ' + error.message;
    }
  },
  beforeUnmount() {
    // 移除工作流更新事件监听
    try {
      window.removeEventListener('workflow-updated', this.handleWorkflowUpdate);
    } catch (error) {
      console.error('移除工作流更新事件监听失败:', error);
    }
    
    // 移除emitter事件监听
    emitter.off('module-changed');
    emitter.off('show-login');
    emitter.off('user-login');
    emitter.off('user-logout');
    emitter.off('session-expired');
  }
};
</script>

<style scoped>
.auth-area {
  position: fixed;
  bottom: 20px;
  left: 20px;
  z-index: 1000;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255,255,255,0.95);
  padding: 8px 12px;
  border-radius: 50px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: all 0.3s;
}

.user-info:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #1890ff;
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
}

.username {
  max-width: 80px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #ff7875;
}

.login-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: all 0.3s;
}

.login-btn:hover {
  background: #40a9ff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.login-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.login-content {
  background: white;
  padding: 24px;
  border-radius: 8px;
  width: 360px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  animation: slideUp 0.3s;
}

@keyframes slideUp {
  from { transform: translateY(30px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.login-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.login-header h3 {
  margin: 0;
  color: #1890ff;
  font-size: 18px;
}

.close-modal-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #999;
  cursor: pointer;
}

.login-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  margin-bottom: 24px;
}

.login-buttons {
  display: flex;
  gap: 8px;
}

.test-accounts {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #f0f0f0;
  font-size: 12px;
  color: #888;
}

.test-accounts-title {
  margin-bottom: 4px;
  font-weight: 500;
}

.test-account {
  margin-top: 4px;
}

.login-error {
  color: #f5222d;
  margin-bottom: 16px;
  font-size: 14px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
  color: #333;
}

.password-group {
  position: relative;
}

.password-input-container {
  position: relative;
  display: flex;
}

.password-input-container input {
  flex: 1;
  padding-right: 70px;
}

.password-toggle-btn {
  position: absolute;
  right: 0;
  top: 0;
  height: 100%;
  padding: 0 12px;
  background: #f0f0f0;
  border: 1px solid #d9d9d9;
  border-left: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  color: #666;
  font-size: 12px;
}

.password-toggle-btn:hover {
  background: #e0e0e0;
}

.app-error {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  text-align: center;
  z-index: 3000;
}

.app-error h2 {
  color: #ff4d4f;
  margin-bottom: 16px;
}

.app-error button {
  margin-top: 16px;
  padding: 8px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.ai-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #1890ff;
  color: white;
  border: none;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.ai-icon {
  font-size: 24px;
}

.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  background: rgba(255,255,255,0.95);
  padding: 10px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: all 0.3s;
  z-index: 3000;
}

.notification.success {
  background: #dff4e5;
  border: 1px solid #b7ebc5;
}

.notification.error {
  background: #ffd6d6;
  border: 1px solid #ffb3b3;
}

.notification-close {
  background: none;
  border: none;
  font-size: 16px;
  color: #999;
  cursor: pointer;
}
</style>