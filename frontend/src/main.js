import { createApp } from 'vue';
import { createPinia } from 'pinia';
import axios from 'axios';
import App from './App.vue';
import './assets/style.css';
import { useUserStore } from './stores/user';
import router from './router/index';
import Antd from 'ant-design-vue';
// 使用正确的样式路径，v4版本将CSS文件放在了不同位置
import 'ant-design-vue/dist/reset.css';
import mitt from 'mitt';
import mermaid from 'mermaid';

// 创建Pinia (必须先创建，以便在路由守卫中使用)
const pinia = createPinia();

// 配置axios - 不设置baseURL，我们在每个请求中直接使用完整路径
// axios.defaults.baseURL = '/api';
axios.defaults.timeout = 15000;  // 15秒超时
axios.defaults.withCredentials = true;  // 允许跨域携带cookie

// 添加axios拦截器处理错误
axios.interceptors.response.use(
  response => response,
  error => {
    console.error('API请求错误:', error);
    
    // 如果是开发环境且访问了不存在的API，提供更详细的日志
    if (process.env.NODE_ENV === 'development') {
      console.log('请求URL:', error.config?.url);
      console.log('请求方法:', error.config?.method);
      console.log('响应状态:', error.response?.status);
      console.log('响应数据:', error.response?.data);
    }
    
    // 处理401未授权错误
    if (error?.response?.status === 401) {
      try {
        // 在这里，通过延时来避免生命周期执行中出现的问题
        setTimeout(() => {
          try {
            const userStore = useUserStore();
            if (userStore && userStore.isLoggedIn) {
              userStore.logout();
              router.push('/login');
            }
          } catch (e) {
            console.error('处理401错误时出错:', e);
          }
        }, 100);
      } catch (e) {
        console.error('处理401错误时出错:', e);
      }
    }
    
    return Promise.reject(error);
  }
);

// 初始化
const app = createApp(App);
const emitter = mitt();

// 配置全局属性
app.config.globalProperties.emitter = emitter;

// 配置Axios
axios.interceptors.request.use(
  config => {
    try {
      const token = localStorage.getItem('token');
      if (token && config?.headers) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
      
      // 开发环境中记录API请求信息
      if (process.env.NODE_ENV === 'development') {
        console.log(`请求: ${config.method?.toUpperCase()} ${config.url}`);
      }
    } catch (e) {
      console.error('设置请求头时出错:', e);
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 配置Mermaid
try {
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
      useMaxWidth: false,
      htmlLabels: true
    }
  });
} catch (e) {
  console.error('Mermaid初始化失败:', e);
}

// 注册插件
app.use(router);
app.use(pinia);
app.use(Antd);

// 配置Ant Design Vue的默认值
import { Modal, message } from 'ant-design-vue';

// 在Ant Design Vue v4中，Modal.config不再是一个函数
// 使用app.config.globalProperties来设置默认值
app.config.globalProperties.$confirm = function(...args) {
  return Modal.confirm({
    okText: '确认',
    cancelText: '取消',
    ...args
  });
};

// 全局配置message组件
message.config({
  duration: 2, // 持续时间，单位：秒
  maxCount: 3  // 最大显示数，超过限制时，最早的消息会被自动关闭
});

// 挂载应用
app.mount('#app');

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('Vue应用错误:', err);
  console.error('错误发生在:', info);
  
  // 可以在这里添加全局错误通知或日志上报
  if (err?.message?.includes('网络错误') || err?.message?.includes('Network Error')) {
    // 显示网络错误提示
    alert('网络连接异常，请检查您的网络连接或稍后再试');
  }
};