from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from models import Document, User
from utils.security import get_current_user
import json
import os
from datetime import datetime
from PyPDF2 import PdfReader
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/documents", tags=["文档"])

# 定义文档创建模型
class DocumentCreate(BaseModel):
    title: str
    content: str
    type: str
    meta_data: Optional[Dict[str, Any]] = None

# 修改 PDF_DIR 的定义
current_dir = os.path.dirname(__file__)
backend_dir = os.path.dirname(current_dir)  # 这里去掉一层，直接用backend目录
PDF_DIR = os.path.abspath(os.path.join(backend_dir, 'data/documents'))

# 确保目录存在
os.makedirs(PDF_DIR, exist_ok=True)

@router.on_event("startup")
async def api_startup():
    """仅进行PDF文件扫描，不初始化数据库"""
    print("文档路由模块启动，开始扫描PDF文件...")
    # 确保文档表已创建
    ensure_documents_table()
    # 首先创建测试文档
    create_sample_documents()
    # 然后扫描文件
    scan_pdf_files()  # 只扫描PDF文件，不初始化数据库
    
    # 打印文档数量
    try:
        db = next(get_db())
        cursor = db.execute(text("SELECT COUNT(*) FROM documents"))
        count = cursor.scalar() or 0
        print(f"文档扫描完成，数据库中共有 {count} 个文档记录")
    except Exception as e:
        print(f"获取文档数量失败: {e}")

def ensure_documents_table():
    """确保documents表存在"""
    print("确保documents表存在...")
    
    # 获取数据库连接
    db = next(get_db())
    try:
        # 直接用SQL创建表，与ORM模型保持一致
        create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            owner_id INTEGER NOT NULL,
            status TEXT,
            type_id INTEGER,
            category_id INTEGER,
            is_public INTEGER DEFAULT 0,
            can_comment INTEGER DEFAULT 1,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)
        db.execute(create_table_sql)
        db.commit()
        print("documents表创建或已存在")
    except Exception as e:
        print(f"确保表存在时出错: {e}")
        db.rollback()
    finally:
        db.close()

def create_sample_documents():
    """创建一些示例PDF文档以供测试"""
    try:
        print("创建示例文档...")
        # 确保目录存在
        os.makedirs(PDF_DIR, exist_ok=True)
        
        # 示例文档内容 - 使用ASCII字符创建一个简单的PDF示例
        sample_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>/Contents 4 0 R/Parent 2 0 R>>\nendobj\n4 0 obj\n<</Length 21>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Sample Document) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\n0000000198 00000 n\ntrailer\n<</Size 5/Root 1 0 R>>\nstartxref\n269\n%%EOF"
        
        # 创建三个示例文档
        samples = [
            {
                "filename": "工作报告_2023-05-01_行政部.pdf",
                "content": sample_content
            },
            {
                "filename": "会议纪要_2023-06-15_人事部.pdf",
                "content": sample_content
            },
            {
                "filename": "项目计划_2023-07-20_技术部.pdf",
                "content": sample_content
            }
        ]
        
        # 写入文件
        for sample in samples:
            file_path = os.path.join(PDF_DIR, sample["filename"])
            if not os.path.exists(file_path):  # 如果文件不存在才创建
                with open(file_path, 'wb') as f:
                    f.write(sample["content"])
                print(f"创建示例文档: {sample['filename']}")
            else:
                print(f"示例文档已存在: {sample['filename']}")
                
        print("示例文档创建完成")
    except Exception as e:
        print(f"创建示例文档失败: {e}")
        import traceback
        traceback.print_exc()

def scan_pdf_files():
    """扫描PDF文件并添加到数据库"""
    print("开始扫描PDF文件...")
    db = next(get_db())
    try:
        # 获取已有文档的文件名列表，使用document_attachments表
        existing_files = set()
        try:
            query = text("""
                SELECT da.filename FROM document_attachments da 
                JOIN documents d ON da.document_id = d.id
            """)
            result = db.execute(query)
            
            for row in result:
                existing_files.add(row[0])
            
            print(f"数据库中已有 {len(existing_files)} 个文档文件记录")
        except Exception as e:
            print(f"获取现有文档文件列表失败: {e}")
            existing_files = set()
        
        # 扫描文件并添加新文件
        count = 0
        print(f"扫描目录: {PDF_DIR}")
        
        if not os.path.exists(PDF_DIR):
            print(f"警告: 目录 {PDF_DIR} 不存在，创建空目录")
            os.makedirs(PDF_DIR, exist_ok=True)
            
        files = os.listdir(PDF_DIR)
        if not files:
            print("警告: 文档目录为空，没有PDF文件可导入")
            return
            
        print(f"找到 {len(files)} 个文件")
        
        # 获取当前的admin用户作为默认owner_id
        try:
            admin_query = text("SELECT id FROM users WHERE username = 'admin' LIMIT 1")
            admin_id = db.execute(admin_query).scalar()
            default_owner_id = admin_id if admin_id else 1  # 默认为1
        except:
            default_owner_id = 1  # 如果查询失败，设置默认值为1
        
        for filename in files:
            if not filename.lower().endswith('.pdf') and not filename.lower().endswith('.PDF'):
                continue
                
            # 检查文件是否已经在数据库中
            if filename in existing_files:
                print(f"跳过已存在的文件: {filename}")
                continue
                
            print(f"处理新文件: {filename}")
            try:
                # 尝试按标准格式解析
                parts = filename.split('_')
                if len(parts) >= 3:
                    title = parts[0]
                    # 尝试从文件名解析额外信息
                    date_part = parts[1]
                    department_part = parts[-1].replace('.pdf', '').replace('.PDF', '')
                else:
                    # 非标准格式，使用文件名作为标题
                    title = filename.replace('.pdf', '').replace('.PDF', '')
                    department_part = "未知部门"
                
                # 尝试提取PDF内容
                content = "这里是公文内容"
                try:
                    pdf_path = os.path.join(PDF_DIR, filename)
                    reader = PdfReader(pdf_path)
                    text_content = ""
                    for i, page in enumerate(reader.pages):
                        if i < 3:  # 只提取前三页内容
                            text_content += page.extract_text() + "\n"
                    
                    if text_content.strip():
                        content = text_content[:1000]  # 限制内容长度
                except Exception as pdf_err:
                    print(f"提取PDF内容失败: {filename}, 错误: {pdf_err}")
                
                # 创建文档记录 - 适配新的文档模型
                try:
                    print(f"添加文档: {title}")
                    
                    # 使用标准的SQLite参数化查询，匹配实际的表结构
                    insert_sql = text("""
                    INSERT INTO documents 
                        (title, content, owner_id, status, is_public, can_comment, created_at, updated_at) 
                    VALUES 
                        (:title, :content, :owner_id, 'APPROVED', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """)
                    
                    result = db.execute(insert_sql, {
                        "title": title, 
                        "content": content,
                        "owner_id": default_owner_id
                    })
                    
                    # 获取新插入文档的ID
                    document_id = result.lastrowid
                    
                    # 为文档添加附件记录
                    if document_id:
                        attachment_sql = text("""
                        INSERT INTO document_attachments
                            (document_id, filename, file_path, file_type, created_at)
                        VALUES
                            (:document_id, :filename, :file_path, 'pdf', CURRENT_TIMESTAMP)
                        """)
                        
                        db.execute(attachment_sql, {
                            "document_id": document_id,
                            "filename": filename,
                            "file_path": os.path.join(PDF_DIR, filename)
                        })
                    
                    count += 1
                    db.flush()  # 让每个添加立即生效
                except Exception as add_err:
                    print(f"添加文档记录失败: {add_err}")
                    continue  # 跳过这个文件，继续处理下一个
                    
            except Exception as doc_err:
                print(f"处理文档失败: {filename}, 错误: {doc_err}")
        
        db.commit()
        if count > 0:
            print(f"文档扫描完成，共添加 {count} 个新文档")
        else:
            print("文档扫描完成，没有新文档需要添加")
            
        # 验证数据库中的记录数
        cursor = db.execute(text("SELECT COUNT(*) FROM documents"))
        final_count = cursor.scalar() or 0
        print(f"数据库中现有 {final_count} 条文档记录")
        
    except Exception as e:
        print(f"扫描文件失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

@router.get("/list")
def get_documents(
    page: int = 1, 
    size: int = 10, 
    keyword: str = "", 
    sort_by: str = "created_at", 
    sort_order: str = "desc", 
    db: Session = Depends(get_db)
):
    """获取文档列表，支持分页和搜索"""
    try:
        # 验证排序字段，如果无效则回退到created_at
        valid_sort_fields = ["title", "created_at", "updated_at", "status"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
            
        # 验证排序顺序
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"
        
        # 计算偏移量
        offset = (page - 1) * size
        
        # 构建基础查询
        base_query = """
            SELECT 
                d.id, 
                d.title, 
                d.content, 
                d.status,
                d.created_at, 
                d.updated_at,
                d.is_public,
                u.username as owner_name,
                u.real_name as owner_real_name,
                t.name as document_type_name,
                c.name as category_name
            FROM 
                documents d
                LEFT JOIN users u ON d.owner_id = u.id
                LEFT JOIN document_types t ON d.type_id = t.id
                LEFT JOIN document_categories c ON d.category_id = c.id
            WHERE 
                1=1
        """
        
        params = {}
        
        # 添加搜索条件
        if keyword:
            base_query += " AND (d.title LIKE :keyword OR d.content LIKE :keyword)"
            params["keyword"] = f"%{keyword}%"
            
        # 添加排序
        base_query += f" ORDER BY d.{sort_by} {sort_order}"
        
        # 添加分页
        base_query += " LIMIT :size OFFSET :offset"
        params["size"] = size
        params["offset"] = offset
        
        # 执行查询获取数据
        result = db.execute(text(base_query), params)
        documents = []
        
        for row in result:
            # 将行转换为字典
            doc = dict(row._mapping)
            
            # 处理附件信息
            try:
                # 查询附件
                attachment_query = """
                    SELECT filename, file_path, file_type 
                    FROM document_attachments 
                    WHERE document_id = :doc_id
                """
                attachments_result = db.execute(text(attachment_query), {"doc_id": doc["id"]})
                attachments = [dict(row._mapping) for row in attachments_result]
                doc["attachments"] = attachments
            except Exception as e:
                doc["attachments"] = []
                
            documents.append(doc)
        
        # 获取总记录数
        count_query = """
            SELECT COUNT(*) FROM documents d
            WHERE 1=1
        """
        if keyword:
            count_query += " AND (d.title LIKE :keyword OR d.content LIKE :keyword)"
            
        total = db.execute(text(count_query), {"keyword": f"%{keyword}%" if keyword else ""}).scalar()
        
        return {
            "items": documents,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败：{str(e)}"
        )

@router.get("/")
def get_all_documents(
    page: int = 1, 
    size: int = 10, 
    keyword: str = "", 
    db: Session = Depends(get_db)
):
    """简化版的文档列表API，仅支持基本分页和搜索"""
    result = get_documents(page=page, size=size, keyword=keyword, db=db)
    
    # 转换数据格式，将items改为documents以匹配前端期望
    if "items" in result:
        result["documents"] = result["items"]
        # 保留items以向后兼容
    
    return result

@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    """获取单个文档"""
    try:
        # 确保db是有效的数据库会话对象
        if not isinstance(db, Session):
            # 如果db不是Session对象，尝试获取一个新的会话
            db = next(get_db())
            
        # 使用与ORM模型一致的表结构
        create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            owner_id INTEGER NOT NULL,
            status TEXT,
            type_id INTEGER,
            category_id INTEGER,
            is_public INTEGER DEFAULT 0,
            can_comment INTEGER DEFAULT 1,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)
        db.execute(create_table_sql)
        
        # 修改查询以匹配实际的表结构
        query_sql = text("""
        SELECT d.id, d.title, d.content, d.status, d.created_at, d.updated_at,
               u.username as owner_name, c.name as category_name
        FROM documents d
        LEFT JOIN users u ON d.owner_id = u.id
        LEFT JOIN document_categories c ON d.category_id = c.id
        WHERE d.id = :doc_id
        """)
        cursor = db.execute(query_sql, {"doc_id": doc_id})
        doc = cursor.fetchone()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 创建结果字典
        result = dict(doc._mapping) if hasattr(doc, '_mapping') else dict(zip([
            "id", "title", "content", "status", "created_at", "updated_at", 
            "owner_name", "category_name"
        ], doc))
        
        # 查询文档附件
        attachments_query = text("""
        SELECT id, filename, file_path, file_type FROM document_attachments
        WHERE document_id = :doc_id
        """)
        attachments = db.execute(attachments_query, {"doc_id": doc_id}).fetchall()
        result["attachments"] = [
            dict(a._mapping) if hasattr(a, '_mapping') else {
                "id": a[0], "filename": a[1], "file_path": a[2], "file_type": a[3]
            }
            for a in attachments
        ]
            
        return result
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"获取文档详情失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取文档失败")

@router.get("/attachment/{filename}")
async def download_attachment(filename: str):
    """下载文档附件"""
    try:
        # 从document_attachments表查找文件路径
        db = next(get_db())
        query = text("""
            SELECT da.file_path FROM document_attachments da
            WHERE da.filename = :filename
            LIMIT 1
        """)
        result = db.execute(query, {"filename": filename}).fetchone()
        
        if not result:
            # 如果在附件表中找不到，尝试直接从documents目录获取
            file_path = os.path.join(PDF_DIR, filename)
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="文件不存在")
        else:
            file_path = result[0]
            # 如果文件路径不存在，使用标准路径
            if not os.path.exists(file_path):
                file_path = os.path.join(PDF_DIR, filename)
                
        return FileResponse(path=file_path, filename=filename, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载附件失败: {str(e)}")

@router.get("/todo", response_model=List[Dict[str, Any]])
async def get_document_todos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取待办文档列表"""
    try:
        # 从数据库查询待审批的文档
        # 使用SQLAlchemy Session的execute方法执行查询
        query = text("SELECT * FROM documents WHERE status = :status AND assignee_id = :assignee_id")
        query_result = db.execute(query, {"status": "pending", "assignee_id": current_user.id})
        
        docs_list = []
        for doc in query_result:
            docs_list.append({
                "id": doc.id,
                "title": doc.title,
                "type": doc.type,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                "creator_name": doc.creator.username if doc.creator else "未知",
                "assignee_name": doc.assignee.username if doc.assignee else "未分配"
            })
            
        return docs_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取待办文档失败: {str(e)}")

@router.post("/create", response_model=Dict[str, Any])
async def create_document(
    document: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新文档"""
    try:
        # 创建新文档
        new_document = Document(
            title=document.title,
            content=document.content,
            type=document.type,
            status="draft",
            creator_id=current_user.id,
            meta_data=document.meta_data if hasattr(document, 'meta_data') else {}
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        return {
            "success": True,
            "message": "文档创建成功",
            "document_id": new_document.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建文档失败: {str(e)}")

@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document_by_id(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文档详情"""
    try:
        # 查询文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 检查访问权限
        # 1. 文档创建者可以查看
        # 2. 文档处理人可以查看
        # 3. 管理员可以查看所有文档
        if document.creator_id != current_user.id and document.assignee_id != current_user.id and not current_user.is_admin:
            # 检查用户部门和职位权限
            # 暂时注释掉这一段，因为涉及到不存在的模型
            # if not can_access_document(document, current_user, db):
            raise HTTPException(status_code=403, detail="您没有权限查看此文档")
        
        # 获取文档的审批历史
        # 暂时注释掉这一段，因为涉及到不存在的模型
        """
        approval_histories = db.query(ApprovalHistory).filter(
            ApprovalHistory.document_id == document_id
        ).order_by(ApprovalHistory.created_at.desc()).all()
        
        history_records = []
        for history in approval_histories:
            history_records.append({
                "id": history.id,
                "action": history.action,
                "approver_name": history.approver.username if history.approver else "系统",
                "comment": history.comment,
                "created_at": history.created_at.isoformat() if history.created_at else None
            })
        """
        history_records = []
        
        return {
            "id": document.id,
            "title": document.title,
            "content": document.content,
            "type": document.type,
            "status": document.status,
            "meta_data": document.meta_data,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "creator": {
                "id": document.creator.id,
                "username": document.creator.username,
                "real_name": document.creator.real_name if hasattr(document.creator, 'real_name') else document.creator.username
            } if document.creator else None,
            "assignee": {
                "id": document.assignee.id,
                "username": document.assignee.username,
                "real_name": document.assignee.real_name if hasattr(document.assignee, 'real_name') else document.assignee.username
            } if document.assignee else None,
            "history": history_records
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档详情失败: {str(e)}")

# 暂时注释掉这个函数，因为它依赖不存在的模型
"""
def can_access_document(document: Document, user: User, db: Session) -> bool:
    #检查用户是否有权限访问文档，基于部门和职位
    try:
        # 获取文档类型对应的审批流程
        process = db.query(ApprovalProcess).filter(
            ApprovalProcess.business_type == document.type,
            ApprovalProcess.is_active == True
        ).first()
        
        if not process:
            # 没有找到对应流程，默认只有创建者和处理人可以查看
            return False
            
        # 获取流程配置
        config = process.config
        if not config:
            return False
            
        # 检查用户是否在流程的任何一个节点的处理人列表中
        # 这里实现简化版，实际应根据具体的流程配置格式调整
        if 'nodes' in config:
            for node in config['nodes']:
                # 检查节点是否有allowed_positions或allowed_roles配置
                allowed_positions = node.get('allowed_positions', [])
                allowed_roles = node.get('allowed_roles', [])
                allowed_dept_levels = node.get('allowed_department_levels', [])
                
                # 检查用户的职位是否在允许列表中
                if user.position and user.position.name in allowed_positions:
                    return True
                    
                # 检查用户的角色是否在允许列表中
                user_roles = [role.name for role in user.roles]
                if any(role in allowed_roles for role in user_roles):
                    return True
                    
                # 检查用户的部门级别是否在允许列表中
                if user.department and (user.department.level in allowed_dept_levels or str(user.department.level) in allowed_dept_levels):
                    return True
                    
                # 检查用户是否是管理岗位
                if user.position and user.position.is_management:
                    return True
            
        return False
    except Exception as e:
        print(f"检查文档访问权限失败: {str(e)}")
        return False
"""

# 添加文档处理相关端点
@router.get("/document-process/pending")
async def get_pending_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取待处理的文档列表"""
    try:
        # 返回模拟数据
        pending_docs = [
            {
                "id": 1,
                "title": "会议纪要审批",
                "type": "approval",
                "status": "pending",
                "created_at": "2023-10-15T08:30:00",
                "creator_name": "张三",
                "department": "行政部",
                "current_node": "部门经理审批",
                "workflow_id": 1
            },
            {
                "id": 2,
                "title": "项目计划书审批",
                "type": "approval",
                "status": "pending",
                "created_at": "2023-10-16T09:15:00",
                "creator_name": "李四",
                "department": "技术部",
                "current_node": "总经理审批",
                "workflow_id": 2
            },
            {
                "id": 3,
                "title": "预算申请审批",
                "type": "approval",
                "status": "pending",
                "created_at": "2023-10-17T14:00:00",
                "creator_name": "王五",
                "department": "财务部",
                "current_node": "财务经理审批",
                "workflow_id": 3
            }
        ]
        return pending_docs
    except Exception as e:
        print(f"获取待处理文档失败: {str(e)}")
        # 返回空列表而不是错误
        return []