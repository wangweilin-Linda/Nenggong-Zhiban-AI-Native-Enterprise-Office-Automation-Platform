import axios from './axios';
import api from '../utils/api';  // 导入工具API实例

/**
 * 获取所有用户
 * @returns {Promise}
 */
export function getUsers() {
  return axios.get('/admin/users')
    .catch(error => {
      console.error('获取用户列表失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        return Promise.resolve({
          data: api.getLocalUsers ? api.getLocalUsers() : []
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取用户详情
 * @param {number} userId 用户ID
 * @returns {Promise}
 */
export function getUserById(userId) {
  return axios.get(`/admin/users/${userId}`)
    .catch(error => {
      console.error(`获取用户(ID: ${userId})失败:`, error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        const users = api.getLocalUsers ? api.getLocalUsers() : [];
        const user = users.find(u => u.id == userId);
        
        if (user) {
          return Promise.resolve({ data: user });
        }
      }
      return Promise.reject(error);
    });
}

/**
 * 创建用户
 * @param {Object} userData 用户数据
 * @returns {Promise}
 */
export function createUser(userData) {
  return axios.post('/admin/users', userData)
    .catch(error => {
      console.error('创建用户失败:', error);
      if (process.env.NODE_ENV === 'development' && api.saveUserToLocal) {
        console.log('开发环境下保存到本地存储');
        
        // 保存到本地存储
        const saved = api.saveUserToLocal(userData);
        
        return Promise.resolve({
          data: {
            success: true,
            message: "用户创建成功（本地存储）",
            data: saved
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 更新用户
 * @param {number} userId 用户ID
 * @param {Object} userData 用户数据
 * @returns {Promise}
 */
export function updateUser(userId, userData) {
  return axios.put(`/admin/users/${userId}`, userData)
    .catch(error => {
      console.error(`更新用户(ID: ${userId})失败:`, error);
      if (process.env.NODE_ENV === 'development' && api.saveUserToLocal) {
        console.log('开发环境下保存到本地存储');
        
        // 保存到本地存储
        const saved = api.saveUserToLocal({...userData, id: userId});
        
        return Promise.resolve({
          data: {
            success: true,
            message: "用户更新成功（本地存储）",
            data: saved
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 删除用户
 * @param {number} userId 用户ID
 * @returns {Promise}
 */
export function deleteUser(userId) {
  return axios.delete(`/admin/users/${userId}`)
    .catch(error => {
      console.error(`删除用户(ID: ${userId})失败:`, error);
      if (process.env.NODE_ENV === 'development' && api.deleteUserFromLocal) {
        console.log('开发环境下从本地存储删除');
        
        // 从本地存储删除
        api.deleteUserFromLocal(userId);
        
        return Promise.resolve({
          data: {
            success: true,
            message: "用户删除成功（本地存储）"
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取用户角色
 * @param {number} userId 用户ID
 * @returns {Promise}
 */
export function getUserRoles(userId) {
  return axios.get(`/admin/users/${userId}/roles`)
    .catch(error => {
      console.error(`获取用户角色(ID: ${userId})失败:`, error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        const users = api.getLocalUsers ? api.getLocalUsers() : [];
        const user = users.find(u => u.id == userId);
        
        if (user && user.roles) {
          return Promise.resolve({ data: user.roles });
        } else {
          return Promise.resolve({ data: [] });
        }
      }
      return Promise.reject(error);
    });
}

/**
 * 更新用户角色
 * @param {number} userId 用户ID
 * @param {Array} roles 角色列表
 * @returns {Promise}
 */
export function updateUserRoles(userId, roles) {
  return axios.put(`/admin/users/${userId}/roles`, { roles })
    .catch(error => {
      console.error(`更新用户角色(ID: ${userId})失败:`, error);
      if (process.env.NODE_ENV === 'development' && api.saveUserToLocal) {
        console.log('开发环境下使用本地存储数据');
        const users = api.getLocalUsers ? api.getLocalUsers() : [];
        const user = users.find(u => u.id == userId);
        
        if (user) {
          // 更新角色
          const updatedUser = {
            ...user,
            roles: roles
          };
          
          // 保存到本地存储
          api.saveUserToLocal(updatedUser);
          
          return Promise.resolve({
            data: {
              success: true,
              message: "用户角色更新成功（本地存储）",
              data: updatedUser
            }
          });
        }
      }
      return Promise.reject(error);
    });
}

/**
 * 重置用户密码
 * @param {number} userId 用户ID
 * @returns {Promise}
 */
export function resetPassword(userId) {
  return axios.post(`/admin/users/${userId}/reset-password`)
    .catch(error => {
      console.error(`重置密码(ID: ${userId})失败:`, error);
      if (process.env.NODE_ENV === 'development') {
        return Promise.resolve({
          data: {
            success: true,
            message: "密码已重置为默认值（本地模拟）",
            password: "123456" // 仅开发环境返回明文密码
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取用户部门
 * @returns {Promise}
 */
export function getDepartments() {
  return axios.get('/admin/departments')
    .catch(error => {
      console.error('获取部门列表失败:', error);
      if (process.env.NODE_ENV === 'development') {
        return Promise.resolve({
          data: [
            { id: 1, name: "总经办", parent_id: null },
            { id: 2, name: "技术部", parent_id: null },
            { id: 3, name: "市场部", parent_id: null },
            { id: 4, name: "人事部", parent_id: null },
            { id: 5, name: "财务部", parent_id: null },
            { id: 6, name: "前端组", parent_id: 2 },
            { id: 7, name: "后端组", parent_id: 2 },
            { id: 8, name: "测试组", parent_id: 2 }
          ]
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取用户职位
 * @returns {Promise}
 */
export function getPositions() {
  return axios.get('/admin/positions')
    .catch(error => {
      console.error('获取职位列表失败:', error);
      if (process.env.NODE_ENV === 'development') {
        return Promise.resolve({
          data: [
            { id: 1, name: "总经理", level: 1 },
            { id: 2, name: "部门经理", level: 2 },
            { id: 3, name: "普通员工", level: 3 },
            { id: 4, name: "实习生", level: 4 }
          ]
        });
      }
      return Promise.reject(error);
    });
}

export default {
  getUsers,
  getUserById,
  createUser,
  updateUser,
  deleteUser,
  getUserRoles,
  updateUserRoles,
  resetPassword,
  getDepartments,
  getPositions
}; 