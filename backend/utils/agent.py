import requests
import os
import json
from typing import Optional, List, Dict, Any

def get_agent():
    """
    获取AI代理实例，优先使用Ollama本地模型
    """
    try:
        # 获取可用的Ollama模型
        models = get_available_ollama_models()
        
        if not models:
            print("未找到可用的Ollama模型，将使用模拟实现")
            return MockAgent()
        
        # 优先选择deepseek-r1:7b模型
        preferred_models = ["deepseek-r1:7b", "deepseek-coder", "llama3", "mistral"]
        selected_model = None
        
        for preferred in preferred_models:
            for model in models:
                if preferred in model.lower():
                    selected_model = model
                    break
            if selected_model:
                break
                
        # 如果没有找到首选模型，使用第一个可用的模型
        if not selected_model and models:
            selected_model = models[0]
            
        print(f"使用Ollama模型: {selected_model}")
        return OllamaAgent(selected_model)
    except Exception as e:
        print(f"初始化代理失败：{str(e)}")
        return MockAgent()

def get_available_ollama_models() -> List[str]:
    """
    获取可用的Ollama模型列表
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        return []
    except Exception as e:
        print(f"获取Ollama模型列表失败：{str(e)}")
        return []

class OllamaAgent:
    """
    使用Ollama的AI代理实现
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.base_url = "http://localhost:11434/api/generate"
        
    def chat(self, prompt: str) -> str:
        """
        与Ollama模型进行对话
        """
        try:
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 2048
                    }
                }
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                print(f"Ollama API请求失败: {response.status_code}")
                return ""
        except Exception as e:
            print(f"与Ollama模型对话失败: {str(e)}")
            return ""

class MockAgent:
    """
    模拟AI代理实现，用于在无法使用真实模型时提供基本功能
    """
    def __init__(self):
        self.name = "模拟代理"
        
    def chat(self, prompt: str) -> str:
        """
        模拟对话，返回预设的工作流示例
        """
        print("使用模拟代理响应请求")
        
        if "请假" in prompt or "休假" in prompt:
            return self._generate_leave_workflow()
        elif "采购" in prompt:
            return self._generate_purchase_workflow()
        else:
            return self._generate_default_workflow()
    
    def _generate_leave_workflow(self) -> str:
        """生成请假流程的示例"""
        return """
```workflow_description
这是一个标准的员工请假审批流程，包含以下步骤：
1. 员工提交请假申请，填写请假类型、起止时间和请假原因
2. 直接主管审批，3天以内的请假由直接主管审批后直接结束流程
3. 如果请假天数超过3天，则需要部门经理进行二次审批
4. 所有请假流程完成后，需要人力资源部进行备案

审批流程支持条件判断，根据请假天数智能路由到相应的审批节点。
```

```workflow_config
{
  "name": "员工请假审批流程",
  "description": "标准的员工请假审批流程，包含直接主管、部门经理审批和人力资源备案环节",
  "nodes": [
    {
      "id": "start",
      "name": "开始",
      "type": "start"
    },
    {
      "id": "supervisor_approval",
      "name": "直接主管审批",
      "type": "approval",
      "allowed_positions": ["team_leader", "supervisor"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "check_days",
      "name": "检查请假天数",
      "type": "condition",
      "condition": "form_data.days > 3"
    },
    {
      "id": "manager_approval",
      "name": "部门经理审批",
      "type": "approval",
      "allowed_positions": ["department_manager", "director"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "hr_record",
      "name": "人力资源备案",
      "type": "approval",
      "allowed_positions": ["hr_specialist", "hr_manager"],
      "form": {
        "comment": "备案意见"
      }
    },
    {
      "id": "end",
      "name": "结束",
      "type": "end"
    }
  ],
  "edges": [
    { "from": "start", "to": "supervisor_approval" },
    { "from": "supervisor_approval", "to": "check_days" },
    { "from": "check_days", "to": "manager_approval", "condition": "true" },
    { "from": "check_days", "to": "hr_record", "condition": "false" },
    { "from": "manager_approval", "to": "hr_record" },
    { "from": "hr_record", "to": "end" }
  ],
  "form_schema": {
    "type": "object",
    "properties": {
      "leave_type": {
        "type": "string",
        "title": "请假类型",
        "enum": ["事假", "病假", "年假", "婚假", "产假", "丧假", "其他"]
      },
      "start_date": {
        "type": "string",
        "title": "开始日期",
        "format": "date"
      },
      "end_date": {
        "type": "string",
        "title": "结束日期",
        "format": "date"
      },
      "days": {
        "type": "number",
        "title": "请假天数"
      },
      "reason": {
        "type": "string",
        "title": "请假原因",
        "maxLength": 500
      }
    },
    "required": ["leave_type", "start_date", "end_date", "days", "reason"]
  }
}
```

```mermaid
flowchart TD
    start([开始]) --> supervisor_approval{直接主管审批}
    supervisor_approval --> check_days{检查请假天数}
    check_days -->|>3天| manager_approval{部门经理审批}
    check_days -->|≤3天| hr_record{人力资源备案}
    manager_approval --> hr_record
    hr_record --> end([结束])
```
"""
    
    def _generate_purchase_workflow(self) -> str:
        """生成采购流程的示例"""
        return """
```workflow_description
这是一个多级审批的采购流程，流程步骤如下：
1. 申请人提交采购申请，填写采购物品、数量、金额等信息
2. 部门主管进行初审，对采购的必要性和合理性进行评估
3. 根据采购金额进行条件判断：
   - 金额小于5000元，由部门经理直接审批
   - 金额在5000元至20000元之间，需要财务部门进行审核
   - 金额超过20000元，需要先经过财务部门审核，再由总经理进行最终审批
4. 采购部门执行采购
5. 申请人确认收货

整个流程支持多级审批和条件分支，确保不同金额的采购申请通过相应的审批流程。
```

```workflow_config
{
  "name": "采购审批流程",
  "description": "多级审批的采购流程，根据金额进行条件判断和审批路径选择",
  "nodes": [
    {
      "id": "start",
      "name": "开始",
      "type": "start"
    },
    {
      "id": "supervisor_approval",
      "name": "部门主管初审",
      "type": "approval",
      "allowed_positions": ["supervisor", "team_leader"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "check_amount",
      "name": "检查采购金额",
      "type": "condition",
      "conditions": [
        { "id": "small", "expression": "form_data.amount < 5000" },
        { "id": "medium", "expression": "form_data.amount >= 5000 && form_data.amount <= 20000" },
        { "id": "large", "expression": "form_data.amount > 20000" }
      ]
    },
    {
      "id": "department_manager",
      "name": "部门经理审批",
      "type": "approval",
      "allowed_positions": ["department_manager", "director"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "finance_approval",
      "name": "财务部门审核",
      "type": "approval",
      "allowed_positions": ["finance_specialist", "finance_manager"],
      "form": {
        "comment": "财务审核意见",
        "budget_code": "预算编码"
      }
    },
    {
      "id": "ceo_approval",
      "name": "总经理审批",
      "type": "approval",
      "allowed_positions": ["ceo", "vp"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "purchase_execution",
      "name": "采购部门执行",
      "type": "approval",
      "allowed_positions": ["purchase_specialist", "purchase_manager"],
      "form": {
        "vendor": "供应商",
        "purchase_date": "采购日期",
        "comment": "执行备注"
      }
    },
    {
      "id": "receipt_confirmation",
      "name": "申请人确认收货",
      "type": "approval",
      "assignee_from_initiator": true,
      "form": {
        "receipt_date": "收货日期",
        "comment": "确认意见"
      }
    },
    {
      "id": "end",
      "name": "结束",
      "type": "end"
    }
  ],
  "edges": [
    { "from": "start", "to": "supervisor_approval" },
    { "from": "supervisor_approval", "to": "check_amount" },
    { "from": "check_amount", "to": "department_manager", "condition": "small" },
    { "from": "check_amount", "to": "finance_approval", "condition": "medium" },
    { "from": "check_amount", "to": "finance_approval", "condition": "large" },
    { "from": "department_manager", "to": "purchase_execution" },
    { "from": "finance_approval", "to": "purchase_execution", "condition": "medium" },
    { "from": "finance_approval", "to": "ceo_approval", "condition": "large" },
    { "from": "ceo_approval", "to": "purchase_execution" },
    { "from": "purchase_execution", "to": "receipt_confirmation" },
    { "from": "receipt_confirmation", "to": "end" }
  ],
  "form_schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "title": "采购标题"
      },
      "items": {
        "type": "string",
        "title": "采购物品",
        "description": "详细描述需要采购的物品"
      },
      "amount": {
        "type": "number",
        "title": "采购金额",
        "minimum": 0
      },
      "purpose": {
        "type": "string",
        "title": "采购目的"
      },
      "expected_date": {
        "type": "string",
        "title": "期望交付日期",
        "format": "date"
      }
    },
    "required": ["title", "items", "amount", "purpose"]
  }
}
```

```mermaid
flowchart TD
    start([开始]) --> supervisor_approval{部门主管初审}
    supervisor_approval --> check_amount{检查采购金额}
    check_amount -->|<5000元| department_manager{部门经理审批}
    check_amount -->|5000-20000元| finance_approval{财务部门审核}
    check_amount -->|>20000元| finance_approval
    department_manager --> purchase_execution{采购部门执行}
    finance_approval -->|5000-20000元| purchase_execution
    finance_approval -->|>20000元| ceo_approval{总经理审批}
    ceo_approval --> purchase_execution
    purchase_execution --> receipt_confirmation{申请人确认收货}
    receipt_confirmation --> end([结束])
```
"""
    
    def _generate_default_workflow(self) -> str:
        """生成默认流程的示例"""
        return """
```workflow_description
这是一个标准的三级审批流程，包含以下步骤：
1. 申请人提交申请表单
2. 部门主管进行初审
3. 部门经理进行复审
4. 总经理进行最终审批
5. 经过所有审批后，流程结束

这是一个通用的审批流程模板，可以应用于多种业务场景。
```

```workflow_config
{
  "name": "三级审批流程",
  "description": "标准的三级审批流程，包含部门主管、部门经理和总经理三级审批",
  "nodes": [
    {
      "id": "start",
      "name": "开始",
      "type": "start"
    },
    {
      "id": "supervisor_approval",
      "name": "部门主管审批",
      "type": "approval",
      "allowed_positions": ["supervisor", "team_leader"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "manager_approval",
      "name": "部门经理审批",
      "type": "approval",
      "allowed_positions": ["department_manager", "director"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "ceo_approval",
      "name": "总经理审批",
      "type": "approval",
      "allowed_positions": ["ceo", "general_manager"],
      "form": {
        "comment": "审批意见"
      }
    },
    {
      "id": "end",
      "name": "结束",
      "type": "end"
    }
  ],
  "edges": [
    { "from": "start", "to": "supervisor_approval" },
    { "from": "supervisor_approval", "to": "manager_approval" },
    { "from": "manager_approval", "to": "ceo_approval" },
    { "from": "ceo_approval", "to": "end" }
  ],
  "form_schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "title": "申请标题"
      },
      "content": {
        "type": "string",
        "title": "申请内容",
        "maxLength": 500
      },
      "category": {
        "type": "string",
        "title": "申请类别",
        "enum": ["行政", "财务", "人事", "业务", "其他"]
      },
      "urgency": {
        "type": "string",
        "title": "紧急程度",
        "enum": ["一般", "紧急", "特急"]
      }
    },
    "required": ["title", "content", "category"]
  }
}
```

```mermaid
flowchart TD
    start([开始]) --> supervisor_approval{部门主管审批}
    supervisor_approval --> manager_approval{部门经理审批}
    manager_approval --> ceo_approval{总经理审批}
    ceo_approval --> end([结束])
```
""" 