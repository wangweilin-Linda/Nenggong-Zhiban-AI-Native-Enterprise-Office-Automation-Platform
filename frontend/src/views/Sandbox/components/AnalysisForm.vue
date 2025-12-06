<template>
  <div class="analysis-form">
    <a-form :model="config" @submit.prevent="handleSubmit">
      <a-form-item label="图表类型">
        <a-select v-model:value="config.chartType">
          <a-select-option v-for="type in chartTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="X轴列名">
        <a-input
          v-model:value="config.xColumn"
          placeholder="例如：地区"
        />
      </a-form-item>

      <a-form-item label="Y轴列名">
        <a-input
          v-model:value="config.yColumn"
          placeholder="例如：销售额"
        />
      </a-form-item>

      <a-form-item label="图表标题">
        <a-input
          v-model:value="config.title"
          placeholder="例如：各地区销售情况"
        />
      </a-form-item>

      <a-form-item>
        <a-button type="primary" html-type="submit">开始分析</a-button>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  onSubmit: {
    type: Function,
    required: true
  }
});

const chartTypes = [
  { value: 'bar', label: '柱状图' },
  { value: 'line', label: '折线图' },
  { value: 'scatter', label: '散点图' },
  { value: 'box', label: '箱线图' },
  { value: 'violin', label: '小提琴图' }
];

const config = ref({
  chartType: 'bar',
  xColumn: '',
  yColumn: '',
  title: ''
});

const handleSubmit = () => {
  const analysisConfig = {
    charts: [{
      type: config.value.chartType,
      x: config.value.xColumn,
      y: config.value.yColumn,
      title: config.value.title || '数据分析'
    }]
  };
  props.onSubmit(analysisConfig);
};
</script>

<style scoped>
.analysis-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}
</style> 