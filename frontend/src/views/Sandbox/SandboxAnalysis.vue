<template>
  <div class="sandbox-analysis">
    <a-card title="数据分析沙盒" :bordered="false">
      <div class="security-notice">
        <a-alert
          message="注意：上传的文件将在完全隔离的安全环境下分析"
          type="info"
          show-icon
          class="mb-4"
        />
      </div>

      <!-- 聊天界面替换原有提示词输入区域 -->
      <div class="chat-container">
        <div class="chat-messages" ref="chatMessagesRef">
          <div v-if="messages.length === 0" class="empty-chat">
            <p>请上传CSV文件并描述您想要进行的数据分析</p>
            <p class="examples-title">示例提示:</p>
            <div class="examples-list">
              <p v-for="(example, index) in promptExamples" :key="index" 
                 @click="usePromptExample(example)" class="example-item">
                {{ example }}
              </p>
            </div>
          </div>
          <div v-for="(message, index) in messages" :key="index" 
               :class="['message-item', message.type === 'user' ? 'user-message' : 'agent-message']">
            <div class="message-avatar">
              <UserOutlined v-if="message.type === 'user'" />
              <RobotOutlined v-else />
            </div>
            <div class="message-content" v-html="message.content"></div>
          </div>
          <div v-if="isThinking" class="message-item agent-message">
            <div class="message-avatar">
              <RobotOutlined />
            </div>
            <div class="message-content thinking">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>

        <div class="chat-input">
        <a-textarea
            v-model:value="userInput"
            placeholder="描述您想要的数据分析，例如：'找出销售额最高的三个地区'"
            :rows="2"
            :disabled="isThinking || !selectedFile"
            @pressEnter.prevent="sendMessage"
        />
          <a-button 
            type="primary"
            :disabled="!userInput.trim() || isThinking || !selectedFile"
            @click="sendMessage"
            class="send-button"
          >
            <SendOutlined />
          </a-button>
        </div>
      </div>

      <!-- 文件上传区域 -->
      <div class="upload-section">
        <a-upload
          :customRequest="handleFileSelect"
          :showUploadList="true"
          accept=".csv"
          :multiple="false"
          name="file"
          :disabled="loading"
          :fileList="fileList"
          @remove="handleFileRemove"
        >
          <a-button :disabled="loading">
            <upload-outlined />
            上传CSV文件
          </a-button>
          <template #tip>
            <div class="ant-upload-tip">
              支持上传 .csv 格式的文件
            </div>
          </template>
        </a-upload>

        <a-button 
          type="primary" 
          class="start-analysis-btn" 
          :disabled="!selectedFile || loading || (messages.length > 1 && !analysisReady)" 
          :loading="loading"
          @click="startFileAnalysis"
        >
          {{ loading ? '分析中...' : '开始分析' }}
        </a-button>
      </div>

      <!-- 加载中状态 -->
      <div v-if="loading" class="loading-container mt-4">
        <a-spin tip="数据分析中...">
          <div class="loading-content">
            <p>正在处理您的数据，这可能需要一点时间...</p>
          </div>
        </a-spin>
      </div>

      <!-- 分析结果展示区域 -->
      <div v-if="!loading && analysisResults" class="analysis-results mt-4">
        <a-descriptions title="基本信息" bordered>
          <a-descriptions-item label="行数">{{ analysisResults.row_count || 'N/A' }}</a-descriptions-item>
          <a-descriptions-item label="列数">{{ analysisResults.column_count || 'N/A' }}</a-descriptions-item>
        </a-descriptions>

        <!-- 数值型列统计 -->
        <a-collapse v-if="analysisResults.summary" class="mt-4">
          <a-collapse-panel key="1" header="数值型列统计">
            <div v-for="(stats, column) in analysisResults.summary" :key="column">
              <h4>{{ column }}</h4>
              <a-descriptions bordered size="small">
                <a-descriptions-item label="平均值">{{ stats.mean?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="中位数">{{ stats.median?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="标准差">{{ stats.std?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="最小值">{{ stats.min?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="最大值">{{ stats.max?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="Q1">{{ stats.q1?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="Q3">{{ stats.q3?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="IQR">{{ stats.iqr?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="有效数据">{{ stats.count || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item label="缺失值">{{ stats.missing || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item v-if="stats.skewness !== undefined" label="偏度">{{ stats.skewness?.toFixed(2) || 'N/A' }}</a-descriptions-item>
                <a-descriptions-item v-if="stats.kurtosis !== undefined" label="峰度">{{ stats.kurtosis?.toFixed(2) || 'N/A' }}</a-descriptions-item>
              </a-descriptions>
              
              <!-- 图表展示区域 -->
              <div class="charts-container mt-3">
                <!-- 描述信息 -->
                <div class="chart-description">
                  <a-alert v-if="getColumnData(column)?.descriptions?.summary" 
                    :message="getColumnData(column)?.descriptions?.summary" 
                    type="info" 
                    showIcon 
                    class="mb-2" />
                </div>
                
                <!-- 多图表展示 -->
                <div class="multi-charts-grid">
                  <!-- 直方图 -->
                  <div class="chart-item">
                    <h5>直方图</h5>
                    <v-chart v-if="getColumnData(column)?.histogram" :option="createHistogramOption(column)" autoresize class="chart" />
                    <div v-else class="no-chart-message">直方图数据不可用</div>
                    <div class="chart-description-text">{{ getColumnData(column)?.descriptions?.histogram || '' }}</div>
                  </div>
                  
                  <!-- 箱线图 -->
                  <div class="chart-item">
                    <h5>箱线图</h5>
                    <v-chart v-if="getColumnData(column)?.boxplot" :option="createBoxplotOption(column)" autoresize class="chart" />
                    <div v-else class="no-chart-message">箱线图数据不可用</div>
                    <div class="chart-description-text">{{ getColumnData(column)?.descriptions?.boxplot || '' }}</div>
                  </div>
                  
                  <!-- 散点图 -->
                  <div class="chart-item">
                    <h5>散点图</h5>
                    <v-chart v-if="getColumnData(column)?.scatter" :option="createScatterOption(column)" autoresize class="chart" />
                    <div v-else class="no-chart-message">散点图数据不可用</div>
                    <div class="chart-description-text">{{ getColumnData(column)?.descriptions?.scatter || '' }}</div>
                  </div>
                  
                  <!-- 趋势图 -->
                  <div class="chart-item">
                    <h5>趋势图</h5>
                    <v-chart v-if="getColumnData(column)?.trend" :option="createTrendOption(column)" autoresize class="chart" />
                    <div v-else class="no-chart-message">趋势图数据不可用</div>
                    <div class="chart-description-text">{{ getColumnData(column)?.descriptions?.trend || '' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </a-collapse-panel>
        </a-collapse>

        <!-- 相关性分析 -->
        <a-collapse v-if="analysisResults.correlations" class="mt-4">
          <a-collapse-panel key="3" header="相关性分析">
            <div class="correlation-container">
              <!-- 相关性热力图 -->
              <div v-if="hasCorrelationData" class="heatmap-container">
                <h4>相关性热力图</h4>
                <v-chart :option="createCorrelationHeatmapOption()" autoresize class="correlation-chart" />
              </div>
              
              <!-- 强相关变量列表 -->
              <div v-if="analysisResults.correlations.strong_correlations && analysisResults.correlations.strong_correlations.length > 0" class="strong-correlations mt-3">
                <h4>强相关变量</h4>
                <a-list bordered>
                  <a-list-item v-for="(item, index) in analysisResults.correlations.strong_correlations" :key="index">
                    <a-tag :color="getCorrelationColor(item.correlation)">
                      {{ item.correlation.toFixed(2) }}
                    </a-tag>
                    {{ item.var1 }} 与 {{ item.var2 }}
                    <div class="correlation-description">
                      {{ item.description || `相关系数: ${item.correlation.toFixed(2)}` }}
                    </div>
                  </a-list-item>
                </a-list>
              </div>
              
              <div v-if="!hasCorrelationData" class="no-chart-message">
                相关性数据不可用或只有一个数值型变量
              </div>
            </div>
          </a-collapse-panel>
        </a-collapse>

        <!-- 缺失值统计 -->
        <a-collapse class="mt-4">
          <a-collapse-panel key="4" header="缺失值统计">
            <div v-if="missingValuesData.length > 0">
              <a-table :dataSource="missingValuesData" :columns="missingValuesColumns" />
            </div>
            <div v-else class="no-missing-values">
              <a-empty description="没有检测到缺失值" />
            </div>
          </a-collapse-panel>
        </a-collapse>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { message } from 'ant-design-vue'
import { UploadOutlined, UserOutlined, RobotOutlined, SendOutlined } from '@ant-design/icons-vue'
import { analyzeFile, startAnalysis, getAnalysisResult, getTaskStatus, chatRequest } from '@/api/sandbox'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, ScatterChart, BoxplotChart, HeatmapChart } from 'echarts/charts'
import { 
  GridComponent, 
  TooltipComponent, 
  TitleComponent, 
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  DataZoomComponent,
  VisualMapComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import axios from 'axios'

// 注册ECharts组件
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  ScatterChart,
  BoxplotChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  DataZoomComponent,
  VisualMapComponent
])

const analysisResults = ref(null)
const loading = ref(false)
const fileList = ref([])
const selectedFile = ref(null)

// 聊天相关状态
const messages = ref([])
const userInput = ref('')
const isThinking = ref(false)
const chatMessagesRef = ref(null)
const analysisReady = ref(false)
const finalPrompt = ref('')

const promptExamples = [
  '找出销售额最高的三个地区',
  '分析各地区销售额和利润的关系',
  '计算各地区的利润率并排序',
  '识别销售额异常偏低的地区',
  '生成销售额和利润的相关性分析'
]

// 使用示例提示
const usePromptExample = (example) => {
  userInput.value = example
}

// 滚动到聊天底部
const scrollToBottom = async () => {
  await nextTick()
  if (chatMessagesRef.value) {
    chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
  }
}

// 监听消息变化，自动滚动
watch(messages, () => {
  scrollToBottom()
})

// 格式化文本为HTML
const formatMessage = (text) => {
  if (!text) return ''
  
  try {
    // 处理可能的JSON字符串
    if (typeof text === 'string' && (text.startsWith('{') || text.startsWith('['))) {
      try {
        const parsed = JSON.parse(text)
        text = typeof parsed === 'string' ? parsed : JSON.stringify(parsed, null, 2)
      } catch (e) {
        // 如果不是有效的JSON，保持原始文本
        console.log('不是有效的JSON格式，保持原始文本')
      }
    }
    
    // 转换换行符
    let formatted = String(text).replace(/\\n/g, '\n').replace(/\n/g, '<br>')
    
    // 转换代码块
    formatted = formatted.replace(/```([^`]+)```/g, '<pre class="code-block">$1</pre>')
    
    // 转换粗体
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    
    return formatted
  } catch (e) {
    console.error('格式化消息出错:', e)
    return String(text) // 返回原始文本的字符串形式
  }
}

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isThinking.value) return
  
  // 添加用户消息
  const userMessage = userInput.value.trim()
  messages.value.push({
    type: 'user',
    content: formatMessage(userMessage)
  })
  
  userInput.value = ''
  isThinking.value = true
  
  try {
    // 去除HTML标签，准备消息历史数据
    const plainHistory = messages.value.map(m => ({
      role: m.type === 'user' ? 'user' : 'assistant',
      content: m.content.replace(/<[^>]*>/g, '') // 去除HTML标签
    }))
    
    console.log('发送请求到后端:', {
      message: userMessage,
      history: plainHistory,
      has_file: !!selectedFile.value
    })
    
    // 调用后端API发送消息获取响应
    const response = await chatRequest({
      message: userMessage,
      history: plainHistory,
      has_file: !!selectedFile.value
    })
    
    console.log('收到后端响应:', response.data)
    
    if (response.data) {
      // 确保response存在，即使结构不完全匹配预期
      const responseText = response.data.response || 
                          (typeof response.data === 'string' ? response.data : JSON.stringify(response.data))
      
      // 添加代理回复
      messages.value.push({
        type: 'agent',
        content: formatMessage(responseText)
      })
      
      // 检查是否可以开始分析
      const isAnalysisReady = response.data.analysis_ready === true || false
      if (isAnalysisReady) {
        analysisReady.value = true
        finalPrompt.value = response.data.final_prompt || userMessage
      }
    } else {
      throw new Error('响应数据为空')
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    console.error('错误详情:', error.response || error.message || error)
    message.error('与AI代理通信失败，请稍后重试')
    
    // 添加错误消息，但避免重复添加
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage?.type !== 'agent' || !lastMessage?.content?.includes('分析过程中遇到了错误')) {
      messages.value.push({
        type: 'agent',
        content: '很抱歉，分析过程中遇到了错误。请稍后重试。'
      })
    }
  } finally {
    isThinking.value = false
  }
}

// 处理文件选择
const handleFileSelect = async ({ file }) => {
  selectedFile.value = file
  fileList.value = [{ 
    uid: '1', 
    name: file.name,
    status: 'done',
    size: file.size
  }]
  
  // 添加初始代理消息（如果没有消息）
  if (messages.value.length === 0) {
    messages.value = []  // 先清空消息
    messages.value.push({
      type: 'agent',
      content: `您好！我已看到您上传了 <strong>${file.name}</strong> 文件。请告诉我您想要进行什么样的数据分析？`
    })
  }
}

// 处理文件移除
const handleFileRemove = () => {
  selectedFile.value = null
  fileList.value = []
  // 重置对话状态
  messages.value = []
  analysisReady.value = false
  finalPrompt.value = ''
}

// 开始文件分析
const startFileAnalysis = async () => {
  if (!selectedFile.value) {
    message.warning('请先选择要分析的文件')
    return
  }
  
  // 检查是否处于对话模式但未完成交互
  if (messages.value.length > 1 && !analysisReady.value) {
    message.warning('请先完成与AI助手的交互')
    return
  }
  
  loading.value = true
  analysisResults.value = null
  
  let taskId = null
  
  try {
    // 创建表单数据
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    // 上传文件并获取任务ID
    console.log('开始上传文件...')
    const response = await analyzeFile(formData)
    
    if (response.data && response.data.task_id) {
      taskId = response.data.task_id
      console.log(`文件上传成功，任务ID: ${taskId}`)
      
      // 添加分析开始消息
      if (messages.value.length > 1) {
        messages.value.push({
          type: 'agent',
          content: '分析任务已启动，正在处理您的数据，请耐心等待...'
        })
      }
      
      // 启动分析任务，使用最终提示词或无提示词
      console.log('开始执行分析...')
      const promptToUse = messages.value.length > 1 ? finalPrompt.value : undefined
      console.log('使用的提示词:', promptToUse)
      
      try {
        await startAnalysis(taskId, { 
          prompt: promptToUse
        })
        console.log('分析任务已成功启动')
      } catch (analysisError) {
        console.error('启动分析任务失败:', analysisError)
        
        // 不显示错误消息，因为可能只是短暂的失败，我们会继续尝试轮询结果
        console.log('尽管启动失败，仍将尝试获取结果...')
      }
      
      // 无论启动是否成功，都尝试轮询结果
      if (taskId) {
        try {
          await pollForResults(taskId)
          
          // 添加分析完成消息
          if (messages.value.length > 1 && analysisResults.value) {
            messages.value.push({
              type: 'agent',
              content: '分析已完成，结果已显示在下方。'
            })
          }
        } catch (pollError) {
          console.error('轮询结果失败:', pollError)
          message.error('获取分析结果失败: ' + (pollError.message || String(pollError)))
        }
      }
    } else {
      message.error('文件上传成功，但未获取到任务ID')
    }
  } catch (error) {
    console.error("文件上传错误:", error)
    message.error('文件上传失败：' + (error.message || String(error)))
    
    // 添加错误消息
    if (messages.value.length > 1) {
      messages.value.push({
        type: 'agent',
        content: '很抱歉，分析过程中遇到了错误。请稍后重试。'
      })
    }
  } finally {
    // 如果有任务ID但没有获取到结果，再次尝试轮询
    if (taskId && !analysisResults.value) {
      console.log('最终尝试获取结果...')
      try {
        // 延迟5秒后再次尝试
        await new Promise(resolve => setTimeout(resolve, 5000))
        await pollForResults(taskId)
      } catch (finalError) {
        console.error('最终尝试获取结果失败:', finalError)
      }
    }
    
    loading.value = false
  }
}

// 轮询获取分析结果
const pollForResults = async (taskId) => {
  try {
    const maxAttempts = 120 // 最多轮询120次（4分钟）
    const delayMs = 2000 // 每次轮询间隔2秒
    let attempts = 0
    let resultData = null
    let consecutiveErrors = 0 // 连续错误计数
    
    console.log(`开始轮询分析结果，任务ID: ${taskId}，最多轮询${maxAttempts}次`)
    
    while (!resultData && attempts < maxAttempts && consecutiveErrors < 5) {
      attempts++
      await new Promise(resolve => setTimeout(resolve, delayMs))
      
      try {
        console.log(`轮询尝试 ${attempts}/${maxAttempts}`)
        const res = await getAnalysisResult(taskId)
        
        // 重置连续错误计数
        consecutiveErrors = 0
        
        if (res.data) {
          resultData = res.data
          console.log('成功获取分析结果！')
          break
        }
      } catch (err) {
        consecutiveErrors++
        console.log(`轮询尝试 ${attempts} 失败: ${err.message}，连续错误: ${consecutiveErrors}`)
        
        // 检查是否是500错误（服务器内部错误）
        if (err.response && err.response.status === 500) {
          console.log('检测到服务器内部错误，可能是任务已失败但结果未保存')
          
          // 如果连续5次500错误，停止轮询
          if (consecutiveErrors >= 5) {
            message.error('分析任务失败，服务器返回内部错误')
            console.error('连续5次服务器内部错误，停止轮询')
            break
          }
        }
        
        // 如果是超时错误，增加延迟时间
        if (err.message.includes('timeout')) {
          await new Promise(resolve => setTimeout(resolve, 3000)) // 额外等待3秒
        }
      }
    }
    
    if (!resultData) {
      if (consecutiveErrors >= 5) {
        message.error('分析任务失败，请检查后端日志以获取详细错误信息')
      } else if (attempts >= maxAttempts) {
        message.warning('获取结果超时，请稍后刷新页面查看')
      }
      return null
    }
    
    if (resultData) {
      analysisResults.value = resultData
      console.log('分析结果已加载到界面')
      return resultData
    }
    
  } catch (error) {
    console.error("Analysis error:", error)
    message.error('分析失败：' + (error.message || String(error)))
    throw error
  } finally {
    loading.value = false
  }
}

// 获取可视化数据的辅助函数
const getColumnData = (column) => {
  if (!analysisResults.value || !analysisResults.value.visualization_data) return null
  return analysisResults.value.visualization_data[column]
}

// 创建直方图配置
const createHistogramOption = (column) => {
  const data = getColumnData(column)
  if (!data || !data.histogram) return null
  
  const { bins, frequencies } = data.histogram
  const categories = []
  
  // 生成区间标签
  for (let i = 0; i < bins.length - 1; i++) {
    categories.push(`${bins[i].toFixed(2)}~${bins[i+1].toFixed(2)}`)
  }
  
  return {
    title: {
      text: `${column} 的分布`,
      left: 'center',
      textStyle: {
        fontWeight: 'bold',
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const index = params[0].dataIndex
        return `${categories[index]}<br/>频数: ${frequencies[index]}`
      }
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisTick: {
        alignWithLabel: true
      },
      axisLabel: {
        interval: Math.ceil(categories.length / 10), // 自动调整标签显示间隔
        rotate: categories.length > 10 ? 45 : 0,
        formatter: function(value) {
          // 如果太长则截断
          if (value.length > 10) {
            return value.substring(0, 10) + '...'
          }
          return value
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '频数'
    },
    dataZoom: [{
      type: 'inside',
      start: 0,
      end: 100
    }, {
      start: 0,
      end: 100
    }],
    series: [
      {
        data: frequencies,
        type: 'bar',
        itemStyle: {
          color: '#5975a4',
          // 高亮颜色
          emphasis: {
            color: '#1890ff'
          }
        },
        // 平均线
        markLine: {
          data: [
            {
              name: '平均值',
              yAxis: analysisResults.value.summary[column].mean,
              lineStyle: {
                color: '#ff7070',
                type: 'dashed',
                width: 2
              },
              label: {
                formatter: '平均值: {c}',
                position: 'middle'
              }
            }
          ]
        }
      }
    ],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    }
  }
}

// 创建箱线图配置
const createBoxplotOption = (column) => {
  const data = getColumnData(column)
  if (!data || !data.boxplot) return null
  
  const { min, q1, median, q3, max, outliers } = data.boxplot
  
  return {
    title: {
      text: `${column} 的箱线图`,
      left: 'center',
      textStyle: {
        fontWeight: 'bold',
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        if (params.seriesName === '异常值') {
          return `异常值: ${params.data[1].toFixed(2)}`
        }
        return `<div>最小值: ${min.toFixed(2)}</div>
                <div>Q1: ${q1.toFixed(2)}</div>
                <div>中位数: ${median.toFixed(2)}</div>
                <div>Q3: ${q3.toFixed(2)}</div>
                <div>最大值: ${max.toFixed(2)}</div>`
      }
    },
    xAxis: {
      type: 'category',
      data: [column],
      boundaryGap: true,
      nameGap: 30,
      splitArea: {
        show: false
      },
      axisLabel: {
        show: true
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      name: '值',
      splitArea: {
        show: true
      }
    },
    series: [
      {
        name: '箱线图',
        type: 'boxplot',
        data: [
          [min, q1, median, q3, max]
        ],
        itemStyle: {
          color: '#5f9e6e',
          borderColor: '#666',
        },
        tooltip: {
          formatter: function(param) {
            return [
              `${column}:`,
              `最大值: ${param.data[4].toFixed(2)}`,
              `上四分位: ${param.data[3].toFixed(2)}`,
              `中位数: ${param.data[2].toFixed(2)}`,
              `下四分位: ${param.data[1].toFixed(2)}`,
              `最小值: ${param.data[0].toFixed(2)}`
            ].join('<br/>')
          }
        }
      },
      {
        name: '异常值',
        type: 'scatter',
        data: outliers.map(value => [0, value]),
        itemStyle: {
          color: '#b55d60',
        }
      }
    ],
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '15%'
    }
  }
}

// 创建散点图配置
const createScatterOption = (column) => {
  const data = getColumnData(column)
  if (!data || !data.scatter) return null
  
  const values = data.scatter.values
  const points = values.map((value, index) => [index, value])
  
  return {
    title: {
      text: `${column} 的散点分布`,
      left: 'center',
      textStyle: {
        fontWeight: 'bold',
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        return `索引: ${params.data[0]}<br/>值: ${params.data[1].toFixed(2)}`
      }
    },
    xAxis: {
      type: 'value',
      name: '数据点索引',
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      name: column
    },
    dataZoom: [{
      type: 'inside',
      start: 0,
      end: 100
    }, {
      start: 0,
      end: 100
    }],
    series: [
      {
        type: 'scatter',
        data: points,
        itemStyle: {
          color: '#857aab',
        },
        symbolSize: 8,
        markLine: {
          data: [
            {
              name: '平均值',
              yAxis: analysisResults.value.summary[column].mean,
              lineStyle: {
                color: '#ff7070',
                type: 'dashed',
                width: 2
              },
              label: {
                formatter: '平均值: {c}',
                position: 'middle'
              }
            }
          ]
        }
      }
    ],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    }
  }
}

// 创建趋势图配置
const createTrendOption = (column) => {
  const data = getColumnData(column)
  if (!data || !data.trend) return null
  
  const values = data.trend.values
  const points = values.map((value, index) => [index, value])
  
  return {
    title: {
      text: `${column} 的排序分布`,
      left: 'center',
      textStyle: {
        fontWeight: 'bold',
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        return `索引: ${params[0].data[0]}<br/>值: ${params[0].data[1].toFixed(2)}`
      }
    },
    xAxis: {
      type: 'value',
      name: '排序后索引',
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      name: column
    },
    dataZoom: [{
      type: 'inside',
      start: 0,
      end: 100
    }, {
      start: 0,
      end: 100
    }],
    series: [
      {
        type: 'line',
        smooth: true,
        data: points,
        itemStyle: {
          color: '#6d9cab',
        },
        lineStyle: {
          width: 2
        },
        markLine: {
          data: [
            {
              name: '平均值',
              yAxis: analysisResults.value.summary[column].mean,
              lineStyle: {
                color: '#ff7070',
                type: 'dashed',
                width: 2
              },
              label: {
                formatter: '平均值: {c}',
                position: 'middle'
              }
            }
          ]
        }
      }
    ],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    }
  }
}

// 创建相关性热力图配置
const hasCorrelationData = computed(() => {
  return analysisResults.value 
    && analysisResults.value.correlations 
    && analysisResults.value.correlations.columns 
    && analysisResults.value.correlations.columns.length > 1
})

const createCorrelationHeatmapOption = () => {
  if (!hasCorrelationData.value) return null
  
  const { columns, matrix } = analysisResults.value.correlations
  
  // 构建热力图数据
  const data = []
  for (let i = 0; i < columns.length; i++) {
    const rowData = matrix[columns[i]] || {}
    for (let j = 0; j < columns.length; j++) {
      const value = rowData[columns[j]] || null
      if (value !== null) {
        data.push([i, j, value.toFixed(2)])
      }
    }
  }
  
  return {
    title: {
      text: '变量相关性热力图',
      left: 'center',
      textStyle: {
        fontWeight: 'bold',
      }
    },
    tooltip: {
      position: 'top',
      formatter: function (params) {
        return `${columns[params.data[0]]} 与 ${columns[params.data[1]]} 的相关性: ${params.data[2]}`
      }
    },
    grid: {
      left: '3%',
      right: '7%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: columns,
      splitArea: {
        show: true
      },
      axisLabel: {
        interval: 0,
        rotate: 45
      }
    },
    yAxis: {
      type: 'category',
      data: columns,
      splitArea: {
        show: true
      }
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#d73027', '#f7f7f7', '#1a9850'],
      },
      controller: {
        inRange: {
          symbol: 'rect'
        }
      }
    },
    series: [{
      name: '相关性',
      type: 'heatmap',
      data: data,
      label: {
        show: true,
        formatter: function(params) {
          return params.data[2];
        }
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }
}

// 根据相关系数获取颜色
const getCorrelationColor = (correlation) => {
  const absCorr = Math.abs(correlation)
  if (absCorr > 0.9) return correlation > 0 ? '#1a9850' : '#d73027'
  if (absCorr > 0.7) return correlation > 0 ? '#91cf60' : '#fc8d59'
  if (absCorr > 0.5) return correlation > 0 ? '#d9ef8b' : '#fee08b'
  return '#f7f7f7'
}

const missingValuesData = computed(() => {
  if (!analysisResults.value) return []
  
  const totalRows = analysisResults.value.row_count || 0
  const missingData = []
  
  // 从summary中提取缺失值信息
  if (analysisResults.value.summary) {
    for (const column in analysisResults.value.summary) {
      const stats = analysisResults.value.summary[column]
      
      if (stats.missing && stats.missing > 0) {
        missingData.push({
          column,
          count: stats.missing,
          percentage: `${((stats.missing / totalRows) * 100).toFixed(2)}%`,
          key: column
        })
      }
    }
  }
  
  return missingData
})

// 获取列的缺失值数量
const getMissingCount = (column) => {
  if (!analysisResults.value || !analysisResults.value.summary) return 0
  
  const columnData = analysisResults.value.summary[column]
  return columnData?.missing || 0
}

const missingValuesColumns = [
  {
    title: '列名',
    dataIndex: 'column',
    key: 'column',
  },
  {
    title: '缺失值数量',
    dataIndex: 'count',
    key: 'count',
  },
  {
    title: '缺失值比例',
    dataIndex: 'percentage',
    key: 'percentage',
  }
]
</script>

<style scoped>
.sandbox-analysis {
  padding: 24px;
}

/* 聊天界面样式 */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 400px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  background-color: #fff;
  margin-bottom: 24px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background-color: #f9f9f9;
}

.message-item {
  display: flex;
  margin-bottom: 16px;
  max-width: 85%;
}

.user-message {
  margin-left: auto;
  flex-direction: row-reverse;
}

.agent-message {
  margin-right: auto;
}

.message-avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #e6f7ff;
  color: #1890ff;
  border-radius: 50%;
  margin: 0 8px;
}

.user-message .message-avatar {
  background-color: #f0f7ff;
  color: #108ee9;
}

.message-content {
  padding: 12px;
  border-radius: 8px;
  background-color: #e6f7ff;
  position: relative;
  word-break: break-word;
}

.user-message .message-content {
  background-color: #1890ff;
  color: white;
}

.thinking {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  min-height: 32px;
}

.dot {
  width: 8px;
  height: 8px;
  margin: 0 3px;
  background-color: #1890ff;
  border-radius: 50%;
  display: inline-block;
  animation: dot-flashing 1s infinite alternate;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes dot-flashing {
  0% {
    opacity: 0.2;
  }
  100% {
    opacity: 1;
  }
}

.chat-input {
  display: flex;
  padding: 12px;
  border-top: 1px solid #e8e8e8;
}

.chat-input textarea {
  flex: 1;
  resize: none;
  border-radius: 4px;
}

.send-button {
  margin-left: 8px;
  align-self: flex-end;
}

.empty-chat {
  text-align: center;
  color: #999;
  padding: 30px 0;
}

.examples-title {
  font-weight: bold;
  margin-top: 16px;
  color: #666;
}

.examples-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.example-item {
  cursor: pointer;
  padding: 8px 12px;
  background-color: #f0f0f0;
  border-radius: 4px;
  transition: all 0.3s;
  text-align: left;
}

.example-item:hover {
  background-color: #e0e0e0;
  color: #1890ff;
}

.code-block {
  background: #f5f5f5;
  border-radius: 4px;
  padding: 8px;
  margin: 8px 0;
  font-family: monospace;
  white-space: pre-wrap;
  font-size: 12px;
  color: #333;
}

/* 保留原有样式 */
.upload-section {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.start-analysis-btn {
  margin-left: 16px;
}

.loading-container {
  text-align: center;
  margin: 48px 0;
  padding: 24px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}

.loading-content {
  margin-top: 16px;
  color: #888;
}

.multi-charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.chart-item {
  background: #fff;
  border-radius: 4px;
  padding: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.chart-item h5 {
  margin-top: 0;
  margin-bottom: 12px;
  text-align: center;
  font-weight: bold;
  color: #333;
}

.chart {
  height: 300px;
  width: 100%;
}

.correlation-chart {
  height: 400px;
  width: 100%;
}

.chart-description-text {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
  text-align: center;
  padding: 4px 8px;
  background: #f9f9f9;
  border-radius: 2px;
}

.correlation-description {
  margin-top: 4px;
  font-size: 12px;
  color: #666;
}

.chart-container {
  border: 1px solid #f0f0f0;
  padding: 12px;
  border-radius: 4px;
  background-color: #fafafa;
  text-align: center;
  margin-top: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.no-chart-message {
  color: #999;
  font-style: italic;
  padding: 16px;
  text-align: center;
  background-color: #f5f5f5;
  border: 1px dashed #d9d9d9;
  border-radius: 4px;
  margin-top: 8px;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-missing-values {
  text-align: center;
  padding: 16px;
  background-color: #f5f5f5;
  border: 1px dashed #d9d9d9;
  border-radius: 4px;
}

.missing-data-hint {
  font-size: 12px;
  color: #ff4d4f;
  margin-left: 4px;
}

.prompt-container {
  margin-bottom: 20px;
}

.prompt-input {
  width: 100%;
  margin: 8px 0;
}

.prompt-hint {
  font-size: 12px;
  color: #666;
}

.separator {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 20px 0;
}

.separator::before,
.separator::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #ddd;
}

.separator span {
  padding: 0 10px;
  color: #666;
}

@media (max-width: 768px) {
  .multi-charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>