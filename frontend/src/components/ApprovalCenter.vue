<template>
  <div class="approval-center">
    <h1 class="page-title">审批中心</h1>
    
    <!-- 审批类型筛选 -->
    <div class="approval-filter">
      <div class="filter-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.value"
          :class="['tab-btn', { active: currentTab === tab.value }]"
          @click="currentTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
      
      <div class="filter-actions">
        <select v-model="typeFilter" class="type-filter">
          <option value="">所有类型</option>
          <option value="leave">请假申请</option>
          <option value="expense">报销申请</option>
          <option value="purchase">采购申请</option>
          <option value="contract">合同审批</option>
        </select>
        
        <input 
          type="text" 
          v-model="searchKeyword" 
          placeholder="搜索申请人或标题" 
          class="search-input"
        />
      </div>
    </div>
    
    <!-- 审批列表 -->
    <div class="approval-list">
      <div v-if="filteredApprovals.length === 0" class="empty-approvals">
        {{ emptyMessage }}
      </div>
      
      <div v-else>
        <!-- 审批表头 -->
        <div class="approval-header">
          <div class="header-item flex-1">申请人</div>
          <div class="header-item flex-2">标题</div>
          <div class="header-item flex-1">类型</div>
          <div class="header-item flex-1">提交时间</div>
          <div class="header-item flex-1">状态</div>
          <div class="header-item flex-1">操作</div>
        </div>
        
        <!-- 审批列表项 -->
        <div 
          v-for="(approval, index) in filteredApprovals" 
          :key="index"
          class="approval-item"
        >
          <div class="item-cell flex-1">{{ approval.applicant }}</div>
          <div class="item-cell flex-2">{{ approval.title }}</div>
          <div class="item-cell flex-1">{{ getTypeName(approval.type) }}</div>
          <div class="item-cell flex-1">{{ formatDate(approval.submitTime) }}</div>
          <div class="item-cell flex-1">
            <span :class="['status-tag', getStatusClass(approval.status)]">
              {{ getStatusText(approval.status) }}
            </span>
          </div>
          <div class="item-cell flex-1">
            <button 
              v-if="approval.status === 'pending' && currentTab === 'pending'"
              @click="showApprovalDetail(approval)"
              class="action-btn view-btn"
            >
              审批
            </button>
            <button 
              v-else
              @click="showApprovalDetail(approval)"
              class="action-btn view-btn"
            >
              查看
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分页器 -->
    <div class="pagination">
      <button 
        :disabled="currentPage <= 1"
        @click="currentPage--"
        class="page-btn"
      >
        上一页
      </button>
      <span class="page-info">第 {{ currentPage }} 页</span>
      <button 
        :disabled="currentPage >= totalPages"
        @click="currentPage++"
        class="page-btn"
      >
        下一页
      </button>
    </div>
    
    <!-- 审批详情弹窗 -->
    <div v-if="showDetailModal" class="modal-mask">
      <div class="modal-container">
        <div class="modal-header">
          <h2>{{ currentApproval.title }}</h2>
          <button @click="showDetailModal = false" class="close-btn">&times;</button>
        </div>
        
        <div class="modal-body">
          <div class="detail-item">
            <span class="detail-label">申请人:</span>
            <span class="detail-value">{{ currentApproval.applicant }}</span>
          </div>
          
          <div class="detail-item">
            <span class="detail-label">申请类型:</span>
            <span class="detail-value">{{ getTypeName(currentApproval.type) }}</span>
          </div>
          
          <div class="detail-item">
            <span class="detail-label">提交时间:</span>
            <span class="detail-value">{{ formatDate(currentApproval.submitTime, true) }}</span>
          </div>
          
          <div class="detail-item">
            <span class="detail-label">当前状态:</span>
            <span :class="['status-tag', getStatusClass(currentApproval.status)]">
              {{ getStatusText(currentApproval.status) }}
            </span>
          </div>
          
          <div class="detail-item full-width">
            <span class="detail-label">申请内容:</span>
            <div class="detail-content">{{ currentApproval.content }}</div>
          </div>
          
          <div v-if="currentApproval.attachments && currentApproval.attachments.length" class="detail-item full-width">
            <span class="detail-label">附件:</span>
            <div class="attachments-list">
              <a 
                v-for="(attachment, idx) in currentApproval.attachments"
                :key="idx"
                href="javascript:void(0)"
                class="attachment-link"
              >
                {{ attachment.name }}
              </a>
            </div>
          </div>
          
          <div v-if="currentApproval.history && currentApproval.history.length" class="detail-item full-width">
            <span class="detail-label">审批历史:</span>
            <div class="approval-history">
              <div 
                v-for="(record, idx) in currentApproval.history"
                :key="idx"
                class="history-item"
              >
                <div class="history-info">
                  <span class="history-user">{{ record.approver }}</span>
                  <span class="history-time">{{ formatDate(record.time) }}</span>
                </div>
                <div class="history-action">
                  <span :class="['status-tag', record.action === 'approve' ? 'status-approved' : 'status-rejected']">
                    {{ record.action === 'approve' ? '通过' : '拒绝' }}
                  </span>
                </div>
                <div v-if="record.comment" class="history-comment">
                  备注: {{ record.comment }}
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="currentApproval.status === 'pending'" class="approval-actions">
            <div class="comment-input">
              <label>审批意见:</label>
              <textarea v-model="approvalComment" rows="3" placeholder="请输入审批意见（可选）"></textarea>
            </div>
            
            <div class="action-buttons">
              <button @click="processApproval('reject')" class="reject-btn">拒绝</button>
              <button @click="processApproval('approve')" class="approve-btn">通过</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ApprovalCenter',
  data() {
    return {
      // 标签页
      tabs: [
        { label: '待审批', value: 'pending' },
        { label: '已审批', value: 'processed' },
        { label: '我的申请', value: 'mine' }
      ],
      currentTab: 'pending',
      
      // 筛选
      typeFilter: '',
      searchKeyword: '',
      
      // 分页
      currentPage: 1,
      pageSize: 10,
      
      // 审批列表
      approvals: [],
      
      // 详情模态框
      showDetailModal: false,
      currentApproval: {},
      approvalComment: '',
      
      // 当前用户信息
      currentUser: {
        id: 1,
        username: 'admin',
        fullName: '管理员'
      }
    };
  },
  computed: {
    filteredApprovals() {
      let result = [...this.approvals];
      
      // 根据标签页筛选
      if (this.currentTab === 'pending') {
        result = result.filter(a => a.status === 'pending');
      } else if (this.currentTab === 'processed') {
        result = result.filter(a => a.status !== 'pending');
      } else if (this.currentTab === 'mine') {
        result = result.filter(a => a.applicantId === this.currentUser.id);
      }
      
      // 根据类型筛选
      if (this.typeFilter) {
        result = result.filter(a => a.type === this.typeFilter);
      }
      
      // 根据关键词搜索
      if (this.searchKeyword) {
        const keyword = this.searchKeyword.toLowerCase();
        result = result.filter(a => 
          a.applicant.toLowerCase().includes(keyword) || 
          a.title.toLowerCase().includes(keyword)
        );
      }
      
      // 分页处理
      const start = (this.currentPage - 1) * this.pageSize;
      const end = start + this.pageSize;
      
      return result.slice(start, end);
    },
    totalPages() {
      // 计算总页数
      let filtered = [...this.approvals];
      
      if (this.currentTab === 'pending') {
        filtered = filtered.filter(a => a.status === 'pending');
      } else if (this.currentTab === 'processed') {
        filtered = filtered.filter(a => a.status !== 'pending');
      } else if (this.currentTab === 'mine') {
        filtered = filtered.filter(a => a.applicantId === this.currentUser.id);
      }
      
      if (this.typeFilter) {
        filtered = filtered.filter(a => a.type === this.typeFilter);
      }
      
      if (this.searchKeyword) {
        const keyword = this.searchKeyword.toLowerCase();
        filtered = filtered.filter(a => 
          a.applicant.toLowerCase().includes(keyword) || 
          a.title.toLowerCase().includes(keyword)
        );
      }
      
      return Math.ceil(filtered.length / this.pageSize);
    },
    emptyMessage() {
      if (this.searchKeyword || this.typeFilter) {
        return '没有找到符合条件的审批项目';
      }
      
      if (this.currentTab === 'pending') {
        return '当前没有待审批的项目';
      } else if (this.currentTab === 'processed') {
        return '当前没有已处理的审批项目';
      } else if (this.currentTab === 'mine') {
        return '您还没有提交过审批申请';
      }
      
      return '没有审批项目';
    }
  },
  mounted() {
    this.loadUserInfo();
    this.loadApprovals();
  },
  methods: {
    loadUserInfo() {
      // 从localStorage加载用户信息
      const userStr = localStorage.getItem('user');
      if (userStr) {
        try {
          const user = JSON.parse(userStr);
          this.currentUser = {
            id: user.id || 1,
            username: user.username || 'admin',
            fullName: user.full_name || user.realName || user.username
          };
        } catch (e) {
          console.error('解析用户信息失败:', e);
        }
      }
    },
    loadApprovals() {
      // 模拟加载审批数据
      // 在实际项目中，这里应该从API获取数据
      setTimeout(() => {
        this.approvals = [
          {
            id: 1,
            title: '年假申请 - 5天',
            type: 'leave',
            applicant: '张三',
            applicantId: 2,
            submitTime: new Date('2023-11-15T09:30:00'),
            status: 'pending',
            content: '申请5天年假，从2023年11月20日至2023年11月24日，请批准。',
            attachments: []
          },
          {
            id: 2,
            title: '差旅费报销 - ¥3,500',
            type: 'expense',
            applicant: '李四',
            applicantId: 3,
            submitTime: new Date('2023-11-14T14:20:00'),
            status: 'approved',
            content: '上海出差产生的差旅费，包含机票、住宿和餐饮费用，共计3500元。',
            attachments: [
              { name: '机票发票.pdf', url: '#' },
              { name: '住宿发票.pdf', url: '#' }
            ],
            history: [
              {
                approver: '王经理',
                time: new Date('2023-11-16T10:15:00'),
                action: 'approve',
                comment: '费用符合规定，同意报销'
              }
            ]
          },
          {
            id: 3,
            title: '开发设备采购 - ¥12,000',
            type: 'purchase',
            applicant: '王五',
            applicantId: 4,
            submitTime: new Date('2023-11-13T11:45:00'),
            status: 'rejected',
            content: '开发部门需要采购3台显示器和2台笔记本电脑，总计约12000元，用于新项目开发。',
            attachments: [
              { name: '设备清单.xlsx', url: '#' }
            ],
            history: [
              {
                approver: '财务主管',
                time: new Date('2023-11-14T09:20:00'),
                action: 'reject',
                comment: '当前季度采购预算已用完，请下季度再申请'
              }
            ]
          },
          {
            id: 4,
            title: '项目合同审批 - 技术服务协议',
            type: 'contract',
            applicant: '赵六',
            applicantId: 5,
            submitTime: new Date('2023-11-16T16:30:00'),
            status: 'pending',
            content: '与某公司签订的技术服务协议，服务周期为6个月，合同金额为30万元。',
            attachments: [
              { name: '技术服务协议.docx', url: '#' }
            ]
          },
          {
            id: 5,
            title: '病假申请 - 2天',
            type: 'leave',
            applicant: '周七',
            applicantId: 6,
            submitTime: new Date('2023-11-17T08:15:00'),
            status: 'pending',
            content: '因发烧感冒，申请2天病假，从2023年11月17日至2023年11月18日。',
            attachments: [
              { name: '医院证明.jpg', url: '#' }
            ]
          }
        ];
        
        // 添加一些我的申请
        if (this.currentUser && this.currentUser.id) {
          this.approvals.push(
            {
              id: 6,
              title: '会议室预订申请',
              type: 'other',
              applicant: this.currentUser.fullName,
              applicantId: this.currentUser.id,
              submitTime: new Date('2023-11-10T09:10:00'),
              status: 'approved',
              content: '申请预订305会议室，用于项目启动会议，时间为2023年11月15日14:00-16:00。',
              attachments: [],
              history: [
                {
                  approver: '行政主管',
                  time: new Date('2023-11-10T10:30:00'),
                  action: 'approve',
                  comment: '已安排会议室'
                }
              ]
            },
            {
              id: 7,
              title: '培训费用报销 - ¥1,800',
              type: 'expense',
              applicant: this.currentUser.fullName,
              applicantId: this.currentUser.id,
              submitTime: new Date('2023-11-12T15:45:00'),
              status: 'pending',
              content: '参加技术培训的费用报销，包含培训费和资料费，共计1800元。',
              attachments: [
                { name: '培训发票.pdf', url: '#' },
                { name: '培训证书.pdf', url: '#' }
              ]
            }
          );
        }
      }, 500);
    },
    showApprovalDetail(approval) {
      this.currentApproval = { ...approval };
      this.approvalComment = '';
      this.showDetailModal = true;
    },
    processApproval(action) {
      if (!this.currentApproval || !this.currentApproval.id) return;
      
      // 创建审批记录
      const approvalRecord = {
        approver: this.currentUser.fullName,
        time: new Date(),
        action,
        comment: this.approvalComment
      };
      
      // 更新审批状态
      const approvalIndex = this.approvals.findIndex(a => a.id === this.currentApproval.id);
      if (approvalIndex !== -1) {
        // 更新状态
        this.approvals[approvalIndex].status = action === 'approve' ? 'approved' : 'rejected';
        
        // 添加审批历史
        if (!this.approvals[approvalIndex].history) {
          this.approvals[approvalIndex].history = [];
        }
        this.approvals[approvalIndex].history.push(approvalRecord);
        
        // 更新当前显示的审批详情
        this.currentApproval = { ...this.approvals[approvalIndex] };
        
        // 显示成功消息
        alert(`审批${action === 'approve' ? '通过' : '拒绝'}成功！`);
      }
    },
    getTypeName(type) {
      const typeMap = {
        'leave': '请假申请',
        'expense': '报销申请',
        'purchase': '采购申请',
        'contract': '合同审批',
        'other': '其他申请'
      };
      
      return typeMap[type] || '未知类型';
    },
    getStatusText(status) {
      const statusMap = {
        'pending': '待审批',
        'approved': '已通过',
        'rejected': '已拒绝'
      };
      
      return statusMap[status] || '未知状态';
    },
    getStatusClass(status) {
      const classMap = {
        'pending': 'status-pending',
        'approved': 'status-approved',
        'rejected': 'status-rejected'
      };
      
      return classMap[status] || '';
    },
    formatDate(date, showTime = false) {
      if (!date) return '';
      
      const d = new Date(date);
      if (isNaN(d.getTime())) return '';
      
      if (showTime) {
        return d.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        });
      } else {
        return d.toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        });
      }
    }
  }
};
</script>

<style scoped>
.approval-center {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  font-size: 24px;
  color: #333;
  margin-bottom: 24px;
}

/* 筛选区域样式 */
.approval-filter {
  margin-bottom: 20px;
}

.filter-tabs {
  display: flex;
  border-bottom: 1px solid #e8e8e8;
  margin-bottom: 16px;
}

.tab-btn {
  padding: 8px 16px;
  font-size: 14px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  margin-right: 8px;
}

.tab-btn.active {
  color: #1890ff;
  border-bottom: 2px solid #1890ff;
}

.filter-actions {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.type-filter {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  width: 150px;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  flex-grow: 1;
  margin-left: 8px;
}

/* 审批列表样式 */
.approval-list {
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.empty-approvals {
  padding: 40px 0;
  text-align: center;
  color: #999;
}

.approval-header {
  display: flex;
  background-color: #f5f5f5;
  padding: 12px 16px;
  font-weight: bold;
  border-bottom: 1px solid #e8e8e8;
}

.approval-item {
  display: flex;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.approval-item:last-child {
  border-bottom: none;
}

.header-item, .item-cell {
  padding: 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flex-1 {
  flex: 1;
}

.flex-2 {
  flex: 2;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-pending {
  background-color: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

.status-approved {
  background-color: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.status-rejected {
  background-color: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffa39e;
}

.action-btn {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  border: none;
}

.view-btn {
  background-color: #1890ff;
  color: white;
}

/* 分页器样式 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
}

.page-btn {
  padding: 6px 12px;
  background-color: white;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  cursor: pointer;
  margin: 0 8px;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: #666;
}

/* 模态框样式 */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-container {
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 600px;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background-color: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.detail-item {
  margin-bottom: 16px;
  display: flex;
}

.detail-item.full-width {
  display: block;
}

.detail-label {
  font-weight: bold;
  width: 80px;
  flex-shrink: 0;
}

.detail-content {
  white-space: pre-line;
  padding: 12px;
  background-color: #f9f9f9;
  border-radius: 4px;
  margin-top: 8px;
}

.attachments-list {
  margin-top: 8px;
}

.attachment-link {
  display: block;
  padding: 4px 0;
  color: #1890ff;
  text-decoration: none;
}

.attachment-link:hover {
  text-decoration: underline;
}

.approval-history {
  margin-top: 8px;
}

.history-item {
  padding: 8px;
  background-color: #f9f9f9;
  border-radius: 4px;
  margin-bottom: 8px;
}

.history-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.history-user {
  font-weight: bold;
}

.history-time {
  font-size: 12px;
  color: #999;
}

.history-comment {
  margin-top: 8px;
  font-size: 13px;
  color: #666;
}

.approval-actions {
  margin-top: 24px;
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.comment-input {
  margin-bottom: 16px;
}

.comment-input label {
  display: block;
  margin-bottom: 8px;
}

.comment-input textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  resize: vertical;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
}

.reject-btn, .approve-btn {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 12px;
}

.reject-btn {
  background-color: white;
  border: 1px solid #ff4d4f;
  color: #ff4d4f;
}

.approve-btn {
  background-color: #52c41a;
  border: 1px solid #52c41a;
  color: white;
}
</style> 