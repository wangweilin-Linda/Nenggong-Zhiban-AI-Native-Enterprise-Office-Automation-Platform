<template>
  <div class="approval-detail">
    <div class="detail-header">
      <h2>审批详情 #{{ approval.id }}</h2>
      <div class="status-badge" :class="statusClass">{{ statusText }}</div>
    </div>
    
    <!-- 错误消息显示 -->
    <div v-if="errorMessage" class="error-message">
      <i class="error-icon">!</i>
      {{ errorMessage }}
    </div>
    
    <div class="detail-section basic-info">
      <h3>基本信息</h3>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">标题:</span>
          <span class="value">{{ approval.title }}</span>
        </div>
        <div class="info-item">
          <span class="label">流程类型:</span>
          <span class="value">{{ approval.process_name }}</span>
        </div>
        <div class="info-item">
          <span class="label">发起人:</span>
          <span class="value">{{ approval.applicant?.real_name || approval.applicant?.username || '未知' }}</span>
        </div>
        <div class="info-item">
          <span class="label">发起时间:</span>
          <span class="value">{{ formatDate(approval.created_at) }}</span>
        </div>
        <div class="info-item">
          <span class="label">紧急程度:</span>
          <span class="value">
            <span class="emergency-level" :class="emergencyClass">{{ emergencyText }}</span>
          </span>
        </div>
        <div class="info-item">
          <span class="label">当前节点:</span>
          <span class="value">{{ approval.current_node_info?.name || '未知节点' }}</span>
        </div>
      </div>
    </div>
    
    <div class="detail-section content-info">
      <h3>审批内容</h3>
      <div v-if="approval.form_data" class="form-data">
        <div v-for="(field, index) in formattedFormData" :key="index" class="form-item">
          <span class="form-label">{{ field.label }}:</span>
          <span class="form-value">{{ field.value }}</span>
        </div>
      </div>
      <div v-else class="empty-content">无表单数据</div>
    </div>
    
    <div class="detail-section flow-info">
      <h3>审批流程</h3>
      <div class="flow-progress">
        <div class="flow-timeline">
          <div 
            v-for="(node, index) in flowNodes" 
            :key="node.id"
            class="timeline-node"
            :class="{
              'completed': isNodeCompleted(node),
              'current': isCurrentNode(node),
              'pending': isNodePending(node),
              'rejected': isNodeRejected(node)
            }"
          >
            <div class="node-connector" v-if="index > 0"></div>
            <div class="node-icon">
              <i class="node-status-icon"></i>
            </div>
            <div class="node-content">
              <div class="node-title">{{ node.name }}</div>
              <div class="node-info">
                <div v-if="getNodeApprover(node)" class="node-approver">
                  审批人: {{ getNodeApprover(node) }}
                </div>
                <div v-if="getNodeTime(node)" class="node-time">
                  {{ getNodeTime(node) }}
                </div>
                <div v-if="getNodeComment(node)" class="node-comment">
                  意见: {{ getNodeComment(node) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 操作区域 -->
    <div class="detail-section action-area" v-if="!['completed', 'rejected', 'withdrawn', 'terminated'].includes(approval.status)">
      <h3>审批操作</h3>
      
      <div class="action-form">
        <div class="form-item">
          <label>处理意见:</label>
          <textarea v-model="approvalComment" rows="3" placeholder="请输入您的处理意见..."></textarea>
        </div>
        
        <div class="action-buttons">
          <button 
            class="btn approve-btn" 
            @click="handleApprove" 
            :disabled="!canApprove || isProcessing"
          >
            <span v-if="isProcessing">处理中...</span>
            <span v-else>批准</span>
          </button>
          
          <button 
            class="btn reject-btn" 
            @click="handleReject" 
            :disabled="!canReject || isProcessing"
          >
            <span v-if="isProcessing">处理中...</span>
            <span v-else>拒绝</span>
          </button>
          
          <button 
            class="btn return-btn" 
            @click="handleReturn" 
            :disabled="!canReturn || isProcessing"
          >
            <span v-if="isProcessing">处理中...</span>
            <span v-else>退回</span>
          </button>
          
          <button 
            class="btn withdraw-btn" 
            @click="handleWithdraw" 
            :disabled="!canWithdraw || isProcessing"
            v-if="canWithdraw"
          >
            <span v-if="isProcessing">处理中...</span>
            <span v-else>撤回</span>
          </button>
        </div>
      </div>
    </div>
    
    <!-- 管理员操作区域 -->
    <div class="detail-section admin-actions" v-if="isAdmin && !['completed', 'rejected', 'withdrawn', 'terminated'].includes(approval.status)">
      <h3>管理员操作</h3>
      
      <div class="form-item">
        <label>跳转至节点:</label>
        <select v-model="skipToNodeId">
          <option value="">请选择目标节点</option>
          <option v-for="node in flowNodes" :key="node.id" :value="node.id">
            {{ node.name || node.id }}
          </option>
          <option value="end">结束节点</option>
        </select>
      </div>
      
      <div class="form-item">
        <label>跳过原因:</label>
        <textarea v-model="skipComment" rows="2" placeholder="请输入跳过原因..."></textarea>
      </div>
      
      <button 
        class="btn skip-btn" 
        @click="handleSkip" 
        :disabled="!skipToNodeId || isProcessing"
      >
        <span v-if="isProcessing">处理中...</span>
        <span v-else>跳过审批</span>
      </button>
    </div>
    
    <!-- 已完成提示 -->
    <div class="detail-section completed-notice" v-else>
      <div class="notice-content">
        <div class="notice-icon">
          <span v-if="approval.status === 'completed'">✓</span>
          <span v-else-if="approval.status === 'rejected'">✗</span>
          <span v-else>!</span>
        </div>
        <div class="notice-text">
          <p v-if="approval.status === 'completed'">此审批已通过并完成</p>
          <p v-else-if="approval.status === 'rejected'">此审批已被拒绝</p>
          <p v-else-if="approval.status === 'withdrawn'">此审批已被申请人撤回</p>
          <p v-else>此审批已终止</p>
        </div>
      </div>
    </div>
    
    <div class="detail-section history-info">
      <h3>审批历史</h3>
      <div class="history-list">
        <div v-if="approval.history && approval.history.length > 0">
          <div 
            v-for="(record, index) in approval.history" 
            :key="index"
            class="history-item"
          >
            <div class="history-avatar">
              <div class="avatar-circle">{{ getInitials(record.approver_name) }}</div>
            </div>
            <div class="history-content">
              <div class="history-header">
                <span class="history-user">{{ record.approver_name }}</span>
                <span class="history-action">{{ getActionText(record.action) }}</span>
                <span class="history-time">{{ formatDate(record.created_at) }}</span>
              </div>
              <div v-if="record.comment" class="history-comment">
                {{ record.comment }}
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-history">
          暂无审批历史记录
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { reactive, ref, computed, onMounted } from 'vue';
import api from '../utils/api';

export default {
  name: 'ApprovalDetail',
  props: {
    approvalId: {
      type: [Number, String],
      required: true
    },
    isAdmin: {
      type: Boolean,
      default: false
    }
  },
  emits: ['approval-updated'],
  setup(props, { emit }) {
    // 状态
    const approval = reactive({
      id: null,
      title: '',
      process_id: null,
      process_name: '',
      applicant: null,
      current_node: '',
      current_node_info: null,
      status: '',
      form_data: {},
      can_approve: false,
      history: [],
      created_at: null,
      updated_at: null,
      emergency_level: 0
    });
    
    const approvalComment = ref('');
    const isProcessing = ref(false);
    const errorMessage = ref('');
    const skipToNodeId = ref('');
    const skipComment = ref('');
    
    // 获取表单模式
    const formSchema = ref(null);
    
    // 计算属性
    const statusText = computed(() => {
      const statusMap = {
        'pending': '待处理',
        'processing': '处理中',
        'approved': '已通过',
        'rejected': '已拒绝',
        'withdrawn': '已撤回',
        'terminated': '已终止',
        'completed': '已完成'
      };
      return statusMap[approval.status] || approval.status;
    });
    
    const statusClass = computed(() => {
      const classMap = {
        'pending': 'status-pending',
        'processing': 'status-processing',
        'approved': 'status-approved',
        'rejected': 'status-rejected',
        'withdrawn': 'status-withdrawn',
        'terminated': 'status-terminated',
        'completed': 'status-completed'
      };
      return classMap[approval.status] || '';
    });
    
    const emergencyClass = computed(() => {
      const level = approval.emergency_level || 0;
      return {
        'level-normal': level === 0,
        'level-medium': level === 1,
        'level-high': level === 2,
        'level-urgent': level === 3
      };
    });
    
    const emergencyText = computed(() => {
      const levelMap = {
        0: '普通',
        1: '中等',
        2: '高',
        3: '紧急'
      };
      return levelMap[approval.emergency_level] || '普通';
    });
    
    const flowNodes = computed(() => {
      // 如果存在完整的节点数组，直接使用
      if (approval.nodes && approval.nodes.length > 0) {
        return approval.nodes;
      }
      
      const nodes = [];
      
      // 从工作流配置获取节点
      if (approval.workflow_config && approval.workflow_config.nodes) {
        approval.workflow_config.nodes.forEach(node => {
          nodes.push({
            id: node.id,
            name: node.name || node.id,
            type: node.type,
            status: getNodeStatusFromHistory(node.id)
          });
        });
      } else if (approval.workflow_config && approval.workflow_config.states) {
        // 处理状态机格式的工作流配置
        Object.entries(approval.workflow_config.states).forEach(([stateId, stateConfig]) => {
          nodes.push({
            id: stateId,
            name: stateConfig.name || stateConfig.description || stateId,
            type: stateConfig.type || 'state',
            status: getNodeStatusFromHistory(stateId)
          });
        });
      } else {
        // 如果没有配置，至少添加当前节点
        if (approval.current_node_info) {
          nodes.push({
            id: approval.current_node_info.id,
            name: approval.current_node_info.name,
            type: approval.current_node_info.type || 'approval',
            status: 'processing'
          });
        }
        
        // 从历史记录构建节点
        if (approval.history && approval.history.length > 0) {
          approval.history.forEach(record => {
            const existingNode = nodes.find(n => n.id === record.node_id);
            if (!existingNode && record.node_id) {
              nodes.push({
                id: record.node_id,
                name: `节点 ${record.node_id}`,
                type: 'approval',
                status: record.action === 'approve' ? 'approved' : 
                       record.action === 'reject' ? 'rejected' : 
                       record.action === 'return' ? 'returned' : 'completed'
              });
            }
          });
        }
      }
      
      // 排序节点 - 尝试使用工作流边缘信息进行排序
      return sortNodes(nodes);
    });
    
    const canReturn = computed(() => {
      // 退回需要当前不是第一个节点
      const currentNodeIndex = flowNodes.value.findIndex(node => node.id === approval.current_node);
      const isFirstNode = currentNodeIndex <= 0;
      
      return approval.can_approve && 
             ['pending', 'processing'].includes(approval.status) &&
             !isFirstNode;
    });
    
    // 是否可以批准
    const canApprove = computed(() => {
      // 优先使用后端返回的值
      if (typeof approval.can_approve !== 'undefined') {
        return approval.can_approve;
      }
      
      // 后备计算逻辑
      return ['pending', 'processing'].includes(approval.status);
    });
    
    // 是否可以拒绝
    const canReject = computed(() => {
      // 优先使用后端返回的值
      if (typeof approval.can_reject !== 'undefined') {
        return approval.can_reject;
      }
      
      // 后备计算逻辑
      return approval.can_approve && 
             ['pending', 'processing'].includes(approval.status);
    });
    
    // 是否可以撤回 - 只有发起人可以撤回，且状态必须是pending或processing
    const canWithdraw = computed(() => {
      // 优先使用后端返回的值
      if (typeof approval.can_withdraw !== 'undefined') {
        return approval.can_withdraw;
      }
      
      // 后备计算逻辑 - 检查当前用户是否是申请人
      const currentUser = getCurrentUser();
      const isInitiator = currentUser && approval.applicant && 
                          currentUser.id === approval.applicant.id;
      
      return isInitiator && 
             ['pending', 'processing'].includes(approval.status);
    });
    
    // 获取当前登录用户信息
    const getCurrentUser = () => {
      try {
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (userStr) {
          return JSON.parse(userStr);
        }
        return null;
      } catch (e) {
        console.error('获取当前用户信息失败:', e);
        return null;
      }
    };
    
    // 计算属性：格式化后的表单数据
    const formattedFormData = computed(() => {
      if (!approval.form_data) return [];
      
      const result = [];
      // 如果有表单模式，优先使用表单模式定义的字段顺序和标签
      if (formSchema.value && formSchema.value.fields) {
        formSchema.value.fields.forEach(field => {
          if (approval.form_data.hasOwnProperty(field.name)) {
            result.push({
              key: field.name,
              label: field.label || formatFieldName(field.name),
              value: formatFieldValue(approval.form_data[field.name], field.type)
            });
          }
        });
        
        // 处理表单模式中未定义的字段
        Object.keys(approval.form_data).forEach(key => {
          if (!formSchema.value.fields.some(f => f.name === key)) {
            result.push({
              key: key,
              label: formatFieldName(key),
              value: formatFieldValue(approval.form_data[key])
            });
          }
        });
      } else {
        // 如果没有表单模式，使用默认处理
        Object.keys(approval.form_data).forEach(key => {
          result.push({
            key: key,
            label: formatFieldName(key),
            value: formatFieldValue(approval.form_data[key])
          });
        });
      }
      
      return result;
    });
    
    // 方法
    const fetchApprovalDetail = async () => {
      try {
        isProcessing.value = true;
        console.log(`获取审批详情: ID=${props.approvalId}`);
        
        // 使用API模块的getApprovalDetail方法
        const response = await api.getApprovalDetail(props.approvalId);
        
        if (response && response.data) {
          Object.assign(approval, response.data);
          console.log('审批详情数据:', approval);
          
          // 获取关联的表单模式
          if (approval.process_id) {
            await fetchFormSchema(approval.process_id);
          }
          
          await loadWorkflowConfig();
          isProcessing.value = false;
        } else {
          throw new Error('获取审批详情失败: 服务器未返回有效数据');
        }
      } catch (error) {
        console.error('获取审批详情失败:', error);
        
        // 开发环境提供模拟数据
        if (process.env.NODE_ENV === 'development') {
          console.log('使用模拟数据');
          approval.id = parseInt(props.approvalId);
          approval.title = `模拟审批详情 ${props.approvalId}`;
          approval.workflow_id = 1;
          approval.status = 'pending';
          approval.current_node = 'manager_approval';
          approval.initiator = '张三';
          approval.created_at = new Date().toISOString();
          approval.form_data = {
            reason: '请假申请',
            date: '2023-10-01',
            days: 5
          };
          approval.process = {
            name: '请假流程'
          };
          approval.logs = [
            {
              id: 1,
              action: 'create',
              user: '张三',
              comment: '提交申请',
              created_at: new Date().toISOString()
            }
          ];
          approval.loaded = true;
        }
        isProcessing.value = false;
        errorMessage.value = `获取审批详情失败: ${error.message || '未知错误'}`;
      }
    };
    
    const loadWorkflowConfig = async () => {
      if (!approval.workflow_id) {
        console.warn('没有工作流ID，无法加载工作流配置');
        return;
      }
      
      try {
        console.log(`加载工作流配置: ID=${approval.workflow_id}`);
        const response = await api.getWorkflow(approval.workflow_id);
        
        if (response && response.config) {
          approval.workflow_config = response.config;
          console.log('工作流配置:', approval.workflow_config);
        } else {
          throw new Error('工作流配置数据格式不正确');
        }
      } catch (error) {
        console.error('加载工作流配置失败:', error);
        
        // 开发环境提供模拟数据
        if (process.env.NODE_ENV === 'development') {
          console.log('使用模拟工作流配置');
          approval.workflow_config = {
            nodes: [
              { id: 'start', name: '开始', type: 'start' },
              { id: 'manager_approval', name: '经理审批', type: 'approval' },
              { id: 'hr_review', name: '人事审核', type: 'approval' },
              { id: 'end', name: '结束', type: 'end' }
            ],
            edges: [
              { source: 'start', target: 'manager_approval' },
              { source: 'manager_approval', target: 'hr_review' },
              { source: 'hr_review', target: 'end' }
            ]
          };
        } else {
          this.$message.warning('无法加载审批流程图');
        }
      }
    };
    
    const showError = (message) => {
      errorMessage.value = message;
      
      // 5秒后自动清除错误消息
      setTimeout(() => {
        errorMessage.value = '';
      }, 5000);
    };
    
    const handleApprove = async () => {
      if (!approval.id || !approval.can_approve) return;
      
      try {
        isProcessing.value = true;
        errorMessage.value = ''; // 清除之前的错误
        
        const response = await api.processApproval({
          instance_id: approval.id,
          action: 'approve',
          comment: approvalComment.value,
          node_id: approval.current_node
        });
        
        if (response.data) {
          // 刷新审批详情
          await fetchApprovalDetail();
          
          // 通知父组件审批已更新
          emit('approval-updated', {
            id: approval.id,
            action: 'approve',
            status: response.data.status
          });
          
          // 清空评论
          approvalComment.value = '';
        }
      } catch (error) {
        console.error('审批操作失败:', error);
        // 显示友好的错误消息
        if (error.response && error.response.data && error.response.data.detail) {
          showError(`审批失败: ${error.response.data.detail}`);
        } else {
          showError('审批操作失败，请稍后重试');
        }
      } finally {
        isProcessing.value = false;
      }
    };
    
    const handleReject = async () => {
      if (!approval.id || !approval.can_approve) return;
      
      try {
        isProcessing.value = true;
        errorMessage.value = ''; // 清除之前的错误
        
        const response = await api.processApproval({
          instance_id: approval.id,
          action: 'reject',
          comment: approvalComment.value,
          node_id: approval.current_node
        });
        
        if (response.data) {
          // 刷新审批详情
          await fetchApprovalDetail();
          
          // 通知父组件审批已更新
          emit('approval-updated', {
            id: approval.id,
            action: 'reject',
            status: response.data.status
          });
          
          // 清空评论
          approvalComment.value = '';
        }
      } catch (error) {
        console.error('拒绝操作失败:', error);
        // 显示友好的错误消息
        if (error.response && error.response.data && error.response.data.detail) {
          showError(`拒绝失败: ${error.response.data.detail}`);
        } else {
          showError('拒绝操作失败，请稍后重试');
        }
      } finally {
        isProcessing.value = false;
      }
    };
    
    const handleReturn = async () => {
      if (!approval.id || !canReturn.value) return;
      
      try {
        isProcessing.value = true;
        errorMessage.value = ''; // 清除之前的错误
        
        const response = await api.processApproval({
          instance_id: approval.id,
          action: 'return',
          comment: approvalComment.value,
          node_id: approval.current_node
        });
        
        if (response.data) {
          // 刷新审批详情
          await fetchApprovalDetail();
          
          // 通知父组件审批已更新
          emit('approval-updated', {
            id: approval.id,
            action: 'return',
            status: response.data.status
          });
          
          // 清空评论
          approvalComment.value = '';
        }
      } catch (error) {
        console.error('退回操作失败:', error);
        // 显示友好的错误消息
        if (error.response && error.response.data && error.response.data.detail) {
          showError(`退回失败: ${error.response.data.detail}`);
        } else {
          showError('退回操作失败，请稍后重试');
        }
      } finally {
        isProcessing.value = false;
      }
    };
    
    const handleWithdraw = async () => {
      if (!approval.id || !canWithdraw.value) return;
      
      try {
        isProcessing.value = true;
        errorMessage.value = ''; // 清除之前的错误
        
        const response = await api.withdrawApproval(approval.id);
        
        if (response.data) {
          // 刷新审批详情
          await fetchApprovalDetail();
          
          // 通知父组件审批已更新
          emit('approval-updated', {
            id: approval.id,
            action: 'withdraw',
            status: response.data.status
          });
          
          // 清空评论
          approvalComment.value = '';
        }
      } catch (error) {
        console.error('撤回操作失败:', error);
        // 显示友好的错误消息
        if (error.response && error.response.data && error.response.data.detail) {
          showError(`撤回失败: ${error.response.data.detail}`);
        } else {
          showError('撤回操作失败，请稍后重试');
        }
      } finally {
        isProcessing.value = false;
      }
    };
    
    const handleSkip = async () => {
      if (!approval.id || !skipToNodeId.value) return;
      
      try {
        isProcessing.value = true;
        errorMessage.value = ''; // 清除之前的错误
        
        // 使用API模块的post方法
        const response = await api.post(`/api/approval/skip/${approval.id}`, {
          to_node_id: skipToNodeId.value,
          comment: skipComment.value
        });
        
        if (response.data && response.data.success) {
          // 刷新审批详情
          await fetchApprovalDetail();
          
          // 通知父组件审批已更新
          emit('approval-updated', {
            id: approval.id,
            action: 'skip',
            status: response.data.status
          });
          
          // 清空输入
          skipToNodeId.value = '';
          skipComment.value = '';
        }
      } catch (error) {
        console.error('跳过审批失败:', error);
        // 显示友好的错误消息
        if (error.response && error.response.data && error.response.data.detail) {
          showError(`跳过审批失败: ${error.response.data.detail}`);
        } else {
          showError('跳过审批操作失败，请稍后重试');
        }
      } finally {
        isProcessing.value = false;
      }
    };
    
    const fetchFormSchema = async (processId) => {
      try {
        console.log(`获取表单模式 processId=${processId}`);
        // 使用API模块的get方法，确保使用正确的token
        const response = await api.get(`/api/approval/form-schema/${processId}`);
        if (response.data) {
          formSchema.value = response.data;
          console.log('获取到表单模式:', formSchema.value);
        }
      } catch (error) {
        console.error('获取表单模式失败:', error);
        formSchema.value = null;
      }
    };
    
    // 辅助函数
    const formatDate = (dateString) => {
      if (!dateString) return '无日期';
      
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    };
    
    const formatFieldName = (key) => {
      // 格式化字段名
      const fieldMap = {
        // 通用字段
        'content': '内容',
        'amount': '金额',
        'reason': '原因',
        'description': '描述',
        'attachments': '附件',
        'note': '备注',
        'comment': '批注',
        
        // 日期相关
        'date': '日期',
        'start_date': '开始日期',
        'end_date': '结束日期',
        'created_at': '创建日期',
        'updated_at': '更新日期',
        'submit_date': '提交日期',
        'expense_date': '费用日期',
        
        // 请假相关
        'leave_type': '请假类型',
        'days': '天数',
        'hours': '小时数',
        
        // 报销相关
        'expense_type': '报销类型',
        'expense_amount': '报销金额',
        'has_receipt': '是否有发票',
        'receipt_number': '发票号码',
        
        // 采购相关
        'purchase_type': '采购类型',
        'items': '采购物品',
        'quantity': '数量',
        'unit_price': '单价',
        'total_price': '总价',
        'supplier': '供应商',
        'expected_cost': '预计费用',
        'actual_cost': '实际费用',
        
        // 审批相关
        'urgency': '紧急程度',
        'emergency_level': '紧急程度',
        'priority': '优先级',
        'status': '状态',
        
        // 人员相关
        'applicant': '申请人',
        'approver': '审批人',
        'department': '部门',
        'position': '职位'
      };
      
      // 如果在映射表中找到对应的中文名称，则使用它
      if (fieldMap[key]) {
        return fieldMap[key];
      }
      
      // 否则进行智能转换：将下划线分隔的字段名转换为可读格式
      // 例如：user_name -> 用户名, approval_status -> 审批状态
      const specialWords = {
        'id': 'ID',
        'hr': 'HR'
      };
      
      return key.split('_')
        .map(word => {
          if (specialWords[word]) {
            return specialWords[word];
          }
          return word.charAt(0).toUpperCase() + word.slice(1);
        })
        .join(' ');
    };
    
    const formatFieldValue = (value, fieldType = '') => {
      // 处理空值
      if (value === null || value === undefined) return '无';
      
      // 根据字段类型格式化值
      switch(fieldType) {
        case 'date':
          // 尝试格式化日期
          try {
            return formatDate(value);
          } catch (e) {
            return value.toString();
          }
          
        case 'number':
          // 对于金额类型，添加货币符号和千分位
          if (typeof value === 'number') {
            return value.toLocaleString('zh-CN') + ' 元';
          }
          return value.toString();
          
        case 'boolean':
        case 'checkbox':
          // 布尔值转为是/否
          return value ? '是' : '否';
          
        case 'select':
          // 选择项直接显示值
          return value.toString();
          
        default:
          // 根据值类型自动判断处理方式
          if (value instanceof Date) {
            return formatDate(value);
          }
          
          if (typeof value === 'boolean') {
            return value ? '是' : '否';
          }
          
          if (typeof value === 'number') {
            // 如果字段名包含金额、费用等关键词，添加货币符号
            if (/amount|cost|price|fee|金额|费用|价格/.test(fieldType)) {
              return value.toLocaleString('zh-CN') + ' 元';
            }
            return value.toString();
          }
          
          if (typeof value === 'object') {
            // 如果是数组，尝试将其格式化为列表
            if (Array.isArray(value)) {
              if (value.length === 0) return '无';
              return value.map(item => {
                if (typeof item === 'object') return JSON.stringify(item);
                return item.toString();
              }).join(', ');
            }
            // 如果是对象，转为JSON字符串
            return JSON.stringify(value, null, 2);
          }
          
          // 默认转为字符串
          return value.toString();
      }
    };
    
    const getNodeStatusFromHistory = (nodeId) => {
      if (!approval.history) return 'pending';
      
      // 查找节点的最新历史记录
      const nodeHistory = approval.history
        .filter(h => h.node_id === nodeId)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      
      if (nodeHistory.length === 0) {
        // 如果是当前节点但没有历史记录
        return approval.current_node === nodeId ? 'processing' : 'pending';
      }
      
      const latestAction = nodeHistory[0].action;
      
      switch (latestAction) {
        case 'approve': return 'approved';
        case 'reject': return 'rejected';
        case 'return': return 'returned';
        case 'create': return 'created';
        default: return 'completed';
      }
    };
    
    const isNodeCompleted = (node) => {
      return node.status === 'approved' || 
             node.status === 'completed' || 
             node.status === 'created';
    };
    
    const isCurrentNode = (node) => {
      return node.id === approval.current_node || 
             node.status === 'processing';
    };
    
    const isNodePending = (node) => {
      return node.status === 'pending' || !node.status;
    };
    
    const isNodeRejected = (node) => {
      return node.status === 'rejected' || 
             node.status === 'returned';
    };
    
    const getNodeApprover = (node) => {
      if (!approval.history) return null;
      
      // 查找节点的审批记录
      const nodeHistory = approval.history
        .filter(h => h.node_id === node.id)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      
      return nodeHistory.length > 0 ? nodeHistory[0].approver_name : null;
    };
    
    const getNodeTime = (node) => {
      if (!approval.history) return null;
      
      // 查找节点的审批记录
      const nodeHistory = approval.history
        .filter(h => h.node_id === node.id)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      
      return nodeHistory.length > 0 ? formatDate(nodeHistory[0].created_at) : null;
    };
    
    const getNodeComment = (node) => {
      if (!approval.history) return null;
      
      // 查找节点的审批记录
      const nodeHistory = approval.history
        .filter(h => h.node_id === node.id)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      
      return nodeHistory.length > 0 ? nodeHistory[0].comment : null;
    };
    
    const sortNodes = (nodes) => {
      // 根据工作流配置中的 edges 或 transitions 信息为节点排序
      if (!approval.workflow_config) {
        return nodes;
      }
      
      // 使用工作流中的边缘关系排序节点
      const sortedNodes = [];
      const nodeMap = {};
      
      // 创建节点映射
      nodes.forEach(node => {
        nodeMap[node.id] = node;
      });
      
      // 查找开始节点
      let startNode = null;
      
      // 基于节点类型查找开始节点
      for (const nodeId in nodeMap) {
        if (nodeMap[nodeId].type === 'start') {
          startNode = nodeMap[nodeId];
          break;
        }
      }
      
      // 如果没有找到 start 类型的节点，使用当前节点或第一个节点
      if (!startNode) {
        if (approval.current_node && nodeMap[approval.current_node]) {
          startNode = nodeMap[approval.current_node];
        } else if (Object.keys(nodeMap).length > 0) {
          startNode = nodeMap[Object.keys(nodeMap)[0]];
        } else {
          return nodes; // 如果没有节点，返回原始数组
        }
      }
      
      // 使用边缘信息构建流程图
      const edges = [];
      if (approval.workflow_config.edges) {
        // edges 格式: [{source: 'node1', target: 'node2'}, ...]
        edges.push(...approval.workflow_config.edges);
      } else if (approval.workflow_config.states) {
        // 状态机格式的转换: {state1: {transitions: [{target: 'state2'}, ...], ...}, ...}
        for (const stateId in approval.workflow_config.states) {
          const state = approval.workflow_config.states[stateId];
          if (state.transitions) {
            state.transitions.forEach(transition => {
              if (transition.target) {
                edges.push({
                  source: stateId,
                  target: transition.target
                });
              }
            });
          }
        }
      }
      
      // 使用拓扑排序
      const visited = new Set();
      const temp = new Set();
      const result = [];
      
      function dfs(nodeId) {
        if (temp.has(nodeId)) {
          // 检测到循环，跳过
          return;
        }
        if (visited.has(nodeId)) {
          return;
        }
        
        temp.add(nodeId);
        
        // 获取当前节点的所有后继节点
        const outgoingEdges = edges.filter(edge => edge.source === nodeId);
        for (const edge of outgoingEdges) {
          dfs(edge.target);
        }
        
        temp.delete(nodeId);
        visited.add(nodeId);
        result.push(nodeId);
      }
      
      // 从开始节点开始遍历
      dfs(startNode.id);
      
      // 处理可能没有被遍历到的节点
      for (const nodeId in nodeMap) {
        if (!visited.has(nodeId)) {
          dfs(nodeId);
        }
      }
      
      // 将结果转换回节点对象并反转（因为DFS是后序遍历）
      const sortedResult = result.reverse().map(nodeId => nodeMap[nodeId]).filter(Boolean);
      
      // 如果排序后的节点数与原节点数不一致，说明有节点丢失，回退到原始数组
      return sortedResult.length === nodes.length ? sortedResult : nodes;
    };
    
    const getInitials = (name) => {
      if (!name) return '?';
      return name.charAt(0).toUpperCase();
    };
    
    const getActionText = (action) => {
      const actionMap = {
        'approve': '同意',
        'reject': '拒绝',
        'return': '退回',
        'create': '创建',
        'submit': '提交',
        'withdraw': '撤回',
        'cancel': '取消'
      };
      return actionMap[action] || action;
    };
    
    // 生命周期钩子
    onMounted(() => {
      fetchApprovalDetail();
    });
    
    return {
      approval,
      approvalComment,
      isProcessing,
      errorMessage,
      skipToNodeId,
      skipComment,
      statusClass,
      statusText,
      emergencyClass,
      emergencyText,
      flowNodes,
      canReturn,
      canApprove,
      canReject,
      canWithdraw,
      formatDate,
      formattedFormData,
      isNodeCompleted,
      isCurrentNode,
      isNodePending,
      isNodeRejected,
      getNodeApprover,
      getNodeTime,
      getNodeComment,
      getInitials,
      getActionText,
      handleApprove,
      handleReject,
      handleReturn,
      handleWithdraw,
      handleSkip
    };
  }
};
</script>

<style scoped>
.approval-detail {
  background-color: #f8f9fa;
  padding: 24px;
  border-radius: 8px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.detail-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1a1a1a;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
}

.status-pending {
  background-color: #e6f7ff;
  color: #1890ff;
}

.status-approved {
  background-color: #f6ffed;
  color: #52c41a;
}

.status-rejected {
  background-color: #fff2f0;
  color: #ff4d4f;
}

.status-canceled {
  background-color: #f5f5f5;
  color: #8c8c8c;
}

.detail-section {
  background-color: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.detail-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #262626;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 10px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 14px;
  color: #8c8c8c;
}

.value {
  font-size: 15px;
  color: #262626;
  word-break: break-word;
}

.emergency-level {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.level-normal {
  background-color: #f5f5f5;
  color: #8c8c8c;
}

.level-medium {
  background-color: #fffbe6;
  color: #faad14;
}

.level-high {
  background-color: #fff7e6;
  color: #fa8c16;
}

.level-urgent {
  background-color: #fff1f0;
  color: #f5222d;
}

.form-data {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #f0f0f0;
}

.form-label {
  font-size: 14px;
  color: #8c8c8c;
}

.form-value {
  font-size: 15px;
  color: #262626;
  word-break: break-word;
}

.empty-content {
  padding: 16px;
  text-align: center;
  color: #8c8c8c;
  font-style: italic;
}

.flow-progress {
  padding: 16px 0;
}

.flow-timeline {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.flow-timeline::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 24px;
  bottom: 24px;
  width: 2px;
  background-color: #e8e8e8;
  z-index: 0;
}

.timeline-node {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding-left: 34px;
  min-height: 28px;
}

.node-icon {
  position: absolute;
  left: 0;
  top: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #f5f5f5;
  border: 2px solid #d9d9d9;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.timeline-node.completed .node-icon {
  background-color: #f6ffed;
  border-color: #52c41a;
}

.timeline-node.current .node-icon {
  background-color: #e6f7ff;
  border-color: #1890ff;
}

.timeline-node.rejected .node-icon {
  background-color: #fff2f0;
  border-color: #ff4d4f;
}

.node-content {
  flex-grow: 1;
  padding-top: 4px;
}

.node-title {
  font-size: 15px;
  font-weight: 500;
  color: #262626;
  margin-bottom: 8px;
}

.node-info {
  font-size: 14px;
  color: #8c8c8c;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.action-form {
  background-color: #fafafa;
  padding: 16px;
  border-radius: 4px;
  border: 1px solid #f0f0f0;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #262626;
}

.form-item textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  resize: vertical;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.approve-btn {
  background-color: #52c41a;
  color: #fff;
}

.approve-btn:hover {
  background-color: #389e0d;
}

.reject-btn {
  background-color: #ff4d4f;
  color: #fff;
}

.reject-btn:hover {
  background-color: #cf1322;
}

.return-btn {
  background-color: #faad14;
  color: #fff;
}

.return-btn:hover {
  background-color: #d48806;
}

.withdraw-btn {
  background-color: #ff4d4f;
  color: #fff;
}

.withdraw-btn:hover {
  background-color: #cf1322;
}

.approve-btn:disabled,
.reject-btn:disabled,
.return-btn:disabled,
.withdraw-btn:disabled {
  background-color: #f5f5f5;
  color: #bfbfbf;
  cursor: not-allowed;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-item {
  display: flex;
  gap: 12px;
}

.history-avatar {
  flex-shrink: 0;
}

.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #1890ff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
}

.history-content {
  flex-grow: 1;
}

.history-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.history-user {
  font-size: 14px;
  font-weight: 500;
  color: #262626;
}

.history-action {
  font-size: 12px;
  color: #1890ff;
  background-color: #e6f7ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.history-time {
  font-size: 12px;
  color: #8c8c8c;
  margin-left: auto;
}

.history-comment {
  font-size: 14px;
  color: #595959;
  padding: 8px;
  background-color: #f9f9f9;
  border-radius: 4px;
  margin-top: 4px;
}

.empty-history {
  padding: 16px;
  text-align: center;
  color: #8c8c8c;
  font-style: italic;
}

.error-message {
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 4px;
  padding: 8px 12px;
  margin-bottom: 16px;
  color: #ff4d4f;
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-style: normal;
  font-weight: bold;
}

.completed-notice {
  padding: 16px;
  background-color: #fff;
  border-radius: 8px;
  margin-bottom: 20px;
}

.notice-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.notice-icon {
  font-size: 24px;
  font-weight: bold;
}

.notice-text {
  flex-grow: 1;
}

.withdraw-btn:disabled {
  background-color: #f5f5f5;
  color: #bfbfbf;
  cursor: not-allowed;
}

.skip-btn {
  background-color: #722ed1;
  color: #fff;
}

.skip-btn:hover {
  background-color: #531dab;
}

.skip-btn:disabled {
  background-color: #f5f5f5;
  color: #bfbfbf;
  cursor: not-allowed;
}

.admin-actions {
  border: 1px dashed #722ed1;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  background-color: #f9f0ff;
}

.admin-actions h3 {
  color: #722ed1;
}

select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: #fff;
}

select:focus {
  outline: none;
  border-color: #722ed1;
  box-shadow: 0 0 0 2px rgba(114, 46, 209, 0.2);
}
</style> 