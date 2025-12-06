import request from '@/utils/request'

// 获取文档列表
export function getDocuments(params) {
  // 确保使用正确的排序字段
  if (params && params.sort_by === 'publish_time') {
    params.sort_by = 'created_at';
  }
  
  return request({
    url: '/api/documents/list',
    method: 'get',
    params
  }).then(response => {
    return processDocumentResponse(response);
  });
}

// 获取文档详情
export function getDocument(id) {
  return request({
    url: `/api/documents/${id}`,
    method: 'get'
  })
}

// 下载文档附件
export function downloadAttachment(filename) {
  return request({
    url: `/api/documents/attachment/${filename}`,
    method: 'get',
    responseType: 'blob'
  })
}

// 上传文档
export function uploadDocument(data) {
  return request({
    url: '/api/documents/upload',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 创建文档
export function createDocument(data) {
  return request({
    url: '/api/documents/create',
    method: 'post',
    data
  })
}

// 更新文档
export function updateDocument(id, data) {
  return request({
    url: `/api/documents/${id}`,
    method: 'put',
    data
  })
}

// 删除文档
export function deleteDocument(id) {
  return request({
    url: `/api/documents/${id}`,
    method: 'delete'
  })
}

// 获取文档分类
export function getDocumentCategories() {
  return request({
    url: '/api/documents/categories',
    method: 'get'
  })
}

// 获取文档类型
export function getDocumentTypes() {
  return request({
    url: '/api/documents/types',
    method: 'get'
  })
}

// 处理返回的数据格式，将后端返回的items改为documents
export function processDocumentResponse(response) {
  if (response && response.items) {
    return {
      documents: response.items,
      total_pages: response.pages || Math.ceil(response.total / response.size) || 1,
      total: response.total || 0,
      current_page: response.page || 1,
      size: response.size || 10
    };
  }
  return {
    documents: [],
    total_pages: 0,
    total: 0,
    current_page: 1,
    size: 10
  };
} 