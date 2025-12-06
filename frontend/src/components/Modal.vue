<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container">
      <div class="modal-header">
        <slot name="header">
          <h3>{{ title }}</h3>
        </slot>
        <button class="close-button" @click="$emit('close')">&times;</button>
      </div>
      
      <div class="modal-body">
        <slot name="body">
          {{ content }}
        </slot>
      </div>
      
      <div class="modal-footer">
        <slot name="footer">
          <button class="button-secondary" @click="$emit('close')">关闭</button>
        </slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Modal',
  props: {
    title: {
      type: String,
      default: '详情'
    },
    content: {
      type: String,
      default: ''
    }
  },
  emits: ['close']
};
</script>

<style scoped>
.modal-overlay {
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
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.close-button:hover {
  color: #333;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  max-height: 60vh;
}

.modal-footer {
  padding: 10px 24px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.button-primary {
  background-color: #1890ff;
  color: white;
  border: 1px solid #1890ff;
}

.button-primary:hover {
  background-color: #40a9ff;
  border-color: #40a9ff;
}

.button-secondary {
  background-color: white;
  color: rgba(0, 0, 0, 0.65);
  border: 1px solid #d9d9d9;
}

.button-secondary:hover {
  color: #40a9ff;
  border-color: #40a9ff;
}

.button-danger {
  background-color: #ff4d4f;
  color: white;
  border: 1px solid #ff4d4f;
}

.button-danger:hover {
  background-color: #ff7875;
  border-color: #ff7875;
}
</style> 