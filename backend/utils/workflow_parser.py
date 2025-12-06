import json
import os

def parse_workflow_config(file_path=None):
    """解析流程配置文件"""
    default_config = {
        "process_meta": {
            "process_type": "generic_approval",
            "version": "1.0",
            "description": "通用审批流程"
        },
        "states": {
            "initiator": {
                "type": "start",
                "transitions": [
                    {"trigger": "submit", "target": "first_approver"}
                ]
            },
            "first_approver": {
                "type": "intermediate",
                "transitions": [
                    {"trigger": "approve", "target": "final_approver"},
                    {"trigger": "reject", "target": "rejected"}
                ]
            },
            "final_approver": {
                "type": "intermediate",
                "transitions": [
                    {"trigger": "approve", "target": "approved"},
                    {"trigger": "reject", "target": "rejected"}
                ]
            },
            "approved": {
                "type": "end"
            },
            "rejected": {
                "type": "end"
            }
        }
    }

    # 如果提供了具体的文件路径，则使用该路径
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            # 返回默认配置
            return default_config
    else:
        try:
            # 尝试在几个可能的位置查找配置文件
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "..", "config", "workflow.json"),
                os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "assets", "workflow.json"),
                os.path.join(os.path.dirname(__file__), "..", "data", "workflow.json"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "workflow.json")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as file:
                        print(f"成功加载工作流配置: {path}")
                        return json.load(file)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
        
        # 如果找不到配置文件，则创建默认配置
        try:
            # 确保config目录存在
            config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
            os.makedirs(config_dir, exist_ok=True)

            default_config_path = os.path.join(config_dir, "workflow.json")
            with open(default_config_path, 'w', encoding='utf-8') as file:
                json.dump(default_config, file, ensure_ascii=False, indent=2)
            print(f"已创建默认工作流配置: {default_config_path}")
            return default_config
        except Exception as e:
            print(f"创建默认配置失败: {e}")
            return default_config

# 使用默认路径加载配置
workflow_config = parse_workflow_config()