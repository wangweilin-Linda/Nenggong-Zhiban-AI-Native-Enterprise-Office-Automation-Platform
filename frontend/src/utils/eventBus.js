import mitt from 'mitt';

// 创建一个事件总线实例
const emitter = mitt();

// 增强事件处理功能
const originalEmit = emitter.emit;
emitter.emit = function(type, event) {
  try {
    console.log(`[EventBus] 发送事件: ${type}`, event);
    const result = originalEmit.call(this, type, event);
    console.log(`[EventBus] 事件 ${type} 发送完成`);
    return result;
  } catch (error) {
    console.error(`[EventBus] 发送事件 ${type} 时出错:`, error);
    // 继续抛出错误，以便上层可以处理
    throw error;
  }
};

const originalOn = emitter.on;
emitter.on = function(type, handler) {
  try {
    console.log(`[EventBus] 注册监听: ${type}`);
    return originalOn.call(this, type, handler);
  } catch (error) {
    console.error(`[EventBus] 注册监听 ${type} 时出错:`, error);
    throw error;
  }
};

const originalOff = emitter.off;
emitter.off = function(type, handler) {
  try {
    console.log(`[EventBus] 移除监听: ${type}`);
    return originalOff.call(this, type, handler);
  } catch (error) {
    console.error(`[EventBus] 移除监听 ${type} 时出错:`, error);
    throw error;
  }
};

// 添加调试方法
emitter.debug = {
  // 获取所有已注册的事件类型
  getRegisteredEvents() {
    return Object.keys(emitter.all);
  },
  
  // 输出所有注册的事件信息
  logAllEvents() {
    console.log('[EventBus] 当前注册的所有事件:', Object.keys(emitter.all));
    
    for (const [type, handlers] of Object.entries(emitter.all)) {
      console.log(`[EventBus] 事件类型: ${type}, 处理器数量: ${handlers.length}`);
    }
  }
};

// 全局可用的事件总线实例
export default emitter;