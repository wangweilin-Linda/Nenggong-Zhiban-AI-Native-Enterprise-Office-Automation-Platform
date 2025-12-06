<template>
  <div class="pagination">
    <div class="page-size">
      <select v-model="localPageSize" @change="$emit('change-page-size', localPageSize)">
        <option value="5">5条/页</option>
        <option value="10">10条/页</option>
        <option value="20">20条/页</option>
      </select>
    </div>
    <div class="page-controls">
      <button class="page-btn" :disabled="currentPage === 1" @click="$emit('change-page', currentPage - 1)">上一页</button>
      <span class="page-info">第 {{ currentPage }} / {{ totalPages }} 页</span>
      <button class="page-btn" :disabled="currentPage === totalPages" @click="$emit('change-page', currentPage + 1)">下一页</button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    currentPage: Number,
    totalPages: Number,
    pageSize: Number
  },
  data() {
    return {
      localPageSize: this.pageSize
    };
  },
  watch: {
    pageSize(newVal) {
      this.localPageSize = newVal;
    }
  }
};
</script>