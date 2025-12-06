import axios from './axios';

/**
 * 获取用户列表
 * @param {Object} params 查询参数
 * @returns {Promise}
 */
export function getUsers(params) {
  return axios.get('/api/admin/users', { params });
}

/**
 * 创建用户
 * @param {Object} userData 用户数据
 * @returns {Promise}
 */
export function createUser(userData) {
  return axios.post('/api/admin/users', userData);
}

/**
 * 更新用户
 * @param {number} userId 用户ID
 * @param {Object} userData 用户数据
 * @returns {Promise}
 */
export function updateUser(userId, userData) {
  return axios.put(`/api/admin/users/${userId}`, userData);
}

/**
 * 删除用户
 * @param {number} userId 用户ID
 * @returns {Promise}
 */
export function deleteUser(userId) {
  return axios.delete(`/api/admin/users/${userId}`);
}

/**
 * 获取角色列表
 * @returns {Promise}
 */
export function getRoles() {
  return axios.get('/api/admin/roles');
}

/**
 * 创建角色
 * @param {Object} roleData 角色数据
 * @returns {Promise}
 */
export function createRole(roleData) {
  return axios.post('/api/admin/roles', roleData);
}

/**
 * 更新角色
 * @param {number} roleId 角色ID
 * @param {Object} roleData 角色数据
 * @returns {Promise}
 */
export function updateRole(roleId, roleData) {
  return axios.put(`/api/admin/roles/${roleId}`, roleData);
}

/**
 * 删除角色
 * @param {number} roleId 角色ID
 * @returns {Promise}
 */
export function deleteRole(roleId) {
  return axios.delete(`/api/admin/roles/${roleId}`);
}

/**
 * 获取部门列表
 * @returns {Promise}
 */
export function getDepartments() {
  return axios.get('/api/admin/departments');
}

/**
 * 创建部门
 * @param {Object} departmentData 部门数据
 * @returns {Promise}
 */
export function createDepartment(departmentData) {
  return axios.post('/api/admin/departments', departmentData);
}

/**
 * 更新部门
 * @param {number} departmentId 部门ID
 * @param {Object} departmentData 部门数据
 * @returns {Promise}
 */
export function updateDepartment(departmentId, departmentData) {
  return axios.put(`/api/admin/departments/${departmentId}`, departmentData);
}

/**
 * 删除部门
 * @param {number} departmentId 部门ID
 * @returns {Promise}
 */
export function deleteDepartment(departmentId) {
  return axios.delete(`/api/admin/departments/${departmentId}`);
}

/**
 * 获取职位列表
 * @returns {Promise}
 */
export function getPositions() {
  return axios.get('/api/admin/positions');
}

/**
 * 创建职位
 * @param {Object} positionData 职位数据
 * @returns {Promise}
 */
export function createPosition(positionData) {
  return axios.post('/api/admin/positions', positionData);
}

/**
 * 更新职位
 * @param {number} positionId 职位ID
 * @param {Object} positionData 职位数据
 * @returns {Promise}
 */
export function updatePosition(positionId, positionData) {
  return axios.put(`/api/admin/positions/${positionId}`, positionData);
}

/**
 * 删除职位
 * @param {number} positionId 职位ID
 * @returns {Promise}
 */
export function deletePosition(positionId) {
  return axios.delete(`/api/admin/positions/${positionId}`);
}

/**
 * 分配用户到部门
 * @param {number} userId 用户ID
 * @param {Object} data 部门数据
 * @returns {Promise}
 */
export function assignUserDepartment(userId, data) {
  return axios.put(`/api/admin/users/${userId}/department`, data);
}

/**
 * 分配用户到职位
 * @param {number} userId 用户ID
 * @param {Object} data 职位数据
 * @returns {Promise}
 */
export function assignUserPosition(userId, data) {
  return axios.put(`/api/admin/users/${userId}/position`, data);
}

export default {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  getRoles,
  createRole,
  updateRole,
  deleteRole,
  getDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  getPositions,
  createPosition,
  updatePosition,
  deletePosition,
  assignUserDepartment,
  assignUserPosition
}; 