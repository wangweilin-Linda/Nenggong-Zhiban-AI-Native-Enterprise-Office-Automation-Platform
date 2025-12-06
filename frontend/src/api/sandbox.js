import request from '@/utils/request'
import axios from 'axios'

export function analyzeFile(data) {
  return request({
    url: '/api/sandbox/upload',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 120000,
    validateStatus: function (status) {
      return status >= 200 && status < 300;
    }
  })
}

export function startAnalysis(taskId, params) {
  return request({
    url: `/api/sandbox/${taskId}/analyze`,
    method: 'post',
    data: params,
    timeout: 120000
  });
}

export const getAnalysisResult = async (taskId) => {
  return request({
    url: `/api/sandbox/result/${taskId}`,
    method: 'get',
    timeout: 30000
  });
};

export const getTaskStatus = async (taskId) => {
  return request({
    url: `/api/sandbox/status/${taskId}`,
    method: 'get',
    timeout: 30000
  });
};

// 创建一个自定义的axios实例，专门用于聊天请求
export const chatRequest = (data) => {
  return axios({
    url: '/api/sandbox/chat',
    method: 'post',
    data,
    timeout: 60000,
  })
}