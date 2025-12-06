import axios from './axios';

/**
 * 获取所有工作流
 * @returns {Promise}
 */
export function getWorkflows() {
  return axios.get('/api/workflows');
}

/**
 * 获取工作流详情
 * @param {string} workflowId 工作流ID
 * @returns {Promise}
 */
export function getWorkflowDetail(workflowId) {
  return axios.get(`/api/workflow-auth/workflow/${workflowId}`);
}

/**
 * 保存工作流
 * @param {Object} workflow 工作流数据
 * @returns {Promise}
 */
export function saveWorkflow(workflow) {
  return axios.post('/api/workflows', workflow);
}

/**
 * 更新工作流
 * @param {string} workflowId 工作流ID
 * @param {Object} data 工作流数据
 * @returns {Promise}
 */
export function updateWorkflow(workflowId, data) {
  return axios.post(`/api/workflow-auth/workflow/${workflowId}`, data);
}

/**
 * 删除工作流
 * @param {string} workflowId 工作流ID
 * @returns {Promise}
 */
export function deleteWorkflow(workflowId) {
  return axios.delete(`/api/workflows/${workflowId}`);
}

/**
 * 生成工作流
 * @param {Object} data 生成请求数据
 * @returns {Promise}
 */
export function generateWorkflow(data) {
  return axios.post('/api/workflows/generate', data);
}

/**
 * 优化工作流
 * @param {Object} data 优化请求数据
 * @returns {Promise}
 */
export function refineWorkflow(data) {
  return axios.post('/api/workflows/update', data);
}

/**
 * 获取工作流权限
 * @returns {Promise}
 */
export function getWorkflowPermissions() {
  return axios.get('/api/workflow-auth/permissions');
}

/**
 * 获取工作流角色
 * @returns {Promise}
 */
export function getWorkflowRoles() {
  return axios.get('/api/workflow-auth/roles');
}

export default {
  getWorkflows,
  getWorkflowDetail,
  saveWorkflow,
  updateWorkflow,
  deleteWorkflow,
  generateWorkflow,
  refineWorkflow,
  getWorkflowPermissions,
  getWorkflowRoles
}; 