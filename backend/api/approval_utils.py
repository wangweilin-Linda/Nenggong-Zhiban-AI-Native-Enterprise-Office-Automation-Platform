"""
审批工具函数
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models.document.approval import ApprovalProcess, ApprovalTemplate

# 默认表单模式定义
DEFAULT_FORM_SCHEMAS = {
    "1": {
        "id": "1",
        "title": "请假申请",
        "fields": [
            {"name": "leave_type", "label": "请假类型", "type": "select", "options": ["事假", "病假", "年假", "调休"]},
            {"name": "start_date", "label": "开始日期", "type": "date"},
            {"name": "end_date", "label": "结束日期", "type": "date"},
            {"name": "days", "label": "请假天数", "type": "number"},
            {"name": "reason", "label": "请假原因", "type": "textarea"}
        ]
    },
    "2": {
        "id": "2",
        "title": "报销申请",
        "fields": [
            {"name": "expense_type", "label": "报销类型", "type": "select", "options": ["差旅费", "办公用品", "招待费", "其他"]},
            {"name": "amount", "label": "报销金额", "type": "number"},
            {"name": "expense_date", "label": "费用发生日期", "type": "date"},
            {"name": "description", "label": "费用说明", "type": "textarea"},
            {"name": "has_receipt", "label": "是否有发票", "type": "checkbox"}
        ]
    },
    "3": {
        "id": "3",
        "title": "采购申请",
        "fields": [
            {"name": "purchase_type", "label": "采购类型", "type": "select", "options": ["办公用品", "电子设备", "软件", "其他"]},
            {"name": "items", "label": "采购物品", "type": "textarea"},
            {"name": "expected_cost", "label": "预计费用", "type": "number"},
            {"name": "urgency", "label": "紧急程度", "type": "select", "options": ["普通", "紧急", "特急"]},
            {"name": "reason", "label": "采购理由", "type": "textarea"}
        ]
    },
    "4": {
        "id": "4",
        "title": "财务审批",
        "fields": [
            {"name": "title", "label": "标题", "type": "text", "required": True},
            {"name": "purchase_type", "label": "采购类型", "type": "select", "options": ["办公资金", "项目资金", "投资", "其他"]},
            {"name": "amount", "label": "预计费用", "type": "number", "required": True},
            {"name": "urgency", "label": "紧急程度", "type": "select", "options": ["普通", "紧急", "特急"]},
            {"name": "reason", "label": "申请理由", "type": "textarea", "required": True}
        ]
    }
}

def get_form_schema_by_id(schema_id: str, db: Session) -> Dict[str, Any]:
    """
    根据ID获取表单模式
    
    参数:
    - schema_id: 表单模式ID
    - db: 数据库会话
    
    返回:
    - 表单模式字典
    """
    try:
        print(f"获取表单模式: {schema_id}")
        
        # 先检查是否有硬编码的表单模式
        if schema_id in DEFAULT_FORM_SCHEMAS:
            print(f"返回硬编码表单: {schema_id}")
            return DEFAULT_FORM_SCHEMAS[schema_id]
        
        # 转换schema_id为整数尝试从数据库查询
        process_id = None
        try:
            process_id = int(schema_id)
        except ValueError:
            # 如果不是整数，使用字符串查询
            pass
        
        # 尝试从数据库获取流程定义
        if process_id:
            # 查询流程定义
            process = db.query(ApprovalProcess).filter(ApprovalProcess.id == process_id).first()
            if process:
                # 如果流程存在，返回它的表单模式
                if process.form_schema:
                    form_schema = process.form_schema
                    if isinstance(form_schema, str):
                        try:
                            form_schema = json.loads(form_schema)
                        except:
                            pass
                    print(f"返回流程表单模式: {process_id}")
                    return form_schema
                
                # 如果流程没有表单模式，检查是否有表单模板ID
                if process.form_template:
                    template_id = process.form_template
                    # 如果是直接引用表单模式ID
                    if template_id in DEFAULT_FORM_SCHEMAS:
                        print(f"返回流程引用的表单模式: {template_id}")
                        return DEFAULT_FORM_SCHEMAS[template_id]
            
            # 尝试直接查询表单模板
            template = db.query(ApprovalTemplate).filter(ApprovalTemplate.id == process_id).first()
            if template and template.form_schema:
                form_schema = template.form_schema
                if isinstance(form_schema, str):
                    try:
                        form_schema = json.loads(form_schema)
                    except:
                        pass
                print(f"返回模板表单模式: {process_id}")
                return form_schema
        
        # 如果是特定ID，返回预定义的表单
        if schema_id == "1":
            return DEFAULT_FORM_SCHEMAS["1"]  # 请假表单
        elif schema_id == "2":
            return DEFAULT_FORM_SCHEMAS["2"]  # 报销表单
        elif schema_id == "3":
            return DEFAULT_FORM_SCHEMAS["3"]  # 采购表单
        elif schema_id == "4":
            return DEFAULT_FORM_SCHEMAS["4"]  # 财务审批表单
        
        # 如果找不到对应的表单模式，返回一个通用模板
        print(f"未找到表单模式 {schema_id}，返回默认模板")
        return {
            "id": schema_id,
            "title": "通用审批表单",
            "is_simple": True, # 标记为简化表单
            "fields": [
                {"name": "title", "label": "标题", "type": "text", "required": True},
                {"name": "content", "label": "内容", "type": "textarea", "required": True}
            ]
        }
    except Exception as e:
        print(f"获取表单模式失败: {str(e)}")
        import traceback
        traceback.print_exc()
        # 返回一个基本表单，避免前端报错
        return {
            "id": schema_id,
            "title": "基础表单(错误回退)",
            "is_simple": True, # 标记为简化表单
            "fields": [
                {"name": "title", "label": "标题", "type": "text", "required": True},
                {"name": "content", "label": "内容", "type": "textarea", "required": True}
            ]
        }

def detect_form_schema_by_data(form_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """根据表单数据自动检测合适的表单模式"""
    if not form_data or not isinstance(form_data, dict):
        return {
            "id": "basic",
            "title": "基础审批表单",
            "is_simple": True,
            "fields": [
                {"name": "content", "label": "内容", "type": "textarea", "required": True}
            ]
        }
    
    # 如果只有content字段，直接返回简化表单
    if len(form_data.keys()) == 1 and "content" in form_data:
        return {
            "id": "basic",
            "title": "基础审批表单",
            "is_simple": True,
            "fields": [
                {"name": "content", "label": "内容", "type": "textarea", "required": True}
            ]
        }
    
    # 提取表单中的字段
    fields = set(form_data.keys())
    
    # 检查是否为请假申请
    leave_fields = {"leave_type", "start_date", "end_date", "days", "reason"}
    if len(leave_fields.intersection(fields)) >= 3:
        return DEFAULT_FORM_SCHEMAS.get("1")  # 匹配请假申请
    
    # 检查是否为报销申请
    expense_fields = {"expense_type", "amount", "expense_date", "description", "has_receipt"}
    if len(expense_fields.intersection(fields)) >= 3:
        return DEFAULT_FORM_SCHEMAS.get("2")  # 匹配报销申请
    
    # 检查是否为采购申请
    purchase_fields = {"purchase_type", "items", "expected_cost", "urgency", "reason"}
    if len(purchase_fields.intersection(fields)) >= 3:
        return DEFAULT_FORM_SCHEMAS.get("3")  # 匹配采购申请
    
    # 检查是否为其他类型的表单
    if "amount" in fields and ("description" in fields or "reason" in fields):
        # 可能是报销或财务申请
        return DEFAULT_FORM_SCHEMAS.get("2")
    
    if "days" in fields and "reason" in fields:
        # 可能是请假申请
        return DEFAULT_FORM_SCHEMAS.get("1")
    
    # 返回动态生成的通用表单
    dynamic_fields = [
        {"name": key, "label": key.replace('_', ' ').capitalize(), "type": detect_field_type(key, value)} 
        for key, value in form_data.items()
    ]
    
    # 如果字段很少，标记为简化表单
    is_simple = len(dynamic_fields) <= 2
    
    return {
        "id": "generic",
        "title": "通用审批表单",
        "is_simple": is_simple,
        "fields": dynamic_fields
    }

def detect_field_type(field_name: str, field_value: Any) -> str:
    """根据字段名和值检测可能的字段类型"""
    
    # 根据字段名猜测类型
    name_lower = field_name.lower()
    
    # 日期相关字段
    if any(date_term in name_lower for date_term in ["date", "time", "day"]):
        return "date"
    
    # 数值相关字段
    if any(num_term in name_lower for num_term in ["amount", "cost", "price", "number", "count", "days"]):
        return "number"
    
    # 选择类型字段
    if any(select_term in name_lower for select_term in ["type", "status", "category", "level"]):
        return "select"
    
    # 长文本字段
    if any(text_term in name_lower for text_term in ["desc", "reason", "content", "comment", "detail"]):
        return "textarea"
    
    # 默认为文本框
    return "text" 