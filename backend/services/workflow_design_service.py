from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_ollama import OllamaLLM
from typing import Dict, Any, List, Optional
import json
import time
import os
import re
from datetime import datetime
import uuid
import traceback
import subprocess

class WorkflowDesignerAgent:
    """工作流设计代理，使用本地ollama模型"""
    
    def __init__(self, model_name="deepseek-r1:7b", temp_dir="./approval_configs"):
        self.model_name = model_name
        self.temp_dir = temp_dir
        
        # 确保临时目录存在
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
    def design_workflow(self, prompt: str, org_info: Optional[Dict] = None) -> Dict:
        """根据提示设计工作流"""
        try:
            # 准备系统提示
            system_prompt = """
            你是一个专业的工作流设计助手。你的任务是根据用户的自然语言描述，
            生成符合有限状态机规范的工作流配置，并提供流程图。
            
            请返回JSON格式的响应，包含以下内容：
            1. workflow_config: 工作流配置JSON对象
            2. diagram: 使用Mermaid.js语法的流程图代码
            3. description: 流程文字描述
            
            工作流配置结构如下：
            {
                "nodes": [
                    {
                        "id": "node_id",
                        "name": "节点名称",
                        "type": "start|approval|condition|end",
                        "next": ["下一个节点ID"],
                        "config": {
                            "required_position_level": 数字，
                            "required_department_level": 数字，
                            "allowed_roles": ["角色名称"],
                            "allowed_users": [用户ID],
                            "conditions": [条件配置]
                        }
                    }
                ],
                "metadata": {
                    "name": "流程名称",
                    "description": "流程描述"
                }
            }
            
            你需要根据用户的描述，识别出审批流程中的关键节点、角色、条件和流转逻辑。
            """
            
            # 准备用户提示
            user_prompt = f"请设计一个工作流：{prompt}\n"
            
            # 如果有组织信息，加入到提示中
            if org_info:
                user_prompt += f"组织架构信息：{json.dumps(org_info, ensure_ascii=False)}\n"
            
            user_prompt += """
            请确保生成的工作流配置包含合理的节点ID、名称、类型以及正确的流转逻辑。
            对于条件节点，请根据业务描述设计合适的条件规则。
            生成的流程图应该清晰展示整个流程的流转路径。
            """
            
            # 调用本地ollama模型
            result = self._call_ollama_model(system_prompt, user_prompt)
            
            # 解析JSON响应
            workflow_data = self._extract_json(result)
            
            # 保存配置到临时文件
            config_file = self._save_config(workflow_data.get("workflow_config", {}))
            
            return {
                "workflow_config": workflow_data.get("workflow_config", {}),
                "diagram": workflow_data.get("diagram", ""),
                "description": workflow_data.get("description", ""),
                "config_file": config_file
            }
        except Exception as e:
            print(f"设计工作流出错: {str(e)}")
            traceback.print_exc()
            return {
                "error": str(e),
                "workflow_config": {},
                "diagram": "",
                "description": "生成失败，请尝试提供更详细的描述。"
            }
    
    def optimize_workflow(self, current_config: Dict, feedback: str) -> Dict:
        """根据反馈优化工作流"""
        try:
            # 准备系统提示
            system_prompt = """
            你是一个专业的工作流设计助手。你的任务是根据用户的反馈，
            优化现有的工作流配置和流程图。
            
            请返回JSON格式的响应，包含以下内容：
            1. workflow_config: 优化后的工作流配置JSON对象
            2. diagram: 更新后的Mermaid.js流程图代码
            3. description: 优化后的流程文字描述
            4. changes: 变更说明列表
            """
            
            # 准备用户提示
            user_prompt = f"""
            请根据以下反馈优化工作流：
            {feedback}
            
            当前工作流配置：
            {json.dumps(current_config, ensure_ascii=False, indent=2)}
            
            请保持节点ID的一致性，除非需要添加新节点或删除现有节点。
            响应中必须包含完整的优化后配置、更新的流程图以及变更说明。
            """
            
            # 调用本地ollama模型
            result = self._call_ollama_model(system_prompt, user_prompt)
            
            # 解析JSON响应
            workflow_data = self._extract_json(result)
            
            # 保存配置到临时文件
            config_file = self._save_config(workflow_data.get("workflow_config", {}))
            
            return {
                "workflow_config": workflow_data.get("workflow_config", {}),
                "diagram": workflow_data.get("diagram", ""),
                "description": workflow_data.get("description", ""),
                "changes": workflow_data.get("changes", []),
                "config_file": config_file
            }
        except Exception as e:
            print(f"优化工作流出错: {str(e)}")
            traceback.print_exc()
            return {
                "error": str(e),
                "workflow_config": current_config,
                "diagram": "",
                "description": "优化失败，请尝试提供更清晰的反馈。",
                "changes": []
            }
    
    def explain_workflow(self, config: Dict) -> str:
        """解释工作流配置"""
        try:
            # 准备系统提示
            system_prompt = """
            你是一个专业的工作流解释助手。你的任务是解释工作流配置，
            生成清晰易懂的文字描述。
            """
            
            # 准备用户提示
            user_prompt = f"""
            请解释以下工作流配置，用通俗易懂的语言描述整个流程的处理逻辑：
            
            {json.dumps(config, ensure_ascii=False, indent=2)}
            
            请按照流程的流转顺序进行解释，包括每个节点的功能、条件分支的判断逻辑、
            以及各角色在流程中的权限和职责。
            """
            
            # 调用本地ollama模型
            result = self._call_ollama_model(system_prompt, user_prompt)
            
            return result.strip()
        except Exception as e:
            print(f"解释工作流出错: {str(e)}")
            return f"解释失败: {str(e)}"
    
    def _call_ollama_model(self, system_prompt: str, user_prompt: str) -> str:
        """调用本地ollama模型"""
        try:
            cmd = [
                "ollama", "run", self.model_name,
                "--system", system_prompt,
                user_prompt
            ]
            
            # 执行命令并获取输出
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"调用Ollama模型错误: {str(e)}")
            print(f"错误输出: {e.stderr}")
            return ""
    
    def _extract_json(self, text: str) -> Dict:
        """从文本中提取JSON对象"""
        # 尝试查找JSON块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试查找{开始和}结束的最大块
            json_match = re.search(r'({[\s\S]*})', text)
            if json_match:
                json_str = json_match.group(1)
            else:
                return {}
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 如果解析失败，尝试修复常见问题并重试
            json_str = re.sub(r',\s*}', '}', json_str)  # 移除尾随逗号
            json_str = re.sub(r',\s*]', ']', json_str)  # 移除数组中的尾随逗号
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"无法解析JSON: {json_str}")
                return {}
    
    def _save_config(self, config: Dict) -> str:
        """保存配置到文件"""
        if not config:
            return ""
            
        # 生成文件名
        filename = f"workflow_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}.json"
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
        return filepath
        
    def generate_mermaid_diagram(self, config: Dict) -> str:
        """根据工作流配置生成Mermaid.js流程图"""
        try:
            # 准备系统提示
            system_prompt = """
            你是一个工作流可视化专家。你的任务是将工作流配置转换为Mermaid.js流程图代码。
            请仅返回Mermaid.js代码，不要包含任何其他内容。
            """
            
            # 准备用户提示
            user_prompt = f"""
            请将以下工作流配置转换为Mermaid.js流程图代码：
            
            {json.dumps(config, ensure_ascii=False, indent=2)}
            
            生成的Mermaid.js代码应该：
            1. 使用flowchart语法
            2. 清晰表示节点之间的关系和流转路径
            3. 为不同类型的节点使用不同的形状（开始/结束使用圆角矩形，审批节点使用矩形，条件节点使用菱形）
            4. 使用有意义的颜色区分不同类型的节点
            5. 为连线添加清晰的标签
            
            只需返回Mermaid.js代码，不要有其他内容。
            """
            
            # 调用本地ollama模型
            result = self._call_ollama_model(system_prompt, user_prompt)
            
            # 提取Mermaid代码
            mermaid_match = re.search(r'```mermaid\s*([\s\S]*?)\s*```', result)
            if mermaid_match:
                return mermaid_match.group(1).strip()
            else:
                # 尝试直接提取flowchart开头的代码
                flowchart_match = re.search(r'(flowchart[\s\S]*)', result)
                if flowchart_match:
                    return flowchart_match.group(1).strip()
                else:
                    return result.strip()
        except Exception as e:
            print(f"生成流程图出错: {str(e)}")
            return "graph TD\nA[生成失败] --> B[请重试]"

# 使用示例
# designer = WorkflowDesignerAgent()
# result = designer.design_workflow("我需要一个三级审批流程，部门经理→财务→总经理") 