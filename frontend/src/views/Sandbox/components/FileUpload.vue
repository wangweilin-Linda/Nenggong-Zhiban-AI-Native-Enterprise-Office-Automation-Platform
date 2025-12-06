<template>
  <a-upload
    :accept="'.xlsx,.xls'"
    :before-upload="handleBeforeUpload"
    :show-upload-list="false"
  >
    <a-button :loading="loading">
      <template #icon><upload-outlined /></template>
      上传 Excel 文件
    </a-button>
  </a-upload>
</template>

<script setup>
import { ref } from 'vue';
import { message } from 'ant-design-vue';
import { UploadOutlined } from '@ant-design/icons-vue';

const props = defineProps({
  onUploadSuccess: {
    type: Function,
    required: true
  }
});

const loading = ref(false);

const handleBeforeUpload = async (file) => {
  loading.value = true;
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('http://localhost:8002/api/v1/analysis/upload', {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    
    if (response.ok) {
      message.success('文件上传成功');
      props.onUploadSuccess(data.task_id);
    } else {
      message.error(data.detail || '上传失败');
    }
  } catch (error) {
    message.error('上传失败，请重试');
  } finally {
    loading.value = false;
  }
  return false;
};
</script>

<style scoped>
</style> 