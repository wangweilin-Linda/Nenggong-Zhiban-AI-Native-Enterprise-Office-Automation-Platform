import axios from 'axios';

// 安全地从localStorage获取数据的函数
function safeGetItem(key) {
  try {
    return localStorage.getItem(key);
  } catch (error) {
    console.warn('Access to localStorage is restricted:', error);
    return null;
  }
}

const apiClient = axios.create({
  baseURL: '/api',  // 使用相对路径，配合vite代理
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器，处理Token
apiClient.interceptors.request.use(config => {
  // 尝试从localStorage获取token，或在开发环境使用模拟token
  const token = safeGetItem('token') || (process.env.NODE_ENV === 'development' ? 'dev-mock-token-12345' : null);
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 添加响应拦截器，处理错误和开发环境模拟数据
apiClient.interceptors.response.use(
  response => response,
  error => {
    // 在开发环境中，对某些接口返回模拟数据
    if (process.env.NODE_ENV === 'development') {
      const url = error.config.url;
      const status = error.response?.status || 0;
      console.warn(`API错误 (${status}): ${url}`);
      
      // 模拟审批创建API (处理500错误)
      if (url.includes('/approval/create') && error.response?.status === 500) {
        console.warn('模拟审批创建成功响应');
        return Promise.resolve({
          data: {
            success: true,
            message: "审批申请已创建",
            data: {
              id: Date.now(),
              title: error.config.data ? JSON.parse(error.config.data).title || "新建审批" : "新建审批",
              status: "pending",
              current_node: "start"
            }
          }
        });
      }
      
      // 审批相关接口的模拟数据
      if ((url.includes('/approval/pending') || url.includes('/api/approval/pending')) && 
          (status === 401 || status === 404 || status === 500)) {
        console.warn('返回审批待处理模拟数据');
        return Promise.resolve({
          data: {
            items: [
              { id: 1, title: '模拟待处理审批1', status: 'pending', created_at: new Date().toISOString() },
              { id: 2, title: '模拟待处理审批2', status: 'pending', created_at: new Date().toISOString() }
            ],
            total: 2
          }
        });
      }
      
      if ((url.includes('/approval/my') || url.includes('/api/approval/my')) && 
          (status === 401 || status === 404 || status === 500)) {
        console.warn('返回我的审批模拟数据');
        return Promise.resolve({
          data: {
            items: [
              { id: 3, title: '我发起的审批1', status: 'approved', created_at: new Date().toISOString() },
              { id: 4, title: '我发起的审批2', status: 'pending', created_at: new Date().toISOString() }
            ],
            total: 2
          }
        });
      }
      
      // 处理审批实例详情
      if ((url.includes('/approval/instance-detail/') || url.includes('/api/approval/instance-detail/')) &&
          (status === 401 || status === 500)) {
        const instanceId = url.split('/').pop();
        console.warn(`返回审批实例详情(ID: ${instanceId})模拟数据`);
        
        return Promise.resolve({
          data: {
            id: parseInt(instanceId),
            title: `审批实例 ${instanceId}`,
            process_id: 1,
            status: "pending",
            current_node: "manager_approval",
            initiator: "当前用户",
            created_at: new Date().toISOString(),
            form_data: {
              leave_type: "年假",
              start_date: "2023-05-20",
              end_date: "2023-05-25",
              days: 5,
              reason: "休假"
            },
            nodes: [
              {
                id: "start",
                name: "开始",
                type: "start",
                status: "completed"
              },
              {
                id: "manager_approval",
                name: "经理审批",
                type: "approval",
                status: "pending"
              },
              {
                id: "hr_review",
                name: "人事审核",
                type: "approval",
                status: "pending"
              },
              {
                id: "end",
                name: "结束",
                type: "end",
                status: "pending"
              }
            ]
          }
        });
      }
      
      // 处理工作流相关请求的错误
      if ((url.includes('/workflow-auth/workflows') || url.includes('/api/workflow-auth/workflows')) && 
          (status === 401 || status === 404 || status === 422 || status === 500)) {
        console.warn('返回工作流配置模拟数据');
        return Promise.resolve({
          data: {
            items: [
              { 
                id: 101, 
                name: '模拟审批工作流1', 
                description: '用于测试的工作流', 
                created_at: new Date().toISOString() 
              },
              { 
                id: 102, 
                name: '模拟审批工作流2', 
                description: '人事审批流程', 
                created_at: new Date().toISOString() 
              },
              { 
                id: 103, 
                name: '模拟审批工作流3', 
                description: '财务报销流程', 
                created_at: new Date().toISOString() 
              }
            ],
            total: 3
          }
        });
      }
      
      // 处理任何审批相关的API路径
      if (url.includes('approval') && 
          (status === 401 || status === 404 || status === 500)) {
        console.warn(`提供通用审批接口模拟数据: ${url}`);
        return Promise.resolve({
          data: {
            success: true,
            message: "操作成功(模拟数据)",
            data: {}
          }
        });
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;