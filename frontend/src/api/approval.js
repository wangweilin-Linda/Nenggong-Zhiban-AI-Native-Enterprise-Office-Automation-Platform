import axios from './axios';
import api from '../utils/api';  // 导入工具API实例

/**
 * 获取待审批的列表
 */
export function getPendingApprovals() {
  return axios.get('/approval/pending')
    .catch(error => {
      console.error('获取待审批列表失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        return Promise.resolve({
          data: {
            success: true,
            data: api.getLocalApprovals ? api.getLocalApprovals().filter(a => 
              (a.status === "pending" || a.status === "processing") && 
              a.initiator !== "当前用户"
            ) : []
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取已完成的审批列表
 */
export function getCompletedApprovals() {
  return axios.get('/approval/completed')
    .catch(error => {
      console.error('获取已完成审批列表失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        return Promise.resolve({
          data: {
            success: true,
            data: api.getLocalApprovals ? api.getLocalApprovals().filter(a => 
              a.status === "completed" || a.status === "rejected" || a.status === "withdrawn"
            ) : []
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取我发起的审批列表
 */
export function getMyApprovals() {
  return axios.get('/approval/my')
    .catch(error => {
      console.error('获取我发起的审批列表失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        
        // 获取当前用户
        let currentUser;
        try {
          const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
          if (userStr) {
            currentUser = JSON.parse(userStr);
          }
        } catch (e) {
          console.error('获取当前用户信息失败:', e);
        }
        
        return Promise.resolve({
          data: {
            success: true,
            data: api.getLocalApprovals ? api.getLocalApprovals().filter(a => {
              if (a.initiator_id && currentUser && a.initiator_id === currentUser.id) {
                return true;
              }
              return a.initiator === "当前用户" || (currentUser && a.initiator === currentUser.username);
            }) : []
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取审批详情
 * @param {number} id 审批实例ID
 */
export function getApprovalDetail(id) {
  return axios.get(`/approval/instance-detail/${id}`)
    .catch(error => {
      console.error('获取审批详情失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
        const approval = approvals.find(a => a.id == id);
        
        if (approval) {
          return Promise.resolve({ data: approval });
        }
      }
      return Promise.reject(error);
    });
}

/**
 * 获取审批日志
 * @param {number} instanceId 实例ID
 * @returns {Promise}
 */
export function getApprovalLogs(instanceId) {
  return axios.get(`/approval/logs/${instanceId}`)
    .catch(error => {
      console.error('获取审批日志失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
        const approval = approvals.find(a => a.id == instanceId);
        
        if (approval && approval.history) {
          return Promise.resolve({ data: approval.history });
        } else {
          return Promise.resolve({ data: [] });
        }
      }
      return Promise.reject(error);
    });
}

/**
 * 提交审批
 * @param {Object} data 审批数据
 */
export function submitApproval(data) {
  console.log('提交审批数据:', data);
  
  // 构建新的审批对象
  const newApproval = {
    ...data,
    created_at: new Date().toISOString(),
    status: 'pending',
    current_node: "部门经理审批",
    emergency_level: data.emergency_level || 0
  };
  
  // 尝试获取当前用户ID
  try {
    const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
    if (userStr) {
      const currentUser = JSON.parse(userStr);
      newApproval.initiator_id = currentUser.id;
      newApproval.initiator = currentUser.real_name || currentUser.username;
    } else {
      newApproval.initiator = "当前用户";
      newApproval.initiator_id = 1;
    }
  } catch (e) {
    console.error('获取当前用户信息失败:', e);
    newApproval.initiator = "当前用户";
    newApproval.initiator_id = 1;
  }
  
  // 添加历史记录
  newApproval.history = [
    {
      action: "create",
      time: new Date().toISOString(),
      approver: newApproval.initiator,
      comment: "创建申请"
    }
  ];
  
  return axios.post('/approval/create', newApproval)
    .then(response => {
      console.log('审批创建成功:', response.data);
      return response.data;
    })
    .catch(error => {
      console.error('创建审批失败:', error, error.response?.status);
      
      // 开发环境或者出现404/500错误时保存到本地
      if (process.env.NODE_ENV === 'development' || 
          (error.response && (error.response.status === 404 || error.response.status === 500))) {
        console.log('保存审批到本地存储');
        
        // 添加持久化标记
        newApproval._persistent = true;
        
        // 使用api工具保存到本地
        if (api.saveApprovalToLocal) {
          const savedApproval = api.saveApprovalToLocal(newApproval, true);
          console.log('审批已保存到本地:', savedApproval);
          
          // 确保设置持久化标记
          localStorage.setItem('persist_approvals', 'true');
          
          return Promise.resolve({
            success: true,
            message: "审批申请已提交（本地存储）",
            data: {
              id: savedApproval.id,
              title: savedApproval.title,
              status: savedApproval.status,
              created_at: savedApproval.created_at
            }
          });
        } else {
          // 使用本地存储模块保存
          try {
            const storage = require('../utils/storage').default;
            const savedApproval = storage.saveApproval(newApproval);
            
            // 确保设置持久化标记
            localStorage.setItem('persist_approvals', 'true');
            
            return Promise.resolve({
              success: true,
              message: "审批申请已提交（本地存储）",
              data: {
                id: savedApproval.id,
                title: savedApproval.title,
                status: savedApproval.status,
                created_at: savedApproval.created_at
              }
            });
          } catch (e) {
            console.error('保存到本地存储失败:', e);
          }
        }
      }
      
      return Promise.reject(error);
    });
}

/**
 * 申请审批
 * @param {Object} data 审批数据
 * @returns {Promise}
 */
export function applyApproval(data) {
  return axios.post('/approval/apply', data)
    .catch(error => {
      console.error('申请审批失败:', error);
      if (process.env.NODE_ENV === 'development') {
        // 复用submitApproval处理逻辑
        return submitApproval(data);
      }
      return Promise.reject(error);
    });
}

/**
 * 获取表单模式
 * @param {string} schemaId 模式ID
 * @returns {Promise}
 */
export function getFormSchema(schemaId) {
  return axios.get(`/approval/form-schema/${schemaId}`)
    .catch(error => {
      console.error(`获取表单架构(ID: ${schemaId})失败:`, error);
      if (process.env.NODE_ENV === 'development') {
        // 返回模拟表单架构
        return Promise.resolve({
          data: {
            id: schemaId,
            title: `表单${schemaId}`,
            fields: [
              {name: "title", label: "标题", type: "text"},
              {name: "content", label: "内容", type: "textarea"},
              {name: "urgency", label: "紧急程度", type: "select", options: ["普通", "紧急", "特急"]}
            ]
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取所有表单模式
 * @returns {Promise}
 */
export function getAllFormSchemas() {
  return axios.get('/approval/form-schemas')
    .catch(error => {
      console.error('获取所有表单架构失败:', error);
      if (process.env.NODE_ENV === 'development') {
        // 返回模拟表单架构列表
        return Promise.resolve({
          data: [
            {
              id: 1,
              title: "请假申请表",
              fields: [
                {name: "title", label: "标题", type: "text"},
                {name: "leave_type", label: "请假类型", type: "select", options: ["年假", "事假", "病假", "婚假", "产假"]},
                {name: "start_date", label: "开始日期", type: "date"},
                {name: "end_date", label: "结束日期", type: "date"},
                {name: "days", label: "天数", type: "number"},
                {name: "reason", label: "请假原因", type: "textarea"}
              ]
            },
            {
              id: 2,
              title: "报销申请表",
              fields: [
                {name: "title", label: "标题", type: "text"},
                {name: "amount", label: "报销金额", type: "number"},
                {name: "purpose", label: "用途", type: "text"},
                {name: "details", label: "明细", type: "textarea"}
              ]
            }
          ]
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取所有实例
 * @returns {Promise}
 */
export function getAllInstances() {
  return axios.get('/approval/instances')
    .catch(error => {
      console.error('获取所有审批实例失败:', error);
      if (process.env.NODE_ENV === 'development') {
        return Promise.resolve({
          data: api.getLocalApprovals ? api.getLocalApprovals() : []
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 搜索审批
 * @param {Object} params 搜索参数
 * @returns {Promise}
 */
export function searchApprovals(params) {
  return axios.get('/approval/search', {
    params: params
  })
  .catch(error => {
    console.error('搜索审批失败:', error);
    if (process.env.NODE_ENV === 'development') {
      console.log('开发环境下使用本地存储数据进行搜索');
      
      const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
      let filtered = [...approvals];
      
      // 根据参数筛选
      if (params) {
        if (params.status) {
          filtered = filtered.filter(a => a.status === params.status);
        }
        
        if (params.initiator) {
          filtered = filtered.filter(a => 
            a.initiator && a.initiator.includes(params.initiator)
          );
        }
        
        if (params.title) {
          filtered = filtered.filter(a => 
            a.title && a.title.includes(params.title)
          );
        }
        
        if (params.start_date) {
          const startDate = new Date(params.start_date).getTime();
          filtered = filtered.filter(a => {
            const createdAt = new Date(a.created_at).getTime();
            return createdAt >= startDate;
          });
        }
        
        if (params.end_date) {
          const endDate = new Date(params.end_date).getTime();
          filtered = filtered.filter(a => {
            const createdAt = new Date(a.created_at).getTime();
            return createdAt <= endDate;
          });
        }
      }
      
      return Promise.resolve({
        data: {
          total: filtered.length,
          items: filtered
        }
      });
    }
    return Promise.reject(error);
  });
}

/**
 * 获取已处理的任务
 * @returns {Promise}
 */
export function getProcessedTasks() {
  return axios.get('/approval/processed-tasks')
    .catch(error => {
      console.error('获取已处理任务失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据');
        
        // 从历史记录中查找当前用户处理过的审批
        let currentUser;
        try {
          const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
          if (userStr) {
            currentUser = JSON.parse(userStr);
          }
        } catch (e) {
          console.error('获取当前用户信息失败:', e);
        }
        
        const approverName = currentUser ? currentUser.real_name || currentUser.username : '当前用户';
        
        const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
        const processed = approvals.filter(a => {
          if (!a.history) return false;
          
          return a.history.some(h => 
            h.approver === approverName && 
            ['approve', 'reject', 'return'].includes(h.action)
          );
        });
        
        return Promise.resolve({
          data: processed
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取任务详情
 * @param {number} taskId
 * @returns {Promise}
 */
export function getTaskDetail(taskId) {
  return getApprovalDetail(taskId);
}

/**
 * 获取审批统计
 * @returns {Promise}
 */
export function getApprovalStats() {
  return axios.get('/approval/stats')
    .catch(error => {
      console.error('获取审批统计失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储数据计算统计信息');
        
        const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
        
        // 统计各种状态的审批数量
        const pendingCount = approvals.filter(a => a.status === 'pending').length;
        const processingCount = approvals.filter(a => a.status === 'processing').length;
        const completedCount = approvals.filter(a => a.status === 'completed').length;
        const rejectedCount = approvals.filter(a => a.status === 'rejected').length;
        
        // 获取当前用户
        let currentUser;
        try {
          const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
          if (userStr) {
            currentUser = JSON.parse(userStr);
          }
        } catch (e) {
          console.error('获取当前用户信息失败:', e);
        }
        
        // 统计当前用户的审批
        const username = currentUser ? currentUser.username : '当前用户';
        const myCount = approvals.filter(a => {
          if (currentUser && a.initiator_id === currentUser.id) return true;
          return a.initiator === username;
        }).length;
        
        // 按月统计审批数量
        const currentYear = new Date().getFullYear();
        const monthlyData = Array(12).fill(0);
        
        approvals.forEach(a => {
          if (a.created_at) {
            const date = new Date(a.created_at);
            if (date.getFullYear() === currentYear) {
              monthlyData[date.getMonth()]++;
            }
          }
        });
        
        return Promise.resolve({
          data: {
            total: approvals.length,
            pending: pendingCount,
            processing: processingCount,
            completed: completedCount,
            rejected: rejectedCount,
            my: myCount,
            monthly: monthlyData
          }
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 撤回审批
 * @param {number} instanceId 实例ID
 * @returns {Promise}
 */
export function withdrawApproval(instanceId) {
  return axios.post(`/approval/${instanceId}/withdraw`)
    .catch(error => {
      console.error('撤回审批失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下在本地存储中撤回审批');
        
        // 获取审批
        const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
        const approval = approvals.find(a => a.id == instanceId);
        
        if (!approval) {
          return Promise.reject(new Error('找不到审批实例'));
        }
        
        // 检查审批状态
        if (approval.status !== 'pending' && approval.status !== 'processing') {
          return Promise.reject(new Error('只能撤回待处理或处理中的审批'));
        }
        
        // 获取当前用户
        let currentUser;
        try {
          const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
          if (userStr) {
            currentUser = JSON.parse(userStr);
          }
        } catch (e) {
          console.error('获取当前用户信息失败:', e);
        }
        
        // 检查是否是发起人
        const username = currentUser ? currentUser.username : '当前用户';
        if (approval.initiator !== username && (!currentUser || approval.initiator_id !== currentUser.id)) {
          return Promise.reject(new Error('只有发起人可以撤回审批'));
        }
        
        // 更新审批状态
        approval.status = 'withdrawn';
        approval.updated_at = new Date().toISOString();
        
        // 添加历史记录
        if (!approval.history) approval.history = [];
        approval.history.push({
          action: 'withdraw',
          time: new Date().toISOString(),
          approver: username,
          comment: '撤回申请'
        });
        
        // 保存到本地存储
        if (api.saveApprovalToLocal) {
          api.saveApprovalToLocal(approval, true);
        } else {
          try {
            const storage = require('../utils/storage').default;
            storage.saveApproval(approval);
          } catch (e) {
            console.error('保存到本地存储失败:', e);
          }
        }
        
        return Promise.resolve({
          message: '审批已撤回'
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 跳过当前审批节点
 * @param {number} instanceId 实例ID
 * @param {string} comment 备注
 * @returns {Promise}
 */
export function skipApprovalNode(instanceId, comment = '') {
  return axios.post(`/approval/${instanceId}/skip`, { comment })
    .catch(error => {
      console.error('跳过审批节点失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下在本地存储中模拟跳过节点');
        
        // 获取审批
        const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
        const approval = approvals.find(a => a.id == instanceId);
        
        if (!approval) {
          return Promise.reject(new Error('找不到审批实例'));
        }
        
        // 更新节点信息
        approval.current_node = '下一审批节点';
        approval.updated_at = new Date().toISOString();
        
        // 添加历史记录
        if (!approval.history) approval.history = [];
        approval.history.push({
          action: 'skip',
          time: new Date().toISOString(),
          approver: '管理员',
          comment: comment || '跳过当前节点'
        });
        
        // 保存到本地存储
        if (api.saveApprovalToLocal) {
          api.saveApprovalToLocal(approval, true);
        } else {
          try {
            const storage = require('../utils/storage').default;
            storage.saveApproval(approval);
          } catch (e) {
            console.error('保存到本地存储失败:', e);
          }
        }
        
        return Promise.resolve({
          message: '已跳过当前节点'
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 用于前端直接撤回我的审批
 */
export function withdrawMyApproval(instanceId) {
  return withdrawApproval(instanceId);
}

/**
 * 处理审批
 * @param {number} instanceId 实例ID
 * @param {boolean} approved 是否批准
 * @param {string} comment 备注
 * @returns {Promise}
 */
export function handleApproval(instanceId, approved, comment = '') {
  const action = approved ? 'approve' : 'reject';
  
  return axios.post(`/approval/${instanceId}/${action}`, { comment })
    .catch(error => {
      console.error(`${approved ? '批准' : '拒绝'}审批失败:`, error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下在本地存储中模拟处理审批');
        
        // 获取审批
        const approvals = api.getLocalApprovals ? api.getLocalApprovals() : [];
        const approval = approvals.find(a => a.id == instanceId);
        
        if (!approval) {
          return Promise.reject(new Error('找不到审批实例'));
        }
        
        // 获取当前用户
        let currentUser;
        try {
          const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
          if (userStr) {
            currentUser = JSON.parse(userStr);
          }
        } catch (e) {
          console.error('获取当前用户信息失败:', e);
        }
        
        const approverName = currentUser ? currentUser.real_name || currentUser.username : '当前用户';
        
        // 更新审批状态
        if (approved) {
          approval.status = 'completed';
        } else {
          approval.status = 'rejected';
        }
        approval.updated_at = new Date().toISOString();
        
        // 添加历史记录
        if (!approval.history) approval.history = [];
        approval.history.push({
          action: action,
          time: new Date().toISOString(),
          approver: approverName,
          comment: comment || (approved ? '同意' : '拒绝')
        });
        
        // 保存到本地存储
        if (api.saveApprovalToLocal) {
          api.saveApprovalToLocal(approval, true);
        } else {
          try {
            const storage = require('../utils/storage').default;
            storage.saveApproval(approval);
          } catch (e) {
            console.error('保存到本地存储失败:', e);
          }
        }
        
        return Promise.resolve({
          message: approved ? '审批已批准' : '审批已拒绝'
        });
      }
      return Promise.reject(error);
    });
}

/**
 * 获取可用的工作流
 * @returns {Promise}
 */
export function getAvailableWorkflows() {
  return axios.get('/workflow-auth/workflows')
    .catch(error => {
      console.error('获取可用工作流失败:', error);
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境下使用本地存储的工作流数据');
        
        // 从本地存储获取工作流
        let workflows = [];
        if (api.getWorkflows) {
          workflows = api.getWorkflows();
        } else {
          try {
            const storage = require('../utils/storage').default;
            workflows = storage.getWorkflows();
          } catch (e) {
            console.error('从本地存储获取工作流失败:', e);
          }
        }
        
        return Promise.resolve({
          data: workflows
        });
      }
      return Promise.reject(error);
    });
}

export default {
  getPendingApprovals,
  getCompletedApprovals,
  getMyApprovals,
  getApprovalDetail,
  getApprovalLogs,
  submitApproval,
  applyApproval,
  getFormSchema,
  getAllFormSchemas,
  getAllInstances,
  searchApprovals,
  getProcessedTasks,
  getTaskDetail,
  getApprovalStats,
  withdrawApproval,
  skipApprovalNode,
  withdrawMyApproval,
  handleApproval,
  getAvailableWorkflows
}; 