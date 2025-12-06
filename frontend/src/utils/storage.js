/**
 * 本地存储工具
 * 提供统一的接口管理本地数据，包括初始化、存取和事件通知功能
 */

// 存储键名常量
const STORAGE_KEYS = {
  APPROVALS: 'local_approvals',
  USERS: 'local_users',
  WORKFLOWS: 'mock_workflows',
  USING_LOCAL_APPROVALS: 'using_local_approvals',
  USING_LOCAL_USERS: 'using_local_users',
  USING_LOCAL_WORKFLOWS: 'using_local_workflows',
  PERSIST_APPROVALS: 'persist_approvals',
  PERSIST_USERS: 'persist_users',
  PERSIST_WORKFLOWS: 'persist_workflows'
};

// 事件类型常量
const EVENT_TYPES = {
  APPROVAL_CHANGED: 'approval_changed',
  USER_CHANGED: 'user_changed',
  WORKFLOW_CHANGED: 'workflow_changed'
};

// 事件监听器
const listeners = {
  [EVENT_TYPES.APPROVAL_CHANGED]: [],
  [EVENT_TYPES.USER_CHANGED]: [],
  [EVENT_TYPES.WORKFLOW_CHANGED]: []
};

// 调试模式开关
const DEBUG = process.env.NODE_ENV !== 'production';

// 调试日志
const debugLog = (...args) => {
  if (DEBUG) {
    console.log('[Storage]', ...args);
  }
};

// 安全地获取localStorage数据
const safeGetItem = (key) => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const value = localStorage.getItem(key);
      debugLog(`读取本地存储 [${key}]:`, value ? (value.length > 100 ? value.substring(0, 100) + '...' : value) : 'null');
      return value;
    }
  } catch (e) {
    console.error(`获取本地存储数据(${key})失败:`, e);
  }
  return null;
};

// 安全地设置localStorage数据
const safeSetItem = (key, value) => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      debugLog(`写入本地存储 [${key}]:`, value ? (value.length > 100 ? value.substring(0, 100) + '...' : value) : 'null');
      localStorage.setItem(key, value);
      // 验证存储是否成功
      const storedValue = localStorage.getItem(key);
      if (!storedValue) {
        console.warn(`存储验证失败: [${key}] 的值未正确保存`);
        return false;
      }
      return true;
    }
  } catch (e) {
    console.error(`保存数据到本地存储(${key})失败:`, e);
  }
  return false;
};

// 触发事件通知
const notifyListeners = (eventType, data) => {
  if (listeners[eventType] && listeners[eventType].length > 0) {
    debugLog(`通知事件: ${eventType}`, data);
    listeners[eventType].forEach(listener => {
      try {
        listener(data);
      } catch (e) {
        console.error(`执行事件监听器失败: ${eventType}`, e);
      }
    });
  }
};

// 默认审批数据
const defaultApprovals = [
  {
    id: 101,
    title: "张三的请假申请",
    created_at: new Date().toISOString(),
    current_node: "部门经理审批",
    status: "pending",
    workflow_id: 1,
    initiator: "张三",
    emergency_level: 0,
    _persistent: true,
    form_data: {
      leave_type: "年假",
      start_date: "2023-05-20",
      end_date: "2023-05-25",
      days: 5,
      reason: "休假"
    }
  },
  {
    id: 102,
    title: "李四的报销申请",
    created_at: new Date().toISOString(),
    current_node: "财务审批",
    status: "pending",
    workflow_id: 2,
    initiator: "李四",
    emergency_level: 1,
    _persistent: true,
    form_data: {
      amount: 3500,
      purpose: "差旅费用",
      details: "上海出差3天"
    }
  },
  {
    id: 201,
    title: "年假申请 (5天)",
    created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    current_node: "部门经理审批",
    status: "processing",
    workflow_id: 1,
    initiator: "当前用户",
    initiator_id: 1,
    emergency_level: 0,
    content: "计划于下月10日-15日休年假，去三亚旅游。工作已安排好交接。",
    _persistent: true,
    form_data: {
      leave_type: "年假",
      start_date: "2023-06-10",
      end_date: "2023-06-15",
      days: 5,
      reason: "个人旅行"
    },
    history: [
      {
        action: "create",
        time: new Date(Date.now() - 5 * 86400000).toISOString(),
        approver: "当前用户",
        comment: "创建申请"
      }
    ]
  }
];

// 默认用户数据
const defaultUsers = [
  {
    id: 1,
    username: "admin",
    real_name: "系统管理员",
    email: "admin@example.com",
    roles: ["admin"],
    is_admin: true,
    department_id: 1,
    position_id: 1,
    status: "active",
    _persistent: true,
    created_at: new Date().toISOString()
  },
  {
    id: 2,
    username: "zhangsan",
    real_name: "张三",
    email: "zhangsan@example.com",
    roles: ["employee"],
    is_admin: false,
    department_id: 2,
    position_id: 3,
    status: "active",
    _persistent: true,
    created_at: new Date().toISOString()
  },
  {
    id: 3,
    username: "lisi",
    real_name: "李四",
    email: "lisi@example.com",
    roles: ["manager"],
    is_admin: false,
    department_id: 2,
    position_id: 2,
    status: "active",
    _persistent: true,
    created_at: new Date().toISOString()
  },
  {
    id: 4,
    username: "wangwu",
    real_name: "王五",
    email: "wangwu@example.com",
    roles: ["employee"],
    is_admin: false,
    department_id: 3,
    position_id: 3,
    status: "active",
    _persistent: true,
    created_at: new Date().toISOString()
  }
];

// 默认工作流数据
const defaultWorkflows = [
  {
    id: 1,
    name: "请假审批",
    description: "员工请假申请流程",
    _persistent: true,
    created_at: new Date().toISOString()
  },
  {
    id: 2,
    name: "报销审批",
    description: "费用报销申请流程",
    _persistent: true,
    created_at: new Date().toISOString()
  },
  {
    id: 3,
    name: "出差申请",
    description: "员工出差审批流程",
    _persistent: true,
    created_at: new Date().toISOString()
  }
];

// 存储工具类
const storage = {
  // 初始化本地存储
  initLocalStorage() {
    debugLog('正在初始化本地存储...');
    
    // 初始化审批数据
    if (!safeGetItem(STORAGE_KEYS.APPROVALS)) {
      debugLog('初始化默认审批数据');
      safeSetItem(STORAGE_KEYS.APPROVALS, JSON.stringify(defaultApprovals));
      safeSetItem(STORAGE_KEYS.USING_LOCAL_APPROVALS, 'true');
      safeSetItem(STORAGE_KEYS.PERSIST_APPROVALS, 'true'); // 默认永久保存
    }
    
    // 初始化用户数据
    if (!safeGetItem(STORAGE_KEYS.USERS)) {
      debugLog('初始化默认用户数据');
      safeSetItem(STORAGE_KEYS.USERS, JSON.stringify(defaultUsers));
      safeSetItem(STORAGE_KEYS.USING_LOCAL_USERS, 'true');
      safeSetItem(STORAGE_KEYS.PERSIST_USERS, 'true'); // 默认永久保存
    }
    
    // 初始化工作流数据
    if (!safeGetItem(STORAGE_KEYS.WORKFLOWS)) {
      debugLog('初始化默认工作流数据');
      safeSetItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(defaultWorkflows));
      safeSetItem(STORAGE_KEYS.USING_LOCAL_WORKFLOWS, 'true');
      safeSetItem(STORAGE_KEYS.PERSIST_WORKFLOWS, 'true'); // 默认永久保存
    }
    
    // 确保持久化标记已设置
    safeSetItem(STORAGE_KEYS.PERSIST_APPROVALS, 'true');
    safeSetItem(STORAGE_KEYS.PERSIST_USERS, 'true');
    safeSetItem(STORAGE_KEYS.PERSIST_WORKFLOWS, 'true');
    
    debugLog('本地存储初始化完成');
  },
  
  // 添加事件监听器
  addEventListener(eventType, callback) {
    if (!listeners[eventType]) {
      listeners[eventType] = [];
    }
    
    if (typeof callback === 'function' && !listeners[eventType].includes(callback)) {
      listeners[eventType].push(callback);
      debugLog(`添加事件监听器: ${eventType}, 当前监听器数量:`, listeners[eventType].length);
      return true;
    }
    return false;
  },
  
  // 移除事件监听器
  removeEventListener(eventType, callback) {
    if (listeners[eventType] && typeof callback === 'function') {
      const index = listeners[eventType].indexOf(callback);
      if (index !== -1) {
        listeners[eventType].splice(index, 1);
        debugLog(`移除事件监听器: ${eventType}, 当前监听器数量:`, listeners[eventType].length);
        return true;
      }
    }
    return false;
  },
  
  // 获取审批数据
  getApprovals() {
    debugLog('获取审批数据');
    const stored = safeGetItem(STORAGE_KEYS.APPROVALS);
    // 检查持久化标志
    const isPersistent = safeGetItem(STORAGE_KEYS.PERSIST_APPROVALS) === 'true';
    debugLog('审批持久化标志:', isPersistent);
    
    if (stored) {
      try {
        const approvals = JSON.parse(stored);
        if (Array.isArray(approvals)) {
          // 始终标记所有数据为持久化，而不管isPersistent
          approvals.forEach(approval => {
            approval._persistent = true;
          });
          debugLog(`成功获取审批数据, 共${approvals.length}条`);
          
          // 打印前5条数据用于调试
          if (approvals.length > 0) {
            debugLog(`审批数据示例:`, approvals.slice(0, Math.min(5, approvals.length)));
          }
          
          return approvals;
        }
      } catch (e) {
        console.error('解析审批数据失败:', e);
      }
    }
    
    // 如果没有数据或解析失败，初始化并返回默认数据
    debugLog('没有找到审批数据，使用默认数据');
    safeSetItem(STORAGE_KEYS.APPROVALS, JSON.stringify(defaultApprovals));
    safeSetItem(STORAGE_KEYS.USING_LOCAL_APPROVALS, 'true');
    // 默认设置为持久化
    safeSetItem(STORAGE_KEYS.PERSIST_APPROVALS, 'true');
    return defaultApprovals;
  },
  
  // 获取用户数据
  getUsers() {
    debugLog('获取用户数据');
    const stored = safeGetItem(STORAGE_KEYS.USERS);
    // 检查持久化标志
    const isPersistent = safeGetItem(STORAGE_KEYS.PERSIST_USERS) === 'true';
    debugLog('用户持久化标志:', isPersistent);
    
    if (stored) {
      try {
        const users = JSON.parse(stored);
        if (Array.isArray(users)) {
          // 如果设置了持久化标志，标记所有数据为持久化
          if (isPersistent) {
            users.forEach(user => {
              user._persistent = true;
            });
          }
          debugLog(`成功获取用户数据, 共${users.length}条`);
          return users;
        }
      } catch (e) {
        console.error('解析用户数据失败:', e);
      }
    }
    
    // 如果没有数据或解析失败，初始化并返回默认数据
    debugLog('没有找到用户数据，使用默认数据');
    safeSetItem(STORAGE_KEYS.USERS, JSON.stringify(defaultUsers));
    safeSetItem(STORAGE_KEYS.USING_LOCAL_USERS, 'true');
    // 默认设置为持久化
    safeSetItem(STORAGE_KEYS.PERSIST_USERS, 'true');
    return defaultUsers;
  },
  
  // 获取工作流数据
  getWorkflows() {
    debugLog('获取工作流数据');
    const stored = safeGetItem(STORAGE_KEYS.WORKFLOWS);
    // 检查持久化标志
    const isPersistent = safeGetItem(STORAGE_KEYS.PERSIST_WORKFLOWS) === 'true';
    debugLog('工作流持久化标志:', isPersistent);
    
    if (stored) {
      try {
        const workflows = JSON.parse(stored);
        if (Array.isArray(workflows)) {
          // 如果设置了持久化标志，标记所有数据为持久化
          if (isPersistent) {
            workflows.forEach(workflow => {
              workflow._persistent = true;
            });
          }
          debugLog(`成功获取工作流数据, 共${workflows.length}条`);
          return workflows;
        }
      } catch (e) {
        console.error('解析工作流数据失败:', e);
      }
    }
    
    // 如果没有数据或解析失败，初始化并返回默认数据
    debugLog('没有找到工作流数据，使用默认数据');
    safeSetItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(defaultWorkflows));
    safeSetItem(STORAGE_KEYS.USING_LOCAL_WORKFLOWS, 'true');
    // 默认设置为持久化
    safeSetItem(STORAGE_KEYS.PERSIST_WORKFLOWS, 'true');
    return defaultWorkflows;
  },
  
  // 保存审批
  saveApproval(approval) {
    const isNew = !approval.id;
    debugLog(`保存审批, ${isNew ? '新建' : '更新'} 审批:`, approval);
    let approvals = this.getApprovals();
    
    if (isNew) {
      // 生成新ID
      const newId = approvals.length > 0 ? 
        Math.max(...approvals.map(a => parseInt(a.id || 0))) + 1 : 1;
        
      // 创建包含ID和时间戳的新审批对象
      const newApproval = {
        ...approval,
        id: newId,
        created_at: approval.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
        _persistent: true // 标记为永久保存
      };
      
      approvals.push(newApproval);
      const saveResult = safeSetItem(STORAGE_KEYS.APPROVALS, JSON.stringify(approvals));
      safeSetItem(STORAGE_KEYS.PERSIST_APPROVALS, 'true'); // 设置永久保存标志
      notifyListeners(EVENT_TYPES.APPROVAL_CHANGED, { type: 'add', approval: newApproval });
      debugLog(`新审批已保存, ID: ${newId}, 保存结果:`, saveResult);
      
      // 额外检查：确认审批已存入本地存储
      try {
        const checkApprovals = JSON.parse(safeGetItem(STORAGE_KEYS.APPROVALS) || '[]');
        const found = checkApprovals.some(a => a.id === newId);
        debugLog(`审批保存后校验: ID ${newId} ${found ? '已找到' : '未找到'}`);
      } catch (e) {
        console.error('保存后校验失败:', e);
      }
      
      return newApproval;
    } else {
      // 更新已有审批
      let updated = false;
      approvals = approvals.map(a => {
        if (a.id == approval.id) {
          updated = true;
          const updatedApproval = {
            ...a,
            ...approval,
            _persistent: true, // 标记为永久保存
            updated_at: new Date().toISOString()
          };
          return updatedApproval;
        }
        return a;
      });
      
      if (!updated) {
        // 如果未找到匹配的ID，可能是新添加的
        debugLog(`未找到ID为${approval.id}的审批，作为新审批处理`);
        const newApproval = {
          ...approval,
          _persistent: true,
          created_at: approval.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        approvals.push(newApproval);
      }
      
      const saveResult = safeSetItem(STORAGE_KEYS.APPROVALS, JSON.stringify(approvals));
      safeSetItem(STORAGE_KEYS.PERSIST_APPROVALS, 'true'); // 确保设置永久保存标志
      notifyListeners(EVENT_TYPES.APPROVAL_CHANGED, { type: 'update', approval });
      debugLog(`审批更新已保存, ID: ${approval.id}, 保存结果:`, saveResult);
      
      // 额外检查：确认审批已更新
      try {
        const checkApprovals = JSON.parse(safeGetItem(STORAGE_KEYS.APPROVALS) || '[]');
        const found = checkApprovals.some(a => a.id === approval.id);
        debugLog(`审批更新后校验: ID ${approval.id} ${found ? '已找到' : '未找到'}`);
      } catch (e) {
        console.error('更新后校验失败:', e);
      }
      
      return approval;
    }
  },
  
  // 保存用户
  saveUser(user) {
    const isNew = !user.id;
    debugLog(`保存用户, ${isNew ? '新建' : '更新'} 用户:`, user);
    let users = this.getUsers();
    
    if (isNew) {
      // 生成新ID
      const newId = users.length > 0 ? 
        Math.max(...users.map(u => parseInt(u.id || 0))) + 1 : 1;
        
      // 创建包含ID和时间戳的新用户对象
      const newUser = {
        ...user,
        id: newId,
        _persistent: true, // 标记为永久保存
        created_at: user.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      users.push(newUser);
      const saveResult = safeSetItem(STORAGE_KEYS.USERS, JSON.stringify(users));
      safeSetItem(STORAGE_KEYS.PERSIST_USERS, 'true'); // 设置永久保存标志
      notifyListeners(EVENT_TYPES.USER_CHANGED, { type: 'add', user: newUser });
      debugLog(`新用户已保存, ID: ${newId}, 保存结果:`, saveResult);
      return newUser;
    } else {
      // 更新已有用户
      let updated = false;
      users = users.map(u => {
        if (u.id == user.id) {
          updated = true;
          const updatedUser = {
            ...u,
            ...user,
            _persistent: true, // 标记为永久保存
            updated_at: new Date().toISOString()
          };
          return updatedUser;
        }
        return u;
      });
      
      if (!updated) {
        // 如果未找到匹配的ID，可能是新添加的
        debugLog(`未找到ID为${user.id}的用户，作为新用户处理`);
        const newUser = {
          ...user,
          _persistent: true,
          created_at: user.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        users.push(newUser);
      }
      
      const saveResult = safeSetItem(STORAGE_KEYS.USERS, JSON.stringify(users));
      safeSetItem(STORAGE_KEYS.PERSIST_USERS, 'true'); // 确保设置永久保存标志
      notifyListeners(EVENT_TYPES.USER_CHANGED, { type: 'update', user });
      debugLog(`用户更新已保存, ID: ${user.id}, 保存结果:`, saveResult);
      return user;
    }
  },
  
  // 保存工作流
  saveWorkflow(workflow) {
    const isNew = !workflow.id;
    debugLog(`保存工作流, ${isNew ? '新建' : '更新'} 工作流:`, workflow);
    let workflows = this.getWorkflows();
    
    if (isNew) {
      // 生成新ID
      const newId = workflows.length > 0 ? 
        Math.max(...workflows.map(w => parseInt(w.id || 0))) + 1 : 1;
        
      // 创建包含ID和时间戳的新工作流对象
      const newWorkflow = {
        ...workflow,
        id: newId,
        _persistent: true,
        created_at: workflow.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      workflows.push(newWorkflow);
      const saveResult = safeSetItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(workflows));
      safeSetItem(STORAGE_KEYS.PERSIST_WORKFLOWS, 'true'); // 设置永久保存标志
      notifyListeners(EVENT_TYPES.WORKFLOW_CHANGED, { type: 'add', workflow: newWorkflow });
      debugLog(`新工作流已保存, ID: ${newId}, 保存结果:`, saveResult);
      return newWorkflow;
    } else {
      // 更新已有工作流
      let updated = false;
      workflows = workflows.map(w => {
        if (w.id == workflow.id) {
          updated = true;
          const updatedWorkflow = {
            ...w,
            ...workflow,
            _persistent: true,
            updated_at: new Date().toISOString()
          };
          return updatedWorkflow;
        }
        return w;
      });
      
      if (!updated) {
        // 如果未找到匹配的ID，可能是新添加的
        debugLog(`未找到ID为${workflow.id}的工作流，作为新工作流处理`);
        const newWorkflow = {
          ...workflow,
          _persistent: true,
          created_at: workflow.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        workflows.push(newWorkflow);
      }
      
      const saveResult = safeSetItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(workflows));
      safeSetItem(STORAGE_KEYS.PERSIST_WORKFLOWS, 'true'); // 确保设置永久保存标志
      notifyListeners(EVENT_TYPES.WORKFLOW_CHANGED, { type: 'update', workflow });
      debugLog(`工作流更新已保存, ID: ${workflow.id}, 保存结果:`, saveResult);
      return workflow;
    }
  },
  
  // 删除审批
  deleteApproval(id) {
    debugLog(`删除审批, ID: ${id}`);
    let approvals = this.getApprovals();
    const filtered = approvals.filter(a => a.id != id);
    
    if (filtered.length !== approvals.length) {
      const saveResult = safeSetItem(STORAGE_KEYS.APPROVALS, JSON.stringify(filtered));
      notifyListeners(EVENT_TYPES.APPROVAL_CHANGED, { type: 'delete', id });
      debugLog(`审批已删除, ID: ${id}, 保存结果:`, saveResult);
      return { success: true };
    }
    
    debugLog(`未找到ID为${id}的审批，删除失败`);
    return { success: false };
  },
  
  // 删除用户
  deleteUser(id) {
    debugLog(`删除用户, ID: ${id}`);
    let users = this.getUsers();
    const filtered = users.filter(u => u.id != id);
    
    if (filtered.length !== users.length) {
      const saveResult = safeSetItem(STORAGE_KEYS.USERS, JSON.stringify(filtered));
      notifyListeners(EVENT_TYPES.USER_CHANGED, { type: 'delete', id });
      debugLog(`用户已删除, ID: ${id}, 保存结果:`, saveResult);
      return { success: true };
    }
    
    debugLog(`未找到ID为${id}的用户，删除失败`);
    return { success: false };
  },
  
  // 删除工作流
  deleteWorkflow(id) {
    debugLog(`删除工作流, ID: ${id}`);
    let workflows = this.getWorkflows();
    const filtered = workflows.filter(w => w.id != id);
    
    if (filtered.length !== workflows.length) {
      const saveResult = safeSetItem(STORAGE_KEYS.WORKFLOWS, JSON.stringify(filtered));
      notifyListeners(EVENT_TYPES.WORKFLOW_CHANGED, { type: 'delete', id });
      debugLog(`工作流已删除, ID: ${id}, 保存结果:`, saveResult);
      return { success: true };
    }
    
    debugLog(`未找到ID为${id}的工作流，删除失败`);
    return { success: false };
  }
};

// 自动初始化
if (typeof window !== 'undefined') {
  setTimeout(() => {
    storage.initLocalStorage();
    debugLog('本地存储已初始化');
  }, 0);
}

export default storage;
export { STORAGE_KEYS, EVENT_TYPES }; 