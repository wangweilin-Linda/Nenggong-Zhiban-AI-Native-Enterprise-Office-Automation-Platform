from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.core.security import SecurityManager
from app.services.analysis import perform_analysis
from app.api.v1.endpoints import documents, files
import json

router = APIRouter()
security = SecurityManager()

# 注册子路由
router.include_router(documents.router)
router.include_router(files.router)

@router.post("/analysis")
async def analyze_data(
    file: UploadFile = Form(...),
    parameters: str = Form(...)
):
    workspace = None
    try:
        # 验证参数格式
        try:
            json.loads(parameters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="参数格式错误：请提供有效的 JSON 格式")

        # 验证文件类型
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="文件格式错误：仅支持 Excel 文件(.xlsx, .xls)")

        # 创建安全工作区
        workspace = security.create_secure_workspace()
        
        # 安全保存文件
        content = await file.read()
        file_path = security.secure_save_file(content, workspace)
        
        # 执行分析
        result = await perform_analysis(file_path, parameters)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理工作区
        if workspace:
            security.cleanup_workspace(workspace)