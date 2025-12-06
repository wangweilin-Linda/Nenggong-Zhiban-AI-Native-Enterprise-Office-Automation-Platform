<template>
  <div class="smart-input-assistant" :class="{ 'collapsed': collapsed }">
    <div class="assistant-header" @click="toggleCollapse">
      <div class="header-content">
        <i class="fas fa-robot"></i>
        <span class="title">智能填充助手</span>
      </div>
      <div class="header-actions">
        <button v-if="!collapsed" class="action-button" @click.stop="clearInput">
          <i class="fas fa-times"></i>
        </button>
        <button class="action-button">
          <i class="fas" :class="collapsed ? 'fa-chevron-down' : 'fa-chevron-up'"></i>
        </button>
      </div>
    </div>
    
    <div v-if="!collapsed" class="assistant-body">
      <div class="input-area">
        <textarea 
          v-model="userInput" 
          placeholder="输入您需要的内容，如：'给市场部张经理写一封关于项目进展的邮件'"
          class="smart-input"
          @keyup.enter="handleUserInput"
        ></textarea>
        <button 
          class="send-button" 
          @click="handleUserInput"
          :disabled="isProcessing || !userInput.trim()"
        >
          <i class="fas" :class="isProcessing ? 'fa-spinner fa-spin' : 'fa-paper-plane'"></i>
        </button>
      </div>
      
      <div v-if="processingStatus" class="processing-status">
        <div class="spinner"><i class="fas fa-spinner fa-spin"></i></div>
        <div class="status-message">{{ processingStatus }}</div>
      </div>
      
      <div v-if="suggestions.length > 0" class="suggestions-area">
        <div class="suggestions-title">智能填充建议</div>
        <div class="suggestion-items">
          <div v-for="(suggestion, index) in suggestions" :key="index" class="suggestion-item">
            <div class="suggestion-content">
              <div class="field-name">{{ getFieldDisplayName(suggestion.field) }}:</div>
              <div class="field-value" :title="suggestion.value">{{ formatValue(suggestion.value) }}</div>
            </div>
            <div class="suggestion-actions">
              <button @click="acceptSuggestion(suggestion)" class="accept-btn">
                <i class="fas fa-check"></i>
              </button>
              <button @click="rejectSuggestion(suggestion)" class="reject-btn">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
        </div>
        <div class="bulk-actions">
          <button @click="acceptAllSuggestions" class="accept-all-btn">
            <i class="fas fa-check-double"></i> 全部采用
          </button>
          <button @click="rejectAllSuggestions" class="reject-all-btn">
            <i class="fas fa-times-circle"></i> 全部忽略
          </button>
        </div>
      </div>
      
      <div v-if="errorMessage" class="error-message">
        <i class="fas fa-exclamation-triangle"></i>
        <span>{{ errorMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { processUserInput, getFormSuggestions } from '../services/smartAgentService';

export default {
  name: 'SmartInputAssistant',
  props: {
    formId: {
      type: String,
      required: true
    },
    formData: {
      type: Object,
      default: () => ({})
    },
    fieldMappings: {
      type: Object,
      default: () => ({
        recipient: '收件人',
        subject: '主题',
        content: '内容',
        name: '名称',
        title: '标题',
        description: '描述'
      })
    }
  },
  emits: ['update:field', 'suggestion-accepted', 'suggestions-ready'],
  setup(props, { emit }) {
    const collapsed = ref(false);
    const userInput = ref('');
    const isProcessing = ref(false);
    const processingStatus = ref('');
    const errorMessage = ref('');
    const suggestions = ref([]);
    
    // 切换折叠状态
    const toggleCollapse = () => {
      collapsed.value = !collapsed.value;
    };
    
    // 清除用户输入
    const clearInput = () => {
      userInput.value = '';
      errorMessage.value = '';
    };
    
    // 处理用户输入
    const handleUserInput = async () => {
      if (!userInput.value.trim() || isProcessing.value) return;
      
      isProcessing.value = true;
      processingStatus.value = '正在分析您的输入...';
      errorMessage.value = '';
      
      try {
        // 处理用户输入
        const result = await processUserInput(userInput.value, {
          form_id: props.formId,
          current_form_data: props.formData
        });
        
        if (result.success) {
          processingStatus.value = '正在生成智能建议...';
          
          // 如果有表单数据，准备建议
          if (result.form_data && Object.keys(result.form_data).length > 0) {
            // 转换为建议列表
            const newSuggestions = [];
            for (const [field, value] of Object.entries(result.form_data)) {
              if (value) {
                newSuggestions.push({
                  field,
                  value,
                  source: 'user_input'
                });
              }
            }
            
            // 获取额外的表单建议
            const enhancedFormData = { ...props.formData, ...result.form_data };
            const formSuggestions = await getFormSuggestions(props.formId, enhancedFormData);
            
            if (formSuggestions && formSuggestions.fields) {
              // 添加从API获取的字段建议
              for (const [field, value] of Object.entries(formSuggestions.fields)) {
                if (value && !newSuggestions.some(s => s.field === field)) {
                  newSuggestions.push({
                    field,
                    value,
                    source: 'ai_suggestion'
                  });
                }
              }
            }
            
            // 更新建议列表
            suggestions.value = newSuggestions;
            
            // 通知父组件有新的建议
            if (newSuggestions.length > 0) {
              emit('suggestions-ready', newSuggestions);
            }
          }
          
          processingStatus.value = '';
        } else {
          errorMessage.value = result.message || '无法处理您的输入';
        }
      } catch (error) {
        console.error('处理用户输入出错:', error);
        errorMessage.value = error.message || '处理失败，请稍后再试';
      } finally {
        isProcessing.value = false;
      }
    };
    
    // 接受建议
    const acceptSuggestion = (suggestion) => {
      emit('update:field', { field: suggestion.field, value: suggestion.value });
      emit('suggestion-accepted', suggestion);
      
      // 从建议列表中移除已接受的建议
      suggestions.value = suggestions.value.filter(s => s.field !== suggestion.field);
    };
    
    // 拒绝建议
    const rejectSuggestion = (suggestion) => {
      // 从建议列表中移除已拒绝的建议
      suggestions.value = suggestions.value.filter(s => s.field !== suggestion.field);
    };
    
    // 接受所有建议
    const acceptAllSuggestions = () => {
      suggestions.value.forEach(suggestion => {
        emit('update:field', { field: suggestion.field, value: suggestion.value });
        emit('suggestion-accepted', suggestion);
      });
      
      // 清空建议列表
      suggestions.value = [];
    };
    
    // 拒绝所有建议
    const rejectAllSuggestions = () => {
      suggestions.value = [];
    };
    
    // 获取字段显示名称
    const getFieldDisplayName = (fieldName) => {
      return props.fieldMappings[fieldName] || fieldName;
    };
    
    // 格式化值显示
    const formatValue = (value) => {
      if (typeof value === 'string' && value.length > 50) {
        return `${value.substring(0, 50)}...`;
      }
      return value;
    };
    
    return {
      collapsed,
      userInput,
      isProcessing,
      processingStatus,
      errorMessage,
      suggestions,
      toggleCollapse,
      clearInput,
      handleUserInput,
      acceptSuggestion,
      rejectSuggestion,
      acceptAllSuggestions,
      rejectAllSuggestions,
      getFieldDisplayName,
      formatValue
    };
  }
};
</script>

<style scoped>
.smart-input-assistant {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #ffffff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
  transition: all 0.3s ease;
}

.smart-input-assistant.collapsed {
  box-shadow: none;
}

.assistant-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #f0f8ff;
  border-radius: 8px 8px 0 0;
  cursor: pointer;
  user-select: none;
}

.collapsed .assistant-header {
  border-radius: 8px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-content i {
  color: #1976d2;
  font-size: 18px;
}

.title {
  font-weight: 500;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 5px;
}

.action-button {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.action-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #333;
}

.assistant-body {
  padding: 15px;
}

.input-area {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.smart-input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  min-height: 40px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.smart-input:focus {
  outline: none;
  border-color: #1976d2;
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
}

.send-button {
  width: 40px;
  height: 40px;
  border: none;
  background-color: #1976d2;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.send-button:hover:not(:disabled) {
  background-color: #1565c0;
  transform: translateY(-1px);
}

.send-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.processing-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background-color: #e3f2fd;
  border-radius: 4px;
  margin-bottom: 15px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

.spinner {
  color: #1976d2;
}

.status-message {
  font-size: 14px;
  color: #333;
}

.suggestions-area {
  margin-top: 15px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 10px;
}

.suggestions-title {
  font-weight: 500;
  margin-bottom: 10px;
  color: #333;
  font-size: 15px;
}

.suggestion-items {
  max-height: 200px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.suggestion-item:last-child {
  border-bottom: none;
}

.suggestion-content {
  display: flex;
  gap: 10px;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.field-name {
  font-weight: 500;
  color: #555;
  white-space: nowrap;
}

.field-value {
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.suggestion-actions {
  display: flex;
  gap: 8px;
}

.accept-btn, .reject-btn {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.accept-btn {
  background-color: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

.accept-btn:hover {
  background-color: rgba(76, 175, 80, 0.2);
  transform: scale(1.1);
}

.reject-btn {
  background-color: rgba(244, 67, 54, 0.1);
  color: #f44336;
}

.reject-btn:hover {
  background-color: rgba(244, 67, 54, 0.2);
  transform: scale(1.1);
}

.bulk-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
}

.accept-all-btn, .reject-all-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.accept-all-btn {
  background-color: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

.accept-all-btn:hover {
  background-color: rgba(76, 175, 80, 0.2);
}

.reject-all-btn {
  background-color: rgba(244, 67, 54, 0.1);
  color: #f44336;
}

.reject-all-btn:hover {
  background-color: rgba(244, 67, 54, 0.2);
}

.error-message {
  margin-top: 10px;
  padding: 10px;
  background-color: #ffebee;
  color: #d32f2f;
  border-radius: 4px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style> 