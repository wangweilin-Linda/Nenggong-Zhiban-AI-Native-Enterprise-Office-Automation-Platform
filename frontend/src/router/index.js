import { createRouter, createWebHistory } from 'vue-router';

// 组件懒加载
const Login = () => import('../views/Login.vue');
const Workspace = () => import('../views/Workspace.vue');
const Dashboard = () => import('../views/Dashboard.vue');
const TodoList = () => import('../components/TodoList.vue');
const EmailSystem = () => import('../components/EmailSystem.vue');
const ApprovalCenter = () => import('../components/ApprovalCenter.vue');
const WorkflowDesigner = () => import('../views/admin/components/WorkflowDesigner.vue');
const SandboxAnalysis = () => import('../views/Sandbox/SandboxAnalysis.vue');
const UserProfile = () => import('../views/user/Profile.vue');

// 定义路由
const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/login',
    name: 'login',
    component: Login,
    meta: {
      title: '登录',
      requiresAuth: false
    }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: Dashboard,
    meta: {
      title: '控制台',
      requiresAuth: true
    }
  },
  {
    path: '/workspace',
    name: 'workspace',
    component: Workspace,
    meta: {
      title: '工作区',
      requiresAuth: true
  },
    children: [
  {
        path: '',
        name: 'Dashboard',
        component: Dashboard
      },
      {
        path: 'todo',
        name: 'TodoList',
        component: TodoList
  },
  {
        path: 'email',
        name: 'EmailSystem',
        component: EmailSystem
  },
  {
        path: 'approval',
        name: 'ApprovalCenter',
        component: ApprovalCenter
      },
      {
        path: 'profile',
        name: 'UserProfile',
        component: UserProfile,
        meta: { title: '个人资料设置' }
      }
    ]
  },
  {
    path: '/workflow-designer',
    name: 'workflow-designer',
    component: WorkflowDesigner,
    meta: {
      title: '工作流设计器',
      requiresAuth: true,
      permissions: ['admin', 'workflow_designer']
    }
  },
  {
    path: '/sandbox',
    name: 'sandbox',
    component: SandboxAnalysis,
    meta: {
      title: '数据分析沙盒',
      requiresAuth: true
    }
  }
];

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
});

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - OA系统` : 'OA系统';
  
  // 检查是否需要登录认证
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  const isAuthenticated = !!token;
  
  // 检查token是否为JWT格式
  const isJwtToken = token && token.split('.').length === 3;
  
  if (to.meta.requiresAuth && !isAuthenticated) {
    // 需要认证但未登录，重定向到登录页
    console.log('需要登录，重定向到登录页');
    next({ name: 'login' });
  } else {
    // 检查权限，使用JWT token进行验证
    if (to.meta.permissions && !isJwtToken) {
      const userRole = localStorage.getItem('userRole');
      const userStr = localStorage.getItem('user');
      let isAdmin = false;
      
      // 尝试从用户信息中获取管理员状态
      if (userStr) {
        try {
          const user = JSON.parse(userStr);
          isAdmin = user.is_admin === true;
        } catch (e) {
          console.error('解析用户信息失败:', e);
        }
      }
      
      // 如果是管理员或路由权限包含用户角色，允许访问
      if (isAdmin || (userRole && to.meta.permissions.includes(userRole))) {
        console.log('权限检查通过:', userRole);
        next();
      } else {
        // 没有权限，重定向到首页
        console.log('权限不足，重定向到首页');
        next({ name: 'dashboard' });
      }
    } else {
      // 无需检查权限或使用JWT token，直接通过
      next();
    }
  }
});

export default router;