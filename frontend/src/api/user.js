import axios from 'axios';
import apiClient from './axios';
import api from '../utils/api';  // 导入工具API实例

/**
 * 用户登录
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<Object>} - 登录响应
 */
export const login = async (username, password) => {
  try {
    const response = await apiClient.post('/auth/login', {
      username,
      password
    });
    
    if (response.data.success) {
      // 保存登录信息
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      localStorage.setItem('persist_users', 'true'); // 永久保存用户数据
      sessionStorage.setItem('token', response.data.token);
      sessionStorage.setItem('user', JSON.stringify(response.data.user));
    }
    
    return response;
  } catch (error) {
    console.error('登录失败:', error);
    throw error;
  }
};

/**
 * 获取当前用户信息
 * @returns {Promise<Object>} - 用户信息
 */
export const getCurrentUser = async () => {
  try {
    const response = await apiClient.get('/auth/me');
    return response.data;
  } catch (error) {
    console.error('获取用户信息失败:', error);
    throw error;
  }
};

/**
 * 用户登出
 * @returns {Promise<void>}
 */
export const logout = async () => {
  // 清除本地存储中的登录信息
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('user');
  
  // 调用登出API
  try {
    await apiClient.post('/auth/logout');
  } catch (error) {
    console.error('登出API调用失败:', error);
    throw error;
  }
};

/**
 * 获取用户列表
 * @returns {Promise<Array>} - 用户列表
 */
export const getUsers = async () => {
  try {
    const response = await apiClient.get('/users');
    return response.data;
  } catch (error) {
    console.error('获取用户列表失败:', error);
    
    // 开发环境中，如果API调用失败，尝试从本地存储获取数据
    if (process.env.NODE_ENV === 'development') {
      console.warn('开发模式：从本地存储获取用户数据');
      
      // 使用api工具获取用户
      if (api.getLocalUsers) {
        return api.getLocalUsers();
      } else {
        // 尝试从storage模块获取
        try {
          const storage = require('../utils/storage').default;
          return storage.getUsers();
        } catch (e) {
          console.error('从本地存储获取用户失败:', e);
        }
        
        // 回退到直接从localStorage获取
        const storage = JSON.parse(localStorage.getItem('local_users') || '[]');
        return storage;
      }
    }
    
    throw error;
  }
};

/**
 * 创建用户
 * @param {Object} userData - 用户数据
 * @returns {Promise<Object>} - 创建的用户
 */
export const createUser = async (userData) => {
  console.log('创建用户:', userData);
  
  // 准备用户数据
  const newUser = {
    ...userData,
    created_at: new Date().toISOString(),
    status: 'active'
  };
  
  try {
    const response = await apiClient.post('/users', newUser);
    console.log('用户创建成功:', response.data);
    return response.data;
  } catch (error) {
    console.error('创建用户失败:', error, error.response?.status);
    
    // 开发环境或者遇到404/500错误时，保存到本地存储
    if (process.env.NODE_ENV === 'development' || 
        (error.response && (error.response.status === 404 || error.response.status === 500))) {
      console.warn('开发环境或API错误：将用户数据保存到本地存储');
      
      // 添加持久化标记
      newUser._persistent = true;
      
      // 使用api工具保存用户
      if (api.saveUserToLocal) {
        const savedUser = api.saveUserToLocal(newUser, true);
        console.log('用户已保存到本地:', savedUser);
        
        // 确保设置持久化标记
        localStorage.setItem('persist_users', 'true');
        
        return {
          success: true,
          message: "用户创建成功（本地存储）",
          user: savedUser
        };
      } else {
        // 尝试使用storage模块保存
        try {
          const storage = require('../utils/storage').default;
          const savedUser = storage.saveUser(newUser);
          
          // 确保设置持久化标记
          localStorage.setItem('persist_users', 'true');
          
          return {
            success: true,
            message: "用户创建成功（本地存储）",
            user: savedUser
          };
        } catch (e) {
          console.error('保存到本地存储失败:', e);
          
          // 回退到直接使用localStorage保存
          const id = Date.now();
          const user = { id, ...newUser, _persistent: true };
          
          const storage = JSON.parse(localStorage.getItem('local_users') || '[]');
          storage.push(user);
          localStorage.setItem('local_users', JSON.stringify(storage));
          localStorage.setItem('persist_users', 'true');
          
          return { 
            success: true, 
            message: "用户创建成功（本地存储）",
            user: user 
          };
        }
      }
    }
    
    throw error;
  }
};

/**
 * 更新用户
 * @param {number} userId - 用户ID
 * @param {Object} userData - 用户数据
 * @returns {Promise<Object>} - 更新的用户
 */
export const updateUser = async (userId, userData) => {
  try {
    const response = await apiClient.put(`/users/${userId}`, userData);
    return response.data;
  } catch (error) {
    console.error('更新用户失败:', error);
    
    // 开发环境中，如果API调用失败，更新本地存储
    if (process.env.NODE_ENV === 'development') {
      console.warn('开发模式：更新本地存储中的用户数据');
      
      // 确保数据具有持久化标记
      const updateData = { ...userData, _persistent: true };
      
      // 使用api工具更新用户
      if (api.saveUserToLocal) {
        const updatedUser = api.saveUserToLocal({ ...updateData, id: userId }, true);
        
        // 确保设置持久化标记
        localStorage.setItem('persist_users', 'true');
        
        return { 
          success: true, 
          message: "用户更新成功（本地存储）",
          user: updatedUser 
        };
      } else {
        try {
          const storage = require('../utils/storage').default;
          const updatedUser = storage.saveUser({ ...updateData, id: userId });
          
          // 确保设置持久化标记
          localStorage.setItem('persist_users', 'true');
          
          return { 
            success: true, 
            message: "用户更新成功（本地存储）",
            user: updatedUser 
          };
        } catch (e) {
          console.error('更新本地存储失败:', e);
          
          // 回退到直接使用localStorage更新
          const storage = JSON.parse(localStorage.getItem('local_users') || '[]');
          const index = storage.findIndex(user => user.id === userId);
          
          if (index !== -1) {
            storage[index] = { 
              ...storage[index], 
              ...updateData, 
              updated_at: new Date().toISOString(),
              _persistent: true
            };
            localStorage.setItem('local_users', JSON.stringify(storage));
            localStorage.setItem('persist_users', 'true');
            
            return { 
              success: true, 
              message: "用户更新成功（本地存储）",
              user: storage[index] 
            };
          }
        }
      }
    }
    
    throw error;
  }
};

/**
 * 删除用户
 * @param {number} userId - 用户ID
 * @returns {Promise<void>}
 */
export const deleteUser = async (userId) => {
  try {
    await apiClient.delete(`/users/${userId}`);
    return { success: true, message: "用户删除成功" };
  } catch (error) {
    console.error('删除用户失败:', error);
    
    // 开发环境中，如果API调用失败，从本地存储删除
    if (process.env.NODE_ENV === 'development') {
      console.warn('开发模式：从本地存储删除用户数据');
      
      // 使用api工具删除用户
      if (api.deleteUserFromLocal) {
        const result = api.deleteUserFromLocal(userId);
        if (result.success) {
          return { success: true, message: "用户删除成功（本地存储）" };
        }
      } else {
        try {
          const storage = require('../utils/storage').default;
          const result = storage.deleteUser(userId);
          if (result.success) {
            return { success: true, message: "用户删除成功（本地存储）" };
          }
        } catch (e) {
          console.error('从本地存储删除用户失败:', e);
          
          // 回退到直接使用localStorage删除
          const storage = JSON.parse(localStorage.getItem('local_users') || '[]');
          const filteredUsers = storage.filter(user => user.id !== userId);
          
          if (filteredUsers.length !== storage.length) {
            localStorage.setItem('local_users', JSON.stringify(filteredUsers));
            return { success: true, message: "用户删除成功（本地存储）" };
          }
        }
      }
    }
    
    throw error;
  }
}; 