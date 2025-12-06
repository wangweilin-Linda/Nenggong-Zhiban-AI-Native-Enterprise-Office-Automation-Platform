<template>
  <div class="document-process">
    <div class="section-header">
      <h2>审批流程</h2>
      <div class="header-actions">
        <button class="create-btn" @click="openNewApprovalForm">发起审批</button>
      <div class="search-bar">
          <input v-model="searchKeyword" placeholder="搜索文档..." @keyup.enter="search">
        <button @click="search">搜索</button>
        </div>
      </div>
    </div>

    <!-- 选项卡导航 -->
    <div class="tabs">
      <div class="tab-list">
        <div 
          v-for="tab in filteredTabs" 
          :key="tab.id" 
          class="tab-item"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.name }}
        </div>
      </div>
    </div>

    <!-- 选项卡内容 -->
    <div class="tab-content">
      <!-- 待处理文档（在'todo'标签页显示） -->
      <div v-if="activeTab === 'todo'" class="documents-section">
      <h3>待处理文档</h3>
      <table class="documents-table">
          <thead>
            <tr>
            <th>ID</th>
              <th>标题</th>
            <th>创建时间</th>
            <th>当前节点</th>
              <th>状态</th>
              <th>紧急程度</th>
              <th>发起人</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
          <tr v-for="doc in documents" :key="doc.id">
            <td>{{ doc.id }}</td>
              <td>{{ doc.title }}</td>
            <td>{{ formatDate(doc.created_at) }}</td>
            <td>{{ doc.current_node }}</td>
              <td><span class="status-tag" :class="getStatusClass(doc.status)">{{ getStatusText(doc.status) }}</span></td>
              <td><span class="emergency-tag" :class="getEmergencyClass(doc.emergency_level || 0)">{{ getEmergencyText(doc.emergency_level || 0) }}</span></td>
              <td>{{ doc.initiator || '未知' }}</td>
              <td>
              <button @click="handleDocument(doc)" class="process-btn">处理</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="documents.length === 0" class="empty-data">
          暂无待处理文档
        </div>
      </div>

      <!-- 已办文档（在'done'标签页显示） -->
      <div v-if="activeTab === 'done'" class="documents-section">
        <h3>已办文档</h3>
        <table class="documents-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>标题</th>
              <th>创建时间</th>
              <th>处理时间</th>
              <th>状态</th>
              <th>发起人</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in doneDocuments" :key="doc.id">
              <td>{{ doc.id }}</td>
              <td>{{ doc.title }}</td>
              <td>{{ formatDate(doc.created_at) }}</td>
              <td>{{ formatDate(doc.updated_at) }}</td>
              <td><span class="status-tag" :class="getStatusClass(doc.status)">{{ getStatusText(doc.status) }}</span></td>
              <td>{{ doc.initiator || '未知' }}</td>
              <td>
                <button @click="viewDocument(doc)" class="view-btn">查看</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="doneDocuments.length === 0" class="empty-data">
          暂无已办文档
        </div>
      </div>

      <!-- 我的发起（在'mine'标签页显示） - 优化UI -->
      <div v-if="activeTab === 'mine'" class="documents-section">
        <h3>我发起的审批</h3>
        <div class="my-approvals-container">
          <div v-for="doc in myDocuments" :key="doc.id" 
               :id="`approval-${doc.id}`" 
               class="approval-card">
            <div class="approval-header">
              <span class="approval-title">{{ doc.title }}</span>
              <span class="status-tag" :class="getStatusClass(doc.status)">{{ getStatusText(doc.status) }}</span>
            </div>
            <div class="approval-info">
              <div class="info-item">
                <span class="info-label">创建时间:</span>
                <span class="info-value">{{ formatDate(doc.created_at) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">当前节点:</span>
                <span class="info-value">{{ doc.current_node }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">流程编号:</span>
                <span class="info-value">#{{ doc.id }}</span>
              </div>
            </div>
            <div class="approval-actions">
              <button @click="viewDocument(doc)" class="action-btn view-btn">
                <i class="icon-view"></i>查看详情
              </button>
              <button 
                v-if="doc.status === 'pending' || doc.status === 'processing'"
                @click="withdrawDocument(doc)" 
                class="action-btn withdraw-btn"
              >
                <i class="icon-withdraw"></i>撤回申请
              </button>
              <button 
                v-if="doc.status === 'withdrawn'"
                @click="deleteDocument(doc)" 
                class="action-btn delete-btn"
              >
                <i class="icon-delete"></i>删除
              </button>
            </div>
          </div>
          <div v-if="myDocuments.length === 0" class="empty-data">
            <div class="empty-icon">📝</div>
            <p class="empty-text">暂无我发起的审批</p>
            <button @click="openNewApprovalForm" class="create-empty-btn">立即发起新审批</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 处理模态框 -->
    <div v-if="showProcessModal" class="modal-overlay">
      <div class="modal-content process-modal">
        <div class="modal-header">
          <h3>处理文档: {{ selectedDocument.title }}</h3>
          <button @click="showProcessModal = false" class="close-modal-btn">&times;</button>
        </div>
        <div class="modal-body">
          <!-- 使用ApprovalDetail组件 -->
          <ApprovalDetail 
            v-if="selectedDocument && selectedDocument.id"
            :approvalId="selectedDocument.id"
            @approval-updated="handleApprovalUpdated"
          />
        </div>
        <div class="modal-footer">
          <button @click="showProcessModal = false" class="close-btn">关闭</button>
        </div>
      </div>
    </div>

    <!-- 新增审批表单模态框 -->
    <div v-if="showNewApprovalForm" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>发起{{ selectedWorkflow ? selectedWorkflow.name : '审批' }}</h3>
          <button @click="showNewApprovalForm = false" class="close-modal-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="!selectedWorkflow" class="workflow-select">
            <h4>请选择审批流程</h4>
            <div class="workflow-select-grid">
              <div 
                v-for="flow in workflows" 
                :key="flow.id" 
                class="workflow-select-item"
                :class="{ 'selected': selectedWorkflowId === flow.id }"
                @click="selectWorkflowForForm(flow)"
              >
                <h5>{{ flow.name }}</h5>
                <p>{{ flow.description }}</p>
              </div>
            </div>
          </div>
          
          <div v-else class="approval-form">
            <div class="form-group">
              <label>标题 <span class="required">*</span></label>
              <input 
                v-model="newApproval.title" 
                type="text" 
                placeholder="请输入审批标题"
              />
            </div>
            
            <!-- 动态表单 -->
            <div v-if="formSchema && formSchema.fields && formSchema.fields.length > 0">
              <div 
                v-for="field in formSchema.fields" 
                :key="field.name" 
                class="form-group"
              >
                <label>{{ field.label }} <span v-if="field.required" class="required">*</span></label>
                
                <!-- 文本框 -->
                <input 
                  v-if="field.type === 'text'" 
                  v-model="newApproval.form_data[field.name]" 
                  type="text" 
                  :placeholder="field.placeholder || '请输入' + field.label"
                />
                
                <!-- 数字输入 -->
                <input 
                  v-else-if="field.type === 'number'" 
                  v-model.number="newApproval.form_data[field.name]" 
                  type="number" 
                  :min="field.min" 
                  :max="field.max" 
                  :placeholder="field.placeholder || '请输入' + field.label"
                />
                
                <!-- 下拉选择 -->
                <select 
                  v-else-if="field.type === 'select'" 
                  v-model="newApproval.form_data[field.name]"
                >
                  <option value="">请选择{{ field.label }}</option>
                  <option 
                    v-for="option in field.options" 
                    :key="option.value || option" 
                    :value="option.value || option"
                  >
                    {{ option.label || option }}
                  </option>
                </select>
                
                <!-- 日期选择 -->
                <input 
                  v-else-if="field.type === 'date'" 
                  v-model="newApproval.form_data[field.name]" 
                  type="date"
                />
                
                <!-- 文本域 -->
          <textarea
                  v-else-if="field.type === 'textarea'" 
                  v-model="newApproval.form_data[field.name]" 
                  :rows="field.rows || 3"
                  :placeholder="field.placeholder || '请输入' + field.label"
          ></textarea>
                
                <!-- 默认为文本框 -->
                <input 
                  v-else 
                  v-model="newApproval.form_data[field.name]" 
                  type="text" 
                  :placeholder="field.placeholder || '请输入' + field.label"
                />
        </div>
            </div>
            
            <!-- 基础表单 -->
            <div v-else>
              <div class="form-group">
                <label>内容描述 <span class="required">*</span></label>
                <textarea 
                  v-model="newApproval.content" 
                  rows="5" 
                  placeholder="请详细描述审批内容"
                ></textarea>
              </div>
              
              <div class="form-group">
                <label>附件</label>
                <input type="file" @change="handleFileUpload" multiple />
                <div v-if="uploadedFiles.length > 0" class="upload-list">
                  <div v-for="(file, index) in uploadedFiles" :key="index" class="upload-item">
                    <span>{{ file.name }}</span>
                    <button @click="removeFile(index)" class="remove-btn">移除</button>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="form-assistant">
              <button @click="getFormAssistance" class="assistant-btn" :disabled="isAssistantResponding">
                {{ isAssistantResponding ? '生成中...' : '获取填写建议' }}
          </button>
              <div v-if="formGuide" class="form-guide">
                <h4>填写建议</h4>
                <div v-html="formattedGuide"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button 
            @click="createApproval" 
            class="submit-btn" 
            :disabled="isSubmitting || (!selectedWorkflow || !newApproval.title)"
          >
            {{ isSubmitting ? '提交中...' : '提交审批' }}
          </button>
          <button @click="cancelApproval" class="close-btn">取消</button>
        </div>
      </div>
    </div>

    <!-- 文档列表和详情区域 -->
    <div class="document-container" v-if="activeTab !== 'workflow'">
      <!-- 文档列表 -->
      <div class="document-list" v-if="!selectedDocument">
        <!-- 现有代码... -->
      </div>
      
      <!-- 文档详情 -->
      <div v-if="selectedDocument && !showDocumentDetail" class="document-detail">
        <!-- 现有代码... -->
      </div>
      
      <!-- 文档详情模态框 -->
      <div v-if="showDocumentDetail" class="approval-detail-overlay">
        <div class="approval-detail-container">
          <div class="approval-detail-header">
            <div class="header-content">
              <h2 class="approval-title">{{ selectedDocument.title }}</h2>
              <span class="status-badge" :class="getStatusClass(selectedDocument.status)">
                {{ getStatusText(selectedDocument.status) }}
              </span>
            </div>
            <button class="close-detail-btn" @click="showDocumentDetail = false">&times;</button>
          </div>

          <div class="approval-detail-content">
            <div class="approval-detail-main">
              <div class="approval-meta-card">
                <div class="card-header">
                  <h3>基本信息</h3>
                </div>
                <div class="card-body">
                  <div class="meta-grid">
                    <div class="meta-item">
                      <div class="meta-label">申请编号</div>
                      <div class="meta-value">#{{ selectedDocument.id }}</div>
                    </div>
                    <div class="meta-item">
                      <div class="meta-label">发起人</div>
                      <div class="meta-value">{{ selectedDocument.initiator || '当前用户' }}</div>
                    </div>
                    <div class="meta-item">
                      <div class="meta-label">创建时间</div>
                      <div class="meta-value">{{ formatDate(selectedDocument.created_at) }}</div>
                    </div>
                    <div class="meta-item">
                      <div class="meta-label">当前节点</div>
                      <div class="meta-value">{{ selectedDocument.current_node }}</div>
                    </div>
                    <div class="meta-item">
                      <div class="meta-label">当前状态</div>
                      <div class="meta-value status-text" :class="getStatusClass(selectedDocument.status)">
                        {{ getStatusText(selectedDocument.status) }}
                      </div>
                    </div>
                    <div class="meta-item">
                      <div class="meta-label">紧急程度</div>
                      <div class="meta-value emergency-text" :class="getEmergencyClass(selectedDocument.emergency_level || 0)">
                        {{ getEmergencyLevelText(selectedDocument.emergency_level) }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="approval-content-card">
                <div class="card-header">
                  <h3>申请内容</h3>
                </div>
                <div class="card-body">
                  <div class="approval-content-text">
                    {{ selectedDocument.content || '无申请内容' }}
                  </div>
                </div>
              </div>
            </div>

            <div class="approval-detail-sidebar">
              <div class="approval-history-card">
                <div class="card-header">
                  <h3>审批历史</h3>
                </div>
                <div class="card-body">
                  <div v-if="selectedDocument.history && selectedDocument.history.length > 0" class="history-timeline">
                    <div v-for="(item, index) in selectedDocument.history" :key="index" class="history-item">
                      <div class="timeline-point"></div>
                      <div class="history-content">
                        <div class="history-header">
                          <span class="approver-name">{{ item.approver }}</span>
                          <span class="action-type" :class="'action-' + item.action">{{ getActionName(item.action) }}</span>
                        </div>
                        <div class="history-time">{{ formatDate(item.time) }}</div>
                        <div class="history-comment">{{ item.comment }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="no-history">
                    暂无审批记录
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="approval-detail-footer">
            <button class="secondary-btn" @click="showDocumentDetail = false">关闭</button>
            <button
              v-if="selectedDocument.status === 'pending' && canWithdraw(selectedDocument)"
              class="danger-btn"
              @click="withdrawApproval(selectedDocument.id)"
            >
              撤回申请
            </button>
          </div>
        </div>
      </div>
    </div>
    <!-- 现有的处理模态框和其他组件 -->
  </div>
</template>

<script>
import ApprovalDetail from './ApprovalDetail.vue';
import WorkflowAuthManager from './WorkflowAuthManager.vue';
import api from '../utils/api';
import axios from 'axios';
import workflowData from '../assets/workflow.json';
import { message, Modal as AntModal } from 'ant-design-vue';
import emitter from '../utils/eventBus';
import Modal from './Modal.vue';

// Ollama模型API的axios实例
const ollamaApi = axios.create({
  baseURL: 'http://localhost:11434/api',
  timeout: 60000, // 更长的超时时间
});

// 确保Ollama API不会触发401错误处理
ollamaApi.interceptors.response.use(
  response => response,
  error => {
    // 自定义错误处理，不触发登出
    console.error('Ollama API请求失败:', error);
    return Promise.reject(error);
  }
);

/* 
// 添加请求拦截器
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
*/

export default {
  name: 'DocumentProcess',
  components: {
    ApprovalDetail,
    WorkflowAuthManager,
    Modal
  },
  data() {
    return {
      activeTab: 'todo',
      tabs: [
        { id: 'todo', name: '待办公文' },
        { id: 'done', name: '已办公文' },
        { id: 'mine', name: '我的发起' }
      ],
      searchKeyword: '',
      todoDocuments: [],
      doneDocuments: [],
      myDocuments: [],
      selectedDocument: null,
      showDocumentDetail: false, // 添加文档详情模态框显示状态
      isProcessing: false,
      approvalComment: '',
      showNewDocumentForm: false,
      newDocument: {
        title: '',
        content: '',
        workflow_id: '',
        form_data: {}
      },
      workflows: [],
      userType: '',
      // 新增协同Agent相关数据
      agentSuggestion: '',
      formGuide: '',
      approvalContext: null,
      isLoadingAgent: false,
      titleChangeTimer: null,
      availableActions: [], // 当前可用的操作按钮
      workflowConfig: null, // 工作流配置
      showProcessModal: false,
      selectedWorkflowDescription: '',
      userIsAdmin: false, // 标记用户是否为管理员
      currentUser: null,
      isLoading: false,
      formSchema: null,
      loading: false,
      isAssistantResponding: false,
      showNewApprovalForm: false,
      selectedWorkflow: null,
      selectedWorkflowId: null,
      newApproval: {
        title: '',
        content: '',
        workflow_id: '',
        form_data: {},
        emergency_level: 0
      },
      isSubmitting: false,
      uploadedFiles: [],
      documents: [], // 添加documents数组用于存储待处理文档
      // 添加预设审批数据属性
      presetApprovalData: null
    };
  },
  computed: {
    filteredTabs() {
      // 管理员可以看到所有选项卡，普通用户只能看到"我的发起"和"待办公文"
      if (this.userType === 'admin') {
        return this.tabs;
      } else {
        return this.tabs.filter(tab => ['mine', 'todo'].includes(tab.id));
      }
    },
    currentUser() {
      // 获取当前登录用户信息
      const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
      try {
        if (userStr) {
          const user = JSON.parse(userStr);
          return user.real_name || user.username || '当前用户';
        }
      } catch (e) {
        console.error('解析用户信息失败:', e);
      }
      return '当前用户';
    },
    // 根据当前用户职位计算可用操作
    canApprove() {
      if (!this.selectedDocument || !this.currentUser) return false;
      
      // 管理员始终有权限
      if (this.currentUser.is_admin) return true;
      
      // 获取当前节点配置
      const nodeId = this.selectedDocument.current_node;
      const nodeConfig = this.getNodeConfig(nodeId);
      
      if (!nodeConfig) return false;
      
      // 检查用户职位级别
      if (nodeConfig.required_position_level && 
          this.currentUser.position_level <= nodeConfig.required_position_level) {
        return true;
      }
      
      // 检查用户部门级别
      if (nodeConfig.required_department_level && 
          this.currentUser.department_level <= nodeConfig.required_department_level) {
        return true;
      }
      
      // 检查允许的角色
      if (nodeConfig.allowed_roles && this.currentUser.roles &&
          nodeConfig.allowed_roles.some(role => this.currentUser.roles.includes(role))) {
        return true;
      }
      
      // 检查指定的用户ID
      if (nodeConfig.allowed_users && 
          nodeConfig.allowed_users.includes(this.currentUser.id)) {
        return true;
      }
      
      return false;
    },
    
    // 根据当前文档和工作流配置计算可用操作按钮
    computedAvailableActions() {
      if (!this.selectedDocument || !this.canApprove) return [];
      
      // 获取当前节点配置
      const nodeId = this.selectedDocument.current_node;
      const nodeConfig = this.getNodeConfig(nodeId);
      
      if (!nodeConfig) return [];
      
      // 根据节点类型和配置返回可用操作
      const actions = [];
      
      // 审批节点的标准操作
      if (nodeConfig.type === 'approval') {
        actions.push(
          { id: 'approve', name: '同意', type: 'primary' },
          { id: 'reject', name: '拒绝', type: 'danger' }
        );
        
        // 特定条件下可以退回
        if (nodeConfig.can_return) {
          actions.push({ id: 'return', name: '退回', type: 'warning' });
        }
      }
      
      // 处理其他类型节点的操作
      return actions;
    },
    // 格式化的表单填写建议
    formattedGuide() {
      if (!this.formGuide) return '';
      // 简单的格式处理：将换行符替换为HTML换行标签
      return this.formGuide.replace(/\n/g, '<br>');
    }
  },
  mounted() {
    console.log('DocumentProcess组件挂载');
    
    // 检查用户角色，确保用户已登录
    const isLoggedIn = this.checkUserRole();
    
    if (isLoggedIn) {
      // 获取工作流列表
      this.fetchWorkflows();
      
      // 获取待处理文档
      this.fetchPendingDocuments();
      
      // 获取我发起的审批
      this.fetchMyDocuments();
      
      // 添加事件监听器，以便在登录状态变化时重新获取数据
      window.addEventListener('storage', this.handleStorageChange);
      
      // 监听登录事件
      document.addEventListener('user-login', this.reloadData);
      emitter.on('user-login', this.reloadData);
      
      // 监听工作流更新事件
      window.addEventListener('workflow-updated', this.handleWorkflowUpdate);
      
      // 检查URL查询参数
      this.checkUrlParams();
      
      // 检查localStorage中是否有预设审批数据
      this.checkLocalStoragePresetData();
    } else {
      console.log('DocumentProcess组件: 用户未登录，不加载数据');
      // 如果用户未登录，尝试订阅登录事件，以便登录后加载数据
      emitter.on('user-login', this.reloadData);
    }
  },
  beforeUnmount() {
    // 移除事件监听器
    window.removeEventListener('storage', this.handleStorageChange);
    document.removeEventListener('user-login', this.reloadData);
    emitter.off('user-login', this.reloadData);
    window.removeEventListener('workflow-updated', this.handleWorkflowUpdate);
  },
  methods: {
    // 存储事件变化监听器
    handleStorageChange(event) {
      if (event.key === 'token' || event.key === 'user' || 
          event.key === 'user_role' || event.key === 'mock_admin_token') {
        console.log('DocumentProcess组件: 检测到存储变化，重新加载数据');
        this.reloadData();
      }
      
      // 特别检查工作流数据变化
      if (event.key === 'mock_workflows') {
        console.log('DocumentProcess组件: 检测到工作流数据变化，重新加载工作流');
        this.fetchWorkflows();
      }
    },
    
    // 处理工作流更新事件
    handleWorkflowUpdate(event) {
      try {
        console.log('DocumentProcess组件: 收到工作流更新事件，重新加载工作流');
        // 确保事件处理不会导致错误
        this.fetchWorkflows();
      } catch (error) {
        console.error('处理工作流更新事件失败:', error);
      }
    },
    
    // 重新加载数据
    reloadData() {
      // 重新检查用户角色
      const isLoggedIn = this.checkUserRole();
      
      if (isLoggedIn) {
        // 重新获取工作流列表
        this.fetchWorkflows();
        
        // 重新获取待处理文档
        this.fetchPendingDocuments();
        
        // 重新获取我发起的审批
        this.fetchMyDocuments();
      }
    },
    // 检查用户是否已登录，返回布尔值表示是否已登录
    checkUserAuth() {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token');
      if (!token) {
        console.warn('用户未登录，请先登录系统');
        emitter.emit('show-login');
        return false;
      } else {
        // 获取用户类型
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        const userRole = localStorage.getItem('user_role') || sessionStorage.getItem('user_role');
        
        // 检查token是否为JWT格式
        const isJwtToken = token && token.split('.').length === 3;
        
        if (userStr) {
          try {
            const userInfo = JSON.parse(userStr);
            // 严格比较以确保正确判断管理员身份
            this.userType = userInfo.is_admin === true || userInfo.role === 'admin' ? 'admin' : 'user';
            this.userIsAdmin = userInfo.is_admin === true || userInfo.role === 'admin';
          } catch (e) {
            console.error('解析user数据失败:', e);
            this.userType = userRole === 'admin' ? 'admin' : 'user';
            this.userIsAdmin = userRole === 'admin';
          }
        } else {
          this.userType = userRole === 'admin' ? 'admin' : 'user';
          this.userIsAdmin = userRole === 'admin';
        }
        
        console.log('DocumentProcess: 当前用户类型:', this.userType, '是否管理员:', this.userIsAdmin);
        return true;
      }
    },
    async fetchDocuments() {
      try {
        if (!this.isLoggedIn) {
          // 如果未登录，使用实际API请求
          await this.fetchDocumentsFromApi();
          return;
        }
        
        await this.fetchDocumentsFromApi();
      } catch (apiError) {
        // 记录错误但继续使用API
        console.error('获取文档失败:', apiError);
      }
    },
    
    async fetchDocumentsFromApi() {
      try {
        // 获取待办文档
        const todoResponse = await api.get('/documents/todo');
        if (todoResponse.data && todoResponse.data.documents) {
          this.todoDocuments = todoResponse.data.documents;
        }
        
        // 获取已处理文档
        const doneResponse = await api.get('/documents/done');
        if (doneResponse.data && doneResponse.data.documents) {
          this.doneDocuments = doneResponse.data.documents;
        }
        
        // 获取我创建的文档
        const myResponse = await api.get('/documents/mine');
        if (myResponse.data && myResponse.data.documents) {
          this.myDocuments = myResponse.data.documents;
        }
      } catch (error) {
        throw error;
      }
    },
    
    async fetchWorkflows() {
      try {
        // 检查用户是否已登录
        if (!this.checkUserRole()) {
          console.warn('用户未登录，无法获取工作流程');
          return;
        }
        
        // 首先尝试从localStorage获取管理员创建的工作流，确保数据同步
        const savedWorkflows = localStorage.getItem('mock_workflows');
        if (savedWorkflows) {
          try {
            const parsedWorkflows = JSON.parse(savedWorkflows);
            if (Array.isArray(parsedWorkflows) && parsedWorkflows.length > 0) {
              this.workflows = parsedWorkflows;
              console.log('成功从localStorage获取到管理员创建的工作流:', this.workflows);
              return;
            }
          } catch (e) {
            console.error('解析localStorage中的工作流数据失败:', e);
          }
        }
        
        // 如果localStorage没有数据，再检查token类型
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        const isMockToken = token === 'mock_admin_token' || token === 'mock_user_token' || token === 'mock_manager_token';
        
        if (isMockToken) {
          console.log('使用模拟数据获取工作流');
          
          // 使用默认模拟数据（因为localStorage中没有数据）
          this.workflows = [
            {
              id: 1,
              name: '报销审批流程',
              description: '员工报销的标准审批流程',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            },
            {
              id: 2,
              name: '请假审批流程',
              description: '员工请假的标准审批流程',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            },
            {
              id: 3,
              name: '采购审批流程',
              description: '物资采购的标准审批流程',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            }
          ];
          
          // 保存到localStorage，以便管理员可以看到和编辑
          localStorage.setItem('mock_workflows', JSON.stringify(this.workflows));
          return;
        }
        
        // 尝试使用通用API获取工作流程列表
        const response = await api.get('/workflow-designer/workflows');
        this.workflows = response.data;
        console.log('从API获取到工作流:', this.workflows);
      } catch (error) {
        console.error('获取工作流失败:', error);
        
        // 如果API调用失败，再次尝试从localStorage获取
        const savedWorkflows = localStorage.getItem('mock_workflows');
        if (savedWorkflows) {
          try {
            this.workflows = JSON.parse(savedWorkflows);
            console.log('API失败，从localStorage获取到工作流:', this.workflows);
            return;
          } catch (e) {
            console.error('解析localStorage中的工作流数据失败:', e);
          }
        }
        
        // 如果上述方法都失败，使用备用模拟数据
        this.workflows = [
          {
            id: 1,
            name: '通用审批流程',
            description: '适用于一般性申请的审批流程',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          },
          {
            id: 2,
            name: '财务审批流程',
            description: '适用于财务预算、报销等财务相关审批',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
        ];
      }
    },
    search() {
      // 实现搜索功能
      console.log('搜索关键词:', this.searchKeyword);
      // 实际项目中应该调用API进行搜索
    },
    handleDocument(doc) {
      this.selectedDocument = doc;
      this.approvalComment = '';
      this.showProcessModal = true;
      
      // 获取当前节点可用的操作
      this.availableActions = this.computedAvailableActions;
    },
    getCurrentNode(doc) {
      // 根据文档状态和审批历史确定当前节点
      if (doc.status === 'pending') {
        const history = doc.history || [];
        if (history.length === 0) {
          return 'initiator';
        }
        const lastRecord = history[history.length - 1];
        return lastRecord.nextNode || 'intermediate_1';
      }
      return null;
    },
    getAvailableActions(nodeId) {
      if (!this.workflowConfig || !this.workflowConfig.states) {
        return [];
      }
      
      const state = Object.values(this.workflowConfig.states).find(s => s.role === nodeId);
      if (!state || !state.transitions) {
        return [];
      }
      
      return state.transitions.map(t => ({
        id: t.trigger,
        name: t.description,
        target: t.target
      }));
    },
    getActionButtonClass(trigger) {
      const baseClass = 'px-4 py-2 text-white rounded';
      switch (trigger) {
        case 'approve':
          return `${baseClass} bg-green-500 hover:bg-green-600`;
        case 'reject':
          return `${baseClass} bg-red-500 hover:bg-red-600`;
        case 'return':
          return `${baseClass} bg-yellow-500 hover:bg-yellow-600`;
        default:
          return `${baseClass} bg-blue-500 hover:bg-blue-600`;
      }
    },
    async processDocument(action) {
      if (!this.approvalComment) {
        alert('请输入处理意见');
        return;
      }

      try {
        const currentNode = this.getCurrentNode(this.selectedDocument);
        const transition = this.workflowConfig.transitions.find(
          t => t.source === currentNode && t.trigger === action
        );

        if (!transition) {
          throw new Error('无效的操作');
        }

        // 发送处理请求
        const response = await fetch(`/api/approval/process/${this.selectedDocument.id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            action,
            comment: this.approvalComment,
            nextNode: transition.destination,
            user: this.currentUser // 添加当前用户信息
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || '处理失败');
        }

        // 更新文档状态
        const updatedDoc = await response.json();
        this.updateDocumentStatus(updatedDoc);
        
        // 关闭弹窗
        this.showProcessModal = false;
        this.approvalComment = '';
        
        alert(`已${this.getActionName(action)}该公文`);
      } catch (error) {
        console.error('处理公文失败:', error);
        alert(`处理失败: ${error.message}`);
      }
    },
    updateDocumentStatus(updatedDoc) {
      // 更新文档列表中的状态
      const docIndex = this.todoDocuments.findIndex(d => d.id === updatedDoc.id);
      if (docIndex !== -1) {
        if (updatedDoc.status === 'completed') {
          // 如果处理完成，从待办移到已完成
          this.todoDocuments.splice(docIndex, 1);
          this.doneDocuments.unshift(updatedDoc);
        } else {
          // 更新待办中的文档状态
          this.todoDocuments[docIndex] = updatedDoc;
        }
      }
    },
    viewDocument(doc) {
      if (!this.checkUserAuth()) return;
      
      console.log('查看文档详情:', doc);
      
      // 保存选中的文档
      this.selectedDocument = JSON.parse(JSON.stringify(doc));
      
      // 根据文档ID和状态加载更多详情
      this.loadDocumentDetails(doc.id);
      
      // 设置处理状态为否
      this.isProcessing = false;
      
      // 显示文档详情模态框
      this.showDocumentDetail = true;
    },
    closeDocumentDetail() {
      this.selectedDocument = null;
      this.isProcessing = false;
      this.approvalComment = '';
    },
    getActionName(action) {
      const actionMap = {
        'approve': '同意',
        'reject': '拒绝',
        'return': '退回',
        'withdraw': '撤回'
      };
      return actionMap[action] || action;
    },
    async openNewDocumentForm() {
      this.showNewDocumentForm = true;
      this.newDocument = {
        title: '',
        content: '',
        workflow_id: ''
      };
      this.formGuide = '';
    },
    async getAIRecommendation() {
      this.isLoadingRecommendation = true;
      
      try {
        const data = {
          title: this.newDocument.title,
          content: this.newDocument.content,
          document_type: this.newDocument.type
        };
        
        // 调用后端API获取推荐
        const response = await api.post('/agent/recommend-workflow', data);
        
        if (response.data && response.data.recommended_workflow) {
          this.recommendedWorkflow = response.data.recommended_workflow;
          return;
        }
        
        // API调用失败或返回数据不完整，尝试本地模型
        this.recommendedWorkflow = null;
        
        // 基于文档内容和标题使用简单规则进行匹配
        this.recommendedWorkflow = this.matchWorkflowByKeywords();
      } catch (error) {
        console.error('获取AI推荐失败:', error);
        // 使用关键词匹配作为后备方案
        this.recommendedWorkflow = this.matchWorkflowByKeywords();
      } finally {
        this.isLoadingRecommendation = false;
      }
    },
    // 生成默认的表单填写指导
    getDefaultGuide(workflowId = null) {
      if (!workflowId) {
        const title = this.newDocument.title.toLowerCase();
        
        // 根据标题关键词推荐不同的工作流
        if (title.includes('财务') || title.includes('预算') || title.includes('报销')) {
          this.newDocument.workflow_id = '2';
          this.formGuide = this.getDefaultGuideText('2');
        } else if (title.includes('采购') || title.includes('设备') || title.includes('购买')) {
          this.newDocument.workflow_id = '3';
          this.formGuide = this.getDefaultGuideText('3');
        } else {
          this.newDocument.workflow_id = '1';
          this.formGuide = this.getDefaultGuideText('1');
        }
      } else {
        // 根据工作流ID提供建议
        this.formGuide = this.getDefaultGuideText(workflowId);
      }
    },
    // 获取默认指导文本
    getDefaultGuideText(workflowId) {
      switch (workflowId) {
        case '2':
          return '这是一份财务相关的申请，请详细说明预算金额和用途，并附上相关财务数据支持您的申请。建议包含以下要点：\n1. 预算总额和明细\n2. 资金用途说明\n3. 预期投资回报率\n4. 历史同类预算执行情况';
        case '3':
          return '这是一份采购申请，请详细列出需要采购的物品、数量、预估价格，以及采购理由。建议包含以下信息：\n1. 采购物品详细清单\n2. 市场调研结果及供应商对比\n3. 采购必要性说明\n4. 预计使用期限和效益分析';
        default:
          return '请在内容中详细说明您的申请目的、背景和预期结果，以便审批人更好地理解您的需求。建议包含以下内容：\n1. 申请背景和目的\n2. 具体实施方案\n3. 所需资源和支持\n4. 预期成果和影响';
      }
    },
    async submitNewDocument() {
      if (!this.checkUserAuth()) return;
      
      if (!this.newDocument.title || !this.newDocument.content || !this.newDocument.workflow_id) {
        alert('请填写完整的公文信息');
        return;
      }
      
      try {
        // 实际提交到后端
        const response = await api.post('/documents/create', this.newDocument);
        
        if (response.data && response.data.success) {
          // 添加到我的文档列表
          const newDoc = {
            id: response.data.document_id,
            title: this.newDocument.title,
            type: this.newDocument.type,
            status: "draft",
            created_at: new Date().toISOString(),
            creator_name: this.currentUser.username
          };
          
          this.myDocuments.unshift(newDoc);
          this.showNewDocumentForm = false;
          this.newDocument = {
            title: '',
            content: '',
            workflow_id: ''
          };
          
          alert('公文提交成功');
        } else {
          alert('公文提交失败: ' + (response.data?.message || '未知错误'));
        }
      } catch (error) {
        console.error('提交文档失败:', error);
        alert('公文提交失败: ' + error.message);
      }
    },
    async askForWorkflowHelp() {
      this.isLoadingAgent = true;
      
      try {
        const data = {
          title: this.newDocument.title,
          content: this.newDocument.content,
          document_type: this.newDocument.type
        };
        
        // 调用后端API获取推荐
        const response = await api.post('/agent/recommend-workflow', data);
        
        if (response.data && response.data.recommended_workflow) {
          this.recommendedWorkflow = response.data.recommended_workflow;
          this.selectedWorkflowDescription = response.data.description;
          return;
        }
        
        // API调用失败或返回数据不完整，尝试本地模型
        this.recommendedWorkflow = null;
        
        // 基于文档内容和标题使用简单规则进行匹配
        this.recommendedWorkflow = this.matchWorkflowByKeywords();
        this.selectedWorkflowDescription = this.getDefaultGuideText(this.newDocument.workflow_id);
      } catch (error) {
        console.error('获取流程设计建议失败:', error);
        // 使用关键词匹配作为后备方案
        this.recommendedWorkflow = this.matchWorkflowByKeywords();
        this.selectedWorkflowDescription = this.getDefaultGuideText(this.newDocument.workflow_id);
      } finally {
        this.isLoadingAgent = false;
      }
    },
    matchWorkflowByKeywords() {
      // 实现关键词匹配逻辑
      // 这里可以根据实际需求实现复杂的匹配逻辑
      return this.getDefaultGuideText(this.newDocument.workflow_id);
    },
    async updateWorkflowDescription(workflowId) {
      try {
        // 查找已选择的工作流
        const workflow = this.workflows.find(w => w.id == workflowId);
        if(workflow) {
          this.selectedWorkflowDescription = workflow.description || '无描述';
        } else {
          this.selectedWorkflowDescription = '';
        }
      } catch(error) {
        console.error('获取流程描述失败:', error);
        this.selectedWorkflowDescription = '';
      }
    },
    // 检查用户角色
    checkUserRole() {
      try {
        // 检查用户是否登录
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (!token) {
          console.warn('用户未登录，请先登录系统');
          // 如果用户未登录，触发登录弹窗事件
          emitter.emit('show-login');
          return false;
        }
        
        // 识别模拟用户token
        const mockTokenRegex = /^mock_(\w+)_token/;
        if (token.match(mockTokenRegex)) {
          const tokenType = token.match(mockTokenRegex)[1];
          if (tokenType === 'admin') {
            this.userType = 'admin';
            this.userIsAdmin = true;
            console.log('文档处理组件: 识别到管理员模拟token');
          } else if (tokenType === 'user') {
            this.userType = 'user';
            this.userIsAdmin = false;
            console.log('文档处理组件: 识别到普通用户模拟token');
          } else if (tokenType === 'manager') {
            this.userType = 'manager';
            this.userIsAdmin = false;
            console.log('文档处理组件: 识别到经理模拟token');
          }
          return true;
        }
        
        // 获取用户类型
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        const userRole = localStorage.getItem('user_role') || sessionStorage.getItem('user_role');
        const mockAdminToken = localStorage.getItem('mock_admin_token') || sessionStorage.getItem('mock_admin_token');
        
        // 检查是否为管理员标记
        if (mockAdminToken === 'true') {
          this.userType = 'admin';
          this.userIsAdmin = true;
          console.log('文档处理组件: 根据mock_admin_token标记识别为管理员');
          return true;
        }
        
        // 优先使用用户角色标记
        if (userRole) {
          this.userType = userRole;
          this.userIsAdmin = userRole === 'admin';
          console.log('文档处理组件: 根据user_role识别用户角色:', this.userType);
          return true;
        }
        
        // 尝试从user对象获取
        if (userStr) {
          try {
            const user = JSON.parse(userStr);
            this.userType = user.role || (user.is_admin ? 'admin' : (user.is_manager ? 'manager' : 'user'));
            this.userIsAdmin = user.is_admin === true || user.role === 'admin';
            console.log('文档处理组件: 从user对象获取用户类型:', this.userType);
            return true;
          } catch (e) {
            console.error('解析user数据失败:', e);
          }
        }
        
        // 如果无法识别，默认为普通用户
        this.userType = 'user';
        this.userIsAdmin = false;
        console.log('文档处理组件: 无法识别用户类型，默认为普通用户');
        return true;
      } catch (error) {
        console.error('检查用户角色失败:', error);
        this.userType = 'user'; // 出错时默认为普通用户
        this.userIsAdmin = false;
        return true;
      }
    },
    // 获取待处理文档
    async fetchPendingDocuments() {
      this.loading = true;
      console.log('开始获取待处理文档');
      
      try {
        // 获取当前用户信息
        const currentUser = this.getCurrentUser();
        if (!currentUser) {
          console.warn('未找到当前用户，无法获取待处理文档');
          return;
        }
        
        let pendingDocs = [];
        
        // 开发环境下从本地存储获取数据
        if (process.env.NODE_ENV === 'development') {
          console.log('开发环境: 从本地存储获取待处理文档');
          
          // 从所有可能的存储位置获取审批
          const approvalMap = new Map();
          
          // 从local_approvals获取
          try {
            const localApprovalsStr = localStorage.getItem('local_approvals');
            if (localApprovalsStr) {
              const localApprovals = JSON.parse(localApprovalsStr);
              console.log(`从local_approvals获取到${localApprovals.length}条审批`);
              
              // 添加到Map，使用ID作为键进行去重
              localApprovals.forEach(approval => {
                if (approval && approval.id) {
                  approvalMap.set(approval.id.toString(), { ...approval, _source: 'local_approvals' });
                }
              });
            }
          } catch (error) {
            console.error('读取local_approvals失败:', error);
          }
          
          // 从mock_approvals获取，如果ID已存在则不覆盖
          try {
            const mockApprovalsStr = localStorage.getItem('mock_approvals');
            if (mockApprovalsStr) {
              const mockApprovals = JSON.parse(mockApprovalsStr);
              console.log(`从mock_approvals获取到${mockApprovals.length}条审批`);
              
              mockApprovals.forEach(approval => {
                if (approval && approval.id && !approvalMap.has(approval.id.toString())) {
                  approvalMap.set(approval.id.toString(), { ...approval, _source: 'mock_approvals' });
                }
              });
            }
          } catch (error) {
            console.error('读取mock_approvals失败:', error);
          }
          
          // 将Map转换为数组
          const allApprovals = Array.from(approvalMap.values());
          console.log(`去重后共有${allApprovals.length}条审批`);
          
          // 筛选待处理的审批
          pendingDocs = allApprovals.filter(doc => {
            // 状态为待处理或处理中
            const statusMatch = doc.status === 'pending' || doc.status === 'processing';
            
            // 如果是当前用户创建的审批且不需要显示在待办中，则排除
            const isCreatedByCurrentUser = 
              (doc.initiator_id && doc.initiator_id == currentUser.id) ||
              (doc.initiator && (
                doc.initiator === currentUser.username || 
                doc.initiator === currentUser.full_name ||
                doc.initiator === currentUser.real_name ||
                doc.initiator === "当前用户"
              ));
            
            // 返回：状态匹配且不是自己发起的（除非是审批人）
            return statusMatch && !isCreatedByCurrentUser;
          });
          
          console.log(`筛选出${pendingDocs.length}条待处理审批`);
          
          // 如果是管理员或有特定权限，可以看到所有待处理审批
          if (currentUser.is_admin || currentUser.roles?.includes('admin') || currentUser.roles?.includes('approver')) {
            console.log('当前用户是管理员或审批人，显示所有待处理审批');
            pendingDocs = allApprovals.filter(doc => 
              doc.status === 'pending' || doc.status === 'processing'
            );
          }
        } else {
          // 生产环境使用API
          try {
            const response = await api.getPendingApprovals();
            pendingDocs = Array.isArray(response) ? response : 
                         (response.data && Array.isArray(response.data) ? response.data : []);
          } catch (error) {
            console.error('API获取待处理审批失败:', error);
          }
        }
        
        // 处理日期和添加其他必要信息
        pendingDocs = pendingDocs.map(doc => {
          if (!doc.created_at) {
            doc.created_at = new Date().toISOString();
          }
          return doc;
        });
        
        // 确保没有重复ID的审批（最终确认）
        const finalMap = new Map();
        pendingDocs.forEach(doc => {
          if (doc && doc.id) {
            finalMap.set(doc.id.toString(), doc);
          }
        });
        pendingDocs = Array.from(finalMap.values());
        
        // 按创建时间降序排序
        pendingDocs.sort((a, b) => {
          return new Date(b.created_at) - new Date(a.created_at);
        });
        
        console.log('最终待处理文档列表:', pendingDocs);
        this.todoDocuments = pendingDocs;
        // 更新显示的文档（当前激活标签页是待办时）
        if (this.activeTab === 'todo') {
          this.documents = pendingDocs;
        }
      } catch (error) {
        console.error('获取待处理文档失败:', error);
        message.error('获取待处理文档失败');
      } finally {
        this.loading = false;
      }
    },
    
    // 获取已处理文档
    async fetchCompletedDocuments() {
      this.loading = true;
      console.log('开始获取已处理文档');
      
      try {
        // 获取当前用户信息
        const currentUser = this.getCurrentUser();
        if (!currentUser) {
          console.warn('未找到当前用户，无法获取已处理文档');
          return;
        }
        
        let completedDocs = [];
        
        // 开发环境下从本地存储获取数据
        if (process.env.NODE_ENV === 'development') {
          console.log('开发环境: 从本地存储获取已处理文档');
          
          // 从所有可能的存储位置获取审批
          const approvalMap = new Map();
          
          // 从local_approvals获取
          try {
            const localApprovalsStr = localStorage.getItem('local_approvals');
            if (localApprovalsStr) {
              const localApprovals = JSON.parse(localApprovalsStr);
              console.log(`从local_approvals获取到${localApprovals.length}条审批`);
              
              // 添加到Map，使用ID作为键进行去重
              localApprovals.forEach(approval => {
                if (approval && approval.id) {
                  approvalMap.set(approval.id.toString(), { ...approval, _source: 'local_approvals' });
                }
              });
            }
          } catch (error) {
            console.error('读取local_approvals失败:', error);
          }
          
          // 从mock_approvals获取，如果ID已存在则不覆盖
          try {
            const mockApprovalsStr = localStorage.getItem('mock_approvals');
            if (mockApprovalsStr) {
              const mockApprovals = JSON.parse(mockApprovalsStr);
              console.log(`从mock_approvals获取到${mockApprovals.length}条审批`);
              
              mockApprovals.forEach(approval => {
                if (approval && approval.id && !approvalMap.has(approval.id.toString())) {
                  approvalMap.set(approval.id.toString(), { ...approval, _source: 'mock_approvals' });
                }
              });
            }
          } catch (error) {
            console.error('读取mock_approvals失败:', error);
          }
          
          // 将Map转换为数组
          const allApprovals = Array.from(approvalMap.values());
          console.log(`去重后共有${allApprovals.length}条审批`);
          
          // 查找该用户处理过的审批
          completedDocs = allApprovals.filter(doc => {
            // 状态为已完成、已拒绝等非待处理状态
            const statusMatch = doc.status === 'completed' || 
                               doc.status === 'rejected' || 
                               doc.status === 'approved';
            
            // 检查是否由当前用户处理过
            let processedByCurrentUser = false;
            
            // 检查历史记录
            if (doc.history && Array.isArray(doc.history)) {
              processedByCurrentUser = doc.history.some(record => {
                return record.approver === currentUser.username || 
                       record.approver === currentUser.full_name ||
                       record.approver === currentUser.real_name ||
                       record.approver_id === currentUser.id;
              });
            }
            
            // 如果是管理员，也可以查看所有已完成审批
            if (currentUser.is_admin || currentUser.roles?.includes('admin')) {
              return statusMatch;
            }
            
            return statusMatch && processedByCurrentUser;
          });
          
          console.log(`筛选出${completedDocs.length}条已处理审批`);
          
          // 如果没有找到已处理审批，展示所有已完成的审批（开发便利）
          if (completedDocs.length === 0) {
            console.log('未找到已处理审批，显示所有已完成审批');
            completedDocs = allApprovals.filter(doc => 
              doc.status === 'completed' || 
              doc.status === 'rejected' || 
              doc.status === 'approved'
            );
          }
        } else {
          // 生产环境使用API
          try {
            const response = await api.getCompletedApprovals();
            completedDocs = Array.isArray(response) ? response : 
                           (response.data && Array.isArray(response.data) ? response.data : []);
          } catch (error) {
            console.error('API获取已处理审批失败:', error);
          }
        }
        
        // 处理日期和添加其他必要信息
        completedDocs = completedDocs.map(doc => {
          if (!doc.created_at) {
            doc.created_at = new Date().toISOString();
          }
          return doc;
        });
        
        // 确保没有重复ID的审批（最终确认）
        const finalMap = new Map();
        completedDocs.forEach(doc => {
          if (doc && doc.id) {
            finalMap.set(doc.id.toString(), doc);
          }
        });
        completedDocs = Array.from(finalMap.values());
        
        // 按完成时间降序排序
        completedDocs.sort((a, b) => {
          const aTime = a.completed_at || a.updated_at || a.created_at;
          const bTime = b.completed_at || b.updated_at || b.created_at;
          return new Date(bTime) - new Date(aTime);
        });
        
        console.log('最终已处理文档列表:', completedDocs);
        this.doneDocuments = completedDocs;
        // 更新显示的文档（当前激活标签页是已办时）
        if (this.activeTab === 'done') {
          this.documents = completedDocs;
        }
      } catch (error) {
        console.error('获取已处理文档失败:', error);
        message.error('获取已处理文档失败');
      } finally {
        this.loading = false;
      }
    },
    // 获取工作流配置
    async getWorkflowConfig(workflowId) {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token');
      
      // 模拟数据
      if (token === 'mock_admin_token' || token === 'mock_user_token' || token === 'mock_manager_token') {
        this.workflowConfig = workflowData;
        return;
      }
      
      try {
        // 实际API调用
        const response = await api.get(`/api/workflow-designer/${workflowId}`);
        this.workflowConfig = response.data.workflow_config;
      } catch (error) {
        console.error('获取工作流配置失败:', error);
        // 使用备用工作流配置
        this.workflowConfig = workflowData;
      }
    },
    // 选择工作流
    selectWorkflow(workflow) {
      try {
        // 记录已选择的工作流
        this.selectedWorkflow = workflow;
        message.success(`已选择工作流: ${workflow.name}`);
        
        // 实际项目中可能需要跳转到新建文档页面
        console.log(`选择了工作流: ${workflow.id} - ${workflow.name}`);
        
        // 模拟弹窗显示选择结果
        this.$modal?.info?.({
          title: '已选择工作流',
          content: `您已成功选择"${workflow.name}"工作流，可以开始创建文档。`,
          okText: '确定'
        });
      } catch (error) {
        console.error('选择工作流失败:', error);
        message.error('选择工作流失败，请重试');
      }
    },
    // 为表单选择工作流
    selectWorkflowForForm(workflow) {
      this.selectedWorkflowId = workflow.id;
      this.selectedWorkflow = workflow;
      this.newApproval.workflow_id = workflow.id;
      
      console.log("选择工作流:", workflow.name, workflow.id);
      
      // 重置表单数据
      this.newApproval.form_data = {};
      
      // 根据工作流名称映射到对应的表单模式ID
      let formSchemaId = null; // 默认不使用表单
      
      // 通过名称和ID尝试匹配合适的表单模式
      if (workflow.name.toLowerCase().includes("请假") || workflow.id === 1) {
        formSchemaId = "1"; // 使用请假申请表单
      } else if (workflow.name.toLowerCase().includes("报销") || workflow.id === 2) {
        formSchemaId = "2"; // 使用报销申请表单
      } else if (workflow.name.toLowerCase().includes("采购") || workflow.id === 3) {
        formSchemaId = "3"; // 使用采购申请表单
      } else if (workflow.name.toLowerCase().includes("财务")) {
        formSchemaId = "4"; // 使用财务审批表单
      }
      
      if (formSchemaId) {
        console.log("选择表单模式:", formSchemaId);
        // 获取对应的表单模式
        this.getFormSchema(formSchemaId);
      } else {
        console.log("未找到匹配的表单模式，使用基础表单");
        // 清空现有表单模式，使用基础表单
        this.formSchema = null;
      }
    },
    // 获取表单模式
    async getFormSchema(workflowId) {
      try {
        this.loading = true;
        console.log(`正在获取表单模式: ${workflowId}`);
        
        // 获取工作流对应的表单模式
        const response = await api.get(`/api/approval/form-schema/${workflowId}`);
        
        if (response && response.data) {
          this.formSchema = response.data;
          console.log('获取到表单模式:', this.formSchema);
          
          // 检查返回的表单是否为基础简化表单
          if (this.formSchema.is_simple || 
              (this.formSchema.fields && this.formSchema.fields.length <= 2)) {
            console.log('检测到基础简化表单，将使用基础表单界面');
            this.formSchema = null; // 使用基础表单界面
          }
        } else {
          console.warn('返回的表单模式无效，将使用基础表单');
          this.formSchema = null;
        }
      } catch (error) {
        console.error('获取表单模式失败:', error);
        console.log('将使用基础表单');
        this.formSchema = null;
      } finally {
        this.loading = false;
      }
    },
    // 使用Agent辅助填写表单
    async getFormAssistance() {
      if (this.isAssistantResponding) return;
      
      this.isAssistantResponding = true;
      this.formGuide = '正在生成建议...';
      
      try {
        // 开发环境中返回模拟数据
        if (process.env.NODE_ENV === 'development') {
          console.log('开发环境: 使用模拟数据');
          
          // 等待一小段时间，模拟网络请求
          await new Promise(resolve => setTimeout(resolve, 1500));
          
          // 根据表单类型生成不同建议
          let suggestion = '';
          if (this.selectedWorkflow?.name?.includes('请假')) {
            suggestion = '请填写请假的起止时间、请假类型和请假原因。\n如果是病假，请记得上传医院证明文件。\n如果请假时间超过3天，请在原因中详细说明情况。';
          } else if (this.selectedWorkflow?.name?.includes('报销')) {
            suggestion = '请填写报销金额、费用类型和用途说明。\n记得上传发票或收据照片作为凭证。\n如果报销金额超过5000元，需要部门经理和财务主管双重审批。';
          } else {
            suggestion = '请填写完整的表单信息，确保所有必填项都已填写。\n如有相关附件，请一并上传以加快审批流程。\n标题应简明扼要地概括申请内容。';
          }
          
          this.formGuide = suggestion;
          this.isAssistantResponding = false;
          return;
        }
        
        // 生产环境使用真实API
        const response = await api.post('/api/agent/assist', {
          task: 'form_assistance',
          form_schema: this.formSchema,
          form_title: this.selectedWorkflow?.name || '表单',
          current_values: this.newApproval.form_data
        });
        
        if (response.data && response.data.success) {
          this.formGuide = response.data.response;
        } else {
          this.formGuide = response.data?.response || '无法获取填写建议';
        }
      } catch (error) {
        console.error('获取表单填写建议失败:', error);
        this.formGuide = '无法获取填写建议，请手动填写表单';
      } finally {
        this.isAssistantResponding = false;
      }
    },
    // 处理文件上传
    handleFileUpload(event) {
      const files = event.target.files;
      if (!files || !files.length) return;
      
      // 将文件添加到上传列表
      for (let i = 0; i < files.length; i++) {
        this.uploadedFiles.push(files[i]);
      }
    },
    // 删除上传的文件
    removeFile(index) {
      this.uploadedFiles.splice(index, 1);
    },
    // 创建审批
    async createApproval() {
      if (this.isSubmitting) return;
      
      if (!this.newApproval.title) {
        message.warn('请填写审批标题');
        return;
      }
      
      if (!this.newApproval.workflow_id) {
        message.warn('请选择流程');
        return;
      }
      
      // 检查基础表单必填内容
      if (!this.formSchema && !this.newApproval.content) {
        message.warn('请填写内容描述');
        return;
      }
      
      this.isSubmitting = true;
      
      try {
        // 显示loading提示
        const loadingMessage = message.loading('正在提交审批申请...', 0);
        
        // 获取当前用户ID
        const currentUserId = this.getCurrentUserId();
        
        // 构建审批数据
        const approvalData = {
          title: this.newApproval.title,
          content: this.newApproval.content || '',
          workflow_id: this.newApproval.workflow_id,
          form_data: this.formSchema ? this.newApproval.form_data : { content: this.newApproval.content },
          emergency_level: this.newApproval.emergency_level || 0,
          initiator_id: currentUserId,
          initiator: this.getCurrentUser().username
        };
        
        console.log('创建审批:', approvalData);
        
        // 调用API创建审批
        const response = await api.submitApproval(approvalData);
        
        // 关闭loading提示
        loadingMessage();
        
        if (response.success) {
          // 创建成功，显示提示
          message.success('审批创建成功');
          
          // 检查api.js是否干净地处理了本地存储，如果有多个存储位置都保存了相同审批，我们应该清理它们
          if (process.env.NODE_ENV === 'development') {
            console.log('确保审批数据不会重复存储');
            
            // 清理其他存储位置中可能出现的重复项
            try {
              const approvalId = response.data?.id;
              if (approvalId) {
                console.log('审批ID:', approvalId);
                
                // 确保各个存储位置中只有一条记录
                this.deduplicateApproval(approvalId);
              }
            } catch (error) {
              console.error('清理重复审批数据失败:', error);
            }
          }
          
          // 刷新列表数据
          await this.fetchMyDocuments();
          
          // 关闭表单并重置
          this.showNewApprovalForm = false;
          this.resetForm();
        } else {
          message.error(response.message || '创建失败');
        }
      } catch (error) {
        console.error('创建审批失败:', error);
        message.error('创建失败: ' + (error.message || '未知错误'));
      } finally {
        this.isSubmitting = false;
      }
    },
    
    // 取消审批
    cancelApproval() {
      // 如果正在提交，不允许取消
      if (this.isSubmitting) {
        return;
      }
      
      // 检查表单是否已填写，如果已填写，提示用户确认
      const hasFormData = this.formSchema && Object.keys(this.newApproval.form_data).some(key => !!this.newApproval.form_data[key]);
      const hasContent = this.newApproval.content;
      
      if ((hasFormData || hasContent) && this.newApproval.title) {
        // 有填写内容，显示确认对话框
        this.$confirm({
          title: '确认取消',
          content: '表单已填写，取消将丢失已填写的内容，确定要取消吗？',
          okText: '确认取消',
          cancelText: '继续编辑',
          onOk: () => {
            this.showNewApprovalForm = false;
            this.resetForm();
          }
        });
      } else {
        // 没有填写内容，直接关闭
        this.showNewApprovalForm = false;
        this.resetForm();
      }
    },
    
    // 审批数据去重
    deduplicateApproval(approvalId) {
      console.log(`开始为审批ID ${approvalId} 进行去重`);
      
      const storageKeys = ['local_approvals', 'mock_approvals', 'my_approvals'];
      
      for (const key of storageKeys) {
        try {
          const storageStr = localStorage.getItem(key);
          if (!storageStr) continue;
          
          let items = JSON.parse(storageStr);
          if (!Array.isArray(items) || items.length === 0) continue;
          
          // 检查是否有多个相同ID的审批
          const idOccurrences = items.filter(item => item.id == approvalId).length;
          if (idOccurrences > 1) {
            console.log(`在 ${key} 中发现 ${idOccurrences} 个ID为 ${approvalId} 的审批，进行去重`);
            
            // 只保留第一个找到的审批
            const firstFound = items.find(item => item.id == approvalId);
            items = items.filter(item => item.id != approvalId);
            if (firstFound) {
              items.push({...firstFound, _persistent: true});
            }
            
            // 保存回存储
            localStorage.setItem(key, JSON.stringify(items));
            console.log(`成功更新 ${key}，现在只有1个ID为 ${approvalId} 的审批`);
          }
        } catch (error) {
          console.error(`处理 ${key} 失败:`, error);
        }
      }
    },
    
    // 保存审批到所有本地存储位置
    saveApprovalToAllStorages(approvalData) {
      console.log('保存审批到所有本地存储:', approvalData);
      
      // 确保有持久化标记
      approvalData._persistent = true;
      
      // 为my_approvals添加额外标记
      const myApprovalData = {
        ...approvalData,
        _fromMyApprovals: true
      };
      
      // 1. 保存到my_approvals (用户自己的审批)
      this.saveToLocalStorage('my_approvals', myApprovalData);
      
      // 2. 保存到local_approvals (所有本地审批)
      this.saveToLocalStorage('local_approvals', approvalData);
      
      // 3. 保存到mock_approvals (模拟审批)
      this.saveToLocalStorage('mock_approvals', approvalData);
      
      // 4. 尝试使用api.saveApprovalToLocal (如果可用)
      if (api.saveApprovalToLocal) {
        try {
          api.saveApprovalToLocal(approvalData, true);
          console.log('使用api.saveApprovalToLocal保存成功');
        } catch (e) {
          console.error('使用api.saveApprovalToLocal保存失败:', e);
        }
      }
      
      console.log('审批数据已保存到所有本地存储');
    },
    
    // 保存到指定的本地存储
    saveToLocalStorage(storageKey, data) {
      try {
        // 读取现有数据
        let existingData = [];
        const existingStr = localStorage.getItem(storageKey);
        
        if (existingStr) {
          existingData = JSON.parse(existingStr);
          if (!Array.isArray(existingData)) {
            console.warn(`${storageKey}不是数组，重置为空数组`);
            existingData = [];
          }
        }
        
        // 查找是否已存在相同ID
        const existingIndex = existingData.findIndex(item => item.id === data.id);
        
        if (existingIndex >= 0) {
          // 更新现有数据
          existingData[existingIndex] = data;
          console.log(`更新${storageKey}中ID=${data.id}的数据`);
        } else {
          // 添加新数据
          existingData.push(data);
          console.log(`添加新数据到${storageKey}, ID=${data.id}`);
        }
        
        // 保存回本地存储
        localStorage.setItem(storageKey, JSON.stringify(existingData));
        console.log(`成功保存到${storageKey}, 现有${existingData.length}条数据`);
      } catch (error) {
        console.error(`保存到${storageKey}失败:`, error);
        throw error;
      }
    },
    
    // 验证本地存储中是否包含指定数据
    verifyLocalStorage(storageKey, data) {
      try {
        const storageStr = localStorage.getItem(storageKey);
        if (!storageStr) {
          console.warn(`${storageKey}为空`);
          return false;
        }
        
        const storageData = JSON.parse(storageStr);
        if (!Array.isArray(storageData)) {
          console.warn(`${storageKey}不是数组`);
          return false;
        }
        
        const found = storageData.some(item => item.id === data.id);
        console.log(`${storageKey}中${found ? '找到' : '未找到'}ID=${data.id}的数据`);
        return found;
      } catch (error) {
        console.error(`验证${storageKey}失败:`, error);
        return false;
      }
    },
    // 重置表单
    resetForm() {
      this.newApproval = {
        title: '',
        content: '',
        workflow_id: '',
        form_data: {},
        emergency_level: 0
      };
      this.uploadedFiles = [];
      this.formGuide = '';
      this.selectedWorkflow = null;
      this.selectedWorkflowId = null;
    },
    // 获取节点配置
    getNodeConfig(nodeId) {
      if (!this.workflowConfig || !this.workflowConfig.nodes) return null;
      
      return this.workflowConfig.nodes.find(node => node.id === nodeId);
    },
    // 打开发起审批表单
    openNewApprovalForm() {
      if (!this.checkUserAuth()) {
        return;
      }
      
      this.showNewApprovalForm = true;
      this.resetForm();
      
      // 如果存在预设数据，填充表单
      if (this.presetApprovalData) {
        console.log('使用预设数据填充审批表单:', this.presetApprovalData);
        
        // 如果是请假类型，尝试找到请假工作流
        if (this.presetApprovalData.type === '请假') {
          const leaveWorkflow = this.workflows.find(w => w.name.includes("请假") || w.id === 1);
          if (leaveWorkflow) {
            this.selectWorkflowForForm(leaveWorkflow);
            
            // 设置标题
            this.newApproval.title = `请假申请 - ${this.presetApprovalData.days}天`;
            
            // 设置表单数据
            this.newApproval.form_data = {
              ...this.newApproval.form_data,
              days: this.presetApprovalData.days || 1,
              reason: this.presetApprovalData.reason || '家里有事'
            };
          }
        } else {
          // 其他类型审批
          // 设置标题
          this.newApproval.title = this.presetApprovalData.type || '新审批';
          
          // 设置表单数据
          if (this.presetApprovalData.reason) {
            this.newApproval.content = this.presetApprovalData.reason;
          }
        }
        
        // 使用后清除预设数据
        this.$nextTick(() => {
          this.presetApprovalData = null;
        });
      }
    },
    // 处理审批
    async submitApproval(action) {
      if (!this.selectedDocument) {
        message.warning('请选择要处理的文档');
          return;
        }
        
      if (!this.approvalComment) {
        message.warning('请输入审批意见');
        return;
      }
      
      try {
        const payload = {
          action: action.id,
          comment: this.approvalComment,
          user_id: this.getCurrentUserId()
        };
        
        const response = await api.post(`/approval/process/${this.selectedDocument.id}`, payload);
        
        if (response.data) {
          message.success(`审批${this.getActionName(action.id)}成功`);
          
          // 关闭处理弹窗并刷新数据
          this.showProcessModal = false;
          this.approvalComment = '';
          this.fetchPendingDocuments();
        }
      } catch (error) {
        console.error('处理审批失败:', error);
        message.error(error.response?.data?.detail || '处理失败，请稍后重试');
      }
    },
    // 获取当前用户ID
    getCurrentUserId() {
      try {
        // 尝试从localStorage或sessionStorage获取用户信息
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (userStr) {
          const user = JSON.parse(userStr);
          console.log('当前登录用户:', user);
          return user.id;
        }
      } catch (e) {
        console.error('获取当前用户ID失败:', e);
      }
      console.warn('未找到当前用户ID，使用默认值1');
      return 1; // 默认用户ID
    },
    
    // 获取当前用户信息
    getCurrentUser() {
      try {
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (userStr) {
          const user = JSON.parse(userStr);
          console.log('获取到当前用户信息:', user);
          return user;
        }
      } catch (e) {
        console.error('获取当前用户信息失败:', e);
      }
      return { id: 1, username: 'admin', full_name: '系统管理员' };
    },
    // 格式化日期
    formatDate(dateString) {
      if (!dateString) return '未知时间';
      
      try {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        });
      } catch (e) {
        console.error('日期格式化错误:', e);
        return dateString;
      }
    },
    // 处理审批完成后的更新
    handleApprovalUpdated(data) {
      console.log('审批更新:', data);
      // 刷新待处理文档列表
      this.fetchPendingDocuments();
      
      // 显示操作结果通知
      const actionMap = {
        'approve': '同意',
        'reject': '拒绝',
        'return': '退回'
      };
      
      alert(`已${actionMap[data.action] || '处理'}该审批`);
      
      // 关闭模态框（可选，也可以保持打开让用户查看结果）
      // this.showProcessModal = false;
    },
    
    // 撤回文档
    withdrawDocument(doc) {
      AntModal.confirm({
        title: '确认撤回',
        content: `确定要撤回 "${doc.title}" 吗？`,
        okText: '确认',
        cancelText: '取消',
        onOk: () => {
          // 调用撤回接口
          this.loading = true;
          console.log('开始撤回文档:', doc.id);
          
          api.withdrawApproval(doc.id)
            .then(response => {
              this.loading = false;
              console.log('撤回结果:', response);
              
              if (response.success) {
                this.$message.success('文档已成功撤回');
                
                // 先在本地UI更新状态
                const index = this.myDocuments.findIndex(d => d.id == doc.id);
                if (index !== -1) {
                  this.myDocuments[index].status = 'withdrawn';
                  this.myDocuments[index].current_node = '已撤回';
                }
                
                // 不需要重新加载列表，状态已在UI中更新
                // this.fetchMyDocuments();

                // 询问用户是否要删除该审批单
                setTimeout(() => {
                  AntModal.confirm({
                    title: '是否删除',
                    content: '文档已撤回，是否同时删除该审批单？',
                    okText: '确认',
                    cancelText: '取消',
                    onOk: () => {
                      console.log('用户确认删除撤回的审批单:', doc.id);
                      
                      // 调用删除接口
                      this.deleteDocument({...doc, status: 'withdrawn'});
                    },
                    onCancel: () => {
                      console.log('用户取消删除');
                    }
                  });
                }, 500);
              } else {
                this.$message.error(response.message || '撤回失败');
              }
            })
            .catch(error => {
              this.loading = false;
              console.error('撤回文档失败:', error);
              
              // 在开发环境下，手动更新审批状态为已撤回
              if (process.env.NODE_ENV === 'development') {
                console.log('开发环境：尝试在本地更新审批状态为已撤回');
                
                // 在UI中更新状态
                const index = this.myDocuments.findIndex(d => d.id == doc.id);
                if (index !== -1) {
                  this.myDocuments[index].status = 'withdrawn';
                  this.myDocuments[index].current_node = '已撤回';
                }
                
                // 在local_approvals中更新
                try {
                  let localApprovals = [];
                  const localApprovalsStr = localStorage.getItem('local_approvals');
                  if (localApprovalsStr) {
                    localApprovals = JSON.parse(localApprovalsStr);
                    for (let i = 0; i < localApprovals.length; i++) {
                      if (localApprovals[i].id == doc.id) {
                        localApprovals[i].status = 'withdrawn';
                        localApprovals[i].current_node = '已撤回';
                        localApprovals[i].updated_at = new Date().toISOString();
                      }
                    }
                    localStorage.setItem('local_approvals', JSON.stringify(localApprovals));
                  }
                } catch (e) {
                  console.error('更新local_approvals失败:', e);
                }
                
                // 在my_approvals中更新
                try {
                  let myApprovals = [];
                  const myApprovalsStr = localStorage.getItem('my_approvals');
                  if (myApprovalsStr) {
                    myApprovals = JSON.parse(myApprovalsStr);
                    for (let i = 0; i < myApprovals.length; i++) {
                      if (myApprovals[i].id == doc.id) {
                        myApprovals[i].status = 'withdrawn';
                        myApprovals[i].current_node = '已撤回';
                        myApprovals[i].updated_at = new Date().toISOString();
                      }
                    }
                    localStorage.setItem('my_approvals', JSON.stringify(myApprovals));
                  }
                } catch (e) {
                  console.error('更新my_approvals失败:', e);
                }
                
                // 在mock_approvals中更新
                try {
                  let mockApprovals = [];
                  const mockApprovalsStr = localStorage.getItem('mock_approvals');
                  if (mockApprovalsStr) {
                    mockApprovals = JSON.parse(mockApprovalsStr);
                    for (let i = 0; i < mockApprovals.length; i++) {
                      if (mockApprovals[i].id == doc.id) {
                        mockApprovals[i].status = 'withdrawn';
                        mockApprovals[i].current_node = '已撤回';
                        mockApprovals[i].updated_at = new Date().toISOString();
                      }
                    }
                    localStorage.setItem('mock_approvals', JSON.stringify(mockApprovals));
                  }
                } catch (e) {
                  console.error('更新mock_approvals失败:', e);
                }
                
                this.$message.success('文档已在本地撤回');
                // 不需要重新加载列表，状态已在UI和localStorage中更新
                // this.fetchMyDocuments();
                
                // 询问用户是否删除
                setTimeout(() => {
                  AntModal.confirm({
                    title: '是否删除',
                    content: '文档已撤回，是否同时删除该审批单？',
                    okText: '确认',
                    cancelText: '取消',
                    onOk: () => {
                      console.log('用户确认删除撤回的审批单:', doc.id);
                      this.deleteDocument({...doc, status: 'withdrawn'});
                    },
                    onCancel: () => {
                      console.log('用户取消删除');
                    }
                  });
                }, 500);
              } else {
                this.$message.error('撤回失败: ' + (error.message || '未知错误'));
              }
            });
        }
      });
    },
    
    // 获取状态显示样式
    getStatusClass(status) {
      const classMap = {
        'pending': 'status-pending',
        'processing': 'status-processing',
        'completed': 'status-completed',
        'rejected': 'status-rejected',
        'withdrawn': 'status-withdrawn'
      };
      return classMap[status] || '';
    },
    
    // 获取状态文本
    getStatusText(status) {
      const statusMap = {
        'pending': '待处理',
        'processing': '处理中',
        'completed': '已完成',
        'rejected': '已拒绝',
        'withdrawn': '已撤回'
      };
      return statusMap[status] || status;
    },
    
    // 获取紧急程度样式
    getEmergencyClass(level) {
      const levelMap = {
        0: 'level-normal',
        1: 'level-medium',
        2: 'level-high',
        3: 'level-urgent'
      };
      return levelMap[level] || 'level-normal';
    },
    
    // 获取紧急程度文本
    getEmergencyText(level) {
      const levelMap = {
        0: '普通',
        1: '中等',
        2: '紧急',
        3: '特急'
      };
      return levelMap[level] || '普通';
    },
    // 获取我发起的文档
    async fetchMyDocuments() {
      this.loading = true;
      console.log('开始获取我的文档');
      
      try {
        // 获取当前用户信息
        const currentUser = this.getCurrentUser();
        if (!currentUser) {
          console.warn('未找到当前用户信息，无法获取文档');
          this.loading = false;
          return;
        }
        
        console.log('当前用户:', currentUser);
        let myDocuments = [];
        
        // 开发环境下从本地存储获取数据
        if (process.env.NODE_ENV === 'development') {
          console.log('开发环境: 从本地存储获取审批数据');
          
          // 1. 从my_approvals获取数据（用户自己的审批）
          let myApprovals = [];
          try {
            const myApprovalsStr = localStorage.getItem('my_approvals');
            if (myApprovalsStr) {
              myApprovals = JSON.parse(myApprovalsStr);
              console.log(`从my_approvals获取到${myApprovals.length}条审批`);
            }
          } catch (error) {
            console.error('读取my_approvals失败:', error);
          }
          
          // 2. 从local_approvals获取数据（所有本地审批）
          let localApprovals = [];
          try {
            const localApprovalsStr = localStorage.getItem('local_approvals');
            if (localApprovalsStr) {
              localApprovals = JSON.parse(localApprovalsStr);
              console.log(`从local_approvals获取到${localApprovals.length}条审批`);
            }
          } catch (error) {
            console.error('读取local_approvals失败:', error);
          }
          
          // 3. 从mock_approvals获取数据（模拟审批）
          let mockApprovals = [];
          try {
            const mockApprovalsStr = localStorage.getItem('mock_approvals');
            if (mockApprovalsStr) {
              mockApprovals = JSON.parse(mockApprovalsStr);
              console.log(`从mock_approvals获取到${mockApprovals.length}条审批`);
            }
          } catch (error) {
            console.error('读取mock_approvals失败:', error);
          }
          
          // 合并所有来源的审批数据并去重
          // 使用Map按ID去重，优先保留my_approvals中的数据
          const approvalMap = new Map();
          
          // 先处理myApprovals，这些数据优先级最高
          myApprovals.forEach(approval => {
            if (approval && approval.id) {
              approvalMap.set(approval.id.toString(), { ...approval, _source: 'my_approvals' });
            }
          });
          
          // 然后处理localApprovals
          localApprovals.forEach(approval => {
            if (approval && approval.id && !approvalMap.has(approval.id.toString())) {
              approvalMap.set(approval.id.toString(), { ...approval, _source: 'local_approvals' });
            }
          });
          
          // 最后处理mockApprovals
          mockApprovals.forEach(approval => {
            if (approval && approval.id && !approvalMap.has(approval.id.toString())) {
              approvalMap.set(approval.id.toString(), { ...approval, _source: 'mock_approvals' });
            }
          });
          
          // 将Map转换为数组
          const allApprovals = Array.from(approvalMap.values());
          console.log(`去重后共有${allApprovals.length}条审批`);
          
          // 检查是否属于当前用户的审批
          myDocuments = allApprovals.filter(doc => {
            // 多种方式匹配当前用户
            return (
              // 匹配ID
              (doc.initiator_id && doc.initiator_id == currentUser.id) ||
              // 匹配用户名
              (doc.initiator && (
                doc.initiator === currentUser.username || 
                doc.initiator === currentUser.full_name ||
                doc.initiator === currentUser.real_name ||
                doc.initiator === "当前用户"
              )) ||
              // 匹配"当前用户"标记
              (doc.initiator === "当前用户") ||
              // 匹配创建者ID
              (doc.creator_id && doc.creator_id == currentUser.id) ||
              // 特定标记
              (doc._fromMyApprovals === true)
            );
          });
          
          console.log(`匹配到当前用户(${currentUser.username})的审批:`, myDocuments.length);
          
          // 如果没有找到匹配的审批，尝试查找所有本地审批
          if (myDocuments.length === 0) {
            console.log('未找到匹配的审批，将显示所有本地审批');
            myDocuments = allApprovals;
          }
        } else {
          // 生产环境使用API
          try {
            const response = await api.getMyApprovals();
            if (response && Array.isArray(response)) {
              myDocuments = response;
            } else if (response && response.data && Array.isArray(response.data)) {
              myDocuments = response.data;
            }
          } catch (error) {
            console.error('API获取我的审批失败:', error);
          }
        }
        
        // 确保所有文档有必要的字段
        myDocuments = myDocuments.map(doc => {
          // 确保有workflow信息
          if (!doc.workflow && doc.workflow_id) {
            const workflow = this.workflows.find(w => w.id === doc.workflow_id);
            if (workflow) {
              doc.workflow = {
                id: workflow.id,
                name: workflow.name
              };
            } else {
              doc.workflow = { name: "未知流程" };
            }
          }
          
          // 确保有创建日期
          if (!doc.created_at) {
            doc.created_at = new Date().toISOString();
          }
          
          return doc;
        });
        
        // 按照创建时间排序，最新的在前面
        myDocuments.sort((a, b) => {
          return new Date(b.created_at) - new Date(a.created_at);
        });
        
        // 如果没有找到数据，在开发环境使用测试数据
        if (myDocuments.length === 0 && process.env.NODE_ENV === 'development') {
          console.warn('未找到审批数据，使用测试数据');
          myDocuments = [
            {
              id: 10001,
              title: "测试审批 - 请假申请",
              workflow_id: 1,
              workflow: { name: "请假流程" },
              status: "pending",
              initiator: currentUser.username || "当前用户",
              initiator_id: currentUser.id || 1,
              created_at: new Date().toISOString(),
              _persistent: true
            }
          ];
        }
        
        // 最终再次确认没有重复ID的审批
        const finalApprovalMap = new Map();
        myDocuments.forEach(doc => {
          if (doc && doc.id) {
            finalApprovalMap.set(doc.id.toString(), doc);
          }
        });
        myDocuments = Array.from(finalApprovalMap.values());
        
        console.log('最终我的文档列表:', myDocuments);
        this.myDocuments = myDocuments;
      } catch (error) {
        console.error('获取我的文档失败:', error);
        message.error('获取文档失败');
      } finally {
        this.loading = false;
      }
    },
    // 打开发起请假表单
    openLeaveApprovalForm() {
      if (!this.checkUserAuth()) return;
      
      // 查找请假流程
      const leaveWorkflow = this.workflows.find(w => w.name.includes("请假") || w.id === 1);
      
      if (leaveWorkflow) {
        this.showNewApprovalForm = true;
        this.resetForm();
        
        // 自动选择请假工作流
        this.selectWorkflowForForm(leaveWorkflow);
        
        // 如果存在预设数据，填充表单
        if (this.presetApprovalData) {
          console.log('使用预设数据填充请假表单:', this.presetApprovalData);
          
          // 设置标题
          this.newApproval.title = `请假申请 - ${this.presetApprovalData.days}天`;
          
          // 设置表单数据
          this.newApproval.form_data = {
            ...this.newApproval.form_data,
            days: this.presetApprovalData.days || 1,
            reason: this.presetApprovalData.reason || '家里有事'
          };
          
          // 使用后清除预设数据
          this.$nextTick(() => {
            this.presetApprovalData = null;
          });
        }
      } else {
        message.warning('未找到请假流程，请先创建');
      }
    },
    // 暴露给外部的方法（避免递归调用）
    handleExternalLeaveApprovalRequest() {
      // 直接调用内部方法，而不是再次调用openLeaveApprovalForm
      if (!this.checkUserAuth()) return;
      
      // 查找请假流程
      const leaveWorkflow = this.workflows.find(w => w.name.includes("请假") || w.id === 1);
      
      if (leaveWorkflow) {
        this.showNewApprovalForm = true;
        this.resetForm();
        
        // 自动选择请假工作流
        this.selectWorkflowForForm(leaveWorkflow);
        
        // 如果存在预设数据，填充表单
        if (this.presetApprovalData) {
          console.log('使用预设数据填充请假表单:', this.presetApprovalData);
          
          // 设置标题
          this.newApproval.title = `请假申请 - ${this.presetApprovalData.days}天`;
          
          // 设置表单数据
          this.newApproval.form_data = {
            ...this.newApproval.form_data,
            days: this.presetApprovalData.days || 1,
            reason: this.presetApprovalData.reason || '家里有事'
          };
          
          // 使用后清除预设数据
          this.$nextTick(() => {
            this.presetApprovalData = null;
          });
        }
      } else {
        message.warning('未找到请假流程，请先创建');
      }
    },
    // 处理审批撤回
    async withdrawApproval(id) {
      try {
        const response = await api.withdrawApproval(id);
        console.log('撤回审批响应:', response);
        
        if (response.status === 200 || response.status === 204) {
          this.$message.success('撤回成功');
          
          // 更新本地状态
          const index = this.myDocuments.findIndex(doc => doc.id === id);
          if (index !== -1) {
            this.myDocuments[index].status = 'withdrawn';
            this.myDocuments[index].current_node = '已撤回';
            
            // 更新localStorage
            try {
              localStorage.setItem('mock_approvals', JSON.stringify(this.myDocuments));
            } catch (e) {
              console.error('更新本地存储失败:', e);
            }
          }
          
          // 刷新我的文档列表
          this.fetchMyDocuments();
        } else {
          this.$message.error('撤回失败: ' + (response.data?.message || '未知错误'));
        }
      } catch (error) {
        console.error('撤回审批错误:', error);
        this.$message.error('撤回失败: ' + (error.message || '网络错误'));
      }
    },
    // 加载文档详情
    async loadDocumentDetails(docId) {
      try {
        // 尝试从API获取文档详情
        const response = await api.getApprovalDetail(docId);
        
        if (response.data) {
          // 更新选中的文档信息
          this.selectedDocument = {
            ...this.selectedDocument,
            ...response.data
          };
          console.log('已加载文档详情:', this.selectedDocument);
          return;
        }
      } catch (error) {
        console.error('获取文档详情失败:', error);
        // 继续使用现有数据
      }
      
      // 如果API失败，保持使用当前数据
      console.log('使用现有文档数据:', this.selectedDocument);
    },
    // 获取紧急程度文本
    getEmergencyLevelText(level) {
      const levelMap = {
        0: '普通',
        1: '中等',
        2: '紧急',
        3: '特急'
      };
      return levelMap[level] || '普通';
    },
    // 判断是否可以撤回审批
    canWithdraw(doc) {
      // 只有发起人可以撤回审批，且只能在审批未完成时撤回
      const isInitiator = doc.initiator === this.currentUser?.username || doc.initiator === '当前用户';
      return isInitiator && (doc.status === 'pending' || doc.status === 'processing');
    },
    // 添加删除文档方法
    deleteDocument(doc) {
      if (!doc || !doc.id) {
        console.error('无法删除文档：文档ID缺失');
        alert('无法删除文档：文档ID缺失');
        return;
      }

      // 定义确认删除的处理函数
      const confirmDelete = () => {
          console.log('开始删除审批单:', doc.id);
          
          // 标记加载状态
          this.isLoading = true;
          
          // 尝试删除审批
          api.deleteApproval(doc.id)
            .then((result) => {
              console.log('删除结果:', result);
              // 使用原生alert确保消息显示
              alert('文档已成功删除');
              
              // 删除所有本地存储中的文档记录
              this.removeDocumentFromAllStorages(doc.id);
              
              // 直接从列表中移除文档，不重新加载
              this.myDocuments = this.myDocuments.filter(d => d.id != doc.id);
              
              console.log(`文档已从UI列表中删除，当前列表长度: ${this.myDocuments.length}`);
              
              // 不再调用fetchMyDocuments，避免重新加载已删除的数据
              // setTimeout(() => {
              //   this.fetchMyDocuments();
              // }, 300);
            })
            .catch(error => {
              console.error('删除文档失败:', error);
              
              // 即使API调用失败，在开发环境下也要尝试从本地数据中移除
              if (process.env.NODE_ENV === 'development') {
                console.log('开发环境：尝试从本地列表中删除文档');
                
                // 从所有本地存储中删除
                this.removeDocumentFromAllStorages(doc.id);
                
                // 然后从当前UI列表中移除
                this.myDocuments = this.myDocuments.filter(d => d.id != doc.id);
                
                console.log(`开发环境下文档已删除，当前列表长度: ${this.myDocuments.length}`);
                alert('文档已从本地存储中删除');
              } else {
                alert(error.message || '删除文档失败，请稍后重试');
              }
            })
            .finally(() => {
              this.isLoading = false;
            });
      };

      // 改进AntModal可用性检查，确保confirm方法存在
      try {
        if (AntModal && typeof AntModal.confirm === 'function') {
          AntModal.confirm({
            title: '确认删除',
            content: `确定要删除"${doc.title || '无标题'}"吗？此操作不可撤销。`,
            okText: '确认',
            cancelText: '取消',
            onOk: confirmDelete
          });
        } else {
          // 使用原生confirm作为后备方案
          if (confirm(`确定要删除"${doc.title || '无标题'}"吗？此操作不可撤销。`)) {
            confirmDelete();
          }
        }
      } catch (e) {
        console.error('调用Modal.confirm失败:', e);
        // 当AntModal出错时，降级使用浏览器原生confirm
        if (confirm(`确定要删除"${doc.title || '无标题'}"吗？此操作不可撤销。`)) {
          confirmDelete();
        }
      }
    },

    // 从所有本地存储中删除文档的辅助方法
    removeDocumentFromAllStorages(docId) {
      if (!docId) return;
      
      console.log(`开始从所有存储中删除文档ID=${docId}`);
      
      // 扩展存储键列表，包含所有可能的数据源
      const storageKeys = [
        'local_approvals', 
        'my_approvals', 
        'mock_approvals',
        'approvals',  // 添加通用的approvals键
        'pending_approvals',  // 添加待处理审批键
        'completed_approvals'  // 添加已完成审批键
      ];
      
      let deletedCount = 0;
      
      for (const key of storageKeys) {
        try {
          const storageStr = localStorage.getItem(key);
          if (!storageStr) continue;
          
          let items = JSON.parse(storageStr);
          if (!Array.isArray(items)) continue;
          
          const originalLength = items.length;
          // 过滤掉要删除的文档，使用严格比较和字符串比较
          const filteredItems = items.filter(item => 
            item.id !== docId && 
            item.id != docId && 
            item.id !== docId.toString() && 
            item.id !== parseInt(docId)
          );
          
          // 如果有变化，保存回存储
          if (filteredItems.length !== originalLength) {
            localStorage.setItem(key, JSON.stringify(filteredItems));
            deletedCount++;
            console.log(`已从${key}中删除文档ID=${docId}，原有${originalLength}条，现有${filteredItems.length}条`);
          }
        } catch (e) {
          console.error(`从${key}删除文档失败:`, e);
        }
      }
      
      // 同时调用storage.js中的deleteApproval方法
      try {
        if (window.storage && typeof window.storage.deleteApproval === 'function') {
          const result = window.storage.deleteApproval(docId);
          console.log('调用storage.deleteApproval结果:', result);
        } else {
          // 如果storage对象不可用，直接操作localStorage中的approvals键
          const approvalsStr = localStorage.getItem('approvals');
          if (approvalsStr) {
            try {
              let approvals = JSON.parse(approvalsStr);
              if (Array.isArray(approvals)) {
                const filteredApprovals = approvals.filter(item => 
                  item.id !== docId && 
                  item.id != docId && 
                  item.id !== docId.toString() && 
                  item.id !== parseInt(docId)
                );
                if (filteredApprovals.length !== approvals.length) {
                  localStorage.setItem('approvals', JSON.stringify(filteredApprovals));
                  console.log('已从approvals键中删除文档');
                  deletedCount++;
                }
              }
            } catch (e) {
              console.error('处理approvals键失败:', e);
            }
          }
        }
      } catch (e) {
        console.error('调用storage.deleteApproval失败:', e);
      }
      
      console.log(`删除操作完成，共从${deletedCount}个存储源中删除了文档ID=${docId}`);
    },
    // 判断是否可以删除审批
    canDelete(doc) {
      // 撤回的审批可以删除
      return doc.status === 'withdrawn';
    },
    // 检查URL查询参数中是否包含审批信息
    checkUrlParams() {
      const query = this.$route.query;
      
      if (query.action === 'create') {
        console.log('从URL参数创建审批:', query);
        
        // 设置预设数据
        this.presetApprovalData = {
          type: query.type || '请假',
          days: parseInt(query.days) || 1,
          reason: query.reason || '家里有事'
        };
        
        // 自动打开审批表单
        if (this.presetApprovalData.type === '请假') {
          this.$nextTick(() => {
            this.openLeaveApprovalForm();
          });
        } else {
          this.$nextTick(() => {
            this.openNewApprovalForm();
          });
        }
      }
    },
    
    // 检查localStorage中是否有预设审批数据
    checkLocalStoragePresetData() {
      try {
        const presetDataStr = localStorage.getItem('presetApprovalData');
        if (presetDataStr) {
          const presetData = JSON.parse(presetDataStr);
          console.log('从localStorage获取预设审批数据:', presetData);
          
          // 设置预设数据
          this.presetApprovalData = presetData;
          
          // 清除localStorage中的数据
          localStorage.removeItem('presetApprovalData');
          
          // 自动打开审批表单
          if (presetData.type === '请假') {
            this.$nextTick(() => {
              this.openLeaveApprovalForm();
            });
          } else {
            this.$nextTick(() => {
              this.openNewApprovalForm();
            });
          }
        }
      } catch (error) {
        console.error('解析localStorage中的预设审批数据失败:', error);
      }
    },
  },
  watch: {
    'newDocument.title': {
      handler(newVal) {
        if (newVal && newVal.length > 0) {
          // 使用防抖，避免频繁请求
          if (this.titleChangeTimer) {
            clearTimeout(this.titleChangeTimer);
          }
          this.titleChangeTimer = setTimeout(() => {
            this.getAIRecommendation();
          }, 500);
        }
      }
    },
    // 监听选择的流程ID变化
    'newDocument.workflow_id': {
      handler(newVal) {
        if(newVal) {
          this.updateWorkflowDescription(newVal);
        } else {
          this.selectedWorkflowDescription = '';
        }
      }
    }
  }
};
</script>

<style scoped>
.document-process {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 150px);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  font-size: 24px;
  color: #333;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 15px;
}

.create-btn {
  padding: 10px 20px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.create-btn:hover {
  background-color: #096dd9;
}

.search-bar {
  display: flex;
  gap: 5px;
}

.search-bar input {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  width: 200px;
}

.search-bar button {
  padding: 8px 15px;
  background-color: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  cursor: pointer;
}

.tabs {
  margin-bottom: 20px;
}

.tab-list {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #e8e8e8;
}

.tab-item {
  padding: 10px 20px;
  cursor: pointer;
  position: relative;
  transition: color 0.3s;
}

.tab-item.active {
  color: #1890ff;
  font-weight: 500;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #1890ff;
}

.workflow-list {
  margin-bottom: 20px;
}

.workflows {
  display: flex;
  gap: 20px;
}

.workflow-card {
  background-color: #fff;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  width: calc(33.33% - 20px);
}

.workflow-card h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.workflow-card p {
  margin: 0;
}

.workflow-meta {
  margin-top: 10px;
  font-size: 0.8em;
  color: #666;
}

.use-workflow-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.documents-section {
  margin-top: 20px;
  overflow-x: auto; /* 添加水平滚动以适应小屏幕 */
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  background-color: #ffffff;
}

.documents-section h3 {
  padding: 16px 20px;
  margin: 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 16px;
  color: #333;
}

.documents-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed; /* 确保表格布局稳定 */
}

.documents-table th,
.documents-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap; /* 防止文字换行导致布局错乱 */
  overflow: hidden;
  text-overflow: ellipsis; /* 溢出文字显示省略号 */
}

.documents-table th {
  background-color: #fafafa;
  font-weight: 500;
  color: #666;
  font-size: 14px;
}

.documents-table tr:hover {
  background-color: #f5f7fa;
  transition: background-color 0.3s ease;
}

/* 优化表格列宽度 */
.documents-table th:nth-child(1), 
.documents-table td:nth-child(1) { /* ID列 */
  width: 60px;
}

.documents-table th:nth-child(2),
.documents-table td:nth-child(2) { /* 标题列 */
  width: 20%;
}

.documents-table th:nth-child(3),
.documents-table td:nth-child(3),
.documents-table th:nth-child(4),
.documents-table td:nth-child(4) { /* 日期和节点列 */
  width: 15%;
}

.documents-table th:nth-child(5),
.documents-table td:nth-child(5),
.documents-table th:nth-child(6),
.documents-table td:nth-child(6) { /* 状态和紧急度列 */
  width: 80px;
}

.documents-table th:nth-child(7),
.documents-table td:nth-child(7) { /* 发起人列 */
  width: 10%;
}

.documents-table th:nth-child(8),
.documents-table td:nth-child(8) { /* 操作列 */
  width: 80px;
  text-align: center;
}

/* 美化状态标签 */
.status-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1;
  font-weight: 500;
}

.status-pending {
  background-color: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

.status-processing {
  background-color: #f0f5ff;
  color: #2f54eb;
  border: 1px solid #adc6ff;
}

.status-completed {
  background-color: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.status-rejected {
  background-color: #fff1f0;
  color: #f5222d;
  border: 1px solid #ffa39e;
}

.status-withdrawn {
  background-color: #f9f9f9;
  color: #999;
  border: 1px solid #d9d9d9;
}

/* 美化紧急程度标签 */
.emergency-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1;
  font-weight: 500;
}

.level-normal {
  background-color: #f9f9f9;
  color: #666;
  border: 1px solid #d9d9d9;
}

.level-medium {
  background-color: #fff7e6;
  color: #fa8c16;
  border: 1px solid #ffd591;
}

.level-high {
  background-color: #fff2e8;
  color: #fa541c;
  border: 1px solid #ffbb96;
}

.level-urgent {
  background-color: #fff1f0;
  color: #f5222d;
  border: 1px solid #ffa39e;
}

/* 美化按钮 */
.process-btn {
  display: inline-block;
  padding: 4px 15px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.3s;
}

.process-btn:hover {
  background-color: #40a9ff;
}

/* 空数据提示优化 */
.empty-data {
  padding: 40px 0;
  text-align: center;
  color: #999;
  font-size: 14px;
  background-color: #fafafa;
}

/* 响应式适配 */
@media screen and (max-width: 768px) {
  .documents-table th:nth-child(3),
  .documents-table td:nth-child(3),
  .documents-table th:nth-child(6),
  .documents-table td:nth-child(6),
  .documents-table th:nth-child(7),
  .documents-table td:nth-child(7) {
    display: none; /* 在小屏幕上隐藏部分列 */
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.modal-content {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 80%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  animation: modal-fade-in 0.3s ease;
}

@keyframes modal-fade-in {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f8f9fa;
  border-radius: 8px 8px 0 0;
}

.modal-header h3 {
  margin: 0;
  color: #1890ff;
  font-size: 18px;
  font-weight: 500;
}

.close-modal-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  transition: color 0.2s;
}

.close-modal-btn:hover {
  color: #f5222d;
}

.modal-body {
  padding: 24px;
  flex: 1;
}

.document-details {
  background-color: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #eee;
}

.detail-item {
  display: flex;
  margin-bottom: 10px;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.detail-item .label {
  width: 100px;
  color: #666;
  font-size: 14px;
}

.detail-item .value {
  color: #333;
  font-weight: 500;
}

.approval-actions {
  background-color: #fafafa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #eee;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.approve-btn, .reject-btn, .other-action-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.approve-btn {
  background-color: #52c41a;
  color: white;
}

.approve-btn:hover {
  background-color: #389e0d;
}

.reject-btn {
  background-color: #ff4d4f;
  color: white;
}

.reject-btn:hover {
  background-color: #cf1322;
}

.other-action-btn {
  background-color: #faad14;
  color: white;
}

.other-action-btn:hover {
  background-color: #d48806;
}

.modal-footer {
  padding: 12px 24px;
  border-top: 1px solid #f0f0f0;
  text-align: right;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.submit-btn {
  padding: 8px 24px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.submit-btn:hover {
  background-color: #096dd9;
}

.submit-btn:disabled {
  background-color: #bfbfbf;
  cursor: not-allowed;
}

.close-btn {
  padding: 8px 16px;
  background-color: #f0f0f0;
  color: #595959;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: #d9d9d9;
}

.workflow-select-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.workflow-select-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.workflow-select-item:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
}

.workflow-select-item.selected {
  border-color: #1890ff;
  background-color: #e6f7ff;
}

.workflow-select-item h5 {
  margin-top: 0;
  margin-bottom: 8px;
  color: #262626;
}

.workflow-select-item p {
  color: #595959;
  margin: 0;
  font-size: 14px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #262626;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="date"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #1890ff;
  outline: none;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.required {
  color: #f5222d;
  margin-left: 4px;
}

.form-assistant {
  margin-top: 24px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.assistant-btn {
  padding: 8px 16px;
  background-color: #52c41a;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.assistant-btn:hover {
  background-color: #389e0d;
}

.assistant-btn:disabled {
  background-color: #d9d9d9;
  cursor: not-allowed;
}

.form-guide {
  margin-top: 16px;
  padding: 12px;
  background-color: #fff;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.form-guide h4 {
  margin-top: 0;
  margin-bottom: 8px;
  color: #52c41a;
}

.upload-list {
  margin-top: 8px;
}

.upload-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background-color: #f8f9fa;
  margin-bottom: 4px;
  border-radius: 4px;
}

.remove-btn {
  background: none;
  border: none;
  color: #ff4d4f;
  cursor: pointer;
  padding: 4px 8px;
}

.remove-btn:hover {
  text-decoration: underline;
}

.process-modal {
  width: 90%;
  max-width: 1000px;
  max-height: 90vh;
}

.tab-list {
  display: flex;
  border-bottom: 1px solid #e8e8e8;
  margin-bottom: 20px;
}

.tab-item {
  padding: 12px 20px;
  cursor: pointer;
  font-size: 15px;
  color: #595959;
  transition: all 0.3s;
}

.tab-item:hover {
  color: #1890ff;
}

.tab-item.active {
  color: #1890ff;
  font-weight: 500;
  position: relative;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background-color: #1890ff;
}

.view-btn {
  padding: 4px 10px;
  margin-right: 8px;
  border: none;
  border-radius: 4px;
  background-color: #e6f7ff;
  color: #1890ff;
  cursor: pointer;
}

.withdraw-btn {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  background-color: #fff7e6;
  color: #fa8c16;
  cursor: pointer;
}

.auth-manager-container {
  margin-top: 20px;
}

.withdraw-btn:hover {
  background-color: #f3ca9c;
}

/* 新审批高亮效果 */
.highlight-new {
  animation: highlight-pulse 3s ease-in-out;
  position: relative;
}

@keyframes highlight-pulse {
  0% {
    background-color: rgba(24, 144, 255, 0.1);
  }
  50% {
    background-color: rgba(24, 144, 255, 0.2);
  }
  100% {
    background-color: transparent;
  }
}

.highlight-new::before {
  content: '新';
  position: absolute;
  left: -4px;
  top: 50%;
  transform: translateY(-50%);
  background-color: #1890ff;
  color: white;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 1;
  animation: fade-out 3s forwards;
}

@keyframes fade-out {
  0% { opacity: 1; }
  70% { opacity: 1; }
  100% { opacity: 0; }
}

/* 文档详情模态框样式 */
.document-detail-modal {
  width: 90%;
  max-width: 800px;
}

.document-detail-modal .modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.document-detail-modal .modal-header h3 {
  margin: 0;
  font-size: 20px;
  color: #1890ff;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.document-info {
  background-color: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.info-row {
  display: flex;
  margin-bottom: 8px;
}

.info-row .label {
  width: 80px;
  color: #666;
  font-weight: 500;
}

.content-section {
  margin-bottom: 20px;
}

.content-section h4 {
  margin-bottom: 10px;
  color: #333;
}

.content-body {
  background-color: #fff;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 4px;
  min-height: 100px;
  white-space: pre-wrap;
}

.approval-history {
  margin-top: 20px;
}

.approval-history h4 {
  margin-bottom: 10px;
  color: #333;
}

.history-item {
  background-color: #fff;
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 10px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #666;
  font-size: 14px;
}

.history-header .approver {
  font-weight: 500;
}

.history-header .action {
  color: #1890ff;
}

.history-header .time {
  color: #999;
}

.comment {
  padding: 8px;
  background-color: #f9f9f9;
  border-radius: 4px;
  color: #333;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.secondary-btn {
  padding: 6px 16px;
  background-color: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
}

.secondary-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.danger-btn {
  padding: 6px 16px;
  background-color: #ff4d4f;
  border: 1px solid #ff4d4f;
  border-radius: 4px;
  color: white;
  cursor: pointer;
}

.danger-btn:hover {
  background-color: #ff7875;
  border-color: #ff7875;
}

/* 优化我的发起部分样式 */
.my-approvals-container {
  padding: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.approval-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 0;
  transition: transform 0.2s, box-shadow 0.2s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid #f0f0f0;
}

.approval-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.approval-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
  background-color: #fafafa;
}

.approval-title {
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
  color: #333;
}

.approval-info {
  padding: 16px;
  flex-grow: 1;
}

.info-item {
  display: flex;
  margin-bottom: 10px;
  font-size: 14px;
}

.info-label {
  width: 80px;
  color: #888;
  flex-shrink: 0;
}

.info-value {
  color: #333;
  word-break: break-word;
}

.approval-actions {
  padding: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #f0f0f0;
  background-color: #fafafa;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid transparent;
}

.view-btn {
  background-color: #f0f7ff;
  color: #1890ff;
  border-color: #d4e8ff;
}

.view-btn:hover {
  background-color: #e6f2ff;
  border-color: #a3d3ff;
}

.withdraw-btn {
  background-color: #fff2f0;
  color: #ff4d4f;
  border-color: #ffccc7;
}

.withdraw-btn:hover {
  background-color: #fff1f0;
  border-color: #ffa39e;
}

.empty-data {
  padding: 40px 0;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  background-color: #fff;
  border-radius: 8px;
  grid-column: 1 / -1;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #bbb;
}

.empty-text {
  color: #999;
  font-size: 16px;
  margin-bottom: 24px;
}

.create-empty-btn {
  padding: 10px 24px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.create-empty-btn:hover {
  background-color: #40a9ff;
}

.highlight-new {
  animation: highlight-pulse 2s;
}

@keyframes highlight-pulse {
  0% { box-shadow: 0 0 0 0 rgba(24, 144, 255, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(24, 144, 255, 0); }
  100% { box-shadow: 0 0 0 0 rgba(24, 144, 255, 0); }
}

.approval-detail-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.approval-detail-container {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 90%;
  height: 90%;
  max-width: 1400px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modal-slide-in 0.3s ease;
}

@keyframes modal-slide-in {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

.approval-detail-header {
  padding: 18px 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f8f8f8;
}

.approval-detail-header .header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.approval-title {
  margin: 0;
  font-size: 22px;
  color: #333;
  font-weight: 600;
}

.close-detail-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #999;
  transition: color 0.2s;
  line-height: 1;
}

.close-detail-btn:hover {
  color: #333;
}

.approval-detail-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.approval-detail-main {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.approval-detail-sidebar {
  width: 350px;
  border-left: 1px solid #f0f0f0;
  background-color: #f9f9f9;
  padding: 24px;
  overflow-y: auto;
}

.approval-meta-card,
.approval-content-card,
.approval-history-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.card-header {
  padding: 14px 20px;
  border-bottom: 1px solid #f0f0f0;
  background-color: #fafafa;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
  font-weight: 500;
}

.card-body {
  padding: 20px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-label {
  font-size: 13px;
  color: #888;
}

.meta-value {
  font-size: 15px;
  color: #333;
  font-weight: 500;
}

.status-text, .emergency-text {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 14px;
  width: max-content;
}

.approval-content-text {
  font-size: 15px;
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
  min-height: 100px;
}

.history-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
}

.history-timeline::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 10px;
  width: 2px;
  background-color: #e8e8e8;
}

.history-item {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  position: relative;
}

.timeline-point {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #1890ff;
  z-index: 1;
  margin-top: 3px;
}

.history-content {
  flex: 1;
}

.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.approver-name {
  font-weight: 500;
  color: #333;
  font-size: 15px;
}

.action-type {
  font-size: 14px;
  padding: 2px 8px;
  border-radius: 4px;
}

.action-approve {
  background-color: #f6ffed;
  color: #52c41a;
}

.action-reject {
  background-color: #fff2f0;
  color: #f5222d;
}

.action-return {
  background-color: #fffbe6;
  color: #faad14;
}

.action-withdraw {
  background-color: #f9f9f9;
  color: #999;
}

.action-create {
  background-color: #e6f7ff;
  color: #1890ff;
}

.history-time {
  color: #999;
  font-size: 13px;
  margin-bottom: 8px;
}

.history-comment {
  background-color: #f9f9f9;
  padding: 12px;
  border-radius: 6px;
  color: #333;
  font-size: 14px;
  line-height: 1.5;
}

.no-history {
  padding: 40px 0;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.approval-detail-footer {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background-color: #f8f8f8;
}

.secondary-btn {
  padding: 8px 16px;
  background-color: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.secondary-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.danger-btn {
  padding: 8px 16px;
  background-color: #ff4d4f;
  border: 1px solid #ff4d4f;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.danger-btn:hover {
  background-color: #ff7875;
  border-color: #ff7875;
}

/* 响应式调整 */
@media screen and (max-width: 1200px) {
  .approval-detail-container {
    width: 95%;
    height: 95%;
  }
  
  .meta-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media screen and (max-width: 768px) {
  .approval-detail-content {
    flex-direction: column;
  }
  
  .approval-detail-sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid #f0f0f0;
  }
  
  .meta-grid {
    grid-template-columns: 1fr;
  }
}

.withdraw-btn {
  background-color: #ff7875;
  color: white;
}

.delete-btn {
  background-color: #ff4d4f;
  color: white;
  margin-left: 8px;
}

.delete-btn:hover {
  background-color: #ff7875;
}

.icon-delete:before {
  content: "🗑";
  margin-right: 4px;
}
</style>