import axios from 'axios';
import { apiBaseUrl } from '../config';

const API_URL = `${apiBaseUrl}/smart-agent`;

/**
 * 处理用户输入，返回智能代理的处理结果
 * @param {string} input - 用户输入的文本
 * @param {Object} context - 上下文信息，如当前页面、用户状态等
 * @returns {Promise<Object>} - 智能代理处理结果
 */
export const processUserInput = async (input, context = {}) => {
  try {
    const response = await axios.post(`${API_URL}/process`, {
      input,
      context
    });
    return response.data;
  } catch (error) {
    console.error('处理用户输入失败:', error);
    throw new Error(error.response?.data?.detail || '智能代理服务暂不可用');
  }
};

/**
 * 获取表单智能填充建议
 * @param {string} formId - 表单ID
 * @param {Object} formData - 当前表单数据
 * @returns {Promise<Object>} - 填充建议
 */
export const getFormSuggestions = async (formId, formData = {}) => {
  try {
    const response = await axios.post(`${API_URL}/suggestions`, {
      form_id: formId,
      form_data: formData
    });
    return response.data;
  } catch (error) {
    console.error('获取表单建议失败:', error);
    throw new Error(error.response?.data?.detail || '智能建议服务暂不可用');
  }
};

/**
 * 执行智能表单填充
 * @param {string} formId - 表单ID 
 * @param {Object} formData - 当前表单数据
 * @param {string} userPrompt - 用户输入的提示
 * @returns {Promise<Object>} - 增强的表单数据
 */
export const smartFormFill = async (formId, formData = {}, userPrompt = "") => {
  try {
    // 首先处理用户输入
    let enhancedData = { ...formData };
    
    if (userPrompt) {
      // 如果有用户提示，先处理用户输入
      const processResult = await processUserInput(userPrompt, {
        form_id: formId,
        current_form_data: formData
      });
      
      if (processResult.success && processResult.form_data) {
        // 合并处理结果到表单数据
        enhancedData = {
          ...enhancedData,
          ...processResult.form_data
        };
      }
    }
    
    // 然后获取额外的智能建议
    const suggestions = await getFormSuggestions(formId, enhancedData);
    
    // 合并智能建议中的字段
    if (suggestions && suggestions.fields) {
      enhancedData = {
        ...enhancedData,
        ...suggestions.fields
      };
    }
    
    return {
      enhancedFormData: enhancedData,
      suggestions: suggestions || {}
    };
  } catch (error) {
    console.error('智能表单填充失败:', error);
    throw new Error(error.response?.data?.detail || '智能填充服务暂不可用');
  }
};

export default {
  processUserInput,
  getFormSuggestions,
  smartFormFill
}; 