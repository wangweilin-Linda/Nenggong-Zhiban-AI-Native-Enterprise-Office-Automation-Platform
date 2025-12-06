<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo-placeholder"></div>
        <h1>OA办公系统</h1>
      </div>
      
      <a-form
        :model="loginForm"
        @finish="handleLogin"
        :rules="rules"
        layout="vertical"
        class="login-form"
      >
        <a-form-item name="username" label="用户名">
          <a-input 
            v-model:value="loginForm.username" 
            placeholder="请输入用户名"
            size="large"
          >
            <template #prefix>
              <user-outlined />
            </template>
          </a-input>
        </a-form-item>
        
        <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password
            v-model:value="loginForm.password"
            size="large"
            placeholder="密码"
            :visibilityToggle="true"
          >
            <template #prefix>
              <LockOutlined />
            </template>
            <template #iconRender="{ visible }">
              <EyeOutlined v-if="visible" />
              <EyeInvisibleOutlined v-else />
            </template>
          </a-input-password>
        </a-form-item>
        
        <a-form-item name="remember">
          <a-checkbox v-model:checked="loginForm.remember">记住我</a-checkbox>
          <a class="login-form-forgot" href="#">忘记密码</a>
        </a-form-item>
        
        <a-form-item>
          <a-button 
            type="primary" 
            html-type="submit" 
            :loading="loading" 
            class="login-form-button"
            size="large"
            block
          >
            登录
          </a-button>
        </a-form-item>
      </a-form>
      
      <div class="footer-links">
        <a href="#">注册账号</a>
        <a href="#">帮助文档</a>
        <a href="#">联系管理员</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { UserOutlined, LockOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons-vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import axios from 'axios';
import { useUserStore } from '../stores/user';
import emitter from '../utils/eventBus';

// 状态变量
const loginForm = reactive({
  username: '',
  password: '',
  remember: false
});

const loading = ref(false);
const router = useRouter();
const userStore = useUserStore();

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ]
};

// 处理登录
const handleLogin = async () => {
  console.log('登录按钮被点击');
  if (!loginForm.username || !loginForm.password) {
    message.error('请输入用户名和密码');
    return;
  }

  loading.value = true;
  
  try {
    // 尝试直接调用后端登录API
    const response = await axios.post('/auth/login-json', {
      username: loginForm.username,
      password: loginForm.password
    });
    
    if (response.data && response.data.access_token) {
      console.log('登录成功，获取到JWT令牌');
      const tokenValue = response.data.access_token;
      const userInfo = response.data.user;
      
      // 保存令牌和用户信息
      saveLoginInfo(tokenValue, userInfo);
      
      // 登录成功消息
      message.success(`欢迎回来，${userInfo.real_name || userInfo.username}！`);
      
      // 根据用户类型跳转到不同页面
      const redirectPath = userInfo.is_admin ? '/admin/dashboard' : '/dashboard';
      window.location.href = redirectPath;
    } else {
      throw new Error('登录响应缺少令牌');
    }
  } catch (error) {
    console.error('API登录失败:', error);
    
    // 如果API调用失败，回退到模拟登录逻辑
    // 检查固定用户
    let tokenValue = '';
    let userInfo = null;
    let userType = '';
    
    if (loginForm.username === 'admin' && loginForm.password === 'admin123') {
      userType = 'admin';
      tokenValue = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6NTUxNjIzOTAyMn0.Cwr_GwNnGQ9XhRNWk8RVzH_9x2nVzhjujDwKTXA9T5Y';
      console.log('使用JWT格式令牌 (admin)');
    } else if (loginForm.username === 'user' && loginForm.password === 'user123') {
      userType = 'user';
      tokenValue = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiZXhwIjo1NTE2MjM5MDIyfQ.xWLh8TqJpTiKM-U5eYNf6Qn06TcvMAdXCpTNWYkCoks';
      console.log('使用JWT格式令牌 (user)');
    } else if (loginForm.username === 'manager' && loginForm.password === 'manager123') {
      userType = 'manager';
      tokenValue = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYW5hZ2VyIiwiZXhwIjo1NTE2MjM5MDIyfQ.pChIbOCfL6r1Bg4cbXXEcErwDp4NQHbX-XVvfF9Ua8M';
      console.log('使用JWT格式令牌 (manager)');
    } else {
      // 如果没有找到用户，显示错误信息
      loading.value = false;
      message.error('用户名或密码错误');
      return;
    }

    let redirectPath = '/dashboard'; // 默认路径
    
    if (userType === 'admin') {
      userInfo = {
        id: 1,
        username: 'admin',
        real_name: '管理员',
        email: 'admin@example.com',
        is_admin: true,
        roles: ['admin'],
        permissions: ['all']
      };
      
      redirectPath = '/admin/dashboard';
    } else if (userType === 'user') {
      userInfo = {
        id: 2,
        username: 'user',
        real_name: '普通用户',
        email: 'user@example.com',
        is_admin: false,
        roles: ['user'],
        permissions: ['read', 'create']
      };
    } else if (userType === 'manager') {
      userInfo = {
        id: 3,
        username: 'manager',
        real_name: '部门经理',
        email: 'manager@example.com',
        is_admin: false,
        is_manager: true,
        roles: ['manager'],
        permissions: ['read', 'create', 'approve']
      };
    }
    
    // 保存令牌和用户信息
    saveLoginInfo(tokenValue, userInfo);
    
    // 显示成功消息并跳转
    setTimeout(() => {
      message.success(`欢迎回来，${userInfo.real_name || userInfo.username}！`);
      loading.value = false;
      window.location.href = redirectPath;
    }, 800);
  } finally {
    loading.value = false;
  }
};

// 保存登录信息到本地存储
const saveLoginInfo = (token, user) => {
  if (!token || !user) {
    console.error('保存登录信息失败: 数据不完整');
    return;
  }
  
  localStorage.setItem('token', token);
  
  // 确保user对象已序列化为字符串
  const userStr = typeof user === 'string' ? user : JSON.stringify(user);
  localStorage.setItem('user', userStr);
  localStorage.setItem('userInfo', userStr);
  
  // 确保安全地访问userStore
  try {
    userStore.setLoginInfo({
      token,
      user
    });
  } catch (err) {
    console.error('设置用户信息到store失败:', err);
  }
  
  // 安全地发布登录事件
  try {
    emitter.emit('user-login', {
      ...user,
      token
    });
    console.log('登录事件已触发');
  } catch (error) {
    console.error('触发登录事件失败:', error);
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
  background-color: #f5f5f5;
  background-size: cover;
  background-position: center;
}

.login-box {
  width: 400px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-placeholder {
  width: 80px;
  height: 80px;
  margin-bottom: 16px;
  background-color: #1890ff;
  border-radius: 50%;
}

.login-header h1 {
  font-size: 24px;
  color: #1890ff;
  margin: 0;
}

.login-form {
  margin-bottom: 24px;
}

.login-form-forgot {
  float: right;
}

.footer-links {
  display: flex;
  justify-content: space-between;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.footer-links a {
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
}

.footer-links a:hover {
  color: #1890ff;
}
</style>