<template>
  <div class="workflow-designer">
    <div class="designer-header">
      <h2>审批流程设计器</h2>
      <button @click="createNewWorkflow" class="primary-btn">新增审批流程</button>
    </div>

    <!-- 工作流列表 -->
    <div v-if="!isDesigning" class="workflow-list">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ errorMessage || '正在加载工作流数据..' }}</p>
      </div>
      
      <!-- 错误状态 -->
      <div v-else-if="hasLoadError" class="error-state">
        <div class="error-icon">!</div>
        <p>{{ errorMessage || '获取工作流数据失败' }}</p>
        <button @click="retryFetchWorkflows" class="retry-btn">重新加载</button>
      </div>
      
      <!-- 数据表格 -->
      <div v-else>
        <div class="table-header">
          <h3>工作流列表</h3>
          <p v-if="workflows.length === 0">没有找到工作流，请创建新的工作流</p>
          <p v-else-if="isUsingMockData" class="mock-data-notice">
            <a-tag color="orange">开发模式</a-tag> 当前使用的是本地存储的数据，数据仅保存在本地浏览器中
          </p>
        </div>
        
        <table v-if="workflows.length > 0">
        <thead>
          <tr>
            <th>ID</th>
            <th>流程名称</th>
            <th>创建时间</th>
            <th>最近更新</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(workflow, index) in workflows" :key="workflow.id">
            <td>{{ index + 1 }}</td>
            <td>{{ workflow.name }}</td>
            <td>{{ formatDate(workflow.created_at) }}</td>
            <td>{{ formatDate(workflow.updated_at) }}</td>
            <td>
              <button @click="editWorkflow(workflow)" class="edit-btn">编辑</button>
                <button @click="deleteWorkflow(workflow)" class="delete-btn">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
        
        <div v-else class="empty-state">
          <p>暂无工作流数据，请点击"新增审批流程"按钮创建</p>
        </div>
      </div>
    </div>

    <!-- 工作流设计界面 -->
    <div v-if="isDesigning" class="design-panel">
      <div class="design-tabs">
        <div 
          v-for="tab in designTabs" :key="tab.key"
          :class="['tab-item', { active: activeDesignTab === tab.key }]"
          @click="changeDesignTab(tab.key)"
        >
          {{ tab.label }}
        </div>
      </div>

      <!-- 基本信息 -->
      <div v-if="activeDesignTab === 'basic'" class="design-tab-content">
        <div class="form-group">
          <label>流程名称</label>
          <input v-model="designData.name" placeholder="请输入流程名称" />
        </div>
        <div class="form-group">
          <label>流程描述</label>
          <textarea v-model="designData.description" rows="2" placeholder="请简要描述该流程的用途"></textarea>
        </div>
        <div class="form-group">
          <label>AI辅助设计 (自然语言描述)</label>
          <textarea 
            v-model="designData.prompt" 
            rows="6"
            placeholder="描述您需要的审批流程，例如：我需要一个三级审批流程，部门经理→财务经理→总经理，如果金额超过10000元，则需要董事长审批"
          ></textarea>
        </div>
      </div>

      <!-- AI设计助手 -->
      <div v-if="activeDesignTab === 'ai'" class="design-tab-content">
        <div class="chat-panel">
          <div class="chat-history" ref="chatHistory">
            <div v-for="(msg, index) in chatHistory" :key="index" :class="['chat-message', msg.role]">
              <div class="message-content" v-html="formatMessage(msg.content)"></div>
            </div>
          </div>
          <div class="chat-input">
            <textarea 
              v-model="chatMessage" 
              placeholder="描述您的需求或修改意见..."
              @keyup.enter.ctrl="sendChatMessage"
              rows="3"
            ></textarea>
            <button @click="sendChatMessage" :disabled="isGenerating">
              {{ isGenerating ? '处理中...' : '发送' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 流程图预览 -->
      <div v-if="activeDesignTab === 'diagram'" class="design-tab-content">
        <div class="diagram-view">
          <div v-if="designData.diagram" ref="mermaidContainer" class="mermaid-container"></div>
          <div v-else class="placeholder">流程图尚未生成，请先使用AI助手设计流程</div>
        </div>
      </div>

      <!-- 配置详情 -->
      <div v-if="activeDesignTab === 'config'" class="design-tab-content">
        <div class="json-config">
          <pre v-if="designData.config">{{ formatJson(designData.config) }}</pre>
          <div v-else class="placeholder">配置尚未生成，请先使用AI助手设计流程</div>
        </div>
      </div>

      <!-- 权限设置 -->
      <div v-if="activeDesignTab === 'permissions'" class="design-tab-content">
        <div v-if="designData.config">
          <WorkflowAuthManager 
            ref="workflowAuthManager"
            :workflowConfig="designData.config"
            :workflowId="editingId"
            :workflowName="designData.name"
            @config-updated="updateWorkflowConfig"
          />
        </div>
        <div v-else class="placeholder">
          权限设置需要先生成工作流配置，请先使用AI助手设计流程
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="action-buttons">
        <button v-if="activeDesignTab === 'basic'" @click="generateFlow" :disabled="isGenerating" class="primary-btn">
          {{ isGenerating ? '生成中...' : '生成流程' }}
        </button>
        <button v-if="designData.config" @click="saveWorkflow" class="save-btn">保存流程</button>
        <button @click="cancelDesign" class="cancel-btn">取消</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { message } from 'ant-design-vue';
import api from '../../../utils/api';
import emitter from '../../../utils/eventBus';
import WorkflowAuthManager from '../../../components/WorkflowAuthManager.vue';
import mermaid from 'mermaid';

// 添加Ollama API实例
const ollamaApi = axios.create({
  baseURL: 'http://localhost:11434/api',
  timeout: 30000,
});

export default {
  components: {
    WorkflowAuthManager
  },
  data() {
    return {
      isDesigning: false,
      isGenerating: false,
      isLoading: false,
      hasLoadError: false,
      errorMessage: '',
      isUsingMockData: false,
      workflows: [],
      activeDesignTab: 'basic',
      editingId: null,
      designTabs: [
        { key: 'basic', label: '基本信息' },
        { key: 'ai', label: 'AI设计助手' },
        { key: 'diagram', label: '流程图' },
        { key: 'config', label: '配置详情' },
        { key: 'permissions', label: '权限设置' }
      ],
      designData: {
        name: '',
        description: '',
        prompt: '',
        config: null,
        diagram: '',
      },
      chatHistory: [],
      chatMessage: '',
      approvalNodes: [],
      roles: [],
      currentUser: null,
      permissionConfigInitialized: false
    };
  },
  created() {
    // 在创建组件时预初始化一些安全的数据
    this.preInitWorkflows();
    
    // 初始化mermaid
    try {
      console.log('初始化Mermaid...');
    mermaid.initialize({
        startOnLoad: false,
        theme: 'neutral',
      securityLevel: 'loose',
        flowchart: { 
          curve: 'basis',
          useMaxWidth: false
        }
      });
      console.log('Mermaid库初始化成功');
    } catch (e) {
      console.error('Mermaid库初始化失败:', e);
    }
  },
  mounted() {
    console.log('工作流设计器组件已加载');
    
    try {
      // 清除旧的工作流数据，强制重新生成（确保时间更新生效）
      localStorage.removeItem('mock_workflows');
      localStorage.removeItem('using_mock_workflows');
      console.log('已清除旧的工作流数据，将重新生成');
      
      // 初始化用户信息
    this.initUserInfo();
      
      // 预加载工作流数据，避免页面闪烁
      this.preInitWorkflows();
      
      // 从API获取工作流数据
      this.isLoading = true;
      this.fetchWorkflows()
        .then(() => {
          console.log('工作流获取成功');
          this.isLoading = false;
        })
        .catch(error => {
          console.error('获取工作流失败:', error);
          this.isLoading = false;
          this.hasLoadError = true;
          
          // 如果获取失败，使用模拟数据
          this.useMockWorkflows();
        });
      
      // 加载角色数据
      this.fetchRoles()
        .catch(error => {
          console.error('获取角色数据失败:', error);
          // 使用默认角色数据
          this.roles = [
            { id: 1, name: '部门经理' },
            { id: 2, name: '财务专员' },
            { id: 3, name: '人事专员' },
            { id: 4, name: '总经理' }
          ];
        });
        
      // 监听工作流创建请求事件
      window.addEventListener('workflow-create-request', this.handleWorkflowCreateRequest);
      
      // 检查是否有存储的工作流设计数据
      this.checkStoredDesignData();
    } catch (error) {
      console.error('组件初始化失败:', error);
      this.hasLoadError = true;
      
      // 显示错误通知
      this.$notification.error({
        message: '初始化失败',
        description: '组件初始化过程中发生错误，部分功能可能无法正常工作',
        duration: 5
      });
    }
  },
  
  beforeUnmount() {
    // 移除事件监听
    window.removeEventListener('workflow-create-request', this.handleWorkflowCreateRequest);
  },

  methods: {
    // 检查localStorage是否可用
    checkLocalStorageAvailability() {
      try {
        // 尝试使用localStorage
        if (typeof window !== 'undefined' && window.localStorage) {
          // 测试写入和读取
          window.localStorage.setItem('__test__', '__test__');
          window.localStorage.removeItem('__test__');
          console.log('localStorage可用');
          
          // 检查是否使用模拟数据
          this.isUsingMockData = window.localStorage.getItem('using_mock_workflows') === 'true';
          
          return true;
        } else {
          console.warn('localStorage不可用');
          return false;
        }
      } catch (e) {
        console.error('localStorage测试失败:', e);
        return false;
      }
    },
    
    // 安全地保存数据到localStorage
    safeSetItem(key, value) {
      try {
        localStorage.setItem(key, value);
        return true;
      } catch (error) {
        console.error(`无法写入localStorage[${key}]:`, error);
        return false;
      }
    },
    
    // 安全地从localStorage读取数据
    safeGetItem(key) {
      try {
        return localStorage.getItem(key);
      } catch (error) {
        console.error(`无法从localStorage获取[${key}]:`, error);
        return null;
      }
    },
    
    // 安全地从localStorage删除数据
    safeRemoveItem(key) {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.removeItem(key);
          return true;
        }
      } catch (e) {
        console.error(`无法从localStorage删除数据(${key}):`, e);
      }
      return false;
    },
    formatDate(dateString) {
      // 确保dateString是有效日期
      if (!dateString) return '未知';
      
      try {
        // 尝试使用标准Date构造函数解析
        const date = new Date(dateString);
        
        // 检查日期是否有误
        if (isNaN(date.getTime())) {
          return '未知日期';
        }
        
        // 格式化日期，不依赖于toLocaleString（可能在某些环境不支持）
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day} ${hours}:${minutes}`;
      } catch (e) {
        console.error('日期格式化错误:', e, dateString);
        return '格式错误';
      }
    },
    formatJson(json) {
      return JSON.stringify(json, null, 2);
    },
    formatMessage(message) {
      return message.replace(/\n/g, '<br>');
    },
    changeDesignTab(tabKey) {
      // 切换标签前确保当前页面数据保存
      if (this.activeDesignTab === 'diagram' && tabKey !== 'diagram') {
        // 记录流程图数据
        console.log('保存流程图数据');
      }
      
      // 切换标签
      this.activeDesignTab = tabKey;
      
      // 切换后的处理
      if (tabKey === 'diagram' && this.designData.diagram) {
        this.$nextTick(() => {
          this.renderMermaid();
        });
      } else if (tabKey === 'permissions') {
        // 如果存在配置数据，才初始化权限设置
        if (this.designData.config && !this.permissionConfigInitialized) {
          console.log('初始化权限配置..');
          this.initializePermissionConfig();
        } else if (!this.designData.config) {
          console.log('无配置数据，跳过权限配置初始化');
        }
        
        // 确保有editingId，即使是新工作流
        if (!this.editingId && this.isDesigning) {
          this.editingId = 'new_workflow_' + Date.now();
          console.log('为新工作流分配临时ID:', this.editingId);
        }
      }
    },
    createNewWorkflow() {
      try {
        // 重置设计状态
      this.isDesigning = true;
      this.activeDesignTab = 'basic';
      this.editingId = null;
        this.permissionConfigInitialized = false;
        
        // 初始化设计数据 - 所有字段保持为空
      this.designData = {
        name: '',
        description: '',
        prompt: '',
        config: null,
        diagram: ''
      };
        
        // 清空聊天历史和节点信息
      this.chatHistory = [];
      this.approvalNodes = [];
        
        // 确保预初始化以防止空数据
        if (!this.workflows || this.workflows.length === 0) {
          this.preInitWorkflows();
        }
        
        console.log('成功创建新工作流');
      } catch (error) {
        console.error('创建新工作流时发生错误:', error);
        // 确保安全回退
        this.isDesigning = false;
        message.error('创建新工作流失败，请刷新页面重试');
      }
    },
    async fetchWorkflows() {
      try {
        this.isLoading = true;
        this.hasLoadError = false;
        this.errorMessage = '';
        
        console.log('开始加载工作流数据...');
        
        try {
          // 使用api工具的getWorkflows方法获取数据
          const data = await api.getWorkflows();
          
          if (Array.isArray(data) && data.length > 0) {
            // 检查本地删除的工作流ID
            const localWorkflows = this.safeGetItem('mock_workflows');
            let localDeletedIds = [];
            if (localWorkflows) {
              try {
                const parsed = JSON.parse(localWorkflows);
                if (Array.isArray(parsed)) {
                  const localIds = parsed.map(w => w.id);
                  // 找出在API数据中但不在本地数据中的工作流（即被本地删除的）
                  localDeletedIds = data.filter(w => !localIds.includes(w.id)).map(w => w.id);
                }
              } catch (e) {
                console.error('解析本地工作流数据失败:', e);
              }
            }
            
            // 过滤掉本地已删除的工作流
            let filteredData = data;
            if (localDeletedIds.length > 0) {
              filteredData = data.filter(w => !localDeletedIds.includes(w.id));
              console.log('过滤掉本地已删除的工作流:', localDeletedIds);
            }
            
            // 按创建时间排序，时间早的在前面
            this.workflows = filteredData.sort((a, b) => {
              const timeA = new Date(a.created_at || 0).getTime();
              const timeB = new Date(b.created_at || 0).getTime();
              return timeA - timeB;
            });
            this.isUsingMockData = false;
            console.log('成功加载工作流数据并排序');
            
            // 移除使用模拟数据的标志
            this.safeRemoveItem('using_mock_workflows');
          } else {
            console.warn('API返回的数据格式不正确或为空');
            // 使用备选数据
            this.useMockWorkflows();
          }
        } catch (error) {
          console.warn('从API获取工作流失败:', error);
          this.errorMessage = '无法从服务器获取数据，将使用本地数据';
          
          // 使用备选数据
          this.useMockWorkflows();
        }
      } catch (e) {
        console.error('获取工作流过程中发生异常:', e);
        this.hasLoadError = true;
        this.errorMessage = '加载失败，请稍后再试';
        
        // 确保页面有数据可显示
        if (this.workflows.length === 0 || (this.workflows.length === 1 && this.workflows[0].id === 0)) {
          this.useDefaultWorkflows();
        }
      } finally {
        this.isLoading = false;
      }
    },
    async fetchRoles() {
      try {
        const token = this.safeGetItem('token') || this.safeGetItem('access_token');
        
        // 检查是否为模拟token，直接返回模拟数据
        if (token === 'mock_admin_token' || token === 'mock_user_token' || token === 'mock_manager_token') {
          this.roles = [
            { id: 1, name: '部门经理' },
            { id: 2, name: '财务专员' },
            { id: 3, name: '人事专员' },
            { id: 4, name: '总经理' }
          ];
          return;
        }
        
        // 对于真实token，进行API调用
        const response = await api.get('/admin/roles');
        this.roles = response.data || [];
      } catch (error) {
        console.error('获取角色列表失败:', error);
        // 提供一些默认角色
        this.roles = [
          { id: 1, name: '部门经理' },
          { id: 2, name: '财务主管' },
          { id: 3, name: '总经理' },
          { id: 4, name: '人事专员' },
          { id: 5, name: '普通员工' }
        ];
      }
    },
    async editWorkflow(workflow) {
      try {
        this.isDesigning = true;
        this.editingId = workflow.id;
        
        console.log('开始编辑工作流:', workflow);
        
        // 深拷贝工作流数据，避免直接修改表格中的内容
        const workflowCopy = JSON.parse(JSON.stringify(workflow));
        
        // 检查配置数据是否存在
        let configData = null;
        if (workflowCopy.workflow_config) {
          configData = workflowCopy.workflow_config;
        } else if (typeof workflowCopy.config === 'object' && workflowCopy.config !== null) {
          configData = workflowCopy.config;
        }
        
        // 确保必要字段存在
        this.designData = {
          name: workflowCopy.name || '未命名工作流',
          description: workflowCopy.description || '',
          prompt: workflowCopy.design_prompt || '',
          // 使用找到的配置或保持为空
          config: configData,
          // 确保图表存在或为空
          diagram: workflowCopy.diagram || ''
        };
        
        console.log('初始化设计数据成功:', this.designData);
      
        // 如果有配置数据才初始化权限和节点
        if (this.designData.config) {
          this.initializePermissionConfig();
          this.approvalNodes = this.extractNodesFromConfig();
        } else {
          this.approvalNodes = [];
          this.permissionConfigInitialized = false;
        }
        
        this.chatHistory = [];
        this.activeDesignTab = 'basic';
        
        this.$nextTick(() => {
          if (this.designData.diagram) {
            // 延迟渲染，确保mermaid库已加载
            setTimeout(() => {
              this.renderMermaid();
            }, 500);
          }
        });
      } catch (error) {
        console.error('编辑工作流时发生错误:', error);
        message.error('编辑工作流失败，请稍后重试');
        this.isDesigning = false;
      }
    },
    extractNodesFromConfig() {
      // 从工作流配置中提取节点信息      if (!this.designData.config) return [];
      
      const nodes = [];
      try {
        const config = typeof this.designData.config === 'string' 
          ? JSON.parse(this.designData.config) 
          : this.designData.config;
          
        if (config.states) {
          Object.entries(config.states).forEach(([key, state]) => {
            if (state.type !== 'end') {
              nodes.push({
                name: state.role || key,
                role: '',
                minPositionLevel: '',
                minDeptLevel: ''
              });
            }
          });
        }
      } catch (e) {
        console.error('解析节点失败:', e);
      }
      
      return nodes;
    },
    async generateFlow() {
      // 记录方法开始
      console.log('开始生成流程');
      
      // 禁止重复生成
      if (this.isGenerating) return;
      
      // 检查名称是否填写
      if (!this.designData.name || this.designData.name.trim() === '') {
        message.error('请填写流程名称');
        return;
      }
      
      // 检查提示词是否填写
      if (!this.designData.prompt || this.designData.prompt.trim() === '') {
        message.error('请填写设计提示或描述');
        return;
      }
      
      // 重置状态
      this.isGenerating = true;
      
      // 检查令牌信息
      let isMockToken = false;
      try {
        // 获取token，判断是否是模拟token
        const token = this.safeGetItem('token') || this.safeGetItem('access_token');
        isMockToken = token && (token.includes('mock_admin_token') || token.includes('mock_user_token') || token.includes('mock_manager_token'));
      } catch (tokenError) {
        console.error('获取token失败:', tokenError);
      }

      // 解析流程图和配置的函数 - 增强以更健壮地处理各种格式
      const parseGeneratedContent = (content) => {
        try {
          console.log('解析AI生成的内容...');
          
          // 增强对空内容的处理
          if (!content || typeof content !== 'string' || content.trim() === '') {
            console.error('AI返回的内容为空或格式无效');
            message.warning('AI模型返回空内容，无法生成流程');
            return { config: null, diagram: null };
          }
          
          // 尝试提取JSON配置，查找各种可能的格式标记
          const configMatches = [
            // 查找```json和```之间的内容
            content.match(/```json\s*(\{[\s\S]*?\})\s*```/),
            // 查找`json和`之间的内容
            content.match(/`json\s*(\{[\s\S]*?\})\s*`/),
            // 查找JSON:和###之间的内容
            content.match(/JSON:\s*(\{[\s\S]*?\})\s*###/),
            // 查找{和}之间最大的内容（可能是JSON)
            content.match(/(\{[\s\S]*\})/),
          ];
          
          // 尝试找到第一个有效的JSON匹配
          let configJson = null;
          for (const match of configMatches) {
            if (match && match[1]) {
              try {
                // 尝试解析JSON
                configJson = JSON.parse(match[1]);
                console.log('成功解析出配置JSON');
                break;
              } catch (e) {
                // 继续尝试下一个匹配
                console.warn('JSON解析失败，尝试下一个匹配', e.message);
              }
            }
          }
          
          // 尝试提取流程图，查找各种可能的Mermaid标记
          const diagramMatches = [
            // 查找```mermaid和```之间的内容
            content.match(/```mermaid\s*(graph[\s\S]*?)```/),
            // 查找```和```之间包含graph的内容
            content.match(/```\s*(graph[\s\S]*?)```/),
            // 查找`mermaid和`之间的内容
            content.match(/`mermaid\s*(graph[\s\S]*?)`/),
            // 查找以graph开头的行到下一个代码块或文本块结束
            content.match(/(graph[^\n]*[\s\S]*?)(?=```|$)/),
          ];
          
          // 尝试找到第一个有效的流程图匹配
          let diagramCode = null;
          for (const match of diagramMatches) {
            if (match && match[1]) {
              // 验证是否是有效的流程图代码，至少包含节点和连接
              const code = match[1].trim();
              if (code.includes('-->') && (code.includes('[') || code.includes('(') || code.includes('{'))) {
                diagramCode = code;
                console.log('成功提取出流程图代码');
                break;
              }
            }
          }
          
          // 如果找到了流程图，验证并修复
          if (diagramCode) {
            diagramCode = this.validateAndFixDiagram(diagramCode);
          }
          
          return { config: configJson, diagram: diagramCode };
        } catch (parseError) {
          console.error('解析生成内容失败:', parseError);
          return { config: null, diagram: null };
        }
      };

      try {
        // 尝试使用本地Ollama模型
        try {
          console.log('尝试使用本地Ollama模型生成...');
          const prompt = `
你是一个专业的工作流设计助手。请根据用户的描述，设计一个审批流程。
用户需求: ${this.designData.prompt}

请提供:
1. 一个Mermaid流程图，使用graph TD语法
2. 完整的JSON工作流配置，包含initiator、各个审批节点和结束节点

注意:
- 流程图必须使用正确的Mermaid语法，不要使用不支持的语法如"end"作为节点
- 审批节点应当明确指定角色和可能的状态转换
- JSON配置应包含完整的状态定义(states对象)和元数据(process_meta对象)

请按以下格式输出:
\`\`\`mermaid
graph TD
A[开始节点] -->|操作| B(处理节点)
...其余流程图代码
\`\`\`

\`\`\`json
{
  "process_meta": {...},
  "states": {...}
}
\`\`\`
`;

          // 调用本地Ollama API
          const ollamaResponse = await ollamaApi.post('/generate', {
            model: 'deepseek-r1:7b',
            prompt: prompt,
            stream: false
          });
          
          // 处理响应
          if (ollamaResponse && ollamaResponse.data && ollamaResponse.data.response) {
            console.log('Ollama返回了响应');
            const response = ollamaResponse.data.response;
            
            // 解析响应内容，提取配置和流程图
            const { config: generatedConfig, diagram: generatedDiagram } = parseGeneratedContent(response);
            
            // 如果成功解析出配置
            if (generatedConfig) {
              this.designData.config = generatedConfig;
              
              // 如果也有流程图，则更新
              if (generatedDiagram) {
                this.designData.diagram = generatedDiagram;
              } else {
                this.designData.diagram = this.generateDefaultDiagram();
              }
              
              // *** 强制同步权限配置 ***
              this.initializePermissionConfig(); 
              
              this.chatHistory = [
                { role: 'user', content: this.designData.prompt },
                { role: 'assistant', content: response }
              ];
              
              this.approvalNodes = this.extractNodesFromConfig();
              this.activeDesignTab = 'diagram';
              
              // 渲染流程图
              this.$nextTick(() => {
                this.renderMermaid();
              });
              
              // 滚动到底部
              if (this.$refs.chatHistory) {
                this.$refs.chatHistory.scrollTop = this.$refs.chatHistory.scrollHeight;
              }
              
              message.success('流程设计生成成功（本地模型）');
              return; // 处理完成，退出
            }
          }
        } catch (ollamaError) {
          console.error('使用Ollama生成失败:', ollamaError);
          
          // 检查是否是404错误（表示模型或服务不可用）
          if (ollamaError.response && ollamaError.response.status === 404) {
            console.error('Ollama API返回404错误，模型可能不可用');
            
            // 在聊天历史中添加错误消息
            this.chatHistory.pop(); // 移除"正在生成"消息
            this.chatHistory.push({ 
              role: 'assistant', 
              content: '无法连接到AI模型服务 (404错误)。请确保:\n' + 
                       '1. 您已安装Ollama\n' + 
                       '2. Ollama服务正在运行\n' + 
                       '3. 已安装deepseek-r1:7b模型\n\n' +
                       '系统将使用模拟数据生成流程。'
            });
            
            // 显示错误通知
            message.error('无法连接到AI模型，将使用模拟数据');
            
            // 使用模拟数据继续
            throw new Error('Ollama服务不可用');
          } else if (ollamaError.message && ollamaError.message.includes('Network Error')) {
            // 处理网络连接错误
            console.error('无法连接到Ollama服务');
            
            this.chatHistory.pop(); // 移除"正在生成"消息
            this.chatHistory.push({ 
              role: 'assistant', 
              content: '无法连接到AI模型服务。请确保Ollama服务正在运行。系统将使用模拟数据生成流程。'
            });
            
            message.error('无法连接到Ollama服务，将使用模拟数据');
            throw new Error('无法连接到Ollama服务');
          } else {
            // 其他错误
            console.error('Ollama API调用失败:', ollamaError);
            
            this.chatHistory.pop(); // 移除"正在生成"消息
            this.chatHistory.push({ 
              role: 'assistant', 
              content: `使用AI模型生成流程时出错: ${ollamaError.message || '未知错误'}。系统将使用模拟数据继续。`
            });
            
            message.error('AI模型调用失败，将使用模拟数据');
          }
        }
        
        // 如果前面的逻辑没有return，说明AI生成失败，使用模拟数据
        console.log('尝试使用模拟数据...');
        
        // 对模拟token用户直接使用模拟数据处理
        if (isMockToken) {
          console.log('模拟环境，使用模拟数据');
          this.generateMockFlow(); // 此方法内部已包含 initializePermissionConfig 调用
          message.success('流程设计生成成功（模拟数据）');
          return;
        }
        
        // 使用后端API
        try {
          console.log('尝试使用后端API生成...');
          // 构建API参数
          const payload = {
            name: this.designData.name,
            description: this.designData.description,
            design_prompt: this.designData.prompt
          };
          
          // 调用后端API
          const response = await api.post('/api/workflows/design', payload);
          
          if (response.data) {
            console.log('API返回成功:', response.data);
            this.designData.config = response.data.workflow_config;
            this.designData.diagram = response.data.diagram;
            
            // 验证并修复流程图
            if (this.designData.diagram) {
              this.designData.diagram = this.validateAndFixDiagram(this.designData.diagram);
            }
            
            // *** 强制同步权限配置 ***
            this.initializePermissionConfig();
            
            this.chatHistory = [
              { role: 'user', content: this.designData.prompt },
              { role: 'assistant', content: '已根据您的描述生成工作流。您可以查看流程图和配置，如需调整，请告诉我您的要求。' }
            ];
            
            this.approvalNodes = this.extractNodesFromConfig();
            this.activeDesignTab = 'diagram';
            
            // 渲染流程图
            this.$nextTick(() => {
              this.renderMermaid();
            });
            
            message.success('流程设计生成成功');
          } else {
            throw new Error('API返回了空数据');
          }
        } catch (apiError) {
          console.error('API调用失败:', apiError);
          // 回退到模拟数据
          this.generateMockFlow(); // 此方法内部已包含 initializePermissionConfig 调用
          message.success('流程设计生成成功（模拟数据）');
        }
      } catch (error) {
        console.error('生成流程图失败', error);
        message.error('生成流程图失败: ' + error.message);
        // 使用默认模拟数据
        this.generateMockFlow(); // 此方法内部已包含 initializePermissionConfig 调用
      } finally {
        this.isGenerating = false;
      }
    },
    async sendChatMessage() {
      if (!this.chatMessage.trim()) return;
      
      if (this.isGenerating) {
        message.warning('正在处理中，请稍候...');
        return;
      }
      
      this.isGenerating = true;
      
      // 添加用户消息到聊天历史
      this.chatHistory.push({ 
        role: 'user', 
        content: this.chatMessage 
      });
      
      // 重置输入框
      const userMessage = this.chatMessage;
      this.chatMessage = '';
      
      // 滚动到底部
      this.$nextTick(() => {
        if (this.$refs.chatHistory) {
          this.$refs.chatHistory.scrollTop = this.$refs.chatHistory.scrollHeight;
        }
      });
      
      try {
        // 检查token类型
        const token = this.safeGetItem('token') || this.safeGetItem('access_token');
        const isMockToken = token && (
          token.includes('mock_admin_token') || 
          token.includes('mock_user_token') || 
          token.includes('mock_manager_token')
        );
        
        // 首先尝试使用本地Ollama模型
        if (this.designData.config) {
          try {
            console.log('尝试使用本地Ollama模型优化工作流...');
            
            // 构建提示信息
            const prompt = `
我需要你帮忙优化一个审批流程。当前流程存在一些问题需要根据用户的要求进行调整。
用户的要求是: "${userMessage}"

当前工作流配置和图表数据如下:

工作流配置:
\`\`\`json
${JSON.stringify(this.designData.config, null, 2)}
\`\`\`

流程图:
\`\`\`mermaid
${this.designData.diagram}
\`\`\`

请根据用户的要求，优化工作流配置和流程图。特别注意：
1. 流程图必须使用正确的Mermaid语法
2. 节点ID不能重复，例如不要出现"A[文本]A[其他文本]"这样的结构
3. 不要使用"end"作为节点ID，请使用"E"或其他字母
4. 流程图格式应该是"graph TD"开头
`;
            
            console.log('发送请求到Ollama...');
            const ollamaResponse = await ollamaApi.post('/generate', {
              model: 'deepseek-r1:7b',
              prompt: prompt,
              stream: false
            });
            
            if (ollamaResponse && ollamaResponse.data && ollamaResponse.data.response) {
              const response = ollamaResponse.data.response;
              console.log('收到Ollama响应，处理中...');
              
              // 解析响应中的JSON和Mermaid部分
              let updatedConfig = null;
              let updatedDiagram = null;
              
              // 尝试提取JSON配置
              const configMatch = response.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
              
              if (configMatch && configMatch[1]) {
                try {
                  const jsonText = configMatch[1].trim();
                  updatedConfig = JSON.parse(jsonText);
                  console.log('成功提取到更新后的工作流配置');
                } catch (e) {
                  console.error('解析工作流配置JSON失败:', e);
                }
              }
              
              // 尝试提取Mermaid部分
              const diagramMatch = response.match(/```(?:mermaid)?\s*(graph[\s\S]*?)```/);
              
              if (diagramMatch && diagramMatch[1]) {
                updatedDiagram = diagramMatch[1].trim();
                console.log('成功提取到更新后的流程图');
                
                // 修复常见的流程图语法问题
                if (updatedDiagram) {
                  // 修复1: 替换 --> end --> E[结束]
                  updatedDiagram = updatedDiagram.replace(/-->\s*end/g, '--> E[结束]');
                  
                  // 修复2: 检查并修复重复节点ID定义 (A[text]A[text])
                  const potentialDuplicates = updatedDiagram.match(/([A-Za-z0-9]+)\[[^\]]+\]\s*\1\[[^\]]+\]/g);
                  if (potentialDuplicates) {
                    for (const duplicate of potentialDuplicates) {
                      // 提取第一个节点ID
                      const nodeId = duplicate.match(/^([A-Za-z0-9]+)/)[1];
                      // 用正则替换第二个节点ID，生成新的唯一ID
                      const fixed = duplicate.replace(
                        new RegExp(`(${nodeId}\\[[^\\]]+\\])\\s*${nodeId}`), 
                        `$1 ${nodeId}2`
                      );
                      updatedDiagram = updatedDiagram.replace(duplicate, fixed);
                    }
                  }
                  
                  // 修复3: 确保以 graph TD 开始
                  if (!updatedDiagram.trim().startsWith('graph')) {
                    updatedDiagram = 'graph TD\n' + updatedDiagram;
                  }
                  
                  console.log('修复后的流程图', updatedDiagram);
                }
              }
              
              if (updatedConfig) {
                this.designData.config = updatedConfig;
              }
              
              if (updatedDiagram) {
                this.designData.diagram = updatedDiagram;
              }
              
              // *** 强制同步权限配置 ***
              if (updatedConfig || updatedDiagram) {
                this.initializePermissionConfig(); 
              }

              this.chatHistory.push({ 
                role: 'assistant', 
                content: response
              });
              
              this.approvalNodes = this.extractNodesFromConfig();
              
              // 如果有流程图更新，切换到流程图标签页
              if (updatedDiagram) {
                this.activeDesignTab = 'diagram';
              this.$nextTick(() => {
                  this.renderMermaid();
                });
                }
                
                // 滚动到底部
              this.$nextTick(() => {
                if (this.$refs.chatHistory) {
                  this.$refs.chatHistory.scrollTop = this.$refs.chatHistory.scrollHeight;
                }
              });
              
              return; // 处理完成，退出
            }
          } catch (ollamaError) {
            console.error('Ollama API调用失败:', ollamaError);
            // 继续使用其他方法
          }
        }
        
        // 对模拟token用户直接使用模拟数据处理
        if (isMockToken) {
          console.log('模拟环境，使用模拟数据优化');
          setTimeout(() => {
            const aiResponse = '根据您的要求，我已优化了流程设计。主要更新了审批流程，使其更加清晰和合理。';
            
            this.chatHistory.push({ 
              role: 'assistant', 
              content: aiResponse
            });
            
            // 简单修改流程图以示变化
            if (this.designData.diagram) {
              // 对流程图进行语法修复
              let updatedDiagram = this.designData.diagram;
              
              // 修复1: 替换 --> end --> E[结束]
              updatedDiagram = updatedDiagram.replace(/-->\s*end/g, '--> E[结束]');
                  
              // 修复2: 检查并修复重复节点ID定义
              const nodePattern = /([A-Za-z][A-Za-z0-9]*)\[[^\]]+\]/g;
              const matches = [...updatedDiagram.matchAll(nodePattern)];
              const nodeIds = matches.map(m => m[1]);
              
              // 检查每一行，查找可能的重复定义
              const lines = updatedDiagram.split('\n');
              for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                const lineMatches = [...line.matchAll(nodePattern)];
                const lineNodeIds = lineMatches.map(m => m[1]);
                
                // 检查这一行中是否有重复的ID
                const uniqueIds = new Set(lineNodeIds);
                if (uniqueIds.size < lineNodeIds.length) {
                  // 有重复，需要修复
                  const idCounts = {};
                  let fixedLine = line;
                  
                  lineNodeIds.forEach(id => {
                    idCounts[id] = (idCounts[id] || 0) + 1;
                    if (idCounts[id] > 1) {
                      // 替换第N次出现的节点ID
                      const pattern = new RegExp(`((?:^|[^A-Za-z0-9])${id}\\[[^\\]]+\\])(?!.*\\1)`, '');
                      const newId = `${id}${idCounts[id]}`;
                      fixedLine = fixedLine.replace(pattern, (match, p1) => {
                        return match.replace(id, newId);
                      });
                    }
                  });
                  
                  lines[i] = fixedLine;
                }
              }
              
              updatedDiagram = lines.join('\n');
              
              // 修复3: 确保以 graph TD 开始
              if (!updatedDiagram.trim().startsWith('graph')) {
                updatedDiagram = 'graph TD\n' + updatedDiagram;
              }
              
              this.designData.diagram = updatedDiagram;
              
              // 更新图表
              this.$nextTick(() => {
                this.renderMermaid();
              });
            }
            
            message.success('流程已根据要求优化');
          }, 1500);
          return;
        }
        
        // 使用后端API
        const response = await api.post('/api/workflows/optimize', {
          workflow_id: this.editingId,
          current_config: this.designData.config,
          current_diagram: this.designData.diagram,
          user_message: userMessage
        });
        
        // 检查响应格式，更新配置和流程图
        if (response.data) {
          if (response.data.workflow_config) {
        this.designData.config = response.data.workflow_config;
          }
          
          if (response.data.diagram) {
            // 修复流程图可能的语法问题
            let diagram = response.data.diagram;
            
            // 修复1: 替换 --> end --> E[结束]
            diagram = diagram.replace(/-->\s*end/g, '--> E[结束]');
            
            // 修复2: 修复重复节点ID定义
            const lines = diagram.split('\n');
            const nodeIds = new Set();
            const idReplacements = {};
            
            for (let i = 0; i < lines.length; i++) {
              const line = lines[i];
              // 匹配所有节点定义如 A[文本] B(文本)
              const matches = line.match(/([A-Za-z0-9_]+)(?:\[|\(|\{)([^\]\)\}]*)(?:\]|\)|\})/g) || [];
              
              for (const match of matches) {
                const idMatch = match.match(/^([A-Za-z0-9_]+)/);
                if (idMatch) {
                  const id = idMatch[1];
                  
                  // 处理重复ID
                  if (id === 'end') {
                    // 替换end关键字
                    lines[i] = lines[i].replace(match, match.replace('end', 'E'));
                    continue;
                  }
                  
                  // 在同一行内检查重复ID
                  const regex = new RegExp(`${id}(?:\\[|\\(|\\{)`, 'g');
                  const count = (line.match(regex) || []).length;
                  
                  if (count > 1) {
                    // 找到第二次及以后出现的ID并替换
                    let tempLine = line;
                    let replacementCount = 0;
                    
                    tempLine = tempLine.replace(regex, function(matched) {
                      replacementCount++;
                      if (replacementCount === 1) {
                        return matched; // 保留第一次出现的
                      } else {
                        // 生成新ID
                        const newId = `${id}${replacementCount}`;
                        return matched.replace(id, newId);
                      }
                    });
                    
                    lines[i] = tempLine;
                  }
                }
              }
            }
            
            diagram = lines.join('\n');
            
            // 修复3: 确保以 graph TD 开始
            if (!diagram.trim().startsWith('graph')) {
              diagram = 'graph TD\n' + diagram;
            }
            
            this.designData.diagram = diagram;
          }
          
          // *** 强制同步权限配置 ***
        this.initializePermissionConfig();
        
        this.chatHistory.push({ 
          role: 'assistant', 
          content: '已根据您的要求调整工作流。您可以在流程图和配置中查看更新后的内容。' 
        });
        
        this.approvalNodes = this.extractNodesFromConfig();
        
        // 渲染流程图
        this.$nextTick(() => {
            this.renderMermaid();
          });
          
          message.success('流程已根据要求优化');
          }
      } catch (error) {
        console.error('发送消息失败:', error);
        this.chatHistory.push({ 
          role: 'assistant', 
          content: '很抱歉，处理您的请求时出现了问题' + (error.message || '未知错误') 
        });
        
        message.error('处理请求失败: ' + (error.message || '未知错误'));
      } finally {
        this.isGenerating = false;
      }
    },
    async saveWorkflow() {
      try {
        if (!this.designData.name) {
          message.error('请填写流程名称');
          return;
        }
        
        // 对于新建流程，如果没有配置数据，提示用户先生成
        if (!this.designData.config) {
          message.error('请先生成流程配置');
          return;
        }
        
        console.log('保存工作流:', this.editingId ? '编辑' : '新增', this.designData.name);

        // 确保权限设置已更新到配置中
        if (this.activeDesignTab === 'permissions') {
          // 触发权限组件的更新
          this.$nextTick(() => {
            const authComponent = this.$refs.workflowAuthManager;
            if (authComponent && typeof authComponent.savePermissions === 'function') {
              authComponent.savePermissions();
            }
          });
        }

        // 确保流程图被保存
        if (this.activeDesignTab === 'diagram' && this.$refs.mermaidEditor) {
          const diagramContent = this.$refs.mermaidEditor.value;
          if (diagramContent && diagramContent !== this.designData.diagram) {
            this.designData.diagram = diagramContent;
            console.log('已更新流程图');
          }
        }

        // 获取token信息，判断是否使用真实API
        const token = this.safeGetItem('token') || this.safeGetItem('access_token');
        const isMockToken = token && (
          token.includes('mock_admin_token') || 
          token.includes('mock_user_token') || 
          token.includes('mock_manager_token')
        );
        
        // 准备发送到后端的数据
        const workflowData = {
          name: this.designData.name,
          description: this.designData.description,
          design_prompt: this.designData.prompt,
          workflow_config: this.designData.config,
          diagram: this.designData.diagram
        };
        
        // 确保使用localStorage进行保存
        let useLocalStorage = true;
        
        try {
          if (!isMockToken && process.env.NODE_ENV === 'production') {
            // 构建API请求路径和方法
            const endpoint = this.editingId ? 
          `/api/workflows/${this.editingId}` :
          '/api/workflows';
            
            const method = this.editingId ? 'put' : 'post';
            
            console.log(`尝试调用API: ${method.toUpperCase()} ${endpoint}`);
            
            // 发送API请求
            const response = await api[method](endpoint, workflowData);
            
            if (response && response.data) {
              console.log('API请求成功:', response.data);
              
              // 使用API返回的数据更新本地数据
              if (this.editingId) {
                // 更新已有工作流
                const index = this.workflows.findIndex(w => w.id == this.editingId);
                if (index !== -1) {
                  this.workflows[index] = {
                    ...this.workflows[index],
                    ...response.data,
                    updated_at: new Date().toISOString()
                  };
                }
              } else {
                // 添加新工作流
                this.workflows.push(response.data);
                // 更新编辑ID为新创建的工作流ID
                this.editingId = response.data.id;
              }
              
              message.success('工作流已成功保存到数据库');
              this.isUsingMockData = false;
              useLocalStorage = false;
              
              // 仍然保存到localStorage作为备份
              this.safeSetItem('mock_workflows', JSON.stringify(this.workflows));
            } else {
              throw new Error('API响应格式不正确');
            }
          }
        } catch (apiError) {
          console.error('API请求失败:', apiError);
          
          if (!isMockToken && process.env.NODE_ENV === 'production') {
            // 生产环境非模拟用户，显示错误
            message.error('保存到数据库失败: ' + (apiError.response?.data?.message || '请检查网络连接'));
            return;
          }
          
          // 开发环境或模拟用户，使用localStorage
          message.warning('保存到数据库失败，将使用本地存储');
          useLocalStorage = true;
        }
        
        // 如果需要使用localStorage进行存储
        if (useLocalStorage) {
          // 保存到localStorage
          if (!this.editingId) {
            // 为新工作流生成ID，确保ID递增
            const newId = this.workflows.length > 0 ? 
              Math.max(...this.workflows.map(w => parseInt(w.id || 0))) + 1 : 1;
            
            console.log('为新工作流生成ID:', newId);
            
            // 创建新工作流对象，使用当前时间确保时间递增
            const now = new Date().toISOString();
            const newWorkflow = {
              id: newId,
              name: this.designData.name,
              description: this.designData.description,
              workflow_config: this.designData.config,
              diagram: this.designData.diagram,
              design_prompt: this.designData.prompt,
              created_at: now,
              updated_at: now
            };
            
            // 添加到数组并重新排序
            this.workflows.push(newWorkflow);
            // 按创建时间排序，确保时间早的在前面
            this.workflows.sort((a, b) => {
              const timeA = new Date(a.created_at || 0).getTime();
              const timeB = new Date(b.created_at || 0).getTime();
              return timeA - timeB;
            });
            console.log('新增工作流成功:', newId, newWorkflow.name);
            
            // 清除删除标志，因为现在有工作流了
            localStorage.removeItem('workflows_deleted');
          } else {
            // 更新已有工作流
            const index = this.workflows.findIndex(w => w.id == this.editingId);
            if (index !== -1) {
              this.workflows[index].name = this.designData.name;
              this.workflows[index].description = this.designData.description;
              this.workflows[index].workflow_config = this.designData.config;
              this.workflows[index].diagram = this.designData.diagram;
              this.workflows[index].design_prompt = this.designData.prompt;
              this.workflows[index].updated_at = new Date().toISOString();
            
              console.log('更新工作流成功:', this.editingId, this.workflows[index].name);
            } else {
              console.warn('未找到要更新的工作流:', this.editingId);
              
              // 如果找不到工作流，可能是ID问题，作为新工作流保存
              const newId = this.workflows.length > 0 ? 
                Math.max(...this.workflows.map(w => parseInt(w.id || 0))) + 1 : 1;
                
              this.workflows.push({
                id: newId,
                name: this.designData.name,
                description: this.designData.description,
                workflow_config: this.designData.config,
                diagram: this.designData.diagram,
                design_prompt: this.designData.prompt,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
              });
              
              console.log('找不到原工作流，作为新工作流保存:', newId);
            }
          }
          
          // 保存到localStorage
          this.safeSetItem('mock_workflows', JSON.stringify(this.workflows));
          this.isUsingMockData = true;
          this.safeSetItem('using_mock_workflows', 'true');
          
          message.success('工作流已保存到本地存储');
        }
            
        // 触发工作流更新事件，通知其他组件
        try {
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('workflow-updated'));
          }
          
          if (typeof emitter !== 'undefined' && emitter) {
            emitter.emit('workflow-updated', { 
              action: this.editingId ? 'update' : 'create', 
              workflows: this.workflows 
            });
          }
        } catch (error) {
          console.error('触发工作流更新事件失败:', error);
        }
            
        // 完成保存，退出设计模式
        this.isDesigning = false;
      } catch (error) {
        console.error('保存流程失败:', error);
        message.error('保存流程失败: ' + (error.message || '请稍后重试'));
      }
    },
    async deleteWorkflow(workflow) {
      try {
        // 确认删除操作
        if (!window.confirm('确定要删除此工作流吗？此操作不可撤销')) {
          return;
        }
        
        console.log('删除工作流:', workflow.id);
        
        // 从流程列表中移除
        this.workflows = this.workflows.filter(w => w.id != workflow.id);
        
        // 确保删除操作持久化到所有可能的存储位置
        try {
          // 保存到localStorage以便持久化
          this.safeSetItem('mock_workflows', JSON.stringify(this.workflows));
          
          // 同时更新其他可能的存储键
          const storageKeys = ['workflows', 'saved_workflows', 'local_workflows'];
          for (const key of storageKeys) {
            try {
              const stored = localStorage.getItem(key);
              if (stored) {
                const parsed = JSON.parse(stored);
                if (Array.isArray(parsed)) {
                  const filtered = parsed.filter(w => w.id != workflow.id);
                  localStorage.setItem(key, JSON.stringify(filtered));
                  console.log(`已从${key}中删除工作流ID=${workflow.id}`);
                }
              }
            } catch (e) {
              console.error(`处理存储键${key}失败:`, e);
            }
          }
          
          // 调用storage.js中的deleteWorkflow方法
          if (window.storage && typeof window.storage.deleteWorkflow === 'function') {
            window.storage.deleteWorkflow(workflow.id);
            console.log('已调用storage.deleteWorkflow');
          }
          
          console.log(`工作流删除完成，当前列表长度: ${this.workflows.length}`);
        } catch (error) {
          console.error('持久化删除操作失败:', error);
        }
        
        // 触发工作流更新事件，通知其他组件
        try {
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('workflow-updated'));
          }
          
          if (typeof emitter !== 'undefined' && emitter) {
            emitter.emit('workflow-updated', { action: 'delete', workflows: this.workflows });
          }
        } catch (error) {
          console.error('触发工作流更新事件失败:', error);
        }
        
        // 如果删除后没有工作流了，设置标志防止重新生成默认数据
        if (this.workflows.length === 0) {
          this.safeSetItem('workflows_deleted', 'true');
          console.log('所有工作流已删除，设置删除标志');
        }
        
        message.success('工作流删除成功');
        
        // 尝试调用后端API删除工作流
        try {
          // 获取token，判断是否是模拟token
          const token = this.safeGetItem('token') || this.safeGetItem('access_token');
          const isMockToken = token && (token.includes('mock_admin_token') || token.includes('mock_user_token') || token.includes('mock_manager_token'));
          
          if (!isMockToken && process.env.NODE_ENV === 'production') {
            // 生产环境且非模拟用户，调用真实API
            console.log('调用后端API删除工作流:', workflow.id);
            await api.deleteWorkflow(workflow.id);
            console.log('后端API删除成功');
          } else {
            // 开发环境或模拟用户，使用本地删除
            console.log('开发环境或模拟用户，使用本地删除');
          }
        } catch (apiError) {
          console.error('后端API删除失败:', apiError);
          // API删除失败时，仍然继续本地删除
        }
      } catch (error) {
        console.error('删除工作流失败:', error);
        message.error('删除工作流失败，请稍后重试');
      }
    },
    renderMermaid() {
      console.log('开始渲染流程图');
      
      // 防御性检查 - 确保designData.diagram存在
      if (!this.designData || !this.designData.diagram) {
        console.warn('没有图表数据，无法渲染');
        const element = this.$refs.mermaidContainer;
        if (element) {
          element.innerHTML = '<div class="placeholder">没有流程图数据</div>';
        }
        return;
      }
      
      // 验证并修复图表语法
      this.designData.diagram = this.validateAndFixDiagram(this.designData.diagram);
      const diagramToRender = this.designData.diagram; // 使用本地变量，避免异步问题
      
      // 添加日志记录图表内容
      console.log('准备渲染的Mermaid图表代码:\n', diagramToRender);
      
      const element = this.$refs.mermaidContainer;
      if (!element) {
        console.warn('找不到mermaid容器元素');
        return;
      }
      
      try {
        element.innerHTML = ''; // 清空容器
        
        // 使用mermaid.render异步渲染
        const id = 'mermaid-diagram-' + Date.now();
        // 先添加一个占位符，避免mermaid直接操作空DOM
        element.innerHTML = `<div id="${id}"></div>`; 
        
        mermaid.render(id, diagramToRender)
          .then(result => {
            console.log('Mermaid渲染成功');
            // 渲染成功后替换占位符内容
            const targetElement = document.getElementById(id);
            if (targetElement) {
              targetElement.innerHTML = result.svg;
            } else {
              // 备用方案：直接设置外部容器
              element.innerHTML = result.svg;
            }
            // 移除可能存在的错误样式
            element.classList.remove('mermaid-error-container'); 
          })
          .catch(err => {
            console.error('Mermaid渲染流程图失败:', err);
            console.error('失败的图表代码:\n', diagramToRender); // 记录失败的代码
            this.showMermaidError(element, `流程图语法错误 ${err.message || '请检查格式'}`, diagramToRender);
            // 添加错误样式
            element.classList.add('mermaid-error-container');
          });
      } catch (error) {
        console.error('渲染Mermaid图表时发生同步错误:', error);
        this.showMermaidError(element, `渲染流程图时出错: ${error.message}`, diagramToRender);
        element.classList.add('mermaid-error-container');
      }
    },
    
    // 显示Mermaid错误信息
    showMermaidError(element, message, diagram) {
      if (!element) return;
      
      try {
        let errorHtml = `
          <div class="error-state">
            <div class="error-icon">!</div>
            <p>${message}</p>`;
            
        if (diagram) {
          errorHtml += `
            <div class="code-preview">
              <p>当前图表代码:</p>
              <pre>${diagram}</pre>
              <p class="help-text">提示：流程图使用Mermaid语法，请确保格式正确</p>
            </div>`;
        }
        
        errorHtml += `
          <div class="help-example">
            <p>示例语法:</p>
            <pre>graph TD
  A[开始节点] -->|操作| B(处理节点)
  B --> C{条件判断}
  C -->|条件1| D[结果1]
  C -->|条件2| E[结果2]</pre>
          </div>
        </div>`;
        
        element.innerHTML = errorHtml;
        } catch (e) {
        console.error('显示错误信息失败:', e);
        if (element) {
          element.innerHTML = '<div class="error-message">无法显示流程图</div>';
        }
      }
    },
    
    // 实际执行渲染的方法
    doRenderMermaid(element) {
      try {
        console.log('开始实际渲染流程图');
        
        // 清空容器
        element.innerHTML = '';
        
        // 创建一个新的div元素
        const container = document.createElement('div');
        container.className = 'workflow-diagram';
        container.style.width = '100%';
        container.style.textAlign = 'center';
        
        // 将图表内容添加到容器
        container.textContent = this.designData.diagram;
        
        // 将容器添加到DOM
        element.appendChild(container);
        
        // 使用mermaid渲染
        window.mermaid.init(undefined, container);
        
        console.log('流程图渲染完成');
      } catch (error) {
        console.error('执行Mermaid渲染失败:', error);
        element.innerHTML = '<div class="error-message">渲染流程图失败，请检查图表语法</div>';
      }
    },
    
    // 取消设计
    cancelDesign() {
      // 确认退出
      if (this.designData.name || this.designData.prompt || this.designData.diagram || this.designData.config) {
        if (!window.confirm('确定要退出设计吗？未保存的更改将丢失')) {
          return;
        }
      }
      
      // 重置设计状态
            this.isDesigning = false;
      this.editingId = null;
        this.designData = {
          name: '',
        description: '',
          prompt: '',
        config: null,
        diagram: ''
        };
        this.chatHistory = [];
      this.activeDesignTab = 'basic';
      this.approvalNodes = [];
      this.permissionConfigInitialized = false;
    },
    
    // 重试获取工作流数据
    retryFetchWorkflows() {
      console.log('重试获取工作流数据');
      this.isLoading = true;
      this.hasLoadError = false;
      
      // 尝试从API获取
      this.fetchWorkflows()
        .then(() => {
          this.isLoading = false;
          message.success('工作流数据加载成功');
        })
        .catch(err => {
          console.error('重试获取工作流失败:', err);
          this.isLoading = false;
          this.hasLoadError = true;
          
          // 显示友好的错误信息
          this.$notification.error({
            message: '工作流加载失败',
            description: '无法从服务器获取工作流数据，将使用离线数据',
            duration: 5
          });
          
          // 使用模拟数据作为备选
          this.useMockWorkflows();
        });
    },
    
    // 预初始化工作流数据
    preInitWorkflows() {
      console.log('预初始化工作流数据');
      
      // 首先尝试从API获取工作流数据
      this.fetchWorkflowsFromAPI()
        .then(apiWorkflows => {
          if (apiWorkflows && Array.isArray(apiWorkflows) && apiWorkflows.length > 0) {
            console.log('成功从API获取工作流数据');
            this.workflows = apiWorkflows;
            this.isUsingMockData = false;
            this.safeRemoveItem('using_mock_workflows');
            return;
          } else {
            // 如果API没有返回数据，使用localStorage
            throw new Error('API返回空数据或格式不正确');
          }
        })
        .catch(error => {
          console.warn('从API获取工作流失败，尝试使用本地数据:', error);
          
          // 检查本地是否有工作流数据
          const savedWorkflows = this.safeGetItem('mock_workflows');
          if (savedWorkflows) {
            try {
              const parsedWorkflows = JSON.parse(savedWorkflows);
              if (Array.isArray(parsedWorkflows) && parsedWorkflows.length > 0) {
                // 使用本地数据
                console.log('从localStorage加载了', parsedWorkflows.length, '个工作流');
                this.workflows = parsedWorkflows;
                this.isUsingMockData = true;
                this.safeSetItem('using_mock_workflows', 'true');
                return;
              }
            } catch (e) {
              console.error('解析本地工作流数据失败:', e);
            }
          }
          
          // 如果没有本地数据，使用默认工作流
          this.useDefaultWorkflows();
        });
    },
    
    // 从API获取工作流数据
    async fetchWorkflowsFromAPI() {
      try {
        console.log('从API获取工作流数据');
        
        // 直接使用api工具的getWorkflows方法，它已经包含了错误处理和模拟数据逻辑
        return await api.getWorkflows();
      } catch (error) {
        console.error('从API获取工作流数据失败:', error);
        throw error;
      }
    },
    
    // 生成默认配置
    generateDefaultConfig(flowName) {
      return {
        process_meta: {
          process_type: "approval_process",
          version: "1.0",
          description: flowName || "默认审批流程"
        },
        states: {
          "initiator": {
            type: "start",
            role: "发起人",
            transitions: [
              { trigger: "submit", target: "first_approver", description: "提交" }
            ]
          },
          "first_approver": {
            type: "intermediate",
            role: "一级审批人",
            transitions: [
              { trigger: "approve", target: "second_approver", description: "通过" },
              { trigger: "reject", target: "rejected", description: "拒绝" }
            ]
          },
          "second_approver": {
            type: "intermediate",
            role: "二级审批人",
            transitions: [
              { trigger: "approve", target: "approved", description: "通过" },
              { trigger: "reject", target: "rejected", description: "拒绝" }
            ]
          },
          "approved": {
            type: "end",
            final_status: "已批"
          },
          "rejected": {
            type: "end",
            final_status: "已拒"
          }
        }
      };
    },
    
    // 生成默认流程图
    generateDefaultDiagram(type = '基础审批') {
      switch (type) {
        case '财务报销':
      return `graph TD
          A[发起人] -->|提交| B(财务初审)
          B -->|通过| C(部门经理)
          B -->|拒绝| D[审批拒绝]
          C -->|通过| E[审批通过]
          C -->|拒绝| D`;
        case '请假申请':
          return `graph TD
          A[发起人] -->|提交| B(直属主管)
          B -->|通过| C(部门经理)
          B -->|拒绝| D[审批拒绝]
          C -->|通过| E[审批通过]
          C -->|拒绝| D`;
        case '采购申请':
          return `graph TD
          A[发起人] -->|提交| B(直属主管)
          B -->|通过| C(部门经理)
          B -->|拒绝| D[审批拒绝]
          C -->|通过| E(财务审核)
          C -->|拒绝| D
          E -->|通过| F[审批通过]
          E -->|拒绝| D`;
        case '游戏申请':
          return `graph TD
          A[发起人] -->|提交| B(辅导员)
          B -->|通过| C[审批通过]
          B -->|拒绝| D[审批拒绝]`;
        default:
          return `graph TD
          A[发起人] -->|提交| B(部门经理)
          B -->|通过| C[审批通过]
          B -->|拒绝| D[审批拒绝]`;
      }
    },
    
    // 从配置中提取节点
    extractNodesFromConfig() {
      // 确保designData.config存在
      if (!this.designData.config || !this.designData.config.states) {
        return [];
      }
      
      const config = this.designData.config;
      const nodes = [];
      
      // 遍历states对象，提取每个节点
      Object.keys(config.states).forEach(stateKey => {
        const state = config.states[stateKey];
        const node = {
          id: stateKey,
          name: state.role || stateKey,
          type: state.is_end ? 'end' : (stateKey === 'initiator' || state.type === 'start' ? 'start' : 'approval'),
          next: ''
        };
        
        // 处理transitions，确定next属性
        if (state.transitions && state.transitions.length > 0 && state.transitions[0].target) {
          node.next = state.transitions[0].target;
        }
        
        // 初始化审批节点的权限属性
        if (node.type === 'approval' || (!node.type && !node.is_end && stateKey !== 'initiator')) {
          node.required_position_level = state.required_position_level || 0;
          node.required_department_level = state.required_department_level || 0;
          node.allowed_roles = state.allowed_roles || [];
          node.allowed_users = state.allowed_users || [];
          node.editable_fields = state.editable_fields || [];
          node.required_fields = state.required_fields || [];
          node.can_return = state.can_return !== undefined ? state.can_return : true;
        }
        
        nodes.push(node);
      });
      
      return nodes;
    },
    
    // 初始化用户信息
    initUserInfo() {
      try {
        const token = this.safeGetItem('token') || this.safeGetItem('access_token');
        const userStr = this.safeGetItem('user');
        
        if (token && userStr) {
          try {
            const user = JSON.parse(userStr);
            this.currentUser = user;
            console.log('初始化用户信息成功');
          } catch (e) {
            console.error('解析用户信息失败:', e);
          }
        }
      } catch (e) {
        console.error('初始化用户信息失败:', e);
      }
    },
    // 使用模拟数据
    useMockWorkflows() {
      console.log('使用模拟工作流数据');
      
      try {
        // 从localStorage获取保存的工作流数据
        const savedWorkflows = this.safeGetItem('mock_workflows');
        if (savedWorkflows) {
          try {
            // 尝试解析JSON数据
            const parsedWorkflows = JSON.parse(savedWorkflows);
            
            // 验证解析出的数据是否是有效的数组
            if (Array.isArray(parsedWorkflows) && parsedWorkflows.length > 0) {
              console.log('从localStorage加载了', parsedWorkflows.length, '个工作流');
              // 按创建时间排序，时间早的在前面
              this.workflows = parsedWorkflows.sort((a, b) => {
                const timeA = new Date(a.created_at || 0).getTime();
                const timeB = new Date(b.created_at || 0).getTime();
                return timeA - timeB;
              });
              this.isUsingMockData = true;
              this.safeSetItem('using_mock_workflows', 'true');
              return;
            } else {
              console.warn('localStorage中的工作流数据无效或为空');
            }
          } catch (error) {
            console.error('解析localStorage中的工作流数据失败:', error);
          }
        } else {
          console.log('localStorage中没有保存的工作流数据');
        }
        
        // 如果没有有效的localStorage数据，检查是否应该使用默认数据
        // 如果用户已经删除了所有工作流，不应该重新生成默认数据
        const hasDeletedWorkflows = this.safeGetItem('workflows_deleted');
        if (!hasDeletedWorkflows) {
          this.useDefaultWorkflows();
        } else {
          console.log('用户已删除工作流，不重新生成默认数据');
          this.workflows = [];
          this.isUsingMockData = true;
          this.safeSetItem('using_mock_workflows', 'true');
        }
      } catch (error) {
        console.error('加载模拟工作流数据失败:', error);
        // 确保至少有默认数据可用
        this.useDefaultWorkflows();
      }
    },
    
    useDefaultWorkflows() {
      console.log('使用默认工作流数据');
      
      // 设置默认的工作流数据
      this.workflows = [
        {
          id: 1,
          name: "请假流程",
          description: "员工请假审批流程",
          workflow_config: this.generateDefaultConfig("请假流程"),
          diagram: `graph TD
  A[申请人] -->|提交| B(直接主管)
  B -->|通过| C{天数判断}
  B -->|拒绝| F[拒绝结束]
  C -->|?天| D[部门经理]
  C -->|>3天| E[人事总监]
  D -->|审批通过| G[批准结束]
  D -->|审批拒绝| F
  E -->|审批通过| G
  E -->|审批拒绝| F`,
          created_at: new Date('2025-04-27T13:17:00.000Z').toISOString(),
          updated_at: new Date('2025-04-27T13:17:00.000Z').toISOString()
        },
        {
          id: 2,
          name: "财务报销流程",
          description: "员工报销审批流程",
          workflow_config: {
            process_meta: {
              process_type: "approval_process",
              version: "1.0",
              description: "报销审批流程"
            },
            states: {
              "initiator": {
                type: "start",
                role: "申请者",
                transitions: [
                  { trigger: "submit", target: "department_manager", description: "提交" }
                ]
              },
              "department_manager": {
                type: "intermediate",
                role: "部门经理",
                transitions: [
                  { trigger: "approve", target: "finance", description: "通过" },
                  { trigger: "reject", target: "rejected", description: "拒绝" }
                ]
              },
              "finance": {
                type: "intermediate",
                role: "财务部门",
                transitions: [
                  { trigger: "approve", target: "approved", description: "通过" },
                  { trigger: "reject", target: "rejected", description: "拒绝" }
                ]
              },
              "approved": {
                type: "end",
                final_status: "已批"
              },
              "rejected": {
                type: "end",
                final_status: "已拒"
              }
            }
          },
          diagram: `graph TD
  A[申请人] -->|提交| B(部门经理)
  B -->|通过| C(财务部门)
  B -->|拒绝| D[拒绝结束]
  C -->|通过| E[批准结束]
  C -->|拒绝| D`,
          created_at: new Date('2025-07-01T09:15:30.000Z').toISOString(),
          updated_at: new Date('2025-07-01T09:15:30.000Z').toISOString()
        },
        {
          id: 3,
          name: "采购流程",
          description: "物资采购审批流程",
          workflow_config: {
            process_meta: {
              process_type: "approval_process",
              version: "1.0",
              description: "采购审批流程"
            },
            states: {
              "initiator": {
                type: "start",
                role: "申请者",
                transitions: [
                  { trigger: "submit", target: "department_manager", description: "提交" }
                ]
              },
              "department_manager": {
                type: "intermediate",
                role: "部门经理",
                transitions: [
                  { trigger: "approve", target: "procurement", description: "通过" },
                  { trigger: "reject", target: "rejected", description: "拒绝" }
                ]
              },
              "procurement": {
                type: "intermediate",
                role: "采购部门",
                transitions: [
                  { trigger: "approve", target: "finance_director", description: "通过" },
                  { trigger: "reject", target: "rejected", description: "拒绝" }
                ]
              },
              "finance_director": {
                type: "intermediate",
                role: "财务总监",
                transitions: [
                  { trigger: "approve", target: "approved", description: "通过" },
                  { trigger: "reject", target: "rejected", description: "拒绝" }
                ]
              },
              "approved": {
                type: "end",
                final_status: "已批"
              },
              "rejected": {
                type: "end",
                final_status: "已拒"
              }
            }
          },
          diagram: `graph TD
  A[申请人] -->|提交| B(部门经理)
  B -->|通过| C(采购部门)
  B -->|拒绝| E[拒绝结束]
  C -->|通过| D(财务总监)
  C -->|拒绝| E
  D -->|通过| F[批准结束]
  D -->|拒绝| E`,
          created_at: new Date('2025-07-19T14:02:00.000Z').toISOString(),
          updated_at: new Date('2025-07-19T14:02:00.000Z').toISOString()
        }
      ];
      
      // 清除旧的localStorage数据并保存新数据
      try {
        // 先清除旧数据
        localStorage.removeItem('mock_workflows');
        localStorage.removeItem('using_mock_workflows');
        
        // 保存新的工作流数据
        this.safeSetItem('mock_workflows', JSON.stringify(this.workflows));
        this.isUsingMockData = true;
        this.safeSetItem('using_mock_workflows', 'true');
        this.isLoading = false;
        this.hasLoadError = false;
        
        console.log('已更新工作流数据，财务报销流程和采购流程时间已设置为7月1日');
      } catch (e) {
        console.error('保存默认工作流到localStorage失败:', e);
      }
    },
    // 初始化权限配置
    initializePermissionConfig() {
      console.log('开始初始化权限配置...');
      
      // 如果没有配置数据，直接返回
      if (!this.designData || !this.designData.config) {
        console.warn('工作流数据或配置不存在，无法初始化权限配置');
        this.permissionConfigInitialized = false;
        return;
      }
      
      try {
        let config = this.designData.config;
        console.log('当前使用的配置:', JSON.parse(JSON.stringify(config))); // 打印用于调试
        
        // 确保config是对象格式
        if (typeof config === 'string') {
          try {
            config = JSON.parse(config);
            this.designData.config = config; // 更新回对象格式
          } catch(e) {
            console.error('配置数据不是有效的JSON字符串:', e);
            message.error('工作流配置格式错误，无法加载权限设置');
            return;
          }
        }

        // 确保权限配置中包含基本元数据
        if (!config.process_meta) {
          config.process_meta = {
            process_type: "approval_process",
            version: "1.0",
            description: this.designData.name || "审批流程"
          };
          console.log('补充了默认的process_meta');
        }
        
        // 不自动生成states，如果不存在则返回
        if (!config.states || Object.keys(config.states).length === 0) {
          console.warn('配置中缺少states，无法初始化权限配置');
          this.permissionConfigInitialized = false;
          return;
        }
        
        // 确保存在用户和角色列表，供权限控制使用
        if (!this.roles || this.roles.length === 0) {
          console.warn('角色列表为空，使用默认角色');
          this.roles = [
            { id: 1, name: '部门经理' }, { id: 2, name: '财务专员' },
            { id: 3, name: '人事专员' }, { id: 4, name: '总经理' },
            { id: 5, name: '导员' } // 确保包含测试用例所需角色
          ];
        }
        
        // **重要**：通知WorkflowAuthManager组件配置已更新
        // 因为权限配置依赖于config，每次config变化（尤其AI生成后）都需要重新初始化权限组件
        // 这通常通过Vue的响应式系统自动完成，因?workflowConfig="designData.config"
        // 但为了确保，我们在这里显式标记初始化完成
        this.permissionConfigInitialized = true;
        console.log('流程权限配置初始化完成');

      } catch (error) {
        console.error('初始化权限配置过程中发生严重错误:', error);
        message.error('初始化权限设置失败');
        // 提供基本配置以防止UI崩溃
        if (!this.designData.config || !this.designData.config.states) {
          this.designData.config = this.generateDefaultConfig(this.designData.name || '错误恢复');
        }
        this.permissionConfigInitialized = false; // 标记为未成功初始化
      }
    },
    // 从流程图同步节点到配置
    syncNodesWithDiagram() {
      try {
        // 如果没有流程图，则跳过同步
        if (!this.designData.diagram) {
          console.log('未找到流程图，跳过同步');
          return;
        }
        
        console.log('开始从流程图同步节点到配置');
        
        
        // 修复流程图的常见语法问题
        let diagram = this.designData.diagram;
        
        // 修复1: 替换 --> end --> E[结束]
        diagram = diagram.replace(/-->\s*end/g, '--> E[结束]');
        
        // 修复2: 检查并修复重复节点ID定义
        const lines = diagram.split('\n');
        const fixedLines = [];
        
        for (const line of lines) {
          // 判断该行是否包含重复节点ID
          const nodeMatches = line.match(/([A-Za-z0-9_]+)(?:\[|\(|\{)([^\]\)\}]*)(?:\]|\)|\})/g) || [];
          const nodeIds = new Set();
          let hasConflict = false;
          
          // 查找重复的节点ID
          for (const match of nodeMatches) {
            const idMatch = match.match(/^([A-Za-z0-9_]+)/);
            if (idMatch) {
              const id = idMatch[1];
              if (nodeIds.has(id)) {
                hasConflict = true;
                break;
              }
              nodeIds.add(id);
            }
          }
          
          if (hasConflict) {
            // 修复重复ID问题
            let fixedLine = line;
            const processedIds = new Set();
            
            for (const match of nodeMatches) {
              const idMatch = match.match(/^([A-Za-z0-9_]+)/);
              if (idMatch) {
                const id = idMatch[1];
                if (processedIds.has(id)) {
                  // 生成新ID
                  const newId = `${id}_${processedIds.size}`;
                  fixedLine = fixedLine.replace(match, match.replace(id, newId));
                }
                processedIds.add(id);
              }
            }
            
            fixedLines.push(fixedLine);
          } else {
            fixedLines.push(line);
          }
        }
        
        // 更新修复后的流程图
        this.designData.diagram = fixedLines.join('\n');
        
        // 解析流程图中的节点
        const diagramText = this.designData.diagram;
        
        // 提取节点名称和类名
        const nodeRegex = /\[([^\]]+)\]|\(([^\)]+)\)/g;
        const edges = diagramText.match(/-->.+?(?=\n|\r|$)/g) || [];
        const diagramNodes = [];
        
        // 提取节点名称
        let match;
        while ((match = nodeRegex.exec(diagramText)) !== null) {
          const nodeName = match[1] || match[2];
          if (nodeName && !diagramNodes.includes(nodeName)) {
            diagramNodes.push(nodeName);
          }
        }
        
        console.log('从流程图中提取的节点:', diagramNodes);
        
        // 更新完成
        return true;
      } catch (error) {
        console.error('从流程图同步节点到配置失败:', error);
        return false;
      }
    },
    // 更新工作流配置
    updateWorkflowConfig(newConfig) {
      try {
        console.log('收到权限管理器更新的配置');
        
        if (!newConfig) {
          console.warn('收到空配置，忽略更新');
          return;
        }
        
        // 深拷贝配置对象，避免直接引用可能导致的问?        this.designData.config = JSON.parse(JSON.stringify(newConfig));
        
        // 如果当前是流程图标签页，尝试重新渲染流程图
        if (this.activeDesignTab === 'diagram') {
          this.$nextTick(() => {
            this.renderMermaid();
          });
        }
        
        // 通知用户配置已更新
        message.success('工作流权限配置已更新');
      } catch (error) {
        console.error('更新工作流配置失败:', error);
        message.error('更新配置失败，请重试');
      }
    },
    // 生成模拟流程
    generateMockFlow(userMessage) {
      // 根据用户消息确定流程类型
      let flowType = '基础审批';
      
      if (userMessage.includes('财务') || userMessage.includes('报销')) {
        flowType = '财务报销';
      } else if (userMessage.includes('请假') || userMessage.includes('休假')) {
        flowType = '请假申请';
      } else if (userMessage.includes('采购') || userMessage.includes('购买') || userMessage.includes('订购')) {
        flowType = '采购申请';
      } else if (userMessage.includes('游戏') || userMessage.includes('导员')) {
        flowType = '游戏申请';
      }
      
      console.log(`根据用户消息确定流程类型: ${flowType}`);
      
      // 生成匹配流程类型的配置和流程图
      let config = {
        process_meta: {
          process_type: "approval_process",
          version: "1.0",
          description: flowType
        },
        states: {}
      };
      
      // 生成流程图
      const diagram = this.generateDefaultDiagram(flowType);
      
      // 根据流程类型生成配置
      switch (flowType) {
        case '财务报销':
          config.states = {
              "initiator": {
              type: "start",
              role: "发起人",
              transitions: [{ trigger: "submit", target: "finance_review" }]
            },
            "finance_review": {
              type: "intermediate",
              role: "财务初审",
              transitions: [
                { trigger: "approve", target: "manager_review" },
                { trigger: "reject", target: "rejected" }
              ]
            },
            "manager_review": {
              type: "intermediate",
                role: "部门经理",
                transitions: [
                { trigger: "approve", target: "approved" },
                { trigger: "reject", target: "rejected" }
              ]
            },
            "approved": {
              type: "end",
              final_status: "审核通过"
            },
            "rejected": {
              type: "end",
              final_status: "审核失败"
            }
          };
          break;
        case '请假申请':
          config.states = {
            "initiator": {
              type: "start",
              role: "发起人",
              transitions: [{ trigger: "submit", target: "supervisor_review" }]
            },
            "supervisor_review": {
              type: "intermediate",
              role: "直属主管",
                transitions: [
                { trigger: "approve", target: "manager_review" },
                { trigger: "reject", target: "rejected" }
                ]
              },
            "manager_review": {
              type: "intermediate",
              role: "部门经理",
                transitions: [
                { trigger: "approve", target: "approved" },
                { trigger: "reject", target: "rejected" }
              ]
            },
            "approved": {
              type: "end",
              final_status: "审核通过"
            },
            "rejected": {
              type: "end",
              final_status: "审核失败"
            }
          };
          break;
        case '采购申请':
          config.states = {
              "initiator": {
              type: "start",
              role: "发起人",
              transitions: [{ trigger: "submit", target: "supervisor_review" }]
              },
            "supervisor_review": {
              type: "intermediate",
              role: "直属主管",
                transitions: [
                { trigger: "approve", target: "manager_review" },
                { trigger: "reject", target: "rejected" }
                ]
              },
            "manager_review": {
              type: "intermediate",
              role: "部门经理",
                transitions: [
                { trigger: "approve", target: "finance_review" },
                { trigger: "reject", target: "rejected" }
                ]
              },
            "finance_review": {
              type: "intermediate",
              role: "财务审核",
                transitions: [
                { trigger: "approve", target: "approved" },
                { trigger: "reject", target: "rejected" }
              ]
            },
            "approved": {
              type: "end",
              final_status: "审核通过"
            },
            "rejected": {
              type: "end",
              final_status: "审核失败"
            }
          };
          break;
        case '游戏申请':
          config.states = {
            "initiator": {
                type: "start",
              role: "发起人",
              transitions: [{ trigger: "submit", target: "tutor_review" }]
            },
            "tutor_review": {
              type: "intermediate",
              role: "辅导员",
              transitions: [
                { trigger: "approve", target: "approved" },
                { trigger: "reject", target: "rejected" }
              ]
            },
            "approved": {
              type: "end",
              final_status: "审核通过"
            },
            "rejected": {
              type: "end",
              final_status: "审核失败"
            }
          };
          break;
        default:
          config.states = {
            "initiator": {
              type: "start",
              role: "发起人",
              transitions: [{ trigger: "submit", target: "manager_review" }]
            },
            "manager_review": {
              type: "intermediate",
              role: "部门经理",
              transitions: [
                { trigger: "approve", target: "approved" },
                { trigger: "reject", target: "rejected" }
              ]
            },
            "approved": {
              type: "end",
              final_status: "审核通过"
            },
            "rejected": {
              type: "end",
              final_status: "审核失败"
            }
          };
      }
      
      return {
        config,
        diagram
      };
    },
    // 添加节点验证方法，确保流程图语法正确
    validateAndFixDiagram(diagram) {
      // 增强防御性检查
      if (!diagram) return '';
      
      let fixedDiagram = diagram;
      
      // 修复1: 检查和添加 graph TD 声明
      if (!fixedDiagram.trim().startsWith('graph')) {
        fixedDiagram = 'graph TD\n' + fixedDiagram;
      }
      
      // 修复2: 替换 end 关键字，它不能作为节点标识符
      fixedDiagram = fixedDiagram.replace(/-->\s*end/g, '--> E[结束]');
      fixedDiagram = fixedDiagram.replace(/\bend\b(?=\[|\(|\{)/g, 'E');
      
      // 修复3: 检测并修复同一行中的重复节点ID
      const lines = fixedDiagram.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // 查找所有的节点定义，格式为 ID[文本]、ID(文本) ID{文本}
        const nodeMatches = line.match(/([A-Za-z0-9_]+)(?:\[|\(|\{)([^\]\)\}]*)(?:\]|\)|\})/g) || [];
        if (nodeMatches.length < 2) continue; // 行中不到两个节点，不可能有重复
        // 提取节点ID并检查重复
        const ids = new Map();
        for (const match of nodeMatches) {
          const idMatch = match.match(/^([A-Za-z0-9_]+)/);
          if (idMatch) {
            const id = idMatch[1];
            if (ids.has(id)) {
              // 发现重复ID，生成一个新ID
              const count = ids.get(id) + 1;
              ids.set(id, count);
              
              // 替换重复的ID为新ID
              const newId = `${id}${count}`;
              
              // 获取已出现次数，替换第n次出现的ID
              const occurrenceToReplace = count;
              let occurrenceSeen = 0;
              
              // 替换这一行中特定出现次数的ID
              lines[i] = lines[i].replace(new RegExp(`${id}(?=\\[|\\(|\\{)`, 'g'), (matched) => {
                occurrenceSeen++;
                return occurrenceSeen === occurrenceToReplace ? newId : matched;
              });
            } else {
              ids.set(id, 1);
            }
          }
        }
      }
      
      return lines.join('\n');
    },
    // 修改renderMermaid方法，在渲染前先验证图表
    renderMermaid() {
      console.log('开始渲染流程图');
      
      // 防御性检查 - 确保designData.diagram存在
      if (!this.designData || !this.designData.diagram) {
        console.warn('没有图表数据，无法渲染');
        const element = this.$refs.mermaidContainer;
        if (element) {
          element.innerHTML = '<div class="placeholder">没有流程图数据</div>';
        }
        return;
      }
      
      // 验证并修复图表语法
      this.designData.diagram = this.validateAndFixDiagram(this.designData.diagram);
      const diagramToRender = this.designData.diagram; // 使用本地变量，避免异步问题
      
      // 添加日志记录图表内容
      console.log('准备渲染的Mermaid图表代码:\n', diagramToRender);
      
      const element = this.$refs.mermaidContainer;
      if (!element) {
        console.warn('找不到mermaid容器元素');
        return;
      }
      
      try {
        element.innerHTML = ''; // 清空容器
        
        // 使用mermaid.render异步渲染
        const id = 'mermaid-diagram-' + Date.now();
        // 先添加一个占位符，避免mermaid直接操作空DOM
        element.innerHTML = `<div id="${id}"></div>`; 
        
        mermaid.render(id, diagramToRender)
          .then(result => {
            console.log('Mermaid渲染成功');
            // 渲染成功后替换占位符内容
            const targetElement = document.getElementById(id);
            if (targetElement) {
              targetElement.innerHTML = result.svg;
            } else {
              // 备用方案：直接设置外部容器
              element.innerHTML = result.svg;
            }
            // 移除可能存在的错误样式
            element.classList.remove('mermaid-error-container'); 
          })
          .catch(err => {
            console.error('Mermaid渲染流程图失败:', err);
            console.error('失败的图表代码:\n', diagramToRender); // 记录失败的代码
            this.showMermaidError(element, `流程图语法错误 ${err.message || '请检查格式'}`, diagramToRender);
            // 添加错误样式
            element.classList.add('mermaid-error-container');
          });
      } catch (error) {
        console.error('渲染Mermaid图表时发生同步错误:', error);
        this.showMermaidError(element, `渲染流程图时出错: ${error.message}`, diagramToRender);
        element.classList.add('mermaid-error-container');
      }
    },
    // 处理从AI助手发来的工作流创建请求
    handleWorkflowCreateRequest(event) {
      console.log('收到工作流创建请求:', event.detail);
      
      try {
        const designData = event.detail;
        
        if (!designData || !designData.prompt) {
          console.warn('设计数据无效，忽略请求');
          return;
        }
        
        // 创建新工作流并填充数据
        this.createNewWorkflowWithData(designData);
        
        // 自动生成流程
        this.$nextTick(() => {
          this.generateFlow();
        });
      } catch (error) {
        console.error('处理工作流创建请求失败:', error);
        message.error('无法创建工作流: ' + error.message);
      }
    },
    
    // 检查是否有存储的工作流设计数据
    checkStoredDesignData() {
      try {
        const storedData = this.safeGetItem('workflow_design_data');
        if (!storedData) return;
        
        console.log('检测到存储的工作流设计数据');
        
        // 解析数据
        const designData = JSON.parse(storedData);
        
        // 清除存储数据，避免重复使用
        this.safeRemoveItem('workflow_design_data');
        
        if (!designData || !designData.prompt) {
          console.warn('存储的设计数据无效，忽略');
          return;
        }
        
        // 创建新工作流并填充数据
        this.createNewWorkflowWithData(designData);
        
        // 自动生成流程
        this.$nextTick(() => {
          this.generateFlow();
        });
      } catch (error) {
        console.error('检查存储设计数据失败:', error);
      }
    },
    
    // 使用提供的数据创建新工作流
    createNewWorkflowWithData(designData) {
      try {
        // 重置设计状态
        this.isDesigning = true;
        this.activeDesignTab = 'basic';
        this.editingId = null;
        this.permissionConfigInitialized = false;
        
        // 设置设计数据
        this.designData = {
          name: designData.name || '新审批流程',
          description: designData.description || '由AI助手自动创建',
          prompt: designData.prompt || '',
          config: null,
          diagram: ''
        };
        
        // 清空聊天历史和节点信息
        this.chatHistory = [];
        this.approvalNodes = [];
        
        console.log('成功创建新工作流并填充数据:', this.designData);
        
        // 显示通知
        message.success('已根据您的请求打开工作流设计器');
      } catch (error) {
        console.error('使用提供数据创建工作流失败:', error);
        throw error;
      }
    }
  }
};
</script>

<style scoped>
.workflow-designer {
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.designer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.designer-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1890ff;
}

button {
  padding: 8px 16px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  transition: all 0.3s;
}

.primary-btn {
  background-color: #1890ff;
  color: white;
}

.primary-btn:hover {
  background-color: #096dd9;
}

.save-btn {
  background-color: #52c41a;
  color: white;
}

.save-btn:hover {
  background-color: #389e0d;
}

.cancel-btn {
  background-color: #f5f5f5;
  color: rgba(0, 0, 0, 0.65);
  margin-left: 10px;
}

.cancel-btn:hover {
  background-color: #e8e8e8;
}

.edit-btn {
  background-color: #1890ff;
  color: white;
  margin-right: 8px;
}

.delete-btn {
  background-color: #ff4d4f;
  color: white;
}

.workflow-list table {
  width: 100%;
  border-collapse: collapse;
}

.workflow-list th, .workflow-list td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.workflow-list th {
  background-color: #fafafa;
  font-weight: 500;
}

.design-panel {
  margin-top: 20px;
}

.design-tabs {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 20px;
}

.tab-item {
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.tab-item:hover {
  color: #1890ff;
}

.tab-item.active {
  color: #1890ff;
  border-bottom: 2px solid #1890ff;
}

.design-tab-content {
  padding: 20px 0;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-group input, .form-group textarea, .form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.chat-panel {
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.chat-history {
  height: 300px;
  overflow-y: auto;
  padding: 16px;
  background-color: #f5f5f5;
}

.chat-message {
  margin-bottom: 16px;
  max-width: 80%;
}

.chat-message.user {
  margin-left: auto;
}

.message-content {
  padding: 12px;
  border-radius: 8px;
  background-color: white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.chat-message.user .message-content {
  background-color: #1890ff;
  color: white;
}

.chat-input {
  display: flex;
  border-top: 1px solid #f0f0f0;
}

.chat-input textarea {
  flex: 1;
  padding: 12px;
  border: none;
  resize: none;
}

.chat-input button {
  padding: 0 20px;
  background-color: #1890ff;
  color: white;
  border: none;
}

.diagram-view, .json-config {
  background-color: #fafafa;
  padding: 16px;
  border-radius: 4px;
  min-height: 300px;
  overflow: auto;
}

.mermaid-container {
  text-align: center;
}

.placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  color: #999;
}

.action-buttons {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
}

.node-permission {
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 16px;
}

.node-name {
  font-weight: 500;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #f0f0f0;
}

.permission-settings {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.permission-item label {
  font-weight: normal;
}

@media (max-width: 768px) {
  .permission-settings {
    grid-template-columns: 1fr;
  }
}

.loading-state, .error-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
  background: #fafafa;
  border-radius: 4px;
  margin: 20px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-bottom: 16px;
}

.retry-btn {
  margin-top: 16px;
  background-color: #1890ff;
  color: white;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.mock-data-notice {
  background-color: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 4px;
  padding: 8px 12px;
  margin-top: 10px;
  display: flex;
  align-items: center;
  font-size: 13px;
}

.empty-state {
  color: #8c8c8c;
}

.error-state {
  text-align: center;
  margin: 20px 0;
  padding: 20px;
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 4px;
}

.error-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin: 0 auto 16px;
}

.code-preview {
  margin-top: 15px;
  text-align: left;
}

.code-preview pre {
  background-color: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: 3px;
  padding: 10px;
  margin: 10px 0;
  overflow-x: auto;
  text-align: left;
  font-family: monospace;
}

.help-text {
  color: #777;
  font-size: 12px;
  margin-top: 8px;
}

.help-example {
  margin-top: 20px;
  border-top: 1px dashed #ddd;
  padding-top: 15px;
  text-align: left;
}

.help-example p {
  font-weight: bold;
  margin-bottom: 5px;
}

.help-example pre {
  background-color: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: 3px;
  padding: 10px;
  overflow-x: auto;
  text-align: left;
  font-family: monospace;
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 16px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.retry-btn:hover {
  background-color: #40a9ff;
}

/* 添加Mermaid错误容器样式 */
.mermaid-container.mermaid-error-container {
  border: 2px dashed red;
  padding: 10px;
  background-color: #fff0f0;
}

/* 调整错误状态样式 */
.error-state {
  text-align: center;
  margin: 20px 0;
  padding: 20px;
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 4px;
}

/* 自动填充确认对话框样式 */
.auto-fill-modal-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.auto-fill-modal {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 600px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #1a1a1a;
}

.modal-header h3 i {
  color: #1890ff;
  margin-right: 8px;
}

.modal-header .close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
}

.modal-header .close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.auto-fill-message {
  display: flex;
  margin-bottom: 20px;
}

.info-icon {
  font-size: 28px;
  margin-right: 16px;
  color: #1890ff;
}

.info-content p {
  margin: 0 0 8px 0;
}

.auto-fill-details {
  background-color: #f9f9f9;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 20px;
}

.detail-item {
  margin-bottom: 12px;
}

.detail-label {
  font-weight: 600;
  color: #555;
  display: inline-block;
  min-width: 80px;
}

.prompt-value {
  background-color: #f0f5ff;
  padding: 10px;
  border-radius: 4px;
  border-left: 3px solid #1890ff;
  margin-top: 6px;
  white-space: pre-wrap;
}

.auto-fill-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.reject-btn {
  background-color: #f5f5f5;
  border: 1px solid #d9d9d9;
  color: #555;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.reject-btn:hover {
  background-color: #fafafa;
  color: #333;
}

.accept-btn {
  background-color: #1890ff;
  border: 1px solid #1890ff;
  color: #fff;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.accept-btn:hover {
  background-color: #40a9ff;
}

/* 错误信息样式 */
.error-message {
  color: #f5222d;
  font-weight: 500;
}

.warning-message {
  color: #faad14;
  font-weight: 500;
}
</style>
