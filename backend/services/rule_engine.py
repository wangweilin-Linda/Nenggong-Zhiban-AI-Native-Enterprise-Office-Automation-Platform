from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.document.approval import ApprovalNode
from models.user import User

class Rule:
    """规则基类"""
    def validate(self, 
               db: Session,
               instance: Dict, 
               current_node: Dict, 
               action: str, 
               user: str) -> bool:
        raise NotImplementedError

class ApprovalOrderRule(Rule):
    """审批顺序强制校验"""
    def validate(self, db, instance, current_node, action, user):
        try:
            # 获取已完成的节点ID列表
            completed_nodes = [n.node_id for n in 
                            db.query(ApprovalNode.node_id)
                            .filter(ApprovalNode.instance_id == instance['id'],
                                    ApprovalNode.status.in_(['approved', 'rejected']))
                            .all()]
            
            # 检查当前节点是否允许执行操作
            required_nodes = current_node.get('requires', [])
            return all(node in completed_nodes for node in required_nodes)
        except Exception as e:
            print(f"审批顺序校验失败: {str(e)}")
            return True  # 失败时默认允许

class PermissionRule(Rule):
    """权限限制实时检查"""
    def validate(self, db, instance, current_node, action, user):
        try:
            # 检查节点是否有职位级别或部门级别限制
            required_position_level = current_node.get('required_position_level', 0)
            required_department_level = current_node.get('required_department_level', 0)
            
            # 获取节点允许的角色/用户
            allowed_roles = current_node.get('allowed_roles', [])
            allowed_users = current_node.get('allowed_users', [])
            
            # 如果未设置任何权限限制，默认允许
            if not (required_position_level or required_department_level or allowed_roles or allowed_users):
                return True
            
            # 检查用户是否管理员（管理员可以执行任何操作）
            user_obj = db.query(User).filter(User.username == user).first()
            if user_obj and user_obj.is_admin:
                return True
                
            # 检查用户是否有足够的职位级别
            if required_position_level > 0 and user_obj:
                if user_obj.position_level == 0 or user_obj.position_level > required_position_level:
                    # 职位级别不足（级别数字越小，级别越高）
                    return False
            
            # 检查用户是否有足够的部门级别
            if required_department_level > 0 and user_obj:
                if user_obj.department_level == 0 or user_obj.department_level > required_department_level:
                    # 部门级别不足
                    return False
                
            # 检查用户是否在允许列表中
            if user in allowed_users:
                return True
                
            # 检查用户是否有允许的角色
            if user_obj and allowed_roles:
                for role in allowed_roles:
                    if self._check_user_role(db, user_obj.id, role):
                        return True
                return False
            
            # 如果只有级别限制且已通过，则允许
            if (required_position_level or required_department_level) and not (allowed_roles or allowed_users):
                return True
                
            return False
        except Exception as e:
            print(f"权限校验失败: {str(e)}")
            return False  # 失败时默认拒绝
    
    def _check_user_role(self, db, user_id, role_name):
        """检查用户是否拥有指定角色"""
        try:
            # 查询用户角色
            user_role_query = """
                SELECT COUNT(*) FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id AND r.name = :role_name
            """
            result = db.execute(user_role_query, {"user_id": user_id, "role_name": role_name}).scalar()
            return result > 0
        except Exception as e:
            print(f"角色检查失败: {str(e)}")
            return False

class RuleEngine:
    def __init__(self):
        self.rules = [
            ApprovalOrderRule(),
            PermissionRule()
        ]
    
    def apply_rules(self, db, instance, current_node, action, user):
        try:
            errors = []
            for rule in self.rules:
                if not rule.validate(db, instance, current_node, action, user):
                    errors.append(rule.__class__.__name__)
            return errors
        except Exception as e:
            print(f"规则引擎执行失败: {str(e)}")
            return []  # 发生错误时，不阻止操作