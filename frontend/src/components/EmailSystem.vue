<template>
  <div class="email-system">
    <div class="email-sidebar">
      <div class="email-menu">
        <div class="menu-item" :class="{ active: currentView === 'drafts' }" @click="switchView('drafts')">
          <i class="fas fa-file"></i> 草稿箱
        </div>
        <div class="menu-item" :class="{ active: currentView === 'outbox' }" @click="switchView('outbox')">
          <i class="fas fa-paper-plane"></i> 发件箱
        </div>
        <div class="menu-item" :class="{ active: currentView === 'inbox' }" @click="switchView('inbox')">
          <i class="fas fa-inbox"></i> 收件箱
        </div>
        <div class="menu-item" :class="{ active: currentView === 'settings' }" @click="switchView('settings')">
          <i class="fas fa-cog"></i> 邮件设置
        </div>
      </div>
      <button class="compose-btn" @click="showComposeModal = true">
        <i class="fas fa-plus"></i> 写邮件
      </button>
    </div>

    <div class="email-content">
      <!-- 草稿箱 -->
      <div v-if="currentView === 'drafts'" class="email-list">
        <h2>草稿箱</h2>
        <div v-if="drafts.length === 0" class="empty-message">草稿箱为空</div>
        <div v-for="email in drafts" :key="email.id" class="email-item">
          <div class="email-subject" @click="viewDraft(email)">{{ email.subject }}</div>
          <div class="email-recipient">收件人: {{ email.recipient }}</div>
          <div class="email-date">{{ email.date }}</div>
          <div class="email-preview" @click="viewDraft(email)">{{ email.content.substring(0, 100) }}{{ email.content.length > 100 ? '...' : '' }}</div>
          <div class="email-actions">
            <button class="action-icon" @click.stop="editDraft(email.id)"><i class="fas fa-edit"></i></button>
          </div>
        </div>
      </div>

      <!-- 发件箱 -->
      <div v-if="currentView === 'outbox'" class="email-list">
        <h2>发件箱</h2>
        <div v-for="email in outbox" :key="email.id" class="email-item">
          <div class="email-subject">{{ email.subject }}</div>
          <div class="email-recipient">发送至: {{ email.recipient }}</div>
          <div class="email-date">{{ email.date }}</div>
          <div class="email-preview" @click="viewEmail(email, 'outbox')">
            {{ email.content.substring(0, 100) }}{{ email.content.length > 100 ? '...' : '' }}
          </div>
        </div>
      </div>

      <!-- 收件箱 -->
      <div v-if="currentView === 'inbox'" class="email-list">
        <h2>收件箱</h2>
        <div v-if="emailSettings.username" class="inbox-info">
          <div class="info-box">
            <i class="fas fa-envelope"></i> 接收邮件地址: <strong>{{ emailSettings.username }}</strong>
            <div class="info-tip">外部邮件发送至此地址将显示在此收件箱中</div>
          </div>
          <button v-if="!isCheckingMails && apiConnected" @click="checkNewEmails" class="refresh-btn">
            <i class="fas fa-sync"></i> 检查新邮件
          </button>
          <div v-if="isCheckingMails" class="checking-status">
            <i class="fas fa-sync fa-spin"></i> 正在检查新邮件...
          </div>
        </div>
        <div v-else class="empty-message warning-message">
          <i class="fas fa-exclamation-triangle"></i> 请先在邮件设置中配置接收邮件信息
        </div>
        <div v-if="inbox.length === 0" class="empty-message">收件箱为空</div>
        <div v-for="email in inbox" :key="email.id" class="email-item">
          <div class="email-sender">{{ email.sender }}</div>
          <div class="email-subject">{{ email.subject }}</div>
          <div class="email-date">{{ email.date }}</div>
          <div class="email-preview" @click="viewEmail(email, 'inbox')">
            {{ email.content.substring(0, 100) }}{{ email.content.length > 100 ? '...' : '' }}
          </div>
        </div>
      </div>

      <!-- 邮件模板 -->
      <div v-if="currentView === 'templates'" class="email-list">
        <h2>邮件模板</h2>
        <button class="create-template-btn" @click="showTemplateModal = true">
          <i class="fas fa-plus"></i> 新建模板
        </button>
        <div v-for="template in templates" :key="template.id" class="email-item">
          <div class="email-subject">{{ template.name }}</div>
          <div class="email-date">{{ template.created_at }}</div>
          <div class="email-actions">
            <button class="action-icon" @click.stop="useTemplate(template)"><i class="fas fa-envelope"></i></button>
            <button class="action-icon" @click.stop="editTemplate(template)"><i class="fas fa-edit"></i></button>
            <button class="action-icon delete" @click.stop="deleteTemplate(template.id)"><i class="fas fa-trash"></i></button>
          </div>
        </div>
      </div>

      <!-- 邮件设置 -->
      <div v-if="currentView === 'settings'" class="email-settings">
        <h2>邮件设置</h2>
        <div class="settings-info">
          <div class="info-icon"><i class="fas fa-info-circle"></i></div>
          <div class="info-text">配置邮件服务器信息，用于发送和接收邮件。请确保信息正确，您可以使用"测试连接"按钮验证设置。</div>
        </div>
        <form @submit.prevent="saveEmailSettings" class="settings-form">
          <!-- 发送邮件设置 -->
          <div class="settings-section">
            <h3 class="section-title"><i class="fas fa-paper-plane"></i> 发送邮件 (SMTP) 设置</h3>
            <div class="form-grid">
              <div class="form-group">
                <label>SMTP服务器</label>
                <div class="input-wrapper">
                  <i class="fas fa-globe input-icon"></i>
                  <input v-model="emailSettings.server" type="text" placeholder="例如: smtp.example.com" class="form-input">
                </div>
              </div>
              <div class="form-group">
                <label>SMTP端口</label>
                <div class="input-wrapper">
                  <i class="fas fa-plug input-icon"></i>
                  <input v-model="emailSettings.port" type="number" placeholder="例如: 587" class="form-input">
                </div>
              </div>
            </div>
          </div>
          
          <!-- 接收邮件设置 -->
          <div class="settings-section">
            <h3 class="section-title"><i class="fas fa-inbox"></i> 接收邮件设置</h3>
            <div class="form-grid">
              <div class="form-group">
                <label>接收服务器类型</label>
                <div class="input-wrapper">
                  <i class="fas fa-server input-icon"></i>
                  <select v-model="emailSettings.receiveType" class="form-input">
                    <option value="pop3">POP3</option>
                    <option value="imap">IMAP</option>
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label>接收服务器地址</label>
                <div class="input-wrapper">
                  <i class="fas fa-globe input-icon"></i>
                  <input v-model="emailSettings.receiveServer" type="text" placeholder="例如: pop.example.com 或 imap.example.com" class="form-input">
                </div>
              </div>
            </div>
            <div class="form-grid">
              <div class="form-group">
                <label>接收服务器端口</label>
                <div class="input-wrapper">
                  <i class="fas fa-plug input-icon"></i>
                  <input v-model="emailSettings.receivePort" type="number" placeholder="POP3通常为110/995，IMAP通常为143/993" class="form-input">
                </div>
              </div>
              <div class="form-group">
                <label>安全连接</label>
                <div class="input-wrapper">
                  <i class="fas fa-lock input-icon"></i>
                  <select v-model="emailSettings.receiveSecure" class="form-input">
                    <option value="none">无</option>
                    <option value="ssl">SSL/TLS</option>
                    <option value="starttls">STARTTLS</option>
                  </select>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label>检查新邮件频率</label>
              <div class="input-wrapper">
                <i class="fas fa-clock input-icon"></i>
                <select v-model="emailSettings.checkFrequency" class="form-input">
                  <option value="manual">手动检查</option>
                  <option value="5">每5分钟</option>
                  <option value="10">每10分钟</option>
                  <option value="15">每15分钟</option>
                  <option value="30">每30分钟</option>
                  <option value="60">每小时</option>
                </select>
              </div>
            </div>
          </div>
          
          <div class="settings-section">
            <h3 class="section-title"><i class="fas fa-user-lock"></i> 账户信息</h3>
            <div class="form-group">
              <label>用户名/邮箱</label>
              <div class="input-wrapper">
                <i class="fas fa-envelope input-icon"></i>
                <input v-model="emailSettings.username" type="email" placeholder="您的邮箱地址" class="form-input">
              </div>
              <div class="input-tip">此邮箱将用于发送和接收邮件</div>
            </div>
            <div class="form-group">
              <label>密码/授权码</label>
              <div class="input-wrapper">
                <i class="fas fa-key input-icon"></i>
                <input v-model="emailSettings.password" type="password" placeholder="您的邮箱密码或授权码" class="form-input">
              </div>
            </div>
            <div class="form-group">
              <label>发件人</label>
              <div class="input-wrapper">
                <i class="fas fa-paper-plane input-icon"></i>
                <input v-model="emailSettings.sender" type="email" placeholder="显示的发件人地址" class="form-input">
              </div>
            </div>
          </div>
          
          <div class="settings-actions">
            <button type="button" @click="testConnection" class="action-button test-btn" :disabled="isTestingConnection">
              <i class="fas" :class="isTestingConnection ? 'fa-spin fa-spinner' : 'fa-vial'"></i> 测试连接
            </button>
            <button type="submit" class="action-button save-btn">
              <i class="fas fa-check"></i> 保存设置
            </button>
          </div>
          
          <!-- 测试连接结果显示区域 -->
          <div v-if="testConnectionResult" class="connection-test-result" :class="{ 'success': testConnectionSuccess, 'error': !testConnectionSuccess }">
            <i class="fas" :class="testConnectionSuccess ? 'fa-check-circle' : 'fa-exclamation-circle'"></i>
            <span>{{ testConnectionResult }}</span>
          </div>
        </form>
      </div>
    </div>

    <!-- 查看邮件内容弹窗 -->
    <div v-if="showEmailViewModal" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ currentEmail.subject }}</h3>
          <button class="close-btn" @click="showEmailViewModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="email-detail">
            <div v-if="emailViewType === 'inbox'" class="email-from">
              <strong>发件人:</strong> {{ currentEmail.sender }}
            </div>
            <div v-if="emailViewType === 'drafts'" class="email-status">
              <strong>状态:</strong> <span class="draft-tag">草稿</span>
            </div>
            <div class="email-to">
              <strong>收件人:</strong> {{ currentEmail.recipient }}
            </div>
            <div class="email-time">
              <strong>时间:</strong> {{ currentEmail.date }}
            </div>
            <div class="email-content-view">
              <pre>{{ displayEmailContent(currentEmail.content) }}</pre>
            </div>
            <div v-if="emailViewType === 'drafts'" class="email-actions-footer">
              <button @click="editDraft(currentEmail.id); showEmailViewModal = false" class="action-btn edit-btn">编辑草稿</button>
              <button @click="sendDraftEmail(currentEmail); showEmailViewModal = false" class="action-btn send-btn">发送邮件</button>
              <button @click="deleteDraft(currentEmail.id); showEmailViewModal = false" class="action-btn delete-btn">删除草稿</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 写邮件弹窗 -->
    <div v-if="showComposeModal" class="modal email-compose-modal-wrapper">
      <div class="modal-content email-compose-modal">
        <div class="modal-header">
          <h3><i class="fas fa-edit"></i> 写邮件</h3>
          <button class="close-btn" @click="closeComposeModal">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="sendEmail" class="email-form">
            <div class="form-group">
              <label for="recipient">
                <i class="fas fa-user"></i> 收件人
              </label>
              <div class="input-field" :class="{ 'error': showRecipientError }">
                <input 
                  type="email" 
                  id="recipient" 
                  v-model="newEmail.recipient" 
                  placeholder="请输入收件人邮箱"
                  class="modern-input"
                >
              </div>
              <div v-if="showRecipientError" class="error-message">
                <i class="fas fa-exclamation-circle"></i> 请输入有效的收件人邮箱
              </div>
            </div>
            
            <div class="form-group">
              <label for="subject">
                <i class="fas fa-heading"></i> 主题
              </label>
              <div class="input-field">
                <input 
                  type="text" 
                  id="subject" 
                  v-model="newEmail.subject" 
                  placeholder="请输入邮件主题"
                  class="modern-input"
                  ref="subjectInput"
                >
              </div>
            </div>
            
            <div class="form-group email-content-group">
              <div class="content-header">
                <label for="content">
                  <i class="fas fa-file-alt"></i> 内容
                </label>
                <div class="content-actions">
                  <button 
                    type="button" 
                    @click="regenerateContent" 
                    :disabled="isGenerating" 
                    class="action-button-small"
                    title="根据主题生成新的邮件内容"
                  >
                    <i class="fas fa-sync-alt" :class="{ 'fa-spin': isGenerating }"></i> 
                    重新生成
                  </button>
                  
                  <button 
                    v-if="newEmail.intention && newEmail.intention.trim()" 
                    type="button" 
                    @click="handleGenerateEmail" 
                    :disabled="isGenerating" 
                    class="action-button-small"
                    title="优化当前邮件内容"
                  >
                    <i class="fas fa-magic" :class="{ 'fa-spin': isGenerating }"></i> AI润色
                  </button>
                </div>
              </div>
              
              <div class="input-field content-field" :class="{ 'error': showContentError }">
                <textarea 
                  id="content" 
                  v-model="newEmail.intention" 
                  placeholder="输入邮件内容或点击使用AI生成邮件"
                  class="modern-textarea"
                  rows="10"
                ></textarea>
              </div>
              
              <div v-if="showContentError" class="error-message">
                <i class="fas fa-exclamation-circle"></i> 请输入邮件内容
              </div>
              
              <!-- 生成状态指示 -->
              <div v-if="isGenerating" class="generating-indicator">
                <div class="processing-message">
                  <i class="fas fa-circle-notch fa-spin"></i> 
                  <span>AI正在为您生成邮件内容...</span>
                  <div class="progress-bar">
                    <div class="progress-fill"></div>
                  </div>
                </div>
              </div>
              
              <!-- 生成错误指示 -->
              <div v-if="generationError" class="error-message generation-error">
                <i class="fas fa-exclamation-triangle"></i> {{ generationError }}
              </div>
            </div>
            
            <div class="form-actions">
              <button type="button" @click="saveDraft" :disabled="isSaving" class="secondary-button">
                <i class="fas fa-save"></i> 保存草稿
              </button>
              <button type="submit" class="primary-button">
                <i class="fas fa-paper-plane"></i> 发送邮件
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 添加通知组件 -->
    <div v-if="notification.show" class="notification" :class="notification.type">
      <div class="notification-content">
        <i v-if="notification.type === 'success'" class="fas fa-check-circle"></i>
        <i v-if="notification.type === 'error'" class="fas fa-exclamation-circle"></i>
        <span>{{ notification.message }}</span>
      </div>
      <button class="notification-close" @click="notification.show = false">×</button>
    </div>

    <!-- 自动填充确认对话框 -->
    <div v-if="showAutoFillConfirm" class="modal auto-fill-confirm-modal">
      <div class="modal-content auto-fill-modal">
        <div class="modal-header">
          <h3><i class="fas fa-robot"></i> 自动填充确认</h3>
          <button class="close-btn" @click="showAutoFillConfirm = false">×</button>
        </div>
        <div class="modal-body">
          <div class="auto-fill-message">
            <div class="info-icon"><i class="fas fa-info-circle"></i></div>
            <p>AI助手已为您自动填充以下内容，请确认是否使用：</p>
          </div>
          
          <div class="auto-fill-items">
            <div v-for="(item, index) in autoFillNotifications" :key="index" class="auto-fill-item">
              <div class="auto-fill-content">
                <div class="auto-fill-field">
                  <strong>{{ item.field === 'recipient' ? '收件人' : '主题' }}:</strong>
                </div>
                <div class="auto-fill-value">{{ item.value }}</div>
              </div>
              <div class="auto-fill-actions">
                <button @click="confirmAutoFill(item.field)" class="confirm-btn">
                  <i class="fas fa-check"></i> 使用
                </button>
                <button @click="rejectAutoFill(item.field)" class="reject-btn">
                  <i class="fas fa-times"></i> 忽略
                </button>
              </div>
            </div>
          </div>
          
          <div class="auto-fill-all-actions">
            <button @click="confirmAllAutoFills" class="confirm-all-btn">
              <i class="fas fa-check-double"></i> 全部使用
            </button>
            <button @click="rejectAllAutoFills" class="reject-all-btn">
              <i class="fas fa-times-circle"></i> 全部忽略
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AiAssistant from './AiAssistant.vue';
import emitter from '../utils/eventBus';

export default {
  name: 'EmailSystem',
  components: {
    AiAssistant
  },
  data() {
    return {
      currentView: 'drafts',
      showComposeModal: false,
      showEmailViewModal: false,
      drafts: [],
      outbox: [],
      inbox: [],

      templates: [],
      selectedTemplateId: null,
      newEmail: {
        recipient: '',
        intention: '',
        subject: 'AI辅助生成的邮件'
      },
      generatedContent: '',
      isEditing: false,
      editedContent: '',
      showRecipientError: false,
      showContentError: false,
      currentEmail: {},
      emailViewType: 'outbox',
      editingTemplate: {
        id: null,
        name: '',
        subject: '',
        content: ''
      },

      emailSettings: {
        server: '',
        port: 587,
        username: '',
        password: '',
        sender: '',
        receiveType: 'imap',
        receiveServer: '',
        receivePort: 993,
        receiveSecure: 'ssl',
        checkFrequency: 'manual'
      },
      currentDraftId: null,
      apiConnected: false,
      backendUrl: '/api',  // 修改为使用相对路径
      isGenerating: false,
      generatingWithSubject: '',
      isCheckingMails: false,
      generationError: null,
      isSaving: false,
      isSending: false,
      
      // 通知系统
      notification: {
        show: false,
        type: 'success',
        message: '',
        timeout: null
      },
      isTestingConnection: false,
      testConnectionResult: '',
      testConnectionSuccess: true,
      
      // 调试信息
      debugLogs: [],
      lastModalToggleTime: 0,
      autoFillNotifications: [], // 用于存储自动填充的通知
      showAutoFillConfirm: false, // 是否显示自动填充确认对话框
      pendingAutoFills: {}, // 待确认的自动填充项
    };
  },
  created() {
    console.log('[EmailSystem] created: 组件创建，注册事件监听器...');
    
    // 监听打开邮件编辑器的事件 (保留，可能其他地方会用)
    emitter.on('open-email-composer', this.openEmailWithData);
    
    // 添加对模块切换事件的监听
    emitter.on('module-changed', this.handleModuleChanged);

    // 监听来自AI助手的邮件写作请求
    emitter.on('open-compose-email', this.handleAIEmailRequest);

    console.log('[EmailSystem] created: 事件监听器注册完成');
  },
  mounted() {
    // 监听tab参数变化
    this.checkUrlTabParam();
    
    // 检查是否有AI生成的邮件等待处理
    this.checkAiGeneratedEmail();
    
    // 检查全局邮件通知数据
    this.checkGlobalEmailData();
    
    // 检查邮件服务器连接
    this.testEmailConnection();
    
    // 从本地存储加载邮件数据
    this.loadLocalStorageEmails();
    
    // 添加对switch-email-tab事件的监听
    window.addEventListener('switch-email-tab', (event) => {
      if (event.detail && event.detail.tab) {
        console.log('收到切换邮件标签事件:', event.detail.tab);
        this.switchView(event.detail.tab);
      }
    });

    // 检查当前路径，是否包含tab参数
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    if (tabParam) {
      console.log('从URL参数获取标签:', tabParam);
      this.switchView(tabParam);
    }
  },
  
  beforeUnmount() {
    // 移除所有事件监听
    emitter.off('open-email-composer', this.openEmailWithData);
    // 移除对模块切换事件的监听
    emitter.off('module-changed', this.handleModuleChanged);
    // 移除AI助手邮件请求事件监听
    emitter.off('open-compose-email', this.handleAIEmailRequest);
    
    // --- 确保移除之前可能添加的监听器 ---
    document.removeEventListener('ai-generated-email', this.handleAiGeneratedEmail);
    window.removeEventListener('ai-email-ready', this.checkGlobalEmailData);
    // --- 移除结束 ---
    
    console.log('EmailSystem组件销毁，已清理所有事件监听器');
  },
  beforeDestroy() {
    // 清理事件总线监听器
    emitter.off('compose-email', this.handleComposeEmail);
    emitter.off('switch-to-email-compose', this.handleComposeEmail);
    emitter.off('compose-email-from-ai', this.handleComposeEmail);
    emitter.off('open-email-composer', this.handleComposeEmail);
    emitter.off('check-email-pending', this.checkPendingEmail);
    emitter.off('module-changed', this.handleModuleChanged);
    
    // 清理DOM事件监听器
    document.removeEventListener('compose-email', this.handleDOMEmailEvent);
    document.removeEventListener('switch-to-email-compose', this.handleDOMEmailEvent);
    document.removeEventListener('compose-email-from-ai', this.handleDOMEmailEvent);
    document.removeEventListener('open-email-composer', this.handleDOMEmailEvent);
    
    // 清理window事件监听器
    window.removeEventListener('compose-email', this.handleDOMEmailEvent);
    window.removeEventListener('compose-email-from-ai', this.handleDOMEmailEvent);
    window.removeEventListener('open-email-composer', this.handleDOMEmailEvent);
    window.removeEventListener('switch-to-email-compose', this.handleDOMEmailEvent);
    window.removeEventListener('storage', this.handleStorageChange);
    
    // 清理定时器
    if (this.checkEmailDataTimer) {
      clearInterval(this.checkEmailDataTimer);
    }
    
    if (this.periodicCheckTimer) {
      clearInterval(this.periodicCheckTimer);
    }
    
    if (this.localStorageCheckInterval) {
      clearInterval(this.localStorageCheckInterval);
    }
    
    // 清理通知超时
    if (this.notification.timeout) {
      clearTimeout(this.notification.timeout);
    }
    
    // 移除全局函数
    if (window._openEmailComposer) {
      window._openEmailComposer = null;
    }
    
    console.log('EmailSystem组件销毁，已清理所有事件监听器和定时器');
  },
  unmounted() {
    // 清理事件监听
    emitter.off('compose-email');
    emitter.off('switch-to-email-compose');
    
    if (this.handleCustomEvent) {
      window.removeEventListener('compose-email', this.handleCustomEvent);
    }
    
    if (this.handleSwitchEvent) {
      window.removeEventListener('switch-to-email-compose', this.handleSwitchEvent);
    }
    
    // 确保在组件销毁时清理通知超时
    if (this.notification.timeout) {
      clearTimeout(this.notification.timeout);
    }
  },
  methods: {
    // 从本地存储加载邮件数据
    loadLocalStorageEmails() {
      console.log('从本地存储加载邮件数据');
      
      // 加载草稿箱
      try {
        const savedDrafts = localStorage.getItem('email_drafts');
        if (savedDrafts) {
          const drafts = JSON.parse(savedDrafts);
          if (Array.isArray(drafts) && drafts.length > 0) {
            console.log('从本地存储加载草稿箱数据:', drafts.length, '条');
            this.drafts = drafts;
          }
        }
      } catch (e) {
        console.error('从本地存储加载草稿箱数据失败:', e);
      }
      
      // 加载发件箱
      try {
        const savedOutbox = localStorage.getItem('email_outbox');
        if (savedOutbox) {
          const outbox = JSON.parse(savedOutbox);
          if (Array.isArray(outbox) && outbox.length > 0) {
            console.log('从本地存储加载发件箱数据:', outbox.length, '条');
            this.outbox = outbox;
          }
        }
      } catch (e) {
        console.error('从本地存储加载发件箱数据失败:', e);
      }
      
      // 加载收件箱
      try {
        const savedInbox = localStorage.getItem('email_inbox');
        if (savedInbox) {
          const inbox = JSON.parse(savedInbox);
          if (Array.isArray(inbox) && inbox.length > 0) {
            console.log('从本地存储加载收件箱数据:', inbox.length, '条');
            this.inbox = inbox;
          }
        }
      } catch (e) {
        console.error('从本地存储加载收件箱数据失败:', e);
      }
      
      // 如果本地存储中没有数据，尝试从API加载
      if (this.drafts.length === 0 && this.outbox.length === 0 && this.inbox.length === 0) {
        console.log('本地存储中没有邮件数据，尝试从API加载');
        this.loadEmailData();
      }
    },
    
    // 加载邮件设置
    async loadEmailSettings() {
      if (!this.apiConnected) {
        await this.checkApiConnection();
        if (!this.apiConnected) {
          console.error('无法加载邮件设置：后端服务未连接');
          return;
        }
      }
      
      try {
        const response = await fetch(`${this.backendUrl}/email/config`);
        if (response.ok) {
          const config = await response.json();
          this.emailSettings = {
            server: config.smtp_server || '',
            port: config.smtp_port || 587,
            username: config.smtp_username || '',
            password: config.smtp_password || '',
            sender: config.sender_email || '',
            receiveType: config.receive_type || 'imap',
            receiveServer: config.receive_server || '',
            receivePort: config.receive_port || 993,
            receiveSecure: config.receive_secure || 'ssl',
            checkFrequency: config.check_frequency || 'manual'
          };
        }
      } catch (error) {
        console.error('加载邮件设置失败:', error);
      }
    },
    
    // 检查API连接状态
    async checkApiConnection() {
      try {
        // 尝试连接到后端健康检查接口
        const response = await fetch(`${this.backendUrl}/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          },
          // 设置超时时间
          signal: AbortSignal.timeout(5000)
        }).catch(error => {
          return { ok: false, status: 0, statusText: error.message };
        });
        
        if (response.ok) {
          this.apiConnected = true;
          return true;
        }
        
        this.apiConnected = false;
        return false;
      } catch (error) {
        this.apiConnected = false;
        return false;
      }
    },
    
    // 加载邮件数据
    async loadEmailData() {
      console.log('开始加载全部邮件数据');
      
      try {
        await Promise.all([
          this.loadDrafts(),
          this.loadOutbox(),
          this.loadInbox(),
          this.loadTemplates()
        ]);
        console.log('所有邮件数据加载完成');
      } catch (error) {
        console.error('加载邮件数据失败:', error);
        
        // 如果服务未连接，显示一些模拟数据
        if (!this.apiConnected) {
          this.loadMockData();
        }
      }
    },
    
    // 加载草稿箱数据
    async loadDrafts() {
      console.log('加载草稿箱数据');
      
      if (!this.apiConnected) {
        await this.checkApiConnection();
      }
      
      try {
        if (this.apiConnected) {
          const response = await fetch(`${this.backendUrl}/email/drafts`);
          
          if (!response.ok) {
            throw new Error('获取草稿数据失败');
          }
          
          const data = await response.json();
          console.log('草稿箱API响应:', data);
          
          // 修复数据结构处理
          if (data && Array.isArray(data.drafts || data.emails)) {
            this.drafts = (data.drafts || data.emails).map(draft => {
              // 确保每个草稿都有所需的字段
              return {
                id: draft.id || `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                recipient: draft.recipient || draft.to || '',
                subject: draft.subject || '(无主题)',
                content: draft.content || draft.body || '',
                date: draft.date || draft.created_at || new Date().toISOString(),
                status: 'draft'
              };
            });
          } else if (data && Array.isArray(data)) {
            // 如果直接返回数组
            this.drafts = data.map(draft => {
              return {
                id: draft.id || `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                recipient: draft.recipient || draft.to || '',
                subject: draft.subject || '(无主题)',
                content: draft.content || draft.body || '',
                date: draft.date || draft.created_at || new Date().toISOString(),
                status: 'draft'
              };
            });
          } else {
            console.error('草稿箱数据格式不正确:', data);
            this.drafts = [];
          }
          
          console.log('加载草稿箱成功, 数量:', this.drafts.length);
          return true;
        } else {
          this.drafts = this.getMockDrafts();
          console.log('使用模拟草稿数据');
          return false;
        }
      } catch (error) {
        console.error('加载草稿箱数据失败:', error);
        this.drafts = this.getMockDrafts();
        return false;
      }
    },
    
    // 加载发件箱数据
    async loadOutbox() {
      console.log('加载发件箱数据');
      
      if (!this.apiConnected) {
        await this.checkApiConnection();
      }
      
      try {
        if (this.apiConnected) {
          const response = await fetch(`${this.backendUrl}/email/outbox`);
          
          if (!response.ok) {
            throw new Error('获取发件箱数据失败');
          }
          
          const data = await response.json();
          console.log('发件箱API响应:', data);
          
          // 修复数据结构处理
          if (data && Array.isArray(data.emails)) {
            this.outbox = data.emails.map(email => {
              return {
                id: email.id || `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                recipient: email.recipient || email.to || '',
                subject: email.subject || '(无主题)',
                content: email.content || email.body || '',
                date: email.date || email.created_at || new Date().toISOString(),
                status: 'sent'
              };
            });
          } else if (data && Array.isArray(data)) {
            // 如果直接返回数组
            this.outbox = data.map(email => {
              return {
                id: email.id || `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                recipient: email.recipient || email.to || '',
                subject: email.subject || '(无主题)',
                content: email.content || email.body || '',
                date: email.date || email.created_at || new Date().toISOString(),
                status: 'sent'
              };
            });
          } else {
            console.error('发件箱数据格式不正确:', data);
            this.outbox = [];
          }
          
          console.log('加载发件箱成功, 数量:', this.outbox.length);
          return true;
        } else {
          this.outbox = this.getMockOutbox();
          console.log('使用模拟发件箱数据');
          return false;
        }
      } catch (error) {
        console.error('加载发件箱数据失败:', error);
        this.outbox = this.getMockOutbox();
        return false;
      }
    },
    
    // 加载收件箱数据
    async loadInbox() {
      console.log('加载收件箱数据');
      
      if (!this.apiConnected) {
        await this.checkApiConnection();
      }
      
      try {
        if (this.apiConnected) {
          const response = await fetch(`${this.backendUrl}/email/inbox`);
          
          if (!response.ok) {
            throw new Error('获取收件箱数据失败');
          }
          
          const data = await response.json();
          console.log('收件箱API响应:', data);
          
          // 修复数据结构处理
          if (data && Array.isArray(data.emails)) {
            this.inbox = data.emails.map(email => {
              return {
                id: email.id || `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                sender: email.sender || email.from || '未知发件人',
                subject: email.subject || '(无主题)',
                content: email.content || email.body || '',
                date: email.date || email.created_at || new Date().toISOString(),
                status: email.status || 'unread'
              };
            });
          } else if (data && Array.isArray(data)) {
            // 如果直接返回数组
            this.inbox = data.map(email => {
              return {
                id: email.id || `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                sender: email.sender || email.from || '未知发件人',
                subject: email.subject || '(无主题)',
                content: email.content || email.body || '',
                date: email.date || email.created_at || new Date().toISOString(),
                status: email.status || 'unread'
              };
            });
          } else {
            console.error('收件箱数据格式不正确:', data);
            this.inbox = [];
          }
          
          console.log('加载收件箱成功, 数量:', this.inbox.length);
          return true;
        } else {
          this.inbox = this.getMockInbox();
          console.log('使用模拟收件箱数据');
          return false;
        }
      } catch (error) {
        console.error('加载收件箱数据失败:', error);
        this.inbox = this.getMockInbox();
        return false;
      }
    },
    
    // 获取模拟草稿数据
    getMockDrafts() {
      return [
        {
          id: 'draft1',
          recipient: 'manager@example.com',
          subject: '下周工作计划',
          content: '尊敬的经理：\n\n下周我计划完成以下工作内容：\n1. 完成项目报告初稿\n2. 与客户确认需求变更\n3. 协助测试团队进行系统测试\n\n如有任何调整，请告知。\n\n祝好，\n张三',
          date: new Date().toISOString(),
          status: 'draft'
        },
        {
          id: 'draft2',
          recipient: 'team@company.com',
          subject: '团队会议通知',
          content: '各位同事：\n\n我们将于本周五下午3点在会议室A举行团队周会，请各位准时参加。\n\n会议内容：\n1. 本周工作总结\n2. 下周工作计划\n3. 项目进度更新\n\n请提前准备相关资料。\n\n谢谢，\n项目组',
          date: new Date(Date.now() - 86400000).toISOString(),
          status: 'draft'
        }
      ];
    },
    
    // 获取模拟发件箱数据
    getMockOutbox() {
      return [
        {
          id: 'out1',
          recipient: 'client@example.com',
          subject: '项目进度报告',
          content: '尊敬的客户：\n\n附上本月项目进度报告，目前项目进展顺利，已完成以下里程碑：\n\n1. 需求分析和系统设计\n2. 核心功能开发\n3. 初步测试\n\n下一阶段我们将进入系统集成测试阶段，预计需要两周时间。\n\n如有任何问题，请随时联系我。\n\n祝好，\n项目经理',
          date: new Date().toISOString(),
          status: 'sent'
        },
        {
          id: 'out2',
          recipient: 'support@company.com',
          subject: '请求技术支持',
          content: '技术支持团队：\n\n我们在使用系统过程中遇到以下问题：\n\n1. 数据导入功能偶尔失败\n2. 报表生成速度较慢\n\n这些问题影响了我们的正常工作，希望能尽快得到解决。\n\n谢谢！\n运营团队',
          date: new Date(Date.now() - 172800000).toISOString(),
          status: 'sent'
        }
      ];
    },
    
    // 获取模拟收件箱数据
    getMockInbox() {
      return [
        {
          id: 'in1',
          sender: 'hr@company.com',
          subject: '关于年度绩效评估的通知',
          content: '各位同事：\n\n公司将于下月开始进行年度绩效评估，请各部门按照附件中的时间安排，做好相关准备工作。\n\n评估流程：\n1. 员工自评\n2. 部门内互评\n3. 主管评估\n4. 绩效面谈\n\n详细说明请参阅附件。\n\n人力资源部',
          date: new Date().toISOString(),
          status: 'unread'
        },
        {
          id: 'in2',
          sender: 'system@company.com',
          subject: '系统维护通知',
          content: '尊敬的用户：\n\n我们计划于本周六凌晨2:00-5:00进行系统维护，在此期间系统将暂停使用。\n\n请您提前做好相关工作安排，由此给您带来的不便，敬请谅解。\n\n系统管理员',
          date: new Date(Date.now() - 259200000).toISOString(),
          status: 'read'
        }
      ];
    },
    
    // 加载模拟数据
    loadMockData() {
      console.log('加载模拟邮件数据');
      this.drafts = this.getMockDrafts();
      this.outbox = this.getMockOutbox();
      this.inbox = this.getMockInbox();
    },
    
    // 处理流式响应中的邮件数据
    async processEmailStreamResponse(response, originalSubject, originalRecipient) {
      // 使用新的ReadableStream API处理流式数据
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      // 用于存储JSON数据的变量
      let jsonString = '';
      let isCollectingJson = false;
      let textContent = '';
      let emailJson = null;
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          // 解码当前块
          const chunk = decoder.decode(value, { stream: true });
          
          // 处理SSE数据格式
          const lines = chunk.split('\n\n');
          for (const line of lines) {
            // 检查是否是SSE数据行
            if (line.startsWith('data:')) {
              const data = line.substring(5).trim();
              
              // 检查特殊标记
              if (data === 'EMAIL_JSON_START') {
                isCollectingJson = true;
                jsonString = '';
                continue;
              } else if (data === 'EMAIL_JSON_END') {
                isCollectingJson = false;
                try {
                  emailJson = JSON.parse(jsonString);
                  console.log('成功解析邮件JSON数据:', emailJson);
                  
                  // 立即使用解析出的JSON数据填充表单
                  this.fillEmailForm(emailJson, originalSubject, originalRecipient);
                } catch (e) {
                  console.error('解析JSON失败:', e);
                }
                continue;
              } else if (data === '[DONE]') {
                break;
              }
              
              // 收集JSON数据或普通文本
              if (isCollectingJson) {
                jsonString += data;
              } else {
                textContent += data;
              }
            }
          }
        }
        
        // 如果有emailJson数据，已经在循环中处理了
        // 如果没有，尝试从textContent中提取
        if (!emailJson && textContent) {
          this.processPlainTextEmail(textContent, originalSubject, originalRecipient);
        }
      } catch (error) {
        console.error('处理流式响应失败:', error);
        throw error;
      }
    },
    
    // 填充邮件表单
    fillEmailForm(emailData, originalSubject, originalRecipient) {
      if (!emailData) return;
      
      // 使用纯内容
      if (emailData.content) {
        const pureContent = this.cleanThinkingContent(emailData.content);
        this.generatedContent = pureContent;
        this.newEmail.intention = pureContent;
      }
      
      // 填充主题，并移除可能的标记
      if (emailData.subject && emailData.subject !== "[邮件主题]" && 
          emailData.subject !== "[未指定]" && emailData.subject !== "请填写主题") {
        // 过滤掉标记前缀
        let cleanSubject = emailData.subject;
        cleanSubject = this.removeJsonTagPrefix(cleanSubject);
        this.newEmail.subject = cleanSubject;
        
        if ((!originalSubject || originalSubject === 'AI辅助生成的邮件') && 
            cleanSubject !== originalSubject) {
          console.log(`已自动填充主题: ${cleanSubject}`);
        }
      }
      
      // 填充收件人，并移除可能的标记
      if (emailData.recipient && emailData.recipient !== "[收件人]" && 
          emailData.recipient !== "[未指定]" && emailData.recipient !== "请填写收件人") {
        // 过滤掉标记前缀
        let cleanRecipient = emailData.recipient;
        cleanRecipient = this.removeJsonTagPrefix(cleanRecipient);
        this.newEmail.recipient = cleanRecipient;
        
        if (!originalRecipient && cleanRecipient !== originalRecipient) {
          console.log(`已自动填充收件人: ${cleanRecipient}`);
        }
      }
      
      console.log('填充邮件表单完成');
    },
    
    // 处理纯文本邮件内容
    processPlainTextEmail(textContent, originalSubject, originalRecipient) {
      if (!textContent) return;
      
      // 先整体过滤掉EMAIL_JSON_START标记
      textContent = this.removeJsonTagPrefix(textContent);
      this.autoFillNotifications = []; // 清空之前的通知
      this.pendingAutoFills = {}; // 清空待确认项
      
      // 清理思考过程标记
      const cleanedContent = this.cleanThinkingContent(textContent);
      
      // 尝试从文本中提取信息
      const recipientMatch = cleanedContent.match(/收件人[:：]\s*(.+?)[\n\r]/);
      const subjectMatch = cleanedContent.match(/主题[:：]\s*(.+?)[\n\r]/);
      
      // 提取主题和收件人
      let extractedRecipient = '';
      let extractedSubject = '';
      
      if (recipientMatch && recipientMatch[1].trim()) {
        extractedRecipient = recipientMatch[1].trim();
        extractedRecipient = this.removeJsonTagPrefix(extractedRecipient);
        if (extractedRecipient !== "[收件人]" && extractedRecipient !== "[未指定]" && extractedRecipient !== "请填写收件人") {
          // 记录待确认的收件人
          if (!originalRecipient && extractedRecipient !== originalRecipient) {
            this.pendingAutoFills.recipient = extractedRecipient;
            this.autoFillNotifications.push({
              field: 'recipient',
              value: extractedRecipient,
              message: `自动填充收件人: ${extractedRecipient}`
            });
            console.log(`待确认自动填充收件人: ${extractedRecipient}`);
          } else {
            this.newEmail.recipient = extractedRecipient;
          }
        }
      }
      
      if (subjectMatch && subjectMatch[1].trim()) {
        extractedSubject = subjectMatch[1].trim();
        extractedSubject = this.removeJsonTagPrefix(extractedSubject);
        if (extractedSubject !== "[邮件主题]" && extractedSubject !== "[未指定]" && extractedSubject !== "请填写主题") {
          // 记录待确认的主题
          if ((!originalSubject || originalSubject === 'AI辅助生成的邮件') && 
              extractedSubject !== originalSubject) {
            this.pendingAutoFills.subject = extractedSubject;
            this.autoFillNotifications.push({
              field: 'subject',
              value: extractedSubject,
              message: `自动填充主题: ${extractedSubject}`
            });
            console.log(`待确认自动填充主题: ${extractedSubject}`);
          } else {
            this.newEmail.subject = extractedSubject;
          }
        }
      }
      
      // 提取内容部分
      const contentMatch = cleanedContent.match(/内容[:：][\r\n]+(.+)/s);
      let pureContent = '';
      
      if (contentMatch && contentMatch[1]) {
        pureContent = contentMatch[1].trim();
      } else {
        pureContent = cleanedContent;
        
        // 如果没有找到明确的 "内容:" 标记，但有收件人和主题标记，移除这些行
        if (recipientMatch) {
          pureContent = pureContent.replace(recipientMatch[0], '');
        }
        if (subjectMatch) {
          pureContent = pureContent.replace(subjectMatch[0], '');
        }
        pureContent = pureContent.replace(/内容[:：][\r\n]+/, '');
        pureContent = pureContent.trim();
      }
      
      // 再次清理思考内容
      pureContent = this.cleanThinkingContent(pureContent);
      pureContent = this.removeJsonTagPrefix(pureContent);
      
      // 更新内容
      this.generatedContent = pureContent;
      this.newEmail.intention = pureContent;
      
      // 显示确认对话框
      if (this.autoFillNotifications.length > 0) {
        this.showAutoFillConfirm = true;
      }
      
      console.log('从纯文本中提取邮件信息完成');
    },
    
    // 清理思考过程标记
    cleanThinkingContent(content) {
      if (!content) return '';
      
      let cleanedContent = content;
      
      // 清理各种思考标记
      // 1. <think>标签及其内容
      cleanedContent = cleanedContent.replace(/<think>[\s\S]*?<\/think>/gi, '');
      // 处理格式不规范的<think>标签
      cleanedContent = cleanedContent.replace(/<th\s*ink>[\s\S]*?<\/th\s*ink>/gi, '');
      
      // 2. 常见的思考标记
      cleanedContent = cleanedContent.replace(/【思考[:：][\s\S]*?】/g, '');
      cleanedContent = cleanedContent.replace(/\[思考[:：][\s\S]*?\]/g, '');
      cleanedContent = cleanedContent.replace(/（思考[:：][\s\S]*?）/g, '');
      cleanedContent = cleanedContent.replace(/\(思考[:：][\s\S]*?\)/g, '');
      
      // 3. AI分析、思路等标记
      cleanedContent = cleanedContent.replace(/AI分析[:：][\s\S]*?(?=\n\n|$)/g, '');
      cleanedContent = cleanedContent.replace(/思路[:：][\s\S]*?(?=\n\n|$)/g, '');
      cleanedContent = cleanedContent.replace(/分析[:：][\s\S]*?(?=\n\n|$)/g, '');
      cleanedContent = cleanedContent.replace(/让我来[:：][\s\S]*?(?=\n\n|$)/g, '');
      
      // 4. 过程引导词语
      cleanedContent = cleanedContent.replace(/接下来[我|我们|开始|将].*?\n/g, '');
      cleanedContent = cleanedContent.replace(/首先[，|,]?我[需要|会|将].*?\n/g, '');
      cleanedContent = cleanedContent.replace(/我需要.*?[\n|。]/g, '');
      cleanedContent = cleanedContent.replace(/我会.*?[\n|。]/g, '');
      
      // 5. 其他常见思考标记
      cleanedContent = cleanedContent.replace(/现在我将.*?\n/g, '');
      cleanedContent = cleanedContent.replace(/下面我将.*?\n/g, '');
      cleanedContent = cleanedContent.replace(/基于以上.*?\n/g, '');
      
      // 6. 移除意图或方法声明
      cleanedContent = cleanedContent.replace(/这封邮件的目的是.*?\n/g, '');
      cleanedContent = cleanedContent.replace(/我将采用.*?的方式.*?\n/g, '');
      
      // 7. 处理任何留下的空行和多余空格
      cleanedContent = cleanedContent.replace(/\n{3,}/g, '\n\n'); // 多于2个换行改为2个
      cleanedContent = cleanedContent.trim();
      
      return cleanedContent;
    },
    
    // 移除JSON标签前缀
    removeJsonTagPrefix(text) {
      if (!text) return '';
      
      // 移除EMAIL_JSON_START前缀和内部出现的标记
      text = text.replace(/EMAIL_JSON_START\s+内容[:：]?\s*/ig, '');
      
      // 移除EMAIL_JSON_END和其他可能的标记
      text = text.replace(/EMAIL_JSON_END/ig, '');
      text = text.replace(/JSON_START\s+/ig, '');
      text = text.replace(/JSON_END/ig, '');
      text = text.replace(/EMAIL_JSON\s+/ig, '');
      
      return text;
    },
    
    startEditing() {
      // 不需要此方法，直接在intention中编辑
    },
    
    cancelEditing() {
      // 不需要此方法
    },

    // 保存草稿
    async saveDraft() {
      if (!this.newEmail.subject && !this.newEmail.intention) {
        this.showNotification('error', '请填写邮件主题或内容');
        return;
      }
      
      this.isSaving = true;
      
      try {
        // 准备要保存的草稿数据
        const draftData = {
          recipient: this.newEmail.recipient,
          subject: this.newEmail.subject || '无主题',
          content: this.newEmail.intention || '',
          date: new Date().toISOString(),
          id: this.currentDraftId || null
        };
        
        console.log('准备保存草稿:', draftData);
        
        // 如果API连接可用，发送到后端
        if (this.apiConnected) {
          const response = await fetch(`${this.backendUrl}/email/save-draft`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(draftData)
          });
          
          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`保存草稿失败: ${response.status} ${errorText}`);
          }
          
          const result = await response.json();
          console.log('草稿保存API响应:', result);
          
          // 如果是新草稿，更新ID
          if (result && result.id) {
            this.currentDraftId = result.id;
          }
          
          // 重新加载草稿箱
          await this.loadDrafts();
          
          this.showNotification('success', '草稿已保存');
        } else {
          // 如果API不可用，保存到本地存储
          console.log('API不可用，保存草稿到本地存储');
          
          // 生成唯一ID
          if (!draftData.id) {
            draftData.id = `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          }
          
          // 获取现有草稿
          let drafts = [];
          try {
            const savedDrafts = localStorage.getItem('email_drafts');
            if (savedDrafts) {
              drafts = JSON.parse(savedDrafts);
            }
          } catch (e) {
            console.error('解析本地草稿失败:', e);
            drafts = [];
          }
          
          // 检查是否已存在该草稿
          const existingIndex = drafts.findIndex(d => d.id === draftData.id);
          if (existingIndex >= 0) {
            // 更新现有草稿
            drafts[existingIndex] = draftData;
          } else {
            // 添加新草稿
            drafts.push(draftData);
          }
          
          // 保存回本地存储
          localStorage.setItem('email_drafts', JSON.stringify(drafts));
          
          // 更新当前草稿ID
          this.currentDraftId = draftData.id;
          
          // 更新草稿箱
          this.drafts = drafts;
          
          this.showNotification('success', '草稿已保存到本地');
        }
        
        // 如果用户选择保存后关闭，则关闭模态框
        if (closeAfterSave) {
          this.showComposeModal = false;
          this.resetForm();
        }
      } catch (error) {
        console.error('保存草稿失败:', error);
        this.showNotification('error', '保存草稿失败: ' + error.message);
        
        // 尝试保存到本地作为备份
        try {
          // 生成唯一ID
          const draftData = {
            recipient: this.newEmail.recipient,
            subject: this.newEmail.subject || '无主题',
            content: this.newEmail.intention || '',
            date: new Date().toISOString(),
            id: this.currentDraftId || `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
          };
          
          // 获取现有草稿
          let drafts = [];
          const savedDrafts = localStorage.getItem('email_drafts');
          if (savedDrafts) {
            drafts = JSON.parse(savedDrafts);
          }
          
          // 检查是否已存在该草稿
          const existingIndex = drafts.findIndex(d => d.id === draftData.id);
          if (existingIndex >= 0) {
            drafts[existingIndex] = draftData;
          } else {
            drafts.push(draftData);
          }
          
          // 保存回本地存储
          localStorage.setItem('email_drafts', JSON.stringify(drafts));
          
          // 更新当前草稿ID
          this.currentDraftId = draftData.id;
          
          console.log('草稿已保存到本地作为备份');
          this.showNotification('info', '草稿已保存到本地作为备份');
        } catch (backupError) {
          console.error('保存草稿到本地备份失败:', backupError);
        }
      } finally {
        this.isSaving = false;
      }
    },
    
    // 发送邮件
    async sendEmail() {
      // 验证邮件数据
      if (!this.newEmail.recipient) {
        this.showRecipientError = true;
        return;
      } else {
        this.showRecipientError = false;
      }
      
      if (!this.newEmail.intention && !this.generatedContent) {
        this.showContentError = true;
        return;
      } else {
        this.showContentError = false;
      }
      
      this.isSending = true;
      
      try {
        // 准备要发送的邮件数据
        const emailData = {
          recipient: this.newEmail.recipient,
          subject: this.newEmail.subject || '无主题',
          content: this.newEmail.intention || this.generatedContent || '',
          date: new Date().toISOString()
        };
        
        console.log('准备发送邮件:', emailData);
        
        // 如果API连接可用，发送到后端
        if (this.apiConnected) {
          const response = await fetch(`${this.backendUrl}/email/send`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(emailData)
          });
          
          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`发送邮件失败: ${response.status} ${errorText}`);
          }
          
          const result = await response.json();
          console.log('邮件发送API响应:', result);
          
          // 重新加载发件箱
          await this.loadOutbox();
          
          // 如果是草稿，删除该草稿
          if (this.currentDraftId) {
            try {
              await fetch(`${this.backendUrl}/email/drafts/${this.currentDraftId}`, {
                method: 'DELETE'
              });
              console.log('已删除草稿:', this.currentDraftId);
            } catch (deleteError) {
              console.error('删除草稿失败:', deleteError);
            }
            
            // 重新加载草稿箱
            await this.loadDrafts();
          }
          
          this.showNotification('success', '邮件已发送');
        } else {
          // 如果API不可用，保存到本地存储
          console.log('API不可用，保存邮件到本地存储');
          
          // 添加ID
          emailData.id = `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          emailData.status = 'sent';
          
          // 获取现有发件箱
          let outbox = [];
          try {
            const savedOutbox = localStorage.getItem('email_outbox');
            if (savedOutbox) {
              outbox = JSON.parse(savedOutbox);
            }
          } catch (e) {
            console.error('解析本地发件箱失败:', e);
            outbox = [];
          }
          
          // 添加新邮件
          outbox.push(emailData);
          
          // 保存回本地存储
          localStorage.setItem('email_outbox', JSON.stringify(outbox));
          
          // 更新发件箱
          this.outbox = outbox;
          
          // 如果是草稿，从本地草稿箱中删除
          if (this.currentDraftId) {
            try {
              let drafts = [];
              const savedDrafts = localStorage.getItem('email_drafts');
              if (savedDrafts) {
                drafts = JSON.parse(savedDrafts);
                drafts = drafts.filter(d => d.id !== this.currentDraftId);
                localStorage.setItem('email_drafts', JSON.stringify(drafts));
              }
              
              // 更新草稿箱
              this.drafts = drafts;
              console.log('已从本地删除草稿:', this.currentDraftId);
            } catch (deleteError) {
              console.error('从本地删除草稿失败:', deleteError);
            }
          }
          
          this.showNotification('success', '邮件已保存到本地发件箱');
        }
        
        // 关闭模态框并重置表单
        this.showComposeModal = false;
        this.resetForm();
      } catch (error) {
        console.error('发送邮件失败:', error);
        this.showNotification('error', '发送邮件失败: ' + error.message);
      } finally {
        this.isSending = false;
      }
    },
    
    resetForm() {
      this.newEmail = {
        recipient: '',
        intention: '',
        subject: 'AI辅助生成的邮件'
      };
      this.generatedContent = '';
      this.currentDraftId = null;
      this.selectedTemplateId = null;
    },
    
    regenerateContent() {
      // 清空生成内容，准备重新生成
      this.generatedContent = '';
      
      // 添加调试日志，查看当前使用的主题
      console.log('根据主题重新生成邮件:', this.newEmail.subject);
      
      // 设置生成状态和当前使用的主题
      this.isGenerating = true;
      this.generatingWithSubject = this.newEmail.subject || "AI辅助生成的邮件";
      
      // 根据主题生成邮件内容
      this.generateEmailFromSubject();
    },
    
    // 根据主题生成邮件
    async generateEmailFromSubject() {
      // 检查API连接
      if (!this.apiConnected) {
        await this.checkApiConnection();
        if (!this.apiConnected) {
          alert('无法连接到后端服务，请检查服务是否启动');
          return;
        }
      }
      
      // 验证是否有主题和收件人
      if (!this.newEmail.subject) {
        alert('请先输入邮件主题');
        this.isGenerating = false;
        return;
      }
      
      if (!this.newEmail.recipient) {
        this.showRecipientError = true;
        this.isGenerating = false;
        return;
      }

      // 保存原始数据
      const originalSubject = this.newEmail.subject;
      const originalRecipient = this.newEmail.recipient;

      try {
        console.log('根据主题生成邮件:', this.newEmail.subject);
        
        // 调用后端API，根据主题生成邮件
        const response = await fetch(`${this.backendUrl}/email/generate-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            intention: "",  // 不使用之前的内容
            subject: this.newEmail.subject,
            recipient: this.newEmail.recipient,
            mode: "generate" // 指定模式为根据主题生成
          })
        });

        if (!response.ok) {
          throw new Error('根据主题生成邮件失败');
        }

        const responseData = await response.json();
        
        // 处理返回的数据
        if (responseData) {
          // 新的API响应格式包含完整的主题、收件人和纯内容
          if (responseData.content && (responseData.subject !== undefined || responseData.recipient !== undefined)) {
            console.log('使用结构化数据填充邮件表单:', responseData);
            
            // 使用返回的纯内容
            const pureContent = this.cleanThinkingContent(responseData.content);
            this.generatedContent = pureContent;
            this.newEmail.intention = pureContent;
            
            // 直接填充返回的主题和收件人
            if (responseData.subject && responseData.subject !== "[邮件主题]" && 
                responseData.subject !== "[未指定]" && responseData.subject !== "请填写主题") {
              this.newEmail.subject = responseData.subject;
              
              if (originalSubject !== responseData.subject) {
                console.log(`更新邮件主题: ${responseData.subject}`);
              }
            }
            
            if (responseData.recipient && responseData.recipient !== "[收件人]" && 
                responseData.recipient !== "[未指定]" && responseData.recipient !== "请填写收件人") {
              this.newEmail.recipient = responseData.recipient;
              
              if (originalRecipient !== responseData.recipient) {
                console.log(`更新收件人: ${responseData.recipient}`);
              }
            }
            
            // 记录日志
            console.log("已使用API返回的结构化数据填充邮件表单");
          } 
          // 兼容旧API响应格式
          else if (responseData.content) {
            console.log('使用非结构化数据处理邮件内容');
            
            // 清理思考过程标记
            const cleanedContent = this.cleanThinkingContent(responseData.content);
            
            // 尝试从生成的内容中提取主题和收件人
            const recipientMatch = cleanedContent.match(/收件人[:：]\s*(.+?)[\n\r]/);
            const subjectMatch = cleanedContent.match(/主题[:：]\s*(.+?)[\n\r]/);
            
            // 先保存提取到的主题和收件人
            let extractedRecipient = '';
            let extractedSubject = '';
            
            // 如果提取到了更好的主题和收件人，更新表单
            if (recipientMatch && recipientMatch[1].trim()) {
              extractedRecipient = recipientMatch[1].trim();
              if (extractedRecipient !== "[收件人]" && extractedRecipient !== "[未指定]" && extractedRecipient !== "请填写收件人") {
                this.newEmail.recipient = extractedRecipient;
                
                if (originalRecipient !== extractedRecipient) {
                  console.log(`更新收件人: ${extractedRecipient}`);
                }
              }
            }
            
            if (subjectMatch && subjectMatch[1].trim()) {
              extractedSubject = subjectMatch[1].trim();
              if (extractedSubject !== "[邮件主题]" && extractedSubject !== "[未指定]" && extractedSubject !== "请填写主题") {
                this.newEmail.subject = extractedSubject;
                
                if (originalSubject !== extractedSubject) {
                  console.log(`更新邮件主题: ${extractedSubject}`);
                }
              }
            }
            
            // 提取内容部分作为正文
            const contentMatch = cleanedContent.match(/内容[:：][\r\n]+(.+)/s);
            let pureContent = '';
            
            if (contentMatch && contentMatch[1]) {
              // 只保存纯正文部分
              pureContent = contentMatch[1].trim();
            } else {
              // 如果无法提取正文部分，则去掉开头的主题和收件人信息后的内容作为正文
              pureContent = cleanedContent;
              
              // 如果没有找到明确的 "内容:" 标记，但有收件人和主题标记，移除这些行
              if (recipientMatch) {
                pureContent = pureContent.replace(recipientMatch[0], '');
              }
              if (subjectMatch) {
                pureContent = pureContent.replace(subjectMatch[0], '');
              }
              // 移除可能的"内容:"标记
              pureContent = pureContent.replace(/内容[:：][\r\n]+/, '');
              
              pureContent = pureContent.trim();
            }
            
            // 确保纯正文部分不包含思考内容
            pureContent = this.cleanThinkingContent(pureContent);
            
            // 更新生成的内容和编辑框
            this.generatedContent = pureContent;
            this.newEmail.intention = pureContent;
            
            // 记录日志
            console.log("已从非结构化数据中提取主题、收件人和内容");
          } else {
            throw new Error('无法解析生成的邮件内容');
          }
        } else {
          throw new Error('生成的内容为空');
        }
        
        console.log('根据主题生成邮件成功');
      } catch (error) {
        console.error('根据主题生成邮件失败:', error);
        alert('根据主题生成邮件内容失败，请检查后端服务是否正常运行');
      } finally {
        // 不管成功还是失败，都重置生成状态
        this.isGenerating = false;
      }
    },
    
    // 查看草稿
    viewDraft(draft) {
      this.currentEmail = draft;
      this.emailViewType = 'drafts';
      this.showEmailViewModal = true;
    },
    
    // 查看邮件详情
    viewEmail(email, type) {
      this.currentEmail = email;
      this.emailViewType = type;
      this.showEmailViewModal = true;
    },
    
    // 编辑草稿
    async editDraft(draftId) {
      console.log('编辑草稿，ID:', draftId);
      try {
        const response = await fetch(`${this.backendUrl}/email/drafts/${draftId}`);
        if (!response.ok) {
          const errorText = await response.text();
          console.error('获取草稿详情失败, 状态码:', response.status, '错误信息:', errorText);
          throw new Error(`获取草稿详情失败 (${response.status})`);
        }
        
        const draft = await response.json();
        console.log('获取到的草稿数据:', draft);
        
        // 打开编辑窗口
        this.showComposeModal = true;
        this.currentDraftId = draftId;
        
        // 填充表单
        this.newEmail = {
          recipient: draft.recipient || '',
          subject: draft.subject || '无主题',
          intention: draft.content || ''
        };
        
        // 更新生成内容状态
        this.generatedContent = draft.content || '';
      } catch (error) {
        console.error('编辑草稿失败:', error);
        alert('获取草稿详情失败，请重试。错误: ' + error.message);
      }
    },
    
    // 删除草稿
    async deleteDraft(draftId) {
      if (!confirm('确定要删除这封草稿吗？')) {
        return;
      }
      
      try {
        const response = await fetch(`${this.backendUrl}/email/drafts/${draftId}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error('删除草稿失败');
        }
        
        // 重新加载草稿箱
        this.loadEmailData();
        alert('草稿删除成功');
      } catch (error) {
        console.error('删除草稿失败:', error);
        alert('删除草稿失败，请重试');
      }
    },
    
    // 创建新模板
    saveAsTemplate() {
      if (!this.newEmail.intention) {
        alert('请先输入邮件内容');
        return;
      }
      
      // 打开模板编辑窗口
      this.showTemplateModal = true;
      this.editingTemplate = {
        id: null,
        name: '新模板 - ' + new Date().toLocaleString(),
        subject: this.newEmail.subject,
        content: this.newEmail.intention
      };
    },
    
    // 编辑模板
    editTemplate(template) {
      this.showTemplateModal = true;
      this.editingTemplate = { ...template };
    },
    
    // 使用模板
    useTemplate(template) {
      this.showComposeModal = true;
      this.newEmail.subject = template.subject;
      this.generatedContent = template.content;
    },
    
    // 应用选择的模板
    applyTemplate() {
      if (!this.selectedTemplateId) {
        return;
      }
      
      const template = this.templates.find(t => t.id === this.selectedTemplateId);
      if (template) {
        this.newEmail.subject = template.subject;
        this.generatedContent = template.content;
      }
    },
    
    // 保存模板
    async saveTemplate() {
      if (!this.editingTemplate.name || !this.editingTemplate.content) {
        alert('请填写必要的模板信息');
        return;
      }
      
      try {
        let url = `${this.backendUrl}/email/templates`;
        let method = 'POST';
        
        // 如果是编辑现有模板
        if (this.editingTemplate.id) {
          url = `${this.backendUrl}/email/templates/${this.editingTemplate.id}`;
          method = 'PUT';
        }
        
        const response = await fetch(url, {
          method: method,
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: this.editingTemplate.name,
            subject: this.editingTemplate.subject,
            content: this.editingTemplate.content
          })
        });
        
        if (!response.ok) {
          throw new Error('保存模板失败');
        }
        
        // 重新加载模板数据
        await this.loadTemplates();
        
        // 关闭模板编辑窗口
        this.showTemplateModal = false;
        alert('模板保存成功');
      } catch (error) {
        console.error('保存模板失败:', error);
        alert('保存模板失败，请重试');
      }
    },
    
    // 删除模板
    async deleteTemplate(templateId) {
      if (!confirm('确定要删除这个模板吗？')) {
        return;
      }
      
      try {
        const response = await fetch(`${this.backendUrl}/email/templates/${templateId}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error('删除模板失败');
        }
        
        // 重新加载模板数据
        await this.loadTemplates();
        alert('模板删除成功');
      } catch (error) {
        console.error('删除模板失败:', error);
        alert('删除模板失败，请重试');
      }
    },
    
    // 测试SMTP连接 - 更新为同时测试收发邮件服务器
    async testConnection() {
      this.isTestingConnection = true;
      this.testConnectionResult = '';
      
      try {
        // 向后端发送测试请求
        const response = await fetch(`${this.backendUrl}/email/test-connection`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            smtp_server: this.emailSettings.server,
            smtp_port: parseInt(this.emailSettings.port),
            receive_type: this.emailSettings.receiveType,
            receive_server: this.emailSettings.receiveServer,
            receive_port: parseInt(this.emailSettings.receivePort),
            receive_secure: this.emailSettings.receiveSecure,
            username: this.emailSettings.username,
            password: this.emailSettings.password
          })
        });
        
        const result = await response.json();
        
        if (response.ok) {
          // 检查新的返回格式
          if (result.smtp_test && result.receive_test) {
            const smtpResult = result.smtp_test.result;
            const receiveResult = result.receive_test.result;
            
            if (smtpResult === "成功" && (receiveResult === "成功" || receiveResult === "未测试")) {
              this.testConnectionResult = '连接测试成功！SMTP和接收服务器配置正确。';
              this.testConnectionSuccess = true;
              
              // 直接更新通知状态而不使用$notification属性
              this.notification = {
                show: true,
                type: 'success',
                message: '连接测试成功！服务器配置正确。',
                timeout: setTimeout(() => {
                  this.notification.show = false;
                }, 3000)
              };
            } else {
              let errorMsg = '';
              if (smtpResult !== "成功") {
                errorMsg += `SMTP连接失败: ${result.smtp_test.error || '未知错误'}\n`;
              }
              if (receiveResult !== "成功" && receiveResult !== "未测试") {
                errorMsg += `接收服务器连接失败: ${result.receive_test.error || '未知错误'}`;
              }
              throw new Error(errorMsg.trim());
            }
          } else {
            // 兼容旧格式
            this.testConnectionResult = result.message || '连接测试成功';
            this.testConnectionSuccess = true;
            
            // 直接更新通知状态而不使用$notification属性
            this.notification = {
              show: true,
              type: 'success',
              message: this.testConnectionResult,
              timeout: setTimeout(() => {
                this.notification.show = false;
              }, 3000)
            };
          }
        } else {
          // 如果新API失败但返回了响应，则显示详细错误
          console.error('连接测试失败 (新API):', result);
          const errorMessage = result.detail || result.message || '未知错误';
          throw new Error(errorMessage);
        }
      } catch (error) {
        this.testConnectionResult = `连接测试失败: ${error.message || '未知错误'}`;
        this.testConnectionSuccess = false;
        
        // 直接更新通知状态而不使用$notification属性
        this.notification = {
          show: true,
          type: 'error',
          message: this.testConnectionResult,
          timeout: setTimeout(() => {
            this.notification.show = false;
          }, 5000)
        };
      } finally {
        this.isTestingConnection = false;
      }
    },
    
    // 保存邮件设置
    async saveEmailSettings() {
      try {
        const response = await fetch(`${this.backendUrl}/email/config`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            smtp_server: this.emailSettings.server,
            smtp_port: this.emailSettings.port,
            smtp_username: this.emailSettings.username,
            smtp_password: this.emailSettings.password,
            sender_email: this.emailSettings.sender,
            receive_type: this.emailSettings.receiveType,
            receive_server: this.emailSettings.receiveServer,
            receive_port: this.emailSettings.receivePort,
            receive_secure: this.emailSettings.receiveSecure,
            check_frequency: this.emailSettings.checkFrequency
          })
        });
        
        if (!response.ok) {
          throw new Error('保存邮件设置失败');
        }
        
        const result = await response.json();
        
        // 直接更新通知状态而不使用$notification属性
        this.notification = {
          show: true,
          type: 'success',
          message: result.message || '邮件设置已保存',
          timeout: setTimeout(() => {
            this.notification.show = false;
          }, 3000)
        };
        
        // 如果设置了自动检查，通知后端开始定时任务
        if (this.emailSettings.checkFrequency !== 'manual') {
          await fetch(`${this.backendUrl}/email/start-mail-check`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              frequency: this.emailSettings.checkFrequency
            })
          });
        }
      } catch (error) {
        console.error('保存邮件设置失败:', error);
        
        // 直接更新通知状态而不使用$notification属性
        this.notification = {
          show: true,
          type: 'error',
          message: '保存邮件设置失败，请重试',
          timeout: setTimeout(() => {
            this.notification.show = false;
          }, 5000)
        };
      }
    },
    
    // 手动检查新邮件
    async checkNewEmails() {
      if (!this.apiConnected) {
        await this.checkApiConnection();
        if (!this.apiConnected) {
          alert('无法连接到后端服务，请检查服务是否启动');
          return;
        }
      }
      
      if (!this.emailSettings.username || !this.emailSettings.password || 
          !this.emailSettings.receiveServer || !this.emailSettings.receivePort) {
        alert('请先完成接收邮件设置');
        return;
      }
      
      this.isCheckingMails = true;
      
      try {
        const response = await fetch(`${this.backendUrl}/email/check-new-mails`, {
          method: 'POST'
        });
        
        if (!response.ok) {
          throw new Error('检查新邮件失败');
        }
        
        const result = await response.json();
        console.log('检查新邮件响应:', result);
        
        // 刷新收件箱数据
        await this.loadEmailData();
        
        // 显示结果 - 修正属性名称，使用new_mails而不是new_emails
        if (result.new_mails && result.new_mails.length > 0) {
          alert(`成功接收到 ${result.new_mails.length} 封新邮件`);
        } else {
          alert('没有新邮件');
        }
      } catch (error) {
        console.error('检查新邮件失败:', error);
        alert('检查新邮件失败，请检查邮件设置或网络连接');
      } finally {
        this.isCheckingMails = false;
      }
    },
    
    // 显示邮件内容，移除思考部分
    displayEmailContent(content) {
      if (!content) return '';
      
      // 直接调用我们增强的清理函数
      return this.cleanThinkingContent(content);
    },
    
    // 处理DOM事件
    handleDOMEmailEvent(event) {
      console.log('收到DOM邮件事件:', event.type);
      try {
        let eventData = null;
          
        // 提取事件数据
          if (event.detail) {
          eventData = event.detail;
          console.log('从event.detail中获取数据');
        } else if (event.data) {
          eventData = event.data;
          console.log('从event.data中获取数据');
        }
        
        if (!eventData) {
          console.warn('DOM事件没有包含有效数据');
          // 即使没有数据，也尝试打开编辑器
          this.showComposeModal = true;
          return;
        }
        
        // 打印数据类型用于调试
        console.log('DOM事件数据类型:', typeof eventData);
        
        // 直接调用处理函数
        this.handleComposeEmail(eventData);
        
        // 强制检查localStorage
        setTimeout(() => {
          this.checkLocalStorageForPendingEmail();
        }, 100);
      } catch (error) {
        console.error('处理DOM邮件事件时出错:', error);
        // 确保错误不会阻止打开编辑器
        this.showComposeModal = true;
      }
    },
    
    // 处理填充邮件内容事件 - 只填充内容但不打开编辑器
    handleFillEmailContent(emailInfo) {
      console.log('处理填充邮件内容事件:', emailInfo);
      
      try {
        // 强制转换为对象，以防传入的是原始类型
        if (!emailInfo || typeof emailInfo !== 'object') {
          emailInfo = typeof emailInfo === 'string' ? { content: emailInfo } : { content: String(emailInfo || '') };
        }
        
        // 如果是CustomEvent类型，从detail属性中提取数据
        if (emailInfo instanceof CustomEvent && emailInfo.detail) {
          emailInfo = emailInfo.detail;
          console.log('从CustomEvent中提取邮件数据:', emailInfo);
        }
        
        // 设置主题 (尝试从不同可能的属性名中获取)
        if (emailInfo.subject) {
          console.log('设置主题:', emailInfo.subject);
          this.newEmail.subject = emailInfo.subject;
        } else if (emailInfo.emailSubject) {
          console.log('设置主题:', emailInfo.emailSubject);
          this.newEmail.subject = emailInfo.emailSubject;
        }
        
        // 设置收件人 (尝试从不同可能的属性名中获取)
        if (emailInfo.recipient) {
          console.log('设置收件人:', emailInfo.recipient);
          this.newEmail.recipient = emailInfo.recipient;
        } else if (emailInfo.to) {
          console.log('设置收件人:', emailInfo.to);
          this.newEmail.recipient = emailInfo.to;
        } else if (emailInfo.emailTo) {
          console.log('设置收件人:', emailInfo.emailTo);
          this.newEmail.recipient = emailInfo.emailTo;
        }
        
        // 设置邮件内容 (尝试从不同可能的属性名中获取)
        if (emailInfo.content && typeof emailInfo.content === 'string') {
          console.log('设置邮件内容:', emailInfo.content.substring(0, 50) + '...');
          this.newEmail.intention = emailInfo.content;
          this.generatedContent = emailInfo.content;
        } else if (emailInfo.emailContent && typeof emailInfo.emailContent === 'string') {
          console.log('设置邮件内容:', emailInfo.emailContent.substring(0, 50) + '...');
          this.newEmail.intention = emailInfo.emailContent;
          this.generatedContent = emailInfo.emailContent;
        } else if (emailInfo.body && typeof emailInfo.body === 'string') {
          console.log('设置邮件内容:', emailInfo.body.substring(0, 50) + '...');
          this.newEmail.intention = emailInfo.body;
          this.generatedContent = emailInfo.body;
        } else if (emailInfo.fullResponse && typeof emailInfo.fullResponse === 'string') {
          // 如果有完整响应，使用它作为备选
          console.log('使用完整响应作为邮件内容');
          this.newEmail.intention = emailInfo.fullResponse;
          this.generatedContent = emailInfo.fullResponse;
        } else if (typeof emailInfo === 'string') {
          // 如果整个emailInfo是字符串，直接使用
          console.log('使用字符串参数作为邮件内容');
          this.newEmail.intention = emailInfo;
          this.generatedContent = emailInfo;
        } else {
          console.warn('未找到有效的邮件内容:', emailInfo);
        }
        
        console.log('邮件内容填充完成:', {
          subject: this.newEmail.subject,
          recipient: this.newEmail.recipient,
          contentLength: this.newEmail.intention ? this.newEmail.intention.length : 0
        });
      } catch (error) {
        console.error('填充邮件内容时出错:', error);
      }
    },
    
    // 处理打开邮件编辑器事件 - 打开编辑器并显示已填充的内容
    handleOpenEmailCompose(emailInfo) {
      console.log('处理打开邮件编辑器事件:', emailInfo);
      
      try {
        // 如果传递了邮件信息，先填充内容
        if (emailInfo) {
          this.handleFillEmailContent(emailInfo);
        }
        
        // 打开编辑器模态框
        this.showComposeModal = true;
        console.log('已打开邮件编辑器, 当前内容长度:', this.newEmail.intention?.length || 0);
        
        // 如果内容是空的，尝试自动生成一封邮件
        if (!this.newEmail.intention || !this.newEmail.intention.trim()) {
          console.log('邮件内容为空，尝试自动生成');
          this.generateFirstEmail();
        }
      } catch (error) {
        console.error('打开邮件编辑器时出错:', error);
        // 确保无论如何都显示编辑器
        this.showComposeModal = true;
      }
    },
    
    // 原有的处理邮件编辑事件 - 保留以兼容现有代码
    handleComposeEmail(emailInfo) {
      console.log('处理邮件编辑事件:', emailInfo);
      
      try {
        // 填充内容
        this.handleFillEmailContent(emailInfo);
        
        // 打开编辑器
        this.handleOpenEmailCompose();
      } catch (error) {
        console.error('处理邮件编辑事件时出错:', error);
        // 确保无论如何都显示编辑器
        this.showComposeModal = true;
      }
    },
    
    // 处理来自document的compose-email事件
    onComposeEmailEvent(event) {
      console.log('EmailSystem - 收到compose-email事件，数据:', event.detail);
      this.handleComposeEmail(event.detail);
    },
    
    // 处理来自document的switch-to-email-compose事件
    onSwitchToEmailComposeEvent(event) {
      console.log('EmailSystem - 收到switch-to-email-compose事件');
      if (event.detail) {
        console.log('事件数据:', event.detail);
        this.handleComposeEmail(event.detail);
      } else {
        console.log('没有收到邮件数据，将打开空白邮件编辑器');
        this.showComposeModal = true;
      }
    },
    
    // 添加新方法确保事件注册
    registerEventListeners() {
      console.log('重新注册邮件相关事件处理器');
      this.removeEventListeners(); // 先移除

      emitter.on('compose-email', this.handleComposeEmail);
      emitter.on('switch-to-email-compose', this.handleComposeEmail);
      emitter.on('compose-email-from-ai', this.handleComposeEmail); // 新增
      emitter.on('check-email-pending', this.checkPendingEmail);

      document.addEventListener('compose-email', this.handleDOMEmailEvent);
      document.addEventListener('switch-to-email-compose', this.handleDOMEmailEvent);
      document.addEventListener('compose-email-from-ai', this.handleDOMEmailEvent); // 新增
      document.addEventListener('open-email-composer', this.handleDOMEmailEvent); // 新增
    },
    
    // 移除事件监听器以避免重复
    removeEventListeners() {
      emitter.off('compose-email', this.handleComposeEmail);
      emitter.off('switch-to-email-compose', this.handleComposeEmail);
      emitter.off('compose-email-from-ai', this.handleComposeEmail); // 新增
      emitter.off('check-email-pending', this.checkPendingEmail);

      document.removeEventListener('compose-email', this.handleDOMEmailEvent);
      document.removeEventListener('switch-to-email-compose', this.handleDOMEmailEvent);
      document.removeEventListener('compose-email-from-ai', this.handleDOMEmailEvent); // 新增
      document.removeEventListener('open-email-composer', this.handleDOMEmailEvent); // 新增
    },
    
    // 检查是否有待处理的邮件内容
    checkPendingEmail() {
      console.log('检查是否有待处理的邮件内容');
      
      // 首先检查localStorage
      this.checkLocalStorageForPendingEmail();
      
      // 如果已经有填充的内容且没有显示编辑器，则显示
      if (!this.showComposeModal && this.newEmail && 
          (this.newEmail.intention || this.newEmail.recipient || this.newEmail.subject !== 'AI辅助生成的邮件')) {
        console.log('发现待处理的邮件内容，打开编辑器：', {
          subject: this.newEmail.subject,
          recipient: this.newEmail.recipient,
          contentLength: this.newEmail.intention ? this.newEmail.intention.length : 0
        });
        
        // 打开邮件编辑器
        this.showComposeModal = true;
      }
    },
    
    // 添加DOM事件监听
    addDOMEventListeners() {
      console.log('添加Window级别的邮件相关事件监听器');
      window.addEventListener('compose-email', this.handleDOMEmailEvent); // 保留
      window.addEventListener('compose-email-from-ai', this.handleDOMEmailEvent); // 新增
      window.addEventListener('open-email-composer', this.handleDOMEmailEvent); // 新增
    },
    
    // 移除DOM事件监听
    removeDOMEventListeners() {
      window.removeEventListener('compose-email', this.handleDOMEmailEvent);
      window.removeEventListener('compose-email-from-ai', this.handleDOMEmailEvent); // 新增
      window.removeEventListener('open-email-composer', this.handleDOMEmailEvent); // 新增
    },
    
    // 检查localStorage中是否有待处理的邮件数据
    checkLocalStorageForPendingEmail() {
      console.log('检查localStorage中是否有待处理的邮件数据');
      
      try {
        // 首先检查force_open_email标志
        const forceOpen = localStorage.getItem('force_open_email') === 'true';
        if (forceOpen) {
          console.log('检测到force_open_email标志');
        }
        
        const pendingEmailData = localStorage.getItem('pending_email_data');
        if (pendingEmailData) {
          console.log('找到待处理的邮件数据，长度:', pendingEmailData.length);
          
          try {
            // 解析数据
          const emailData = JSON.parse(pendingEmailData);
            console.log('成功从localStorage解析的邮件数据:', emailData);
            
            // 暂时不移除数据，等处理成功后再移除
            // localStorage.removeItem('pending_email_data');
            
            // 检查forceOpen标志和from来源
            const needsForceOpen = emailData.forceOpen === true || forceOpen;
            const fromAI = emailData.from === 'ai_assistant';
            
            console.log('邮件数据属性:', {
              needsForceOpen,
              fromAI,
              subject: emailData.subject,
              hasContent: !!emailData.content,
              timestamp: emailData.timestamp
            });
            
            // 检查时间戳，如果数据太旧（超过5分钟），则忽略
            const now = Date.now();
            const dataTime = emailData.timestamp || 0;
            const dataAge = now - dataTime;
            console.log('邮件数据年龄:', dataAge + 'ms');
            
            if (dataAge > 10 * 60 * 1000) { // 10分钟
              console.log('邮件数据已过期（超过10分钟），忽略');
            localStorage.removeItem('pending_email_data');
              localStorage.removeItem('force_open_email');
              return false;
            }
            
            // 先确保我们在正确的视图
            if (this.currentView !== 'drafts') {
              console.log('切换到草稿箱视图');
              this.switchView('drafts');
            }
            
            // 直接处理数据 - 强制使用setTimeout以避免Vue更新周期的问题
            window.setTimeout(() => {
              console.log('立即处理pending email数据');
              
              // 重置表单并设置数据
              this.resetForm();
              
              if (emailData.subject) {
                console.log('设置主题:', emailData.subject);
                this.newEmail.subject = emailData.subject;
              }
              
              if (emailData.recipient) {
                console.log('设置收件人:', emailData.recipient);
                this.newEmail.recipient = emailData.recipient;
              }
              
              if (emailData.content) {
                console.log('设置内容，长度:', emailData.content.length);
                this.newEmail.intention = emailData.content;
                this.generatedContent = emailData.content;
              } else if (emailData.fullResponse) {
                console.log('使用完整响应作为内容');
                this.newEmail.intention = emailData.fullResponse;
                this.generatedContent = emailData.fullResponse;
              }
              
              // 如果需要强制打开，使用专门的方法
              if (needsForceOpen) {
                console.log('使用强制打开方法打开邮件编辑器');
                // 设置视图和状态
          this.showComposeModal = true;
                
                // 确保视图更新后再尝试聚焦
                this.$nextTick(() => {
                  if (this.$refs.subjectInput) {
                    this.$refs.subjectInput.focus();
                  }
                  
                  // 如果成功打开，清除localStorage中的数据
                  if (this.showComposeModal) {
                    console.log('邮件编辑器已成功打开，清除localStorage数据');
                    localStorage.removeItem('pending_email_data');
                    localStorage.removeItem('force_open_email');
                    localStorage.removeItem('email_timestamp');
                  }
                });
              } else {
                // 正常打开编辑器
                console.log('正常打开邮件编辑器');
                this.showComposeModal = true;
                
                // 检查是否成功打开
                setTimeout(() => {
                  if (this.showComposeModal) {
                    console.log('邮件编辑器已成功打开，清除localStorage数据');
                    localStorage.removeItem('pending_email_data');
                    localStorage.removeItem('force_open_email');
                    localStorage.removeItem('email_timestamp');
                  } else {
                    console.warn('邮件编辑器未成功打开，保留localStorage数据');
                  }
                }, 500);
              }
              
              console.log('已打开邮件编辑器并填充数据');
            }, 100);
            
            return true;
          } catch (parseError) {
            console.error('解析邮件数据出错:', parseError);
            // 出错时清除数据，避免反复处理错误数据
            localStorage.removeItem('pending_email_data');
            localStorage.removeItem('force_open_email');
          }
        }
      } catch (error) {
        console.error('处理localStorage中的待处理邮件数据时出错:', error);
      }
      
      console.log('没有找到待处理的邮件数据');
      return false;
    },

    // 在methods部分添加以下方法
    handleModuleChanged(moduleName) {
      console.log(`[EmailSystem] handleModuleChanged: 响应模块切换事件: ${moduleName}`);
      if (moduleName === 'personal-office') {
        // 检查是否有来自AI助手的待处理邮件
        console.log('[EmailSystem] handleModuleChanged: 模块切换到 personal-office，准备延迟调用 checkAiGeneratedEmail');
        
        // 使用setTimeout以确保在Vue组件更新后执行
        window.setTimeout(() => {
          console.log('[EmailSystem] handleModuleChanged: setTimeout 回调执行，准备调用 checkAiGeneratedEmail');
          this.checkAiGeneratedEmail();
        }, 100); // 100ms 延迟，给DOM更新留出时间
      }
    },

    // 添加storage事件处理方法
    handleStorageChange(event) {
      if (event.key === 'pending_email_data') {
        console.log('检测到localStorage中的pending_email_data变化');
        if (event.newValue) {
          console.log('通过storage事件处理邮件数据');
          this.checkLocalStorageForPendingEmail();
        }
      }
    },

    // 强制打开邮件编辑器的方法
    forceOpenEmailComposer(emailData) {
      console.log('强制打开邮件编辑器');
      
      // 如果提供了邮件数据，先处理数据
      if (emailData) {
        this.handleComposeEmail(emailData);
      }
      
      // 设置状态并使用多个尝试确保成功
      this.showComposeModal = true;
      
      // 使用setTimeout进行多次尝试，确保UI更新
      setTimeout(() => {
        if (!this.showComposeModal) {
          console.warn('第一次尝试失败，再次尝试打开邮件编辑器');
          this.showComposeModal = true;
          
          // 额外切换视图确保激活正确的组件
          this.switchView('drafts');
          
          // 最后一次尝试
          setTimeout(() => {
            if (!this.showComposeModal) {
              console.error('多次尝试后仍未能打开邮件编辑器，使用最终方法');
              // 尝试直接操作DOM（如果有引用）
              this.showComposeModal = true;
              
              // 添加到调试日志
              this.debugLogs.push({
                time: new Date().toISOString(),
                event: '最终尝试打开邮件编辑器',
                success: this.showComposeModal
              });
            }
          }, 200);
        } else {
          console.log('邮件编辑器已成功打开');
        }
      }, 100);
      
      return this.showComposeModal;
    },
    
    /**
     * 处理AI生成的邮件事件
     * @param {CustomEvent} event 包含邮件数据的事件对象
     */
    handleAiGeneratedEmail(event) {
      console.log('收到AI生成邮件事件', event?.detail);
      try {
        // 获取邮件数据
        let emailData = null;
        
        if (event && event.detail) {
          emailData = event.detail;
        } else if (window.AI_GENERATED_EMAIL) {
          emailData = window.AI_GENERATED_EMAIL;
          // 清除全局变量
          window.AI_GENERATED_EMAIL = null;
        }
        
        if (!emailData) {
          console.warn('未找到有效的邮件数据');
          return;
        }
        
        console.log('处理AI生成的邮件数据:', emailData);
        
        // 重置表单
        this.resetForm();
        
        // 填充数据
        if (emailData.subject) {
          this.newEmail.subject = emailData.subject;
        }
        
        if (emailData.recipient || emailData.to) {
          this.newEmail.recipient = emailData.recipient || emailData.to || '';
        }
        
        if (emailData.content) {
          this.newEmail.intention = emailData.content;
          this.generatedContent = emailData.content;
        }
        
        // 显示邮件编辑器
        this.showComposeModal = true;
        console.log('已打开邮件编辑器');
        
        // 聚焦到主题输入框
        this.$nextTick(() => {
          if (this.$refs.subjectInput) {
            this.$refs.subjectInput.focus();
          }
        });
      } catch (error) {
        console.error('处理AI生成邮件时出错:', error);
      }
    },

    /**
     * 检查全局存储的邮件数据
     */
    checkGlobalEmailData(event) {
      console.log('检查全局邮件数据');
      try {
        // 从多个可能的来源获取数据
        let emailData = null;
        
        // 1. 从event中获取
        if (event && event.detail) {
          emailData = event.detail;
          console.log('从事件中获取邮件数据');
        } 
        // 2. 从全局变量中获取
        else if (window.AI_GENERATED_EMAIL) {
          emailData = window.AI_GENERATED_EMAIL;
          window.AI_GENERATED_EMAIL = null;
          console.log('从全局变量中获取邮件数据');
        } 
        // 3. 从localStorage中获取
        else {
          // 检查多个可能的键名
          const data1 = localStorage.getItem('aiGeneratedEmail');
          const data2 = localStorage.getItem('ai_generated_email');
          
          if (data1) {
            emailData = JSON.parse(data1);
            localStorage.removeItem('aiGeneratedEmail');
            console.log('从localStorage[aiGeneratedEmail]中获取邮件数据');
          } else if (data2) {
            emailData = JSON.parse(data2);
            localStorage.removeItem('ai_generated_email');
            console.log('从localStorage[ai_generated_email]中获取邮件数据');
          }
        }
        
        if (emailData) {
          console.log('找到全局邮件数据:', emailData);
          
          // 重置表单
          this.resetForm();
          
          // 填充数据
          if (emailData.subject) {
            this.newEmail.subject = emailData.subject;
          }
          
          if (emailData.recipient || emailData.to) {
            this.newEmail.recipient = emailData.recipient || emailData.to || '';
          }
          
          if (emailData.content) {
            this.newEmail.intention = emailData.content;
            this.generatedContent = emailData.content;
          }
          
          // 打开邮件编辑器
          this.showComposeModal = true;
          console.log('已打开邮件编辑器');
          
          // 聚焦到主题输入框
          this.$nextTick(() => {
            if (this.$refs.subjectInput) {
              this.$refs.subjectInput.focus();
            }
          });
        }
      } catch (error) {
        console.error('检查全局邮件数据时出错:', error);
      }
    },

    /**
     * 应用启动时检查是否有AI生成的邮件等待处理
     */
    checkAiGeneratedEmail() {
      console.log('[EmailSystem] checkAiGeneratedEmail: 开始检查 localStorage...');
      try {
        // 仅检查 'ai_generated_email' 键
        const emailDataStr = localStorage.getItem('ai_generated_email');
        console.log(`[EmailSystem] checkAiGeneratedEmail: 从 localStorage 读取到的原始字符串: ${emailDataStr ? emailDataStr.substring(0, 100) + '...' : 'null'}`);
        
        let emailData = null;
        
        if (emailDataStr) {
          // 使用双引号避免引号冲突
          console.log("[EmailSystem] checkAiGeneratedEmail: 从 localStorage['ai_generated_email'] 中找到数据");
          try {
            emailData = JSON.parse(emailDataStr);
            console.log('[EmailSystem] checkAiGeneratedEmail: 成功解析 JSON 数据:', emailData);
            // 处理完后立即移除，防止重复处理
          localStorage.removeItem('ai_generated_email');
            console.log('[EmailSystem] checkAiGeneratedEmail: 已从 localStorage 移除 ai_generated_email');
          } catch (parseError) {
            console.error('[EmailSystem] checkAiGeneratedEmail: 解析 localStorage 数据失败:', parseError);
            localStorage.removeItem('ai_generated_email'); // 解析失败也移除，防止卡住
            console.log('[EmailSystem] checkAiGeneratedEmail: 解析失败，已从 localStorage 移除 ai_generated_email');
            emailData = null; // 确保 emailData 为 null
          }
        }
        
        if (emailData) {
          console.log('[EmailSystem] checkAiGeneratedEmail: 找到待处理的AI生成邮件', emailData);
          
          // 重置表单
          console.log('[EmailSystem] checkAiGeneratedEmail: 调用 resetForm');
          this.resetForm();
          
          // 填充数据
          console.log('[EmailSystem] checkAiGeneratedEmail: 开始填充 newEmail 数据...');
          if (emailData.subject) {
            this.newEmail.subject = emailData.subject;
          }
          
          if (emailData.recipient || emailData.to) {
            this.newEmail.recipient = emailData.recipient || emailData.to || '';
          }
          
          if (emailData.content) {
            this.newEmail.intention = emailData.content;
            this.generatedContent = emailData.content;
          } else if (emailData.fullResponse) {
            this.newEmail.intention = emailData.fullResponse;
            this.generatedContent = emailData.fullResponse;
          }
          console.log('[EmailSystem] checkAiGeneratedEmail: newEmail 数据填充完成:', this.newEmail);
          
          // 打开编辑器
          console.log('[EmailSystem] checkAiGeneratedEmail: 准备设置 showComposeModal = true');
          this.showComposeModal = true;
          console.log(`[EmailSystem] checkAiGeneratedEmail: showComposeModal 已设置为 ${this.showComposeModal}`);
          
          // 聚焦到主题输入框
          this.$nextTick(() => {
            console.log('[EmailSystem] checkAiGeneratedEmail: nextTick 回调执行，尝试聚焦 subjectInput');
            if (this.$refs.subjectInput) {
              this.$refs.subjectInput.focus();
              console.log('[EmailSystem] checkAiGeneratedEmail: subjectInput 已聚焦');
            } else {
              console.warn('[EmailSystem] checkAiGeneratedEmail: 未找到 subjectInput 引用');
            }
          });
          
          return true;
        } else {
          console.log('[EmailSystem] checkAiGeneratedEmail: 未找到或无法处理 localStorage 中的邮件数据');
        }
      } catch (error) {
        console.error('[EmailSystem] checkAiGeneratedEmail: 检查待处理AI生成邮件时发生意外错误:', error);
      }
      
      console.log('[EmailSystem] checkAiGeneratedEmail: 检查结束，未打开编辑器');
      return false;
    },

    // 打开邮件编辑器并填充数据
    openEmailWithData(data) {
      console.log('打开邮件编辑器并填充数据:', data);
      
      // 检查数据有效性
      if (!data) {
        console.error('邮件数据为空');
        return;
      }
      
      try {
        // 确保数据格式正确
        let emailData = data;
        
        // 如果数据是字符串，尝试解析为JSON
        if (typeof data === 'string') {
          try {
            emailData = JSON.parse(data);
          } catch (e) {
            console.error('解析邮件JSON数据失败:', e);
            // 如果解析失败，尝试作为纯文本处理
            emailData = {
              content: data,
              subject: '自动生成的邮件',
              recipient: ''
            };
          }
        }
        
        console.log('处理的邮件数据:', emailData);
        
        // 重置新邮件表单
        this.newEmail = {
          recipient: emailData.recipient || '',
          subject: emailData.subject || 'AI辅助生成的邮件',
          intention: emailData.content || ''
        };
        
        // 显示邮件编辑器
        this.showComposeModal = true;
        
        // 聚焦到收件人输入框
        this.$nextTick(() => {
          const recipientInput = document.getElementById('recipient');
          if (recipientInput) {
            recipientInput.focus();
          }
        });
        
        console.log('邮件编辑器已打开并填充数据');
      } catch (error) {
        console.error('打开邮件编辑器失败:', error);
      }
    },
    
    // 关闭写邮件窗口
    closeComposeModal() {
      console.log('关闭邮件编辑器');
      
      // 检查是否有未保存的内容
      if (this.newEmail.intention && this.newEmail.intention.trim() && !this.isSaving) {
        if (confirm('是否要保存草稿？')) {
          this.saveDraft();
          return;
        }
      }
      
      // 重置表单并关闭窗口
      this.showComposeModal = false;
      this.resetForm();
      
      console.log('邮件编辑器已关闭');
    },
    
    // 检查URL中的tab参数并切换视图
    checkUrlTabParam() {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const tabParam = urlParams.get('tab');
        
        if (tabParam) {
          console.log('从URL参数获取标签:', tabParam);
          this.switchView(tabParam);
        }
      } catch (error) {
        console.error('解析URL参数出错:', error);
      }
    },
    
    // 测试邮件服务器连接
    testEmailConnection() {
      // 只在有配置的情况下测试连接
      if (this.emailSettings.server && this.emailSettings.username) {
        this.testServerConnection();
      }
    },
    
    // 切换当前视图
    switchView(view) {
      console.log('切换邮件视图:', view);
      
      // 验证视图参数
      const validViews = ['drafts', 'outbox', 'inbox', 'settings', 'templates'];
      if (!validViews.includes(view)) {
        console.error('尝试切换到无效的视图:', view);
        return;
      }
      
      // 设置当前视图
      this.currentView = view;
      
      // 根据视图加载相应数据
      if (view === 'drafts') {
        this.loadDrafts();
      } else if (view === 'outbox') {
        this.loadOutbox();
      } else if (view === 'inbox') {
        this.loadInbox();
      } else if (view === 'templates') {
        this.loadTemplates();
      }
      
      console.log('邮件视图已切换到:', view);
    },
    
    // 确认自动填充
    confirmAutoFill(field) {
      if (this.pendingAutoFills[field]) {
        this.newEmail[field] = this.pendingAutoFills[field];
        console.log(`确认自动填充 ${field}: ${this.pendingAutoFills[field]}`);
        
        // 从待确认列表中移除
        const index = this.autoFillNotifications.findIndex(item => item.field === field);
        if (index > -1) {
          this.autoFillNotifications.splice(index, 1);
        }
        
        // 检查是否所有自动填充都已处理
        if (this.autoFillNotifications.length === 0) {
          this.showAutoFillConfirm = false;
        }
      }
    },
    
    // 拒绝自动填充
    rejectAutoFill(field) {
      // 从待确认列表中移除
      const index = this.autoFillNotifications.findIndex(item => item.field === field);
      if (index > -1) {
        this.autoFillNotifications.splice(index, 1);
        console.log(`拒绝自动填充 ${field}: ${this.pendingAutoFills[field]}`);
        delete this.pendingAutoFills[field];
      }
      
      // 检查是否所有自动填充都已处理
      if (this.autoFillNotifications.length === 0) {
        this.showAutoFillConfirm = false;
      }
    },
    
    // 确认所有自动填充
    confirmAllAutoFills() {
      for (const field in this.pendingAutoFills) {
        this.newEmail[field] = this.pendingAutoFills[field];
        console.log(`确认自动填充 ${field}: ${this.pendingAutoFills[field]}`);
      }
      
      // 清空列表并关闭对话框
      this.autoFillNotifications = [];
      this.pendingAutoFills = {};
      this.showAutoFillConfirm = false;
    },
    
    // 拒绝所有自动填充
    rejectAllAutoFills() {
      this.pendingAutoFills = {};
      this.autoFillNotifications = [];
      this.showAutoFillConfirm = false;
      console.log('已拒绝所有自动填充');
    },

    // 处理AI助手的邮件请求
    handleAIEmailRequest(data) {
      console.log('EmailSystem收到AI助手邮件请求:', data);
      
      // 检查数据有效性
      if (!data) {
        console.error('邮件数据为空');
        return;
      }
      
      try {
        // 确保数据格式正确
        let emailData = data;
        
        // 如果数据是字符串，尝试解析为JSON
        if (typeof data === 'string') {
          try {
            emailData = JSON.parse(data);
          } catch (e) {
            console.error('解析邮件JSON数据失败:', e);
            // 如果解析失败，尝试作为纯文本处理
            emailData = {
              content: data,
              subject: '自动生成的邮件',
              recipient: ''
            };
          }
        }
        
        console.log('处理的邮件数据:', emailData);
        
        // 重置表单
        this.resetForm();
        
        // 填充数据
        this.newEmail.recipient = emailData.recipient || '';
        this.newEmail.subject = emailData.subject || 'AI辅助生成的邮件';
        
        // 确保内容字段正确处理
        if (emailData.content) {
          console.log('使用content字段填充内容，长度:', emailData.content.length);
          this.newEmail.intention = emailData.content;
          this.generatedContent = emailData.content;
        } else if (emailData.body) {
          console.log('使用body字段填充内容');
          this.newEmail.intention = emailData.body;
          this.generatedContent = emailData.body;
        } else if (emailData.message) {
          console.log('使用message字段填充内容');
          this.newEmail.intention = emailData.message;
          this.generatedContent = emailData.message;
        } else if (emailData.text) {
          console.log('使用text字段填充内容');
          this.newEmail.intention = emailData.text;
          this.generatedContent = emailData.text;
        } else {
          console.warn('未找到有效的内容字段');
        }
        
        // 显示写邮件面板
        this.showComposeModal = true;
        
        console.log('邮件编辑器已打开并填充数据:', {
          recipient: this.newEmail.recipient,
          subject: this.newEmail.subject,
          contentLength: this.newEmail.intention ? this.newEmail.intention.length : 0
        });
        
        // 使用nextTick确保DOM更新后再聚焦
        this.$nextTick(() => {
          // 聚焦收件人输入框
          const recipientInput = document.getElementById('recipient');
          if (recipientInput) {
            recipientInput.focus();
          }
        });
      } catch (error) {
        console.error('处理AI邮件请求失败:', error);
        // 确保无论如何都显示编辑器
        this.showComposeModal = true;
      }
    },

    // 显示通知
    showNotification(type, message) {
      this.notification = {
        show: true,
        type: type,
        message: message
      };
      
      // 清除之前的定时器
      if (this.notification.timeout) {
        clearTimeout(this.notification.timeout);
      }
      
      // 设置自动关闭
      this.notification.timeout = setTimeout(() => {
        this.notification.show = false;
      }, type === 'error' ? 5000 : 3000);
    },
  },
  watch: {
    showComposeModal(newVal, oldVal) {
      // 记录状态变化
      const now = Date.now();
      const timeSinceLastToggle = now - this.lastModalToggleTime;
      this.lastModalToggleTime = now;
      
      // 添加到调试日志
      this.debugLogs.push({
        time: new Date().toISOString(),
        event: 'showComposeModal变化',
        from: oldVal,
        to: newVal,
        timeSince: timeSinceLastToggle + 'ms'
      });
      
      // 限制日志条数
      if (this.debugLogs.length > 20) {
        this.debugLogs.shift();
      }
      
      console.log(`邮件编辑器状态变化: ${oldVal} -> ${newVal}, 距离上次切换: ${timeSinceLastToggle}ms`);
      
      // 如果是关闭编辑器，检查是否有未保存的内容
      if (oldVal && !newVal && this.newEmail.intention.trim()) {
        console.log('关闭编辑器时有未保存的内容，长度:', this.newEmail.intention.length);
      }
    }
  },
};
</script>

<style scoped>
.email-system {
  display: flex;
  height: 100%;
  background-color: #f5f5f5;
}

.email-sidebar {
  width: 200px;
  background-color: #fff;
  padding: 20px;
  border-right: 1px solid #e0e0e0;
}

.email-menu {
  margin-bottom: 20px;
}

.menu-item {
  padding: 10px;
  cursor: pointer;
  border-radius: 4px;
  margin-bottom: 5px;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item.active {
  background-color: #e3f2fd;
  color: #1976d2;
}

.compose-btn {
  width: 100%;
  padding: 10px;
  background-color: #1976d2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.email-content {
  flex-grow: 1;
  padding: 20px;
  overflow-y: auto;
}

.email-list {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
}

.email-item {
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  cursor: pointer;
  position: relative;
  margin-bottom: 12px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  transition: all 0.2s ease;
}

.email-item:hover {
  background-color: #f5f5f5;
  box-shadow: 0 4px 8px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}

.email-subject {
  font-weight: bold;
  margin-bottom: 8px;
  font-size: 16px;
  color: #333;
}

.email-recipient, .email-sender {
  color: #666;
  margin-bottom: 5px;
  font-size: 14px;
}

.email-date {
  color: #888;
  font-size: 12px;
  margin-bottom: 8px;
}

.email-preview {
  margin-top: 8px;
  color: #555;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  border-left: 3px solid #e0e0e0;
  padding-left: 10px;
  background-color: #f9f9f9;
  border-radius: 0 4px 4px 0;
  padding: 8px 10px;
}

.email-content-view {
  margin-top: 20px;
  white-space: pre-wrap;
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  max-height: 400px;
  overflow-y: auto;
  word-break: break-word;
}

.email-content-view pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  margin: 0;
  padding: 0;
}

.email-actions {
  position: absolute;
  right: 15px;
  top: 15px;
  display: flex;
  gap: 8px;
  background-color: rgba(255, 255, 255, 0.8);
  padding: 4px 8px;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.email-item:hover .email-actions {
  display: flex;
}

.action-icon {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #666;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.action-icon:hover {
  color: #1976d2;
  background-color: rgba(25, 118, 210, 0.1);
}

.action-icon.delete:hover {
  color: #f44336;
  background-color: rgba(244, 67, 54, 0.1);
}

.modal {
  position: fixed;
  z-index: 1000;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-y: auto;
  padding: 20px;
  box-sizing: border-box;
}

.email-compose-modal-wrapper {
  animation: fadeIn 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

@media (max-width: 600px) {
  .content-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .content-actions {
    margin-top: 10px;
    width: 100%;
    justify-content: space-between;
  }
}

.content-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.action-button-small {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background-color: #f7f9fb;
  color: #2c3e50;
  border: 1px solid #e0e5e9;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 110px;
  height: 36px;
  white-space: nowrap;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  margin-top: 15px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  position: sticky;
  bottom: 0;
  background: white;
  padding-bottom: 10px;
  z-index: 10;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.modal-content {
  background-color: #fff;
  border-radius: 12px;
  width: 800px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-header h3 {
  margin: 0;
  color: #333;
  font-size: 20px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 80%;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #333;
}

.modal-body {
  padding: 25px;
}

.email-detail {
  padding: 0;
}

.email-from, .email-to, .email-time, .email-status {
  margin-bottom: 10px;
  padding: 8px 0;
  color: #666;
  font-size: 15px;
}

.email-actions-footer {
  margin-top: 25px;
  display: flex;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.action-btn {
  padding: 10px 18px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.edit-btn {
  background-color: #1976d2;
  color: white;
}

.edit-btn:hover {
  background-color: #1565c0;
}

.send-btn {
  background-color: #4caf50;
}

.send-btn:hover {
  background-color: #43a047;
}

.delete-btn {
  background-color: #f44336;
  color: white;
}

.delete-btn:hover {
  background-color: #e53935;
}

.draft-tag {
  background-color: #ff9800;
  color: white;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: normal;
}

.empty-message {
  padding: 20px;
  text-align: center;
  color: #999;
  font-style: italic;
}

.template-selection {
  margin-bottom: 15px;
}

.preview-section {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.preview-content {
  margin: 10px 0;
  padding: 10px;
  background-color: #fff;
  border-radius: 4px;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
}

.edit-section {
  margin-top: 20px;
}

.edit-content {
  width: 100%;
  min-height: 200px;
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
}

.button-container {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 20px;
}

.secondary-buttons {
  margin-top: 12px;
  border-top: 1px solid #eee;
  padding-top: 12px;
}

.action-button {
  flex: 1;
  height: 40px;
  padding: 0 16px;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
  color: white;
}

.action-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.action-button:active {
  transform: translateY(0);
  box-shadow: none;
}

.generate-btn {
  background-color: #1976d2;
}

.draft-btn {
  background-color: #757575;
}

.regenerate-btn {
  background-color: #ff9800;
}

.template-btn {
  background-color: #4caf50;
}

.test-btn {
  background-color: #ff9800;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.test-btn:hover {
  background-color: #f57c00;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.save-btn {
  background-color: #4caf50;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.save-btn:hover {
  background-color: #43a047;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.create-template-btn {
  padding: 10px;
  background-color: #1976d2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 20px;
}

.email-settings {
  background-color: #fff;
  border-radius: 8px;
  padding: 25px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.email-settings h2 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 24px;
  color: #333;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 12px;
}

.settings-info {
  margin-bottom: 25px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 15px;
  border-left: 4px solid #ffd600;
}

.info-icon {
  background-color: #ffd600;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #333;
  font-size: 16px;
}

.info-text {
  color: #555;
  font-size: 14px;
  line-height: 1.5;
}

.settings-form {
  margin-top: 20px;
}

.settings-section {
  margin-bottom: 30px;
  background-color: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
}

.section-title {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title i {
  color: #1976d2;
}

.form-grid {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.form-grid .form-group {
  flex: 1;
  min-width: 200px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
  font-size: 15px;
}

.input-wrapper {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #aaa;
  font-size: 16px;
}

.input-wrapper .form-input {
  width: 100%;
  padding: 12px 15px;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 15px;
  transition: all 0.2s ease;
}

.input-wrapper .form-input:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.15);
  outline: none;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  margin-top: 25px;
}

.settings-actions .action-button {
  height: 45px;
  min-width: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
  cursor: pointer;
  border: none;
  color: white;
  padding: 0 20px;
}

.settings-actions .test-btn {
  background-color: #ff9800;
}

.settings-actions .test-btn:hover {
  background-color: #f57c00;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.settings-actions .save-btn {
  background-color: #4caf50;
}

.settings-actions .save-btn:hover {
  background-color: #43a047;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.generating-status {
  margin-top: 15px;
  padding: 10px 15px;
  background-color: #e3f2fd;
  border-radius: 6px;
  color: #1976d2;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.feature-info {
  margin-top: 12px;
  margin-bottom: 12px;
}

.feature-tip {
  background-color: #fffde7;
  border-left: 4px solid #ffd600;
  padding: 12px 16px;
  border-radius: 0 4px 4px 0;
  font-size: 14px;
  color: #555;
}

.feature-tip i {
  color: #ffc107;
  margin-right: 6px;
}

.feature-tip ul {
  margin: 8px 0 0 20px;
  padding: 0;
}

.feature-tip li {
  margin-bottom: 4px;
}

.error-message {
  color: #f44336;
  font-size: 13px;
  margin-top: 5px;
}

.form-group.required label:after {
  content: " *";
  color: #f44336;
}

/* 邮件编辑弹窗专用样式 */
.email-compose-modal {
  width: 850px;
  max-width: 95%;
}

.compose-input {
  width: 100%;
  height: 48px;
  padding: 12px 15px;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 15px;
  transition: all 0.2s ease;
}

.compose-input:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.15);
  outline: none;
}

.compose-textarea {
  width: 100%;
  min-height: 220px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-sizing: border-box;
  font-size: 15px;
  line-height: 1.6;
  font-family: inherit;
  resize: vertical;
  transition: all 0.2s ease;
}

.compose-textarea:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.15);
  outline: none;
}

/* 调整模板选择下拉框 */
.template-selection {
  margin: 18px 0;
}

.template-selection select {
  height: 45px;
  padding: 0 15px;
  border-radius: 6px;
}

.inbox-info {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.info-box {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-box strong {
  color: #1976d2;
}

.info-tip {
  font-size: 13px;
  color: #666;
  margin-top: 3px;
}

.refresh-btn {
  background-color: #1976d2;
  color: white;
  border: none;
  padding: 8px 15px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  background-color: #1565c0;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.checking-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1976d2;
  font-size: 14px;
}

.warning-message {
  background-color: #fff8e1;
  border-left: 4px solid #ffb300;
  color: #333;
}

.warning-message i {
  color: #f57c00;
  margin-right: 8px;
}

.input-tip {
  font-size: 12px;
  color: #666;
  margin-top: 5px;
  padding-left: 5px;
}

/* 写邮件弹窗专用样式 */
.email-compose-modal-wrapper {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-content.email-compose-modal {
  width: 850px;
  max-width: 95%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  border: none;
  animation: slideIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

@keyframes slideIn {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-header {
  background: linear-gradient(135deg, #2980b9, #1a5276);
  color: white;
  padding: 20px 25px;
  border-bottom: none;
}

.modal-header h3 {
  font-size: 22px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-header .close-btn {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.1);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: all 0.2s ease;
}

.modal-header .close-btn:hover {
  color: white;
  background: rgba(255, 255, 255, 0.2);
  transform: rotate(90deg);
}

.modal-body {
  padding: 30px;
  background-color: #fff;
  overflow-y: auto;
  flex: 1;
}

.email-form {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.form-group {
  margin-bottom: 0;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: #2c3e50;
  margin-bottom: 10px;
}

.form-group label i {
  color: #3498db;
}

.input-field {
  position: relative;
}

.input-field.error {
  animation: shake 0.4s cubic-bezier(.36,.07,.19,.97) both;
}

@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}

.modern-input, .modern-textarea {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-sizing: border-box;
  font-size: 15px;
  transition: all 0.25s ease;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.modern-input:focus, .modern-textarea:focus {
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
  outline: none;
}

.modern-textarea {
  min-height: 200px;
  line-height: 1.6;
  resize: vertical;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.content-actions {
  display: flex;
  gap: 10px;
}

.action-button-small {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background-color: #f7f9fb;
  color: #2c3e50;
  border: 1px solid #e0e5e9;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 110px;
  height: 36px;
}

.action-button-small:hover {
  background-color: #edf2f7;
  transform: translateY(-2px);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
}

.action-button-small:active {
  transform: translateY(0);
}

.action-button-small:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  margin-top: 15px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  position: sticky;
  bottom: 0;
  background: white;
  padding-bottom: 5px;
  z-index: 10;
}

.secondary-button, .primary-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  border: none;
  min-width: 120px;
}

.secondary-button {
  background-color: #f0f4f8;
  color: #2c3e50;
  border: 1px solid #dde4ee;
}

.secondary-button:hover {
  background-color: #e1e8ef;
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.primary-button {
  background: linear-gradient(135deg, #2980b9, #3498db);
  color: white;
}

.primary-button:hover {
  background: linear-gradient(135deg, #2573a7, #2980b9);
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
}

.secondary-button:disabled, .primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.generating-indicator {
  background-color: #e3f2fd;
  padding: 15px;
  border-radius: 8px;
  margin-top: 15px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(52, 152, 219, 0); }
  100% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0); }
}

.processing-message {
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: #2c3e50;
}

.processing-message i {
  color: #3498db;
  font-size: 18px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background-color: #d1e7f6;
  border-radius: 3px;
  overflow: hidden;
  margin-top: 5px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #2980b9);
  border-radius: 3px;
  width: 30%;
  animation: progressAnimation 1.5s ease-in-out infinite;
}

@keyframes progressAnimation {
  0% { width: 5%; }
  50% { width: 80%; }
  100% { width: 5%; }
}

.error-message {
  color: #e74c3c;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  animation: fadeIn 0.3s ease;
}

.error-message i {
  font-size: 14px;
}

.generation-error {
  background-color: #fdeaea;
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #e74c3c;
}

/* 通知组件样式 */
.notification {
  position: fixed;
  bottom: 30px;
  right: 30px;
  min-width: 280px;
  max-width: 380px;
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 1100;
  opacity: 0;
  transform: translateY(30px);
  animation: notificationIn 0.3s forwards, notificationOut 0.3s forwards 2.7s;
}

@keyframes notificationIn {
  to { opacity: 1; transform: translateY(0); }
}

@keyframes notificationOut {
  to { opacity: 0; transform: translateY(30px); }
}

.notification.success {
  background-color: #e7f9ed;
  border-left: 4px solid #2ecc71;
  color: #27ae60;
}

.notification.error {
  background-color: #fdeaea;
  border-left: 4px solid #e74c3c;
  color: #c0392b;
}

.notification.info {
  background-color: #e3f2fd;
  border-left: 4px solid #3498db;
  color: #2980b9;
}

.notification-content {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 500;
}

.notification-content i {
  font-size: 18px;
}

.notification-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: inherit;
  opacity: 0.6;
  transition: opacity 0.2s;
  padding: 0;
  margin-left: 10px;
}

.notification-close:hover {
  opacity: 1;
}

.connection-test-result {
  margin-top: 15px;
  padding: 10px;
  border-radius: 6px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.connection-test-result.success {
  background-color: #e7f9ed;
  border: 1px solid #2ecc71;
  color: #27ae60;
}

.connection-test-result.error {
  background-color: #fdeaea;
  border: 1px solid #e74c3c;
  color: #c0392b;
}

/* 自动填充确认对话框样式 */
.auto-fill-confirm-modal {
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
}

.auto-fill-modal {
  background-color: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  max-width: 90%;
  width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.auto-fill-message {
  margin-bottom: 20px;
}

.info-icon {
  font-size: 24px;
  margin-right: 10px;
}

.auto-fill-items {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.auto-fill-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.auto-fill-content {
  display: flex;
  align-items: center;
}

.auto-fill-field {
  font-weight: 600;
}

.auto-fill-value {
  margin-left: 10px;
}

.auto-fill-actions {
  display: flex;
  gap: 10px;
}

.confirm-btn, .reject-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #1976d2;
  transition: color 0.2s;
}

.confirm-btn:hover, .reject-btn:hover {
  color: #4caf50;
}

.confirm-all-btn, .reject-all-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #2c3e50;
  transition: color 0.2s;
}

.confirm-all-btn:hover, .reject-all-btn:hover {
  color: #4caf50;
}
</style>