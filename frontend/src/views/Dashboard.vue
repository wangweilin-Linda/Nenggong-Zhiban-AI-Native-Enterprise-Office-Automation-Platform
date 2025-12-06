<template>
  <div class="dashboard-container">
    <h1>仪表盘</h1>
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="待处理事项" :loading="loading">
          <template #extra>
            <a href="#" @click="refreshData">刷新</a>
          </template>
          <a-list item-layout="horizontal" :data-source="todoItems" size="small">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta
                  :title="item.title"
                  :description="item.description"
                >
                  <template #avatar>
                    <a-avatar 
                      :style="{ backgroundColor: getTypeColor(item.type) }" 
                      :icon="getTypeIcon(item.type)"
                    />
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <a @click="handleProcessItem(item)">处理</a>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="审批流程" :loading="loading">
          <a-statistic-countdown
            title="下一次工作流自动检查"
            :value="nextCheckTime"
            format="HH:mm:ss"
            style="text-align: center"
          />
          <a-divider />
          <div class="process-stats">
            <a-statistic
              title="待我审批"
              :value="stats.pendingCount"
              :value-style="{ color: '#1890ff' }"
            >
              <template #suffix>
                <span class="small-text">项</span>
              </template>
            </a-statistic>
            <a-statistic
              title="已完成"
              :value="stats.completedCount"
              :value-style="{ color: '#52c41a' }"
            >
              <template #suffix>
                <span class="small-text">项</span>
              </template>
            </a-statistic>
            <a-statistic
              title="已拒绝"
              :value="stats.rejectedCount"
              :value-style="{ color: '#ff4d4f' }"
            >
              <template #suffix>
                <span class="small-text">项</span>
              </template>
            </a-statistic>
          </div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="通知公告" :loading="loading">
          <a-tabs>
            <a-tab-pane key="news" tab="新闻">
              <a-list :data-source="newsList" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <a-list-item-meta
                      :title="item.title"
                      :description="formatDate(item.date)"
                    />
                  </a-list-item>
                </template>
              </a-list>
            </a-tab-pane>
            <a-tab-pane key="notices" tab="公告">
              <a-list :data-source="noticeList" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <a-list-item-meta
                      :title="item.title"
                      :description="formatDate(item.date)"
                    />
                  </a-list-item>
                </template>
              </a-list>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
    
    <a-row :gutter="16" style="margin-top: 16px">
      <a-col :span="16">
        <a-card title="待审批文档" :loading="loading">
          <a-table
            :columns="documentColumns"
            :data-source="documents"
            :pagination="{ pageSize: 5 }"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'action'">
                <a @click="viewDocument(record)">查看</a>
                <a-divider type="vertical" />
                <a @click="approveDocument(record)">审批</a>
              </template>
              <template v-else-if="column.dataIndex === 'status'">
                <a-tag :color="getStatusColor(record.status)">
                  {{ getStatusText(record.status) }}
                </a-tag>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="系统状态" :loading="loading">
          <div class="system-status">
            <a-progress
              type="circle"
              :percent="systemStatus.cpuUsage"
              :width="80"
              :format="percent => `${percent}%`"
              :stroke-color="getProgressColor(systemStatus.cpuUsage)"
            />
            <div>
              <div>CPU使用率</div>
              <div class="status-detail">{{ systemStatus.cpuUsage }}% / 100%</div>
            </div>
          </div>
          <a-divider />
          <div class="system-status">
            <a-progress
              type="circle"
              :percent="systemStatus.memoryUsage"
              :width="80"
              :format="percent => `${percent}%`"
              :stroke-color="getProgressColor(systemStatus.memoryUsage)"
            />
            <div>
              <div>内存使用率</div>
              <div class="status-detail">{{ systemStatus.memoryUsage }}% / 100%</div>
            </div>
          </div>
          <a-divider />
          <div class="system-status">
            <a-progress
              type="circle"
              :percent="systemStatus.diskUsage"
              :width="80"
              :format="percent => `${percent}%`"
              :stroke-color="getProgressColor(systemStatus.diskUsage)"
            />
            <div>
              <div>磁盘使用率</div>
              <div class="status-detail">{{ systemStatus.diskUsage }}% / 100%</div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 审批模块 -->
    <template v-if="activeModule === 'approval'">
      <div class="approval-container">
        <div v-if="loadingApprovals" class="loading-state">
          <div class="spinner"></div>
          <p>正在加载审批数据...</p>
        </div>
        
        <div v-else-if="approvalError" class="error-state">
          <p>{{ approvalError }}</p>
          <button @click="fetchApprovalData" class="btn-retry">重试</button>
        </div>
        
        <div v-else>
          <h3>待处理审批</h3>
          <div v-if="pendingApprovals.length === 0" class="empty-state">
            <p>没有待处理的审批</p>
          </div>
          <table v-else class="approval-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>发起人</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="approval in pendingApprovals" :key="approval.id">
                <td>{{ approval.title }}</td>
                <td>{{ approval.initiator }}</td>
                <td>{{ approval.status }}</td>
                <td>{{ approval.created_at }}</td>
                <td>
                  <button @click="viewApproval(approval.id)" class="btn-view">查看</button>
                </td>
              </tr>
            </tbody>
          </table>
          
          <h3>我发起的审批</h3>
          <div v-if="myApprovals.length === 0" class="empty-state">
            <p>您还没有发起过审批</p>
          </div>
          <table v-else class="approval-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>状态</th>
                <th>当前节点</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="approval in myApprovals" :key="approval.id">
                <td>{{ approval.title }}</td>
                <td>{{ approval.status }}</td>
                <td>{{ approval.current_node }}</td>
                <td>{{ approval.created_at }}</td>
                <td>
                  <button @click="viewApproval(approval.id)" class="btn-view">查看</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { getPendingApprovals, getMyApprovals, getApprovalStats } from '@/api/approval';
import { getDocuments } from '@/api/document';
import { getSystemStatus } from '@/api/system';
import { getNews, getNotices } from '@/api/notice';
import { formatDate } from '@/utils/date';

const loading = ref(true);
const todoItems = ref([]);
const stats = ref({
  pendingCount: 0,
  completedCount: 0,
  rejectedCount: 0
});
const newsList = ref([]);
const noticeList = ref([]);
const documents = ref([]);
const systemStatus = ref({
  cpuUsage: 0,
  memoryUsage: 0,
  diskUsage: 0
});
const nextCheckTime = ref(Date.now() + 60000); // 1分钟后
const pendingApprovals = ref([]);
const myApprovals = ref([]);
const loadingApprovals = ref(false);
const approvalError = ref(null);

const documentColumns = [
  {
    title: '标题',
    dataIndex: 'title',
    key: 'title'
  },
  {
    title: '类型',
    dataIndex: 'document_type',
    key: 'document_type'
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status'
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at'
  },
  {
    title: '操作',
    dataIndex: 'action',
    key: 'action'
  }
];

const getTypeColor = (type) => {
  const colors = {
    approval: '#1890ff',
    document: '#52c41a',
    notice: '#faad14'
  };
  return colors[type] || '#1890ff';
};

const getTypeIcon = (type) => {
  const icons = {
    approval: 'check-circle',
    document: 'file',
    notice: 'notification'
  };
  return icons[type] || 'check-circle';
};

const getStatusColor = (status) => {
  const colors = {
    pending: 'blue',
    approved: 'green',
    rejected: 'red'
  };
  return colors[status] || 'default';
};

const getStatusText = (status) => {
  const texts = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝'
  };
  return texts[status] || status;
};

const getProgressColor = (percent) => {
  if (percent < 50) return '#52c41a';
  if (percent < 80) return '#faad14';
  return '#ff4d4f';
};

const refreshData = async () => {
  loading.value = true;
  try {
    await Promise.all([
      fetchApprovalStats(),
      fetchDocuments(),
      fetchNews(),
      fetchNotices(),
      fetchSystemStatus()
    ]);
  } catch (error) {
    console.error('刷新数据失败:', error);
  } finally {
    loading.value = false;
  }
};

const fetchApprovalStats = async () => {
  try {
    const response = await getApprovalStats();
    stats.value = response.data;
  } catch (error) {
    console.error('获取审批统计失败:', error);
  }
};

const fetchDocuments = async () => {
  try {
    const response = await getDocuments();
    documents.value = response.data;
  } catch (error) {
    console.error('获取文档列表失败:', error);
  }
};

const fetchNews = async () => {
  try {
    const response = await getNews();
    newsList.value = response.data;
  } catch (error) {
    console.error('获取新闻列表失败:', error);
  }
};

const fetchNotices = async () => {
  try {
    const response = await getNotices();
    noticeList.value = response.data;
  } catch (error) {
    console.error('获取公告列表失败:', error);
  }
};

const fetchSystemStatus = async () => {
  try {
    const response = await getSystemStatus();
    systemStatus.value = response.data;
  } catch (error) {
    console.error('获取系统状态失败:', error);
  }
};

const handleProcessItem = (item) => {
  // 处理待办事项
  console.log('处理待办事项:', item);
};

const viewDocument = (document) => {
  // 查看文档
  console.log('查看文档:', document);
};

const approveDocument = (document) => {
  // 审批文档
  console.log('审批文档:', document);
};

const fetchApprovalData = async () => {
  loadingApprovals.value = true;
  approvalError.value = null;
  
  try {
    // 获取待处理审批
    const pendingResponse = await getPendingApprovals();
    pendingApprovals.value = pendingResponse.data;
    
    // 获取我发起的审批
    const myResponse = await getMyApprovals();
    myApprovals.value = myResponse.data;
  } catch (error) {
    console.error('获取审批数据失败:', error);
    approvalError.value = '获取审批数据失败，请稍后重试';
  } finally {
    loadingApprovals.value = false;
  }
};

onMounted(() => {
  refreshData();
  fetchApprovalData();
});
</script>

<style scoped>
.dashboard-container {
  padding: 24px;
}

.process-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 16px;
}

.small-text {
  font-size: 12px;
  margin-left: 4px;
}

.system-status {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-detail {
  font-size: 12px;
  color: #999;
}

.approval-container {
  padding: 24px;
}

.loading-state, .error-state {
  text-align: center;
  padding: 24px;
}

.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-left-color: #1890ff;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.btn-retry {
  background-color: #1890ff;
  color: #fff;
  border: none;
  padding: 8px 16px;
  cursor: pointer;
  margin-top: 16px;
}

.empty-state {
  text-align: center;
  padding: 24px;
}

.approval-table {
  width: 100%;
  border-collapse: collapse;
}

.approval-table th, .approval-table td {
  padding: 8px;
  text-align: left;
}

.approval-table th {
  background-color: #f0f0f0;
}

.approval-table .btn-view {
  background-color: #1890ff;
  color: #fff;
  border: none;
  padding: 4px 8px;
  cursor: pointer;
}
</style> 