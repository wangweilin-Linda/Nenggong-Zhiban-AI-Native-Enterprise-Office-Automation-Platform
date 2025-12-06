<template>
  <div class="workflow-auth-manager">
    <div class="auth-header">
      <h3>审批权限配置</h3>
      <div class="workflow-badge">{{ workflowName || '未命名工作流' }}</div>
    </div>
    
    <div class="auth-content">
      <div class="node-list-container">
        <!-- 审批节点列表 -->
        <div class="node-list">
          <div v-for="node in approvalNodes" :key="node.id" 
               :class="['node-card', { active: selectedNode === node.id }]"
               @click="selectNode(node.id)">
            <div class="node-card-header">
              <div class="node-title">{{ getNodeLabel(node.id) }}</div>
              <div class="node-type">审批节点</div>
            </div>
          </div>
          
          <div v-if="approvalNodes.length === 0" class="empty-nodes">
            <div class="empty-icon">📝</div>
            <p>没有审批节点需要配置</p>
            <p class="empty-hint">请先使用AI助手设计流程图</p>
          </div>
        </div>

        <!-- 节点权限配置 -->
        <div class="node-config-panel" v-if="selectedNode && nodeSettings[selectedNode]">
          <div class="panel-header">
            <h4>{{ getNodeLabel(selectedNode) }} - 权限配置</h4>
          </div>
          
          <div class="panel-body">
            <div class="form-group">
              <label>节点名称</label>
              <input v-model="nodeSettings[selectedNode].name" type="text" placeholder="审批节点名称" />
            </div>
            
            <div class="form-group">
              <label>审批人角色</label>
              <div class="role-selector">
                <div v-for="role in roles" :key="role.id" 
                     :class="['role-chip', { selected: nodeSettings[selectedNode].allowed_roles.includes(role.id) }]"
                     @click="toggleRole(selectedNode, role.id)">
                  {{ role.name }}
                </div>
                <div v-if="roles.length === 0" class="no-roles">暂无可用角色</div>
              </div>
            </div>
            
            <div class="form-group">
              <label>职位要求</label>
              <select v-model="nodeSettings[selectedNode].required_position_level" class="select-control">
                <option value="0">无要求</option>
                <option value="1">初级职位</option>
                <option value="2">中级职位</option>
                <option value="3">高级职位</option>
                <option value="4">管理层</option>
              </select>
            </div>
            
            <div class="form-group">
              <label>部门级别</label>
              <select v-model="nodeSettings[selectedNode].required_department_level" class="select-control">
                <option value="0">无要求</option>
                <option value="1">普通部门</option>
                <option value="2">核心部门</option>
                <option value="3">总部</option>
              </select>
            </div>
            
            <div class="form-group">
              <label>审批功能</label>
              <div class="toggle-option">
                <label class="toggle-label">
                  <input type="checkbox" v-model="nodeSettings[selectedNode].can_return">
                  <span class="toggle-switch"></span>
                  <span>允许退回上一步</span>
                </label>
              </div>
              <div class="toggle-option">
                <label class="toggle-label">
                  <input type="checkbox" v-model="nodeSettings[selectedNode].requireComment">
                  <span class="toggle-switch"></span>
                  <span>要求填写审批意见</span>
                </label>
              </div>
            </div>
          </div>
        </div>
        
        <div class="empty-panel" v-else>
          <div class="empty-icon">👈</div>
          <p>请选择左侧的审批节点进行配置</p>
        </div>
      </div>
    </div>
    
    <div class="auth-footer">
      <button @click="saveSettings" class="primary-btn">保存权限设置</button>
      <button @click="cancel" class="secondary-btn">取消</button>
    </div>
  </div>
</template>

<script>
import { message } from 'ant-design-vue';
import api from '../utils/api';

export default {
  name: 'WorkflowAuthManager',
  props: {
    workflowConfig: {
      type: Object,
      required: true
    },
    workflowId: {
      type: [String, Number],
      default: null
    },
    workflowName: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      roles: [],
      selectedNode: null,
      nodeSettings: {},
      isLoading: false,
      useMockData: true
    };
  },
  computed: {
    // 获取审批节点列表（不包括初始和结束节点）
    approvalNodes() {
      try {
        if (!this.workflowConfig || !this.workflowConfig.states) {
          return [];
        }
        
        const nodes = [];
        const states = this.workflowConfig.states;
        
        // 遍历所有状态节点，找出审批节点
        Object.keys(states).forEach(stateId => {
          const state = states[stateId];
          
          // 排除初始节点和结束节点
          if (stateId !== 'initiator' && stateId !== 'approved' && stateId !== 'rejected' &&
              state.type !== 'start' && state.type !== 'end') {
            nodes.push({
              id: stateId,
              name: state.role || stateId,
              type: 'approval'
            });
          }
        });
        
        return nodes;
      } catch (error) {
        console.error('获取审批节点失败:', error);
        return [];
      }
    }
  },
  created() {
    // 初始化角色列表
    this.fetchRoles();
    
    // 初始化节点设置
    this.initNodeSettings();
    
    // 默认选择第一个节点
    if (this.approvalNodes.length > 0) {
      this.selectedNode = this.approvalNodes[0].id;
    }
  },
  methods: {
    async fetchRoles() {
      try {
        this.isLoading = true;
        
        // 优先使用模拟数据
        if (this.useMockData) {
          this.roles = [
            { id: 1, name: '部门经理' },
            { id: 2, name: '财务专员' },
            { id: 3, name: '导员' },
            { id: 4, name: '总经理' },
            { id: 5, name: '人事专员' }
          ];
          this.isLoading = false;
          return;
        }
        
        // 从API获取角色列表
        try {
          const response = await api.get('/admin/roles');
          if (response.data) {
            this.roles = response.data;
          } else {
            // 如果API返回空数据，使用默认角色列表
            this.roles = this.getDefaultRoles();
          }
        } catch (error) {
          console.error('获取角色列表失败:', error);
          // 使用默认角色列表
          this.roles = this.getDefaultRoles();
          
          // 使用离线模式
          this.useMockData = true;
        }
      } catch (error) {
        console.error('初始化角色列表失败:', error);
      } finally {
        this.isLoading = false;
      }
    },
    getDefaultRoles() {
      return [
        { id: 1, name: '部门经理' },
        { id: 2, name: '财务专员' },
        { id: 3, name: '导员' },
        { id: 4, name: '总经理' }
      ];
    },
    initNodeSettings() {
      try {
        const config = this.workflowConfig;
        
        if (!config || !config.states) {
          console.warn('工作流配置为空或不包含节点信息');
          return;
        }
        
        // 初始化节点设置
        this.nodeSettings = {};
        
        // 处理所有状态节点
        Object.keys(config.states).forEach(stateId => {
          const state = config.states[stateId];
          
          // 初始化每个节点的设置
          this.nodeSettings[stateId] = {
            name: state.role || stateId,
            allowed_roles: state.allowed_roles || [],
            required_position_level: state.required_position_level || 0,
            required_department_level: state.required_department_level || 0,
            editable_fields: state.editable_fields || [],
            required_fields: state.required_fields || [],
            can_return: state.can_return !== undefined ? state.can_return : true,
            canEditBasicInfo: (state.editable_fields || []).includes('basic_info'),
            canEditAttachments: (state.editable_fields || []).includes('attachments'),
            requireComment: (state.required_fields || []).includes('comment')
          };
        });
      } catch (error) {
        console.error('初始化节点设置失败:', error);
      }
    },
    selectNode(nodeId) {
      this.selectedNode = nodeId;
    },
    getNodeLabel(nodeId) {
      if (nodeId === 'initiator') {
        return '发起人';
      }
      
      if (this.nodeSettings[nodeId]) {
        return this.nodeSettings[nodeId].name;
      }
      
      // 从工作流配置中获取
      if (this.workflowConfig && 
          this.workflowConfig.states && 
          this.workflowConfig.states[nodeId]) {
        return this.workflowConfig.states[nodeId].role || nodeId;
      }
      
      return nodeId;
    },
    toggleRole(nodeId, roleId) {
      const roles = this.nodeSettings[nodeId].allowed_roles;
      const index = roles.indexOf(roleId);
      
      if (index === -1) {
        roles.push(roleId);
      } else {
        roles.splice(index, 1);
      }
    },
    saveSettings() {
      try {
        // 克隆原始配置
        const updatedConfig = JSON.parse(JSON.stringify(this.workflowConfig));
        
        // 更新节点设置
        Object.keys(this.nodeSettings).forEach(nodeId => {
          if (updatedConfig.states[nodeId]) {
            const settings = this.nodeSettings[nodeId];
            
            // 更新节点名称
            updatedConfig.states[nodeId].role = settings.name;
            
            // 更新权限设置
            updatedConfig.states[nodeId].allowed_roles = settings.allowed_roles;
            updatedConfig.states[nodeId].required_position_level = parseInt(settings.required_position_level);
            updatedConfig.states[nodeId].required_department_level = parseInt(settings.required_department_level);
            
            // 更新表单字段权限
            const editableFields = [];
            if (settings.canEditBasicInfo) editableFields.push('basic_info');
            if (settings.canEditAttachments) editableFields.push('attachments');
            updatedConfig.states[nodeId].editable_fields = editableFields;
            
            // 更新必填字段
            const requiredFields = [];
            if (settings.requireComment) requiredFields.push('comment');
            updatedConfig.states[nodeId].required_fields = requiredFields;
            
            // 更新其他设置
            updatedConfig.states[nodeId].can_return = settings.can_return;
          }
        });
        
        // 发送配置更新事件
        this.$emit('config-updated', updatedConfig);
        
        // 显示成功消息
        message.success('权限设置已保存');
      } catch (error) {
        console.error('保存权限设置失败:', error);
        message.error('保存权限设置失败，请重试');
      }
    },
    cancel() {
      // 重置为原始设置
      this.initNodeSettings();
    }
  }
};
</script>

<style scoped>
.workflow-auth-manager {
  background-color: #f9fafc;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.auth-header {
  padding: 20px 24px;
  background-color: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.auth-header h3 {
  margin: 0;
  font-size: 18px;
  color: #1e293b;
  font-weight: 600;
}

.workflow-badge {
  padding: 6px 12px;
  background-color: #f0f7ff;
  color: #0066ff;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.auth-content {
  flex: 1;
  padding: 24px;
  overflow: auto;
}

.node-list-container {
  display: flex;
  gap: 24px;
  min-height: 450px;
}

.node-list {
  width: 280px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
  overflow-y: auto;
}

.node-card {
  padding: 16px;
  border-radius: 8px;
  background-color: #f9fafc;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid #eaecf0;
}

.node-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
}

.node-card.active {
  background-color: #f0f7ff;
  border-color: #0066ff;
}

.node-card-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-title {
  font-weight: 600;
  color: #1e293b;
}

.node-type {
  font-size: 12px;
  color: #64748b;
  background-color: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.node-config-panel {
  flex: 1;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: a1px solid #f0f0f0;
  background-color: #f8fafc;
}

.panel-header h4 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
  font-weight: 600;
}

.panel-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #475569;
  font-weight: 500;
}

.form-group input[type="text"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input[type="text"]:focus {
  border-color: #0066ff;
  outline: none;
}

.select-control {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23475569' viewBox='0 0 16 16'%3E%3Cpath d='M8 10.5a.5.5 0 0 1-.354-.146l-4-4A.5.5 0 0 1 4.354 5.5h8.292a.5.5 0 0 1 .354.854l-4 4A.5.5 0 0 1 8 10.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  transition: border-color 0.2s;
}

.select-control:focus {
  border-color: #0066ff;
  outline: none;
}

.role-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.role-chip {
  padding: 6px 12px;
  border-radius: 20px;
  background-color: #f1f5f9;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.role-chip:hover {
  background-color: #e2e8f0;
}

.role-chip.selected {
  background-color: #0066ff;
  color: white;
}

.toggle-option {
  margin-bottom: 12px;
}

.toggle-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.toggle-label input {
  display: none;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  background-color: #cbd5e1;
  border-radius: 20px;
  margin-right: 10px;
  transition: all 0.2s;
}

.toggle-switch:before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background-color: white;
  top: 2px;
  left: 2px;
  transition: all 0.2s;
}

.toggle-label input:checked + .toggle-switch {
  background-color: #0066ff;
}

.toggle-label input:checked + .toggle-switch:before {
  transform: translateX(16px);
}

.empty-nodes, .empty-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #64748b;
  height: 100%;
}

.empty-icon {
  font-size: 36px;
  margin-bottom: 16px;
  opacity: 0.7;
}

.empty-hint {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 8px;
}

.no-roles {
  color: #94a3b8;
  font-size: 13px;
  padding: 10px;
}

.auth-footer {
  padding: 16px 24px;
  background-color: #fff;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.primary-btn {
  padding: 10px 16px;
  background-color: #0066ff;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.primary-btn:hover {
  background-color: #0052cc;
}

.secondary-btn {
  padding: 10px 16px;
  background-color: #f1f5f9;
  color: #475569;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.secondary-btn:hover {
  background-color: #e2e8f0;
}

@media (max-width: 768px) {
  .node-list-container {
    flex-direction: column;
  }
  
  .node-list {
    width: 100%;
  }
}
</style> 