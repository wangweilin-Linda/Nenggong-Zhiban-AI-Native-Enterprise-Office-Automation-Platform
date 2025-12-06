# EmailSystem.vue 智能代理集成指南

本文档提供了将智能输入助手 `SmartInputAssistant` 组件集成到 `EmailSystem.vue` 的步骤。

## 步骤 1: 导入组件

在 `EmailSystem.vue` 文件的 `<script>` 部分中，添加导入语句：

```javascript
import SmartInputAssistant from './SmartInputAssistant.vue';
```

## 步骤 2: 注册组件

在 `components` 部分添加组件：

```javascript
export default {
  name: 'EmailSystem',
  components: {
    AiAssistant,
    SmartInputAssistant  // 添加这一行
  },
  // ...其余部分保持不变
}
```

## 步骤 3: 在模板中添加组件

在写邮件弹窗内的表单中添加组件，建议放置在表单开头：

```html
<!-- 写邮件弹窗 -->
<div v-if="showComposeModal" class="modal email-compose-modal-wrapper">
  <div class="modal-content email-compose-modal">
    <div class="modal-header">
      <h3><i class="fas fa-edit"></i> 写邮件</h3>
      <button class="close-btn" @click="closeComposeModal">×</button>
    </div>
    <div class="modal-body">
      <form @submit.prevent="sendEmail" class="email-form">
        <!-- 添加智能输入助手组件 -->
        <SmartInputAssistant
          formId="email_compose"
          :formData="{
            recipient: newEmail.recipient,
            subject: newEmail.subject,
            content: newEmail.intention
          }"
          @update:field="handleFieldUpdate"
          @suggestion-accepted="handleSuggestionAccepted"
        />
        
        <!-- 现有表单字段 -->
        <div class="form-group">
          <!-- ...剩余表单内容不变... -->
        </div>
      </form>
    </div>
  </div>
</div>
```

## 步骤 4: 添加事件处理方法

在 `methods` 部分添加处理智能输入助手事件的方法：

```javascript
// 处理智能输入助手字段更新
handleFieldUpdate({ field, value }) {
  if (field === 'recipient') {
    this.newEmail.recipient = value;
  } else if (field === 'subject') {
    this.newEmail.subject = value;
  } else if (field === 'content') {
    this.newEmail.intention = value;
    this.generatedContent = value;
  }
},

// 处理建议被接受事件
handleSuggestionAccepted(suggestion) {
  console.log(`建议已采用: ${suggestion.field} = ${suggestion.value.substring(0, 30)}...`);
  
  // 可以在这里添加额外的处理逻辑，如显示通知
  this.notification = {
    show: true,
    type: 'success',
    message: `已自动填充${suggestion.field === 'recipient' ? '收件人' : 
              suggestion.field === 'subject' ? '主题' : '内容'}`,
    timeout: setTimeout(() => {
      this.notification.show = false;
    }, 3000)
  };
},
```

## 步骤 5: 替换或集成现有的autoFill确认对话框

智能输入助手可以替代现有的 `showAutoFillConfirm` 对话框，或者与之集成。建议的方法是：

1. 保留 `autoFillNotifications` 和 `pendingAutoFills` 数据结构
2. 修改 `processPlainTextEmail` 和其他相关方法，使用新的智能输入助手
3. 将自动填充确认逻辑移至智能输入助手中处理

例如，可以这样修改 `processPlainTextEmail` 方法：

```javascript
processPlainTextEmail(textContent, originalSubject, originalRecipient) {
  if (!textContent) return;
  
  // 先整体过滤掉EMAIL_JSON_START标记
  textContent = this.removeJsonTagPrefix(textContent);
  
  // 清理思考过程标记
  const cleanedContent = this.cleanThinkingContent(textContent);
  
  // 尝试从文本中提取信息
  const recipientMatch = cleanedContent.match(/收件人[:：]\s*(.+?)[\n\r]/);
  const subjectMatch = cleanedContent.match(/主题[:：]\s*(.+?)[\n\r]/);
  
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
  
  // 直接更新表单，不显示确认对话框
  if (recipientMatch && recipientMatch[1].trim() && !originalRecipient) {
    const extractedRecipient = recipientMatch[1].trim();
    this.newEmail.recipient = this.removeJsonTagPrefix(extractedRecipient);
  }
  
  if (subjectMatch && subjectMatch[1].trim() && 
      (!originalSubject || originalSubject === 'AI辅助生成的邮件')) {
    const extractedSubject = subjectMatch[1].trim();
    this.newEmail.subject = this.removeJsonTagPrefix(extractedSubject);
  }
  
  // 再次清理内容
  pureContent = this.cleanThinkingContent(pureContent);
  pureContent = this.removeJsonTagPrefix(pureContent);
  
  // 更新内容
  this.generatedContent = pureContent;
  this.newEmail.intention = pureContent;
}
```

## 完成集成

按照以上步骤完成集成后，EmailSystem.vue 将具有更强大的智能填充能力，并且在关键词匹配失效的情况下，可以使用 LangGraph 代理进行更智能的处理。 