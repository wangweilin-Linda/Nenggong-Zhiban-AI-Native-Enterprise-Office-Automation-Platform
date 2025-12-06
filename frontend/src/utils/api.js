import axios from 'axios';
import { message } from 'ant-design-vue';
import storage from './storage';

// 默认工作流数据（避免频繁创建）
// 7月1日的随机时间点
const july1st2025_1 = new Date('2025-07-01T09:15:30.000Z').toISOString();
const july1st2025_2 = new Date('2025-07-01T14:22:45.000Z').toISOString();

const DEFAULT_WORKFLOWS = [
  {
    id: 1,
    name: "请假流程",
    description: "员工请假审批流程",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: 2,
    name: "财务报销流程",
    description: "员工报销审批流程",
    created_at: july1st2025_1,
    updated_at: july1st2025_1
  },
  {
    id: 3,
    name: "采购流程",
    description: "物资采购审批流程",
    created_at: july1st2025_2,
    updated_at: july1st2025_2
  }
];

// 错误消息映射表
const ERROR_MESSAGES = {
  network: '网络连接异常，请检查您的网络连接',
  timeout: '请求超时，服务器可能正忙',
  server: '服务器内部错误，请稍后再试',
  auth: '身份验证失败，请重新登录',
  forbidden: '您没有权限执行此操作',
  notFound: '请求的资源不存在',
  validation: '提交的数据无效，请检查输入',
  conflict: '操作冲突，资源可能已被修改',
  unknown: '发生未知错误，请稍后再试'
};

// 安全地访问localStorage
const safeGetItem = (key) => {
  if (key === 'local_approvals') {
    return JSON.stringify(storage.getApprovals());
  } else if (key === 'local_users') {
    return JSON.stringify(storage.getUsers());
  } else if (key === 'mock_workflows') {
    return JSON.stringify(storage.getWorkflows());
  }
  
  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.error(`获取本地存储数据(${key})失败:`, e);
    return null;
  }
};

const safeSetItem = (key, value) => {
  try {
    if (key === 'local_approvals' && typeof value === 'string') {
      const approvals = JSON.parse(value);
      approvals.forEach(a => storage.saveApproval(a));
      return true;
    } else if (key === 'local_users' && typeof value === 'string') {
      const users = JSON.parse(value);
      users.forEach(u => storage.saveUser(u));
      return true;
    } else if (key === 'mock_workflows' && typeof value === 'string') {
      const workflows = JSON.parse(value);
      workflows.forEach(w => storage.saveWorkflow(w));
      return true;
    }
    
    localStorage.setItem(key, value);
    return true;
  } catch (e) {
    console.error(`保存数据到本地存储(${key})失败:`, e);
    return false;
  }
};

// 创建一个axios实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 添加一个获取认证token的辅助函数
const getAuthToken = () => {
  // 尝试从不同的存储位置获取令牌
  const token = localStorage.getItem('token') || 
                localStorage.getItem('access_token') || 
                sessionStorage.getItem('token') || 
                sessionStorage.getItem('access_token');
  
  if (!token) {
    console.warn('找不到认证令牌，将使用开发模式');
    
    // 在开发环境中，返回一个模拟令牌
    if (process.env.NODE_ENV === 'development') {
      return 'Bearer mock_dev_token';
    }
    return null;
  }
  
  // 检查token是否为合法的JWT格式
  if (token.split('.').length !== 3) {
    console.warn('令牌不是有效的JWT格式（期望有3个点分段），但仍将使用');
  } else {
    console.log('使用JWT格式的令牌');
  }
  
  const authHeader = `Bearer ${token}`;
  return authHeader;
};

// 确保在实例创建后添加正确的拦截器
api.interceptors.request.use(
  config => {
    // 添加请求标识符，用于日志和错误跟踪
    config.requestId = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
    
    // 添加认证令牌
    const authToken = getAuthToken();
    if (authToken) {
      config.headers['Authorization'] = authToken;
    }
    
    // 开发环境下添加更多日志
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API:${config.requestId}] 请求: ${config.method?.toUpperCase()} ${config.url}`, 
                 config.data ? '数据:' : '', config.data || '');
    }
    
    return config;
  },
  error => {
    console.error('请求配置失败:', error);
    return Promise.reject(error);
  }
);

// 拦截响应
api.interceptors.response.use(
  response => {
    // 开发环境下记录响应
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API:${response.config?.requestId}] 响应: ${response.status} ${response.config?.url}`, 
                 response.data ? '数据:' : '', response.data || '');
    }
    return response;
  },
  error => {
    // 获取请求信息
    const requestId = error.config?.requestId || 'unknown';
    const url = error.config?.url || 'unknown';
    const method = (error.config?.method || 'get').toUpperCase();
    
    // 记录详细错误
    console.error(`[API:${requestId}] 错误: ${method} ${url}`, error);
    
    // 处理错误类型
    let errorType = 'unknown';
    let errorDetail = '';
    
    if (error.response) {
      // 服务器返回了错误状态码
      const status = error.response.status;
      const serverErrorMessage = error.response.data?.detail || error.response.data?.message || '';
      
      if (status === 400) {
        errorType = 'validation';
        errorDetail = serverErrorMessage || '提交的数据无效';
      } else if (status === 401) {
        errorType = 'auth';
        // 检查是否需要自动重定向到登录页
        if (!url.includes('/login') && !url.includes('/auth/token')) {
          console.log('未授权，准备重定向到登录页');
          setTimeout(() => {
            if (window.location.pathname !== '/login') {
              // 保存当前URL，以便登录后返回
              const returnUrl = window.location.pathname + window.location.search;
              if (returnUrl !== '/login') {
                localStorage.setItem('returnUrl', returnUrl);
              }
              // 延迟重定向，避免路由冲突
              setTimeout(() => {
                window.location.href = '/login';
              }, 100);
            }
          }, 1000);
        }
      } else if (status === 403) {
        errorType = 'forbidden';
      } else if (status === 404) {
        errorType = 'notFound';
      } else if (status === 409) {
        errorType = 'conflict';
      } else if (status >= 500) {
        errorType = 'server';
      }
      
      errorDetail = serverErrorMessage || ERROR_MESSAGES[errorType] || ERROR_MESSAGES.unknown;
    } else if (error.request) {
      // 请求已发送但未收到响应
      if (error.code === 'ECONNABORTED') {
        errorType = 'timeout';
      } else {
        errorType = 'network';
      }
    }
    
    // 统一错误处理
    if (process.env.NODE_ENV === 'development') {
      // 开发环境下，提供更详细的错误信息
      console.warn(`开发环境下处理${errorType}错误，URL: ${url}`);
      
      // 继续模拟数据的逻辑...
      
      // 保留原有模拟数据逻辑
      if (error.response?.status === 401) {
        console.warn('401未授权，返回模拟数据');
        
        // 审批相关API返回模拟数据
        if (url.includes('/approval/')) {
          if (url.includes('/pending')) {
            return Promise.resolve({
              data: storage.getApprovals().filter(a => a.status === 'pending')
            });
          }
          if (url.includes('/my')) {
            return Promise.resolve({
              data: storage.getApprovals().filter(a => a.initiator_id === 1 || a.initiator === '当前用户')
            });
          }
          if (url.includes('/completed')) {
            return Promise.resolve({
              data: storage.getApprovals().filter(a => a.status === 'completed')
            });
          }
          if (url.match(/\/approval\/\d+$/)) {
            // 获取审批详情
            const id = url.split('/').pop();
            const approval = storage.getApprovals().find(a => a.id == id);
            if (approval) {
              return Promise.resolve({ data: approval });
            }
          }
        }
        
        // 用户相关API返回模拟数据
        if (url.includes('/users')) {
          if (url === '/users') {
            return Promise.resolve({
              data: storage.getUsers()
            });
          }
          // 获取用户详情
          const match = url.match(/\/users\/(\d+)$/);
          if (match) {
            const id = match[1];
            const user = storage.getUsers().find(u => u.id == id);
            if (user) {
              return Promise.resolve({ data: user });
            }
          }
        }
      }
      
      // 其他模拟数据逻辑...
      
    } else {
      // 生产环境下，显示友好的错误信息
      const errorMessage = ERROR_MESSAGES[errorType] || ERROR_MESSAGES.unknown;
      // 只有在不是401未授权的情况下才显示错误消息
      // （401的情况下已经处理了重定向到登录页）
      if (errorType !== 'auth') {
        message.error(`${errorMessage}${errorDetail ? `：${errorDetail}` : ''}`);
      }
    }
    
    // 增强错误对象，便于上层组件处理
    error.errorType = errorType;
    error.errorDetail = errorDetail;
    error.friendlyMessage = ERROR_MESSAGES[errorType] || ERROR_MESSAGES.unknown;
    
    // 返回增强的错误对象
    return Promise.reject(error);
  }
);

// 审批相关API方法
// 获取待处理审批
const getPendingApprovals = () => {
  return api.get('/api/approval/pending');
};

// 获取已处理审批
const getCompletedApprovals = () => {
  return api.get('/api/approval/completed');
};

// 获取我的审批
const getMyApprovals = () => {
  return api.get('/api/approval/my');
};

// 获取审批详情
const getApprovalDetail = (approvalId) => {
  const authToken = getAuthToken();
  return api.get(`/api/approval/instance-detail/${approvalId}`, {
    headers: {
      'Authorization': authToken
    }
  });
};

// 获取审批日志
const getApprovalLogs = (approvalId) => {
  const authToken = getAuthToken();
  return api.get(`/api/approval/logs/${approvalId}`, {
    headers: {
      'Authorization': authToken
    }
  });
};

// 处理审批
const processApproval = (data) => {
  const authToken = getAuthToken();
  return api.post('/api/approval/process', data, {
    headers: {
      'Authorization': authToken
    }
  });
};

// 撤回审批
const withdrawApproval = async (approvalId) => {
  try {
    console.log('撤回审批:', approvalId);
    const authToken = getAuthToken();
    
    if (!authToken) {
      console.error('无法撤回审批：未找到认证令牌');
      return Promise.reject(new Error('未找到认证令牌，请重新登录'));
    }
    
    const response = await api.post(`/api/approval/withdraw/${approvalId}`, null, {
      headers: {
        'Authorization': authToken
      }
    });
    return {
      success: true,
      message: '审批已成功撤回',
      data: response.data
    };
  } catch (error) {
    console.error('撤回审批失败:', error);
    
    // 开发环境下使用本地存储
    if (process.env.NODE_ENV === 'development') {
      console.log('开发环境: 在本地存储中撤回审批');
      
      // 获取审批数据
      const approvals = getLocalApprovals();
      const approval = approvals.find(a => a.id == approvalId);
      
      if (!approval) {
        console.error(`找不到ID为${approvalId}的审批`);
        return Promise.reject(new Error('找不到指定的审批'));
      }
      
      // 更新审批状态为已撤回
      const updatedApproval = {
        ...approval,
        status: 'withdrawn',
        current_node: '已撤回',
        updated_at: new Date().toISOString()
      };
      
      // 如果没有历史记录，初始化它
      if (!updatedApproval.history) {
        updatedApproval.history = [];
      }
      
      // 获取当前用户
      let currentUser = { username: '当前用户' };
      try {
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (userStr) {
          currentUser = JSON.parse(userStr);
        }
      } catch (e) {
        console.error('获取当前用户信息失败:', e);
      }
      
      // 添加撤回历史记录
      updatedApproval.history.push({
        action: 'withdraw',
        time: new Date().toISOString(),
        approver: currentUser.real_name || currentUser.username || '当前用户',
        comment: '用户主动撤回'
      });
      
      // 保存到本地存储
      try {
        saveApprovalToLocal(updatedApproval, true);
        
        // 同时更新所有其他存储位置
        try {
          // 1. 更新local_approvals
          let localApprovals = JSON.parse(localStorage.getItem('local_approvals') || '[]');
          const localIndex = localApprovals.findIndex(a => a.id == approvalId);
          if (localIndex !== -1) {
            localApprovals[localIndex] = { ...updatedApproval };
            localStorage.setItem('local_approvals', JSON.stringify(localApprovals));
          }
          
          // 2. 更新mock_approvals
          let mockApprovals = JSON.parse(localStorage.getItem('mock_approvals') || '[]');
          const mockIndex = mockApprovals.findIndex(a => a.id == approvalId);
          if (mockIndex !== -1) {
            mockApprovals[mockIndex] = { ...updatedApproval };
            localStorage.setItem('mock_approvals', JSON.stringify(mockApprovals));
          }
          
          // 3. 更新my_approvals
          let myApprovals = JSON.parse(localStorage.getItem('my_approvals') || '[]');
          const myIndex = myApprovals.findIndex(a => a.id == approvalId);
          if (myIndex !== -1) {
            myApprovals[myIndex] = { ...updatedApproval, _fromMyApprovals: true };
            localStorage.setItem('my_approvals', JSON.stringify(myApprovals));
          }
        } catch (e) {
          console.error('更新多个存储位置失败:', e);
        }
        
        // 返回成功结果
        return Promise.resolve({
          success: true,
          message: '审批已成功撤回（本地存储）',
          data: {
            id: approvalId,
            status: 'withdrawn'
          }
        });
      } catch (e) {
        console.error('保存撤回状态失败:', e);
        return Promise.reject(new Error('保存撤回状态失败'));
      }
    }
    
    // 生产环境直接抛出错误
    return Promise.reject(error);
  }
};

// 获取工作流列表
const getWorkflows = async () => {
  try {
    console.log('获取工作流列表');
    const authToken = getAuthToken();
    
    // 尝试不同的API路径
    let response;
    try {
      // 使用正确的/api/workflows路径
      response = await api.get('/api/workflows', {
        headers: {
          'Authorization': authToken
        }
      });
    } catch (error) {
      console.error('从/workflows获取失败:', error);
      throw error;
    }
    
    // 检查响应数据格式
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    } else if (response.data && response.data.message) {
      console.warn('API返回消息而非数据:', response.data.message);
      throw new Error('API返回的不是工作流数据');
    } else {
      console.warn('API返回的数据格式不正确:', response.data);
      throw new Error('API返回的数据格式不正确');
    }
  } catch (error) {
    console.error('获取工作流列表失败:', error);
    
    // 如果是在开发模式或离线模式，尝试从localStorage获取
    if (process.env.NODE_ENV === 'development' || localStorage.getItem('using_mock_workflows') === 'true') {
      console.log('使用本地存储的工作流数据');
      const mockWorkflows = localStorage.getItem('mock_workflows');
      if (mockWorkflows) {
        try {
          return JSON.parse(mockWorkflows);
        } catch (e) {
          console.error('解析本地工作流数据失败:', e);
        }
      }
      
      // 返回默认数据
      return generateDefaultWorkflows();
    }
    
    // 在生产环境直接抛出错误
    throw error;
  }
};

// 获取单个工作流详情
const getWorkflow = async (id) => {
  try {
    console.log('获取工作流详情:', id);
    const authToken = getAuthToken();
    const response = await api.get(`/api/workflows/${id}`, {
      headers: {
        'Authorization': authToken
      }
    });
    return response.data;
  } catch (error) {
    console.error('获取工作流详情失败:', error);
    
    // 开发模式或离线模式下，从本地存储获取
    if (process.env.NODE_ENV === 'development' || localStorage.getItem('using_mock_workflows') === 'true') {
      console.log('从本地存储获取工作流详情');
      try {
        const savedWorkflows = localStorage.getItem('mock_workflows');
        if (savedWorkflows) {
          const workflows = JSON.parse(savedWorkflows);
          const workflow = workflows.find(w => w.id == id);
          if (workflow) {
            return workflow;
          }
        }
      } catch (e) {
        console.error('从本地存储获取工作流详情失败:', e);
      }
      
      // 没有找到匹配的工作流，创建一个默认的
      return {
        id: id,
        name: `工作流 ${id}`,
        description: '默认工作流',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
    }
    
    throw error;
  }
};

// 保存工作流
const saveWorkflow = async (workflow) => {
  const isNew = !workflow.id;
  const method = isNew ? 'post' : 'put';
  const endpoint = isNew ? '/api/workflows' : `/api/workflows/${workflow.id}`;
  
  try {
    console.log(`${isNew ? '创建' : '更新'}工作流:`, workflow.name);
    const response = await api[method](endpoint, workflow);
    return response.data;
  } catch (error) {
    console.error(`${isNew ? '创建' : '更新'}工作流失败:`, error);
    
    // 在开发模式下，模拟成功响应
    if (process.env.NODE_ENV === 'development') {
      console.log('开发模式: 返回模拟数据');
      
      // 如果是新增，为工作流生成ID
      if (isNew) {
        // 从localStorage获取现有工作流
        const existingWorkflows = [];
        try {
          const savedWorkflows = localStorage.getItem('mock_workflows');
          if (savedWorkflows) {
            const parsed = JSON.parse(savedWorkflows);
            if (Array.isArray(parsed)) {
              parsed.forEach(w => existingWorkflows.push(w));
            }
          }
        } catch (e) {
          console.error('解析本地工作流数据失败:', e);
        }
        
        // 生成新ID
        const newId = existingWorkflows.length > 0 ? 
          Math.max(...existingWorkflows.map(w => parseInt(w.id || 0))) + 1 : 1;
          
        // 创建包含ID和时间戳的新工作流对象
        const newWorkflow = {
          ...workflow,
          id: newId,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        
        // 将新工作流保存到localStorage
        existingWorkflows.push(newWorkflow);
        localStorage.setItem('mock_workflows', JSON.stringify(existingWorkflows));
        
        return newWorkflow;
      } else {
        // 更新已有工作流
        const existingWorkflows = [];
        try {
          const savedWorkflows = localStorage.getItem('mock_workflows');
          if (savedWorkflows) {
            const parsed = JSON.parse(savedWorkflows);
            if (Array.isArray(parsed)) {
              parsed.forEach(w => {
                if (w.id == workflow.id) {
                  // 更新已有工作流
                  existingWorkflows.push({
                    ...w,
                    ...workflow,
                    updated_at: new Date().toISOString()
                  });
                } else {
                  existingWorkflows.push(w);
                }
              });
            }
          }
          localStorage.setItem('mock_workflows', JSON.stringify(existingWorkflows));
        } catch (e) {
          console.error('更新本地工作流数据失败:', e);
        }
        
        return {
          ...workflow,
          updated_at: new Date().toISOString()
        };
      }
    }
    
    // 在生产环境直接抛出错误
    throw error;
  }
};

// 删除工作流
const deleteWorkflow = async (id) => {
  try {
    console.log('删除工作流:', id);
    const response = await api.delete(`/api/workflows/${id}`);
    return response.data;
  } catch (error) {
    console.error('删除工作流失败:', error);
    
    // 在开发模式下，模拟成功响应
    if (process.env.NODE_ENV === 'development') {
      console.log('开发模式: 从本地存储中删除工作流');
      
      // 从localStorage中删除
      try {
        const savedWorkflows = localStorage.getItem('mock_workflows');
        if (savedWorkflows) {
          const parsed = JSON.parse(savedWorkflows);
          if (Array.isArray(parsed)) {
            const filtered = parsed.filter(w => w.id != id);
            localStorage.setItem('mock_workflows', JSON.stringify(filtered));
          }
        }
      } catch (e) {
        console.error('从本地存储删除工作流失败:', e);
      }
      
      return { success: true };
    }
    
    // 在生产环境直接抛出错误
    throw error;
  }
};

// 生成默认工作流数据
const generateDefaultWorkflows = () => {
  console.log('生成默认工作流数据');
  
  // 使用默认工作流数据
  const defaultWorkflows = [...DEFAULT_WORKFLOWS];
  
  // 保存到localStorage
  try {
    localStorage.setItem('mock_workflows', JSON.stringify(defaultWorkflows));
    localStorage.setItem('using_mock_workflows', 'true');
  } catch (e) {
    console.error('保存默认工作流到localStorage失败:', e);
  }
  
  return defaultWorkflows;
};

// 获取当前用户ID
const getCurrentUserId = () => {
  // 尝试从localStorage或sessionStorage获取用户信息
  const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      return user.id || 1; // 如果有用户ID则返回，否则默认为1
    } catch (e) {
      console.error('解析用户信息失败:', e);
    }
  }
  return 1; // 默认用户ID
};

// 初始化审批数据
const initApprovalData = () => {
  // 委托给storage模块处理
  storage.initLocalStorage();
  // 确保永久保存标志
  localStorage.setItem('persist_approvals', 'true');
  return getLocalApprovals();
};

// 初始化用户数据
const initUserData = () => {
  // 委托给storage模块处理
  storage.initLocalStorage();
  // 确保永久保存标志
  localStorage.setItem('persist_users', 'true');
  return getLocalUsers();
};

// 获取本地审批数据
const getLocalApprovals = () => {
  const approvals = storage.getApprovals();
  // 确保所有审批都标记为永久保存
  if (Array.isArray(approvals)) {
    approvals.forEach(approval => {
      approval._persistent = true;
    });
  }
  return approvals;
};

// 获取本地用户数据
const getLocalUsers = () => {
  const users = storage.getUsers();
  // 确保所有用户都标记为永久保存
  if (Array.isArray(users)) {
    users.forEach(user => {
      user._persistent = true;
    });
  }
  return users;
};

// 保存审批到本地存储的辅助函数
const saveApprovalToLocal = (approval, persistent = true) => {
  console.log('保存审批到本地存储:', approval);
  // 确保审批被标记为持久化
  const approvalToSave = {
    ...approval,
    _persistent: persistent
  };
  
  try {
    // 使用storage工具保存
    return storage.saveApproval(approvalToSave);
  } catch (e) {
    console.error('保存审批到本地存储失败:', e);
    throw e;
  }
};

// 保存用户到本地存储的辅助函数
const saveUserToLocal = (user, persistent = true) => {
  console.log('保存用户到本地存储:', user);
  // 确保用户被标记为持久化
  const userToSave = {
    ...user,
    _persistent: persistent
  };
  
  try {
    // 使用storage工具保存
    return storage.saveUser(userToSave);
  } catch (e) {
    console.error('保存用户到本地存储失败:', e);
    throw e;
  }
};

// 删除本地审批
const deleteApprovalFromLocal = (id) => {
  return storage.deleteApproval(id);
};

// 删除本地用户
const deleteUserFromLocal = (id) => {
  return storage.deleteUser(id);
};

// 扩展api对象
Object.assign(api, {
  getApprovalDetail,
  getApprovalLogs,
  processApproval,
  getWorkflows,
  saveWorkflow,
  deleteWorkflow,
  initApprovalData,
  initUserData,
  getLocalApprovals,
  getLocalUsers,
  saveApprovalToLocal,
  saveUserToLocal,
  deleteApprovalFromLocal,
  deleteUserFromLocal
});

// 获取我发起的审批
api.getMyApprovals = async () => {
  try {
    const response = await api.get('/api/approval/my');
    return response.data;
  } catch (error) {
    console.error('获取我的审批失败:', error);
    
    // 开发环境返回本地存储的数据
    if (process.env.NODE_ENV === 'development') {
      console.log('从本地存储获取我的审批数据');
      const approvals = getLocalApprovals();
      // 过滤出当前用户发起的审批
      let currentUser;
      try {
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (userStr) {
          currentUser = JSON.parse(userStr);
        }
      } catch (e) {
        console.error('获取当前用户信息失败:', e);
      }
      
      // 根据当前用户过滤审批列表
      const filtered = approvals.filter(a => {
        // 如果有明确的initiator_id字段，优先使用
        if (a.initiator_id && currentUser && a.initiator_id === currentUser.id) {
          return true;
        }
        // 否则使用initiator字段
        return a.initiator === "当前用户" || (currentUser && a.initiator === currentUser.username);
      });
      
      return filtered;
    }
    
    throw error;
  }
};

// 提交审批（创建新审批）
const submitApproval = async (approvalData) => {
  console.log('提交审批:', approvalData);
  
  // 获取当前用户ID
  let userId = null;
  try {
    const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
    if (userStr) {
      const user = JSON.parse(userStr);
      userId = user.id;
    }
  } catch (e) {
    console.error('获取当前用户信息失败:', e);
  }
  
  // 构建新审批
  const newApproval = {
    ...approvalData,
    creator_id: userId,
    status: 'pending',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    _persistent: true  // 确保明确设置持久化标记
  };
  
  try {
    // 尝试提交到API
    const response = await api.post('/api/approval/create', newApproval);
    return response.data;
  } catch (error) {
    console.error('提交审批失败:', error);
    
    // 处理开发环境下的错误情况
    if (process.env.NODE_ENV === 'development') {
      console.log('开发环境: 在本地存储中保存审批');
      
      // 无论是404还是500错误，都尝试保存到本地
      if (error.response?.status === 404 || error.response?.status === 500) {
        try {
          // 确保审批有一个唯一ID
          const approvals = storage.getApprovals();
          const maxId = approvals.length > 0 
            ? Math.max(...approvals.map(a => parseInt(a.id || 0))) 
            : 0;
          
          const localApproval = {
            ...newApproval,
            id: maxId + 1,
            _persistent: true  // 再次确保持久化标记已设置
          };
          
          // 保存到本地存储
          const savedApproval = saveApprovalToLocal(localApproval, true);
          
          return {
            success: true,
            message: '审批已保存到本地（开发模式）',
            data: savedApproval
          };
        } catch (saveError) {
          console.error('保存审批到本地存储失败:', saveError);
          throw saveError;
        }
      }
    }
    
    // 其他情况直接抛出错误
    throw error;
  }
};

// 添加获取待办审批接口
api.getPendingApprovals = async () => {
  try {
    const response = await api.get('/api/approval/pending');
    return response.data;
  } catch (error) {
    console.error('获取待办审批失败:', error);
    
    // 开发环境返回本地存储的待办审批
    if (process.env.NODE_ENV === 'development') {
      console.log('从本地存储获取待办审批数据');
      const approvals = getLocalApprovals();
      // 过滤出待处理的审批
      const pending = approvals.filter(a => 
        a.status === "pending" || a.status === "processing" &&
        a.initiator !== "当前用户" // 排除自己发起的
      );
      
      return pending;
    }
    
    throw error;
  }
};

// 处理审批操作
api.processApproval = async (data) => {
  try {
    const response = await api.post('/api/approval/process', data);
    return response.data;
  } catch (error) {
    console.error('处理审批失败:', error);
    
    // 开发环境在本地存储中处理审批
    if (process.env.NODE_ENV === 'development') {
      console.log('在本地存储中处理审批');
      
      // 获取审批实例
      const approvals = getLocalApprovals();
      const instance = approvals.find(a => a.id == data.instance_id);
      
      if (!instance) {
        return Promise.reject(new Error('找不到审批实例'));
      }
      
      // 获取当前用户
      let currentUser = { username: '当前用户' };
      try {
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (userStr) {
          currentUser = JSON.parse(userStr);
        }
      } catch (e) {
        console.error('获取当前用户信息失败:', e);
      }
      
      // 根据操作更新审批状态
      const action = data.action;
      const comment = data.comment || '';
      const approverName = currentUser.real_name || currentUser.username;
      
      // 创建历史记录
      const historyItem = {
        action: action,
        time: new Date().toISOString(),
        approver: approverName,
        comment: comment
      };
      
      // 更新审批状态
      let newStatus;
      switch (action) {
        case 'approve':
          newStatus = 'completed';
          break;
        case 'reject':
          newStatus = 'rejected';
          break;
        case 'return':
          newStatus = 'returned';
          break;
        case 'withdraw':
          newStatus = 'withdrawn';
          break;
        default:
          newStatus = 'processing';
      }
      
      // 添加历史记录
      const history = instance.history || [];
      history.push(historyItem);
      
      // 更新审批实例
      const updatedInstance = {
        ...instance,
        status: newStatus,
        history: history,
        updated_at: new Date().toISOString()
      };
      
      // 保存到本地存储
      saveApprovalToLocal(updatedInstance);
      
      return {
        success: true,
        message: `审批${action === 'approve' ? '通过' : 
                action === 'reject' ? '拒绝' : 
                action === 'return' ? '退回' :
                action === 'withdraw' ? '撤回' : '处理'}成功（本地存储）`,
        data: {
          id: instance.id,
          status: newStatus
        }
      };
    }
    
    throw error;
  }
};

// 用户管理API增强
api.getUsers = async () => {
  try {
    const response = await api.get('/admin/users');
    return response.data;
  } catch (error) {
    console.error('获取用户列表失败:', error);
    
    // 开发环境返回本地存储的用户
    if (process.env.NODE_ENV === 'development') {
      console.log('从本地存储获取用户列表');
      return getLocalUsers();
    }
    
    throw error;
  }
};

api.getUserById = async (userId) => {
  try {
    const response = await api.get(`/admin/users/${userId}`);
    return response.data;
  } catch (error) {
    console.error(`获取用户(ID: ${userId})失败:`, error);
    
    // 开发环境从本地存储获取用户
    if (process.env.NODE_ENV === 'development') {
      console.log('从本地存储获取用户详情');
      const users = getLocalUsers();
      const user = users.find(u => u.id == userId);
      
      if (user) {
        return user;
      }
      throw new Error('用户不存在');
    }
    
    throw error;
  }
};

// 创建用户
const createUser = async (userData) => {
  console.log('创建用户:', userData);
  
  try {
    const response = await api.post('/users/create', userData);
    return response.data;
  } catch (error) {
    console.error('创建用户失败:', error);
    
    // 处理开发环境下的错误情况
    if (process.env.NODE_ENV === 'development') {
      console.log('开发环境: 在本地存储中创建用户');
      
      try {
        // 确保用户有用户名和其他必要字段
        const newUser = {
          ...userData,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          status: 'active',
          _persistent: true  // 确保持久化标记已设置
        };
        
        // 保存到本地存储
        const savedUser = saveUserToLocal(newUser, true);
        
        return {
          success: true,
          message: '用户已创建（本地存储）',
          data: savedUser
        };
      } catch (saveError) {
        console.error('保存用户到本地存储失败:', saveError);
        throw saveError;
      }
    }
    
    // 其他情况直接抛出错误
    throw error;
  }
};

api.updateUser = async (userId, userData) => {
  try {
    const response = await api.put(`/admin/users/${userId}`, userData);
    return response.data;
  } catch (error) {
    console.error(`更新用户(ID: ${userId})失败:`, error);
    
    // 开发环境更新本地存储
    if (process.env.NODE_ENV === 'development') {
      console.log('在本地存储中更新用户');
      const updatedUser = saveUserToLocal({...userData, id: userId});
      return updatedUser;
    }
    
    throw error;
  }
};

api.deleteUser = async (userId) => {
  try {
    const response = await api.delete(`/admin/users/${userId}`);
    return response.data;
  } catch (error) {
    console.error(`删除用户(ID: ${userId})失败:`, error);
    
    // 开发环境从本地存储删除
    if (process.env.NODE_ENV === 'development') {
      console.log('从本地存储删除用户');
      return deleteUserFromLocal(userId);
    }
    
    throw error;
  }
};

// 删除审批
const deleteApproval = async (approvalId) => {
  try {
    console.log('删除审批:', approvalId);
    const authToken = getAuthToken();
    
    if (!authToken) {
      console.error('无法删除审批：未找到认证令牌');
      return Promise.reject(new Error('未找到认证令牌，请重新登录'));
    }
    
    const response = await api.delete(`/api/approval/${approvalId}`, {
      headers: {
        'Authorization': authToken
      }
    });
    return {
      success: true,
      message: '审批已成功删除',
      data: response.data
    };
  } catch (error) {
    console.error('删除审批失败:', error);
    
    // 开发环境下使用本地存储
    if (process.env.NODE_ENV === 'development') {
      console.log('开发环境: 在本地存储中删除审批');
      
      // 获取审批数据
      const approvals = getLocalApprovals();
      const approvalIndex = approvals.findIndex(a => a.id == approvalId);
      
      if (approvalIndex === -1) {
        console.error(`找不到ID为${approvalId}的审批`);
        return Promise.reject(new Error('找不到指定的审批'));
      }
      
      // 从数组中移除审批
      approvals.splice(approvalIndex, 1);
      
      // 保存到本地存储
      try {
        localStorage.setItem('local_approvals', JSON.stringify(approvals));
        
        // 同时更新所有其他存储位置
        try {
          // 1. 更新mock_approvals
          let mockApprovals = JSON.parse(localStorage.getItem('mock_approvals') || '[]');
          const mockIndex = mockApprovals.findIndex(a => a.id == approvalId);
          if (mockIndex !== -1) {
            mockApprovals.splice(mockIndex, 1);
            localStorage.setItem('mock_approvals', JSON.stringify(mockApprovals));
          }
          
          // 2. 更新my_approvals
          let myApprovals = JSON.parse(localStorage.getItem('my_approvals') || '[]');
          const myIndex = myApprovals.findIndex(a => a.id == approvalId);
          if (myIndex !== -1) {
            myApprovals.splice(myIndex, 1);
            localStorage.setItem('my_approvals', JSON.stringify(myApprovals));
          }
        } catch (e) {
          console.error('更新多个存储位置失败:', e);
        }
        
        // 返回成功结果
        return Promise.resolve({
          success: true,
          message: '审批已成功删除（本地存储）',
          data: {
            id: approvalId
          }
        });
      } catch (e) {
        console.error('保存删除操作失败:', e);
        return Promise.reject(new Error('保存删除操作失败'));
      }
    }
    
    // 生产环境直接抛出错误
    return Promise.reject(error);
  }
};

// 确保初始化
if (process.env.NODE_ENV === 'development') {
  // 初始化本地存储的数据
  initApprovalData();
  initUserData();
}

// 将新的函数添加到api对象中
api.submitApproval = submitApproval;
api.createUser = createUser;

// 将deleteApproval函数绑定到api对象
api.deleteApproval = deleteApproval;

// 导出API和其他方法
export default {
  // 实例和方法
  instance: api,
  get: api.get,
  post: api.post,
  put: api.put,
  delete: api.delete,
  
  // 审批相关
  getPendingApprovals,
  getCompletedApprovals,
  getMyApprovals,
  getApprovalDetail,
  getApprovalLogs,
  processApproval,
  withdrawApproval,
  submitApproval: api.submitApproval,
  deleteApproval: api.deleteApproval,
  
  // 工作流相关
  getWorkflows,
  getWorkflow,
  saveWorkflow,
  deleteWorkflow,
  
  // 用户管理相关
  getUsers: api.getUsers,
  getUserById: api.getUserById,
  createUser: api.createUser,
  updateUser: api.updateUser,
  deleteUser: api.deleteUser,
  
  // 辅助方法
  generateDefaultWorkflows,
  initApprovalData,
  initUserData,
  getLocalApprovals,
  getLocalUsers,
  saveApprovalToLocal,
  saveUserToLocal,
  deleteApprovalFromLocal,
  deleteUserFromLocal,
  getCurrentUserId
};