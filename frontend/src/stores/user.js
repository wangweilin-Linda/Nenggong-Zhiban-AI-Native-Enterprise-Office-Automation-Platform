import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)
  const loading = ref(false)
  const initialized = ref(false)
  
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_admin || false)
  const userRoles = computed(() => user.value?.roles || [])
  
  // 初始化函数
  async function initialize() {
    if (initialized.value) return;
    
    // 如果有令牌，尝试获取用户信息
    if (token.value) {
      try {
        // 确保设置了Authorization头
        if (axios.defaults && axios.defaults.headers) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`;
        }
        await fetchUserInfo();
      } catch (error) {
        console.warn('初始化用户信息失败:', error);
        // 不要在这里登出，让用户可以重新登录
      }
    }
    
    initialized.value = true;
  }
  
  // 登录方法
  async function login(username, password) {
    try {
      loading.value = true
      
      // 首先尝试使用JSON格式登录
      try {
        const response = await fetch('/auth/login-json', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: username,
            password: password
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data) {
            setUserInfo(data);
            console.log('登录成功 (JSON方式)');
            return true;
          }
        }
        
        // 如果JSON登录失败但状态码不是服务器错误，尝试表单登录
        if (response.status < 500) {
          console.log('JSON登录失败，尝试表单登录...');
          throw new Error('尝试表单登录');
        } else {
          // 服务器错误，直接抛出
          const error = await response.json();
          throw new Error(error.detail || `服务器错误 (${response.status})`);
        }
      } catch (jsonError) {
        // 尝试使用表单格式登录（兼容旧API）
        console.log('尝试使用表单格式登录...');
        
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const formResponse = await fetch('/auth/login', {
          method: 'POST',
          body: formData
        });
        
        if (!formResponse.ok) {
          if (formResponse.headers.get('content-type')?.includes('application/json')) {
            const error = await formResponse.json();
            throw new Error(error.detail || '登录失败');
          } else {
            throw new Error(`登录失败 (${formResponse.status})`);
          }
        }
        
        const data = await formResponse.json();
        if (data) {
          setUserInfo(data);
          console.log('登录成功 (表单方式)');
          return true;
        }
      }
    } catch (error) {
      console.error('登录错误:', error);
      throw new Error(error.message || '登录失败，请检查网络连接和服务器状态');
    } finally {
      loading.value = false
    }
  }
  
  // 获取用户信息
  async function fetchUserInfo() {
    if (!token.value) return;
    
    try {
      loading.value = true;
      // 确保设置了Authorization头
      if (axios.defaults && axios.defaults.headers && axios.defaults.headers.common) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`;
      }
      
      const response = await axios.get('/auth/me');
      
      if (response && response.data) {
        user.value = response.data;
        console.log('用户信息获取成功');
      } else {
        throw new Error('获取用户信息响应为空');
      }
    } catch (error) {
      console.error('获取用户信息失败:', error);
      
      // 如果是401错误，说明令牌失效，需要登出
      if (error.response && error.response.status === 401) {
        console.warn('令牌已失效，需要重新登录');
        logout();
      }
      
      throw error;
    } finally {
      loading.value = false;
    }
  }
  
  // 登出方法
  function logout() {
    token.value = '';
    user.value = null;
    
    // 清除所有相关的存储数据
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('userInfo');
    localStorage.removeItem('userRole');
    localStorage.removeItem('adminUsername');
    
    // 清除请求头中的授权信息
    if (axios.defaults && axios.defaults.headers && axios.defaults.headers.common) {
      delete axios.defaults.headers.common['Authorization'];
    }
    
    console.log('用户已成功登出');
  }
  
  // 检查用户是否有特定权限
  function hasPermission(resource, action) {
    if (!user.value) return false;
    if (user.value.is_admin) return true;
    
    // 检查用户角色
    const roles = userRoles.value;
    if (roles.includes('admin')) return true;
    
    // 检查具体权限
    return user.value.permissions?.some(
      p => p.resource === resource && p.action === action
    ) || false;
  }
  
  // 检查用户是否有特定角色
  function hasRole(roleName) {
    if (!user.value) return false;
    if (user.value.is_admin) return true;
    
    return userRoles.value.includes(roleName);
  }
  
  // 设置用户信息
  function setUserInfo(data) {
    if (!data) {
      console.error('设置用户信息失败: 数据为空');
      return;
    }
    
    token.value = data.access_token || data.token;
    user.value = data.user;
    
    if (token.value) {
      localStorage.setItem('token', token.value);
      if (axios.defaults && axios.defaults.headers) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`;
      }
      console.log('用户信息已设置');
    }
  }

  // 设置登录信息（用于从localStorage恢复用户状态）
  function setLoginInfo(data) {
    if (!data) {
      console.error('设置登录信息失败: 数据为空');
      return;
    }
    
    if (!data.token || !data.user) {
      console.error('设置登录信息失败: 数据不完整');
      return;
    }
    
    token.value = data.token;
    user.value = data.user;
    
    // 设置请求头
    if (axios.defaults && axios.defaults.headers) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${data.token}`;
    }
    
    console.log('已恢复用户登录状态');
    return true;
  }

  return {
    token,
    user,
    loading,
    isLoggedIn,
    isAdmin,
    userRoles,
    initialize,
    login,
    logout,
    fetchUserInfo,
    hasPermission,
    hasRole,
    setUserInfo,
    setLoginInfo
  }
})