import request from './axios';

// 获取新闻列表
export function getNews(params) {
  return request({
    url: '/api/notices/news',
    method: 'get',
    params
  });
}

// 获取通知列表
export function getNotices(params) {
  return request({
    url: '/api/notices',
    method: 'get',
    params
  });
}

// 获取通知详情
export function getNoticeDetail(id) {
  return request({
    url: `/api/notices/${id}`,
    method: 'get'
  });
}

// 创建通知
export function createNotice(data) {
  return request({
    url: '/api/notices',
    method: 'post',
    data
  });
}

// 更新通知
export function updateNotice(id, data) {
  return request({
    url: `/api/notices/${id}`,
    method: 'put',
    data
  });
}

// 删除通知
export function deleteNotice(id) {
  return request({
    url: `/api/notices/${id}`,
    method: 'delete'
  });
}

// 标记通知为已读
export function markNoticeAsRead(id) {
  return request({
    url: `/api/notices/${id}/read`,
    method: 'put'
  });
}

// 获取未读通知数量
export function getUnreadNoticeCount() {
  return request({
    url: '/api/notices/unread/count',
    method: 'get'
  });
} 