<template>
  <main class="workspace" :style="{ width: workspaceWidth + 'px' }">
    <!-- 根据当前模块显示不同的内容 -->
    <template v-if="currentModule === 'public-info'">
      <div class="workspace-header">
        <h2>公共信息</h2>
        <div class="search-bar">
          <input v-model="searchKeyword" placeholder="搜索..." @keyup.enter="search" />
          <button @click="search">搜索</button>
        </div>
      </div>
      <div class="workspace-content">
        <DocumentList
          v-if="!selectedDocument"
          :documents="filteredDocuments"
          @select-document="showDocumentDetail"
          @fetch-documents="fetchDocuments"
        />
        <DocumentDetail
          v-if="selectedDocument"
          :document="selectedDocument"
          @back="backToList"
        />
        <Pagination
          v-if="!selectedDocument"
          :current-page="currentPage"
          :total-pages="totalPages"
          :page-size="pageSize"
          @change-page="changePage"
          @change-page-size="changePageSize"
        />
      </div>
    </template>
       
    <!-- 个人知识库模块 -->
    <KnowledgeBase v-else-if="currentModule === 'knowledge-base'" />
    
    <!-- 个人办公模块 -->
    <EmailSystem v-else-if="currentModule === 'personal-office'" ref="emailSystem" />
     
    <!-- 公文办理模块 -->
    <div v-else-if="currentModule === 'document-process'">
      <DocumentProcess ref="documentProcess" />
    </div>

    <!-- 管理员功能模块 -->
    <div v-else-if="currentModule === 'admin-workflow'">
      <WorkflowDesigner />
    </div>
    <div v-else-if="currentModule === 'admin-users'">
      <UserManagement />
    </div>
    <!-- 数据分析沙盒模块 -->
    <div v-else-if="currentModule === 'sandbox'">
      <SandboxAnalysis />
    </div>
    <div v-else>请选择一个功能模块</div>
  </main>
</template>

<script>
import axios from 'axios';
import DocumentList from './DocumentList.vue';
import DocumentDetail from './DocumentDetail.vue';
import Pagination from './Pagination.vue';
import KnowledgeBase from './KnowledgeBase.vue';
import EmailSystem from './EmailSystem.vue';
import DocumentProcess from './DocumentProcess.vue';
import emitter from '../utils/eventBus';
import PersonalKnowledgeBase from './PersonalKnowledgeBase.vue';
import WorkflowDesigner from '../views/admin/components/WorkflowDesigner.vue';
import UserManagement from '../views/admin/components/UserManagement.vue';
import SandboxAnalysis from '../views/Sandbox/SandboxAnalysis.vue';

export default {
  components: { 
    DocumentList, 
    DocumentDetail, 
    Pagination,
    KnowledgeBase,
    EmailSystem,
    DocumentProcess,
    PersonalKnowledgeBase,
    WorkflowDesigner,
    UserManagement,
    SandboxAnalysis
  },
  data() {
    return {
      workspaceWidth: 800,
      documents: [],
      filteredDocuments: [],
      selectedDocument: null,
      searchKeyword: '',
      currentPage: 1,
      pageSize: 10,
      totalPages: 1,
      currentModule: 'public-info',  // 添加当前模块状态
      currentUser: localStorage.getItem('username') || '未登录'
    };
  },
  computed: {
    moduleTitle() {
      const modules = {
        'document-process': '审批流程',
        'admin-document': '文档管理',
        'admin-user': '用户管理',
        'admin-workflow': '工作流管理'
      };
      return modules[this.currentModule] || '工作区';
    }
  },
  mounted() {
    this.fetchDocuments();
    // 使用 emitter 监听模块变化
    emitter.on('workspace-module-changed', (module) => {
      console.log('Workspace收到模块切换事件:', module);
      this.currentModule = module;
      
      // 如果是个人办公模块，检查是否有邮件需要处理
      if (module === 'personal-office') {
        // 确保先渲染出模块
        this.$nextTick(() => {
          // 触发一个显示邮件组件的事件
          console.log('切换到个人办公模块，检查是否有邮件需要处理');
          
          // 延迟一下以确保模块完全渲染
          setTimeout(() => {
            emitter.emit('check-email-pending');
            
            // 直接访问EmailSystem组件并调用方法
            if (this.$refs.emailSystem) {
              console.log('找到邮件系统组件实例，检查待处理邮件');
              this.$refs.emailSystem.checkPendingEmail();
              
              // 检查localStorage
              this.$refs.emailSystem.checkLocalStorageForPendingEmail();
            } else {
              console.warn('未找到emailSystem组件实例');
            }
          }, 300);
        });
      }
    });
    
    // 直接监听module-changed事件
    emitter.on('module-changed', (module) => {
      console.log('Workspace直接接收到module-changed事件:', module);
      // 更新模块
      this.currentModule = module;
      
      // 同时触发workspace-module-changed事件以保持兼容性
      emitter.emit('workspace-module-changed', module);
      
      // 作为备用，直接在localStorage中保存当前模块
      try {
        localStorage.setItem('current_module', module);
      } catch (e) {
        console.error('保存当前模块到localStorage失败:', e);
      }
    });
    
    // 监听打开文档事件
    emitter.on('open-document', (docId) => {
      this.openDocumentById(docId);
    });
  },
  beforeUnmount() {
    emitter.off('workspace-module-changed');
    emitter.off('module-changed');
    emitter.off('open-document');
  },
  beforeDestroy() {
    // 清理事件监听
    this.$root.$off('module-changed');
  },
  methods: {
    async fetchDocuments() {
      try {
        console.log("开始获取文档列表...");
        const response = await axios.get('/api/documents/list', {
          params: {
            page: this.currentPage,
            size: this.pageSize,
            keyword: this.searchKeyword,
            sort_by: 'created_at', // 使用正确的排序字段
            sort_order: 'desc'
          }
        });
        
        console.log("文档API响应:", response.data);
        
        // 检查响应是否包含documents或items数组
        const documentsList = response.data.documents || response.data.items;
        if (!response.data || !documentsList) {
          console.error("API响应不包含documents或items数据:", response.data);
          this.documents = [];
          this.filteredDocuments = [];
          this.totalPages = 0;
          return;
        }
        
        // 处理文档数据，确保必要字段存在，但不改变字段名
        const documents = documentsList.map(doc => ({
          ...doc,
          // 确保content存在
          content: doc.content || "暂无内容"
        }));
        
        console.log(`获取到${documents.length}个文档`);
        this.documents = documents;
        this.filteredDocuments = this.documents;
        this.totalPages = response.data.pages || response.data.total_pages || 1;
      } catch (error) {
        console.error('获取文档失败:', error);
        // 如果API调用失败，显示空列表
        this.documents = [];
        this.filteredDocuments = [];
        this.totalPages = 0;
      }
    },
    changePage(page) {
      this.currentPage = page;
      this.fetchDocuments();
    },
    changePageSize(size) {
      this.pageSize = size;
      this.currentPage = 1;
      this.fetchDocuments();
    },
    showDocumentDetail(document) {
      this.selectedDocument = document;
    },
    backToList() {
      this.selectedDocument = null;
    },
    search() {
      this.currentPage = 1; // 重置到第一页
      this.fetchDocuments(); // 使用关键词执行搜索
    },
    async openDocumentById(docId) {
      try {
        // 切换到公共信息模块
        this.currentModule = 'public-info';
        
        // 获取文档详情
        const response = await axios.get(`/api/documents/documents/${docId}`);
        
        // 显示文档详情
        this.selectedDocument = response.data;
      } catch (error) {
        console.error('获取文档详情失败:', error);
      }
    },
    logout() {
      // 清除本地存储的用户信息和token
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('username');
      
      // 重定向到登录页
      window.location.href = '/login';
    },
    // 处理发起请假按钮点击
    handleLeaveApproval() {
      // 查找DocumentProcess组件实例并调用其方法
      const docProcess = this.$refs.documentProcess;
      if (docProcess) {
        // 由于是发起请假，我们要查找请假流程并自动选择
        if (typeof docProcess.openLeaveApprovalForm === 'function') {
          docProcess.openLeaveApprovalForm();
        } else {
          console.error('DocumentProcess组件中找不到openLeaveApprovalForm方法');
          
          // 备用方案，使用通用方法
          docProcess.openNewApprovalForm();
        }
      } else {
        console.error('未找到DocumentProcess组件实例');
      }
    },
    // 处理发起一般审批按钮点击
    handleNewApproval() {
      const docProcess = this.$refs.documentProcess;
      if (docProcess) {
        docProcess.openNewApprovalForm();
      } else {
        console.error('未找到DocumentProcess组件实例');
      }
    }
  }
};
</script>

<style scoped>
.workspace {
  flex: 1;
  padding: 20px;
  background: #f5f5f5;
  height: 100vh;
  overflow-y: auto;
}
</style>
