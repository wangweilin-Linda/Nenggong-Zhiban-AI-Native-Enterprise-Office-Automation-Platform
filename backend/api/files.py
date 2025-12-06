from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Path
from fastapi.responses import FileResponse
import os
import shutil
from typing import List, Optional
import uuid
from werkzeug.utils import secure_filename
from pydantic import BaseModel

router = APIRouter()

# 创建数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# 创建上传文件保存的目录
PERSONAL_DIR = os.path.join(DATA_DIR, "personal")
os.makedirs(PERSONAL_DIR, exist_ok=True)

# 创建知识库目录
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# 创建图片目录
IMAGES_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

print(f"文件API初始化: personal目录: {PERSONAL_DIR}, knowledge目录: {KNOWLEDGE_DIR}, images目录: {IMAGES_DIR}")

class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    success: bool = True
    name: str
    path: Optional[str] = None

@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件，支持PDF和图片文件"""
    try:
        # 记录上传开始
        print(f"开始处理文件上传: {file.filename}")
        
        # 检查文件类型
        original_filename = file.filename or "unknown_file"
        file_ext = os.path.splitext(original_filename)[1].lower()
        valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp']
        
        if file_ext not in valid_extensions:
            print(f"不支持的文件类型: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。只支持 PDF 和常见图片格式。"
            )
        
        # 根据文件类型确定存储路径
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            # 图片文件存储在 images 目录
            upload_folder = IMAGES_DIR
            file_type = "images"
            print(f"识别为图片文件，将保存到: {upload_folder}")
        else:
            # PDF 文件存储在 personal 目录
            upload_folder = PERSONAL_DIR
            file_type = "personal"
            print(f"识别为PDF文件，将保存到: {upload_folder}")
            
        # 确保目录存在
        os.makedirs(upload_folder, exist_ok=True)
        
        # 生成唯一文件名，避免覆盖
        unique_filename = secure_filename(f"{uuid.uuid4().hex}_{original_filename}")
        file_path = os.path.join(upload_folder, unique_filename)
        
        print(f"准备写入文件到: {file_path}")
        
        # 写入文件
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                if not content:
                    raise ValueError("读取到的文件内容为空")
                    
                f.write(content)
                file_size = len(content)
                print(f"文件写入成功: {file_path}, 大小: {file_size} 字节")
        except Exception as write_error:
            print(f"写入文件失败: {str(write_error)}")
            raise write_error
            
        # 确认文件已正确写入
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件写入后不存在: {file_path}")
            
        if os.path.getsize(file_path) == 0:
            raise ValueError(f"写入的文件大小为0: {file_path}")
            
        print(f"文件上传成功: {file_path}")
        return {
            "success": True, 
            "name": unique_filename,
            "path": f"{file_type}/{unique_filename}"
        }
    except Exception as e:
        print(f"文件上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.get("/files/download/{filename}")
async def download_file(filename: str):
    """
    下载文件
    """
    try:
        # 构建完整的文件路径
        file_path = os.path.join(PERSONAL_DIR, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 返回文件响应
        return FileResponse(path=file_path, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@router.get("/files/list")
async def list_files(folder: str = Query(..., description="文件夹名称，如personal或knowledge")):
    """
    列出指定文件夹中的文件
    """
    try:
        print(f"请求列出{folder}文件夹中的文件")
        # 确定要列出的目录
        if folder == "personal":
            target_dir = PERSONAL_DIR
        elif folder == "knowledge":
            target_dir = KNOWLEDGE_DIR
        elif folder == "images":
            target_dir = IMAGES_DIR
        else:
            # 返回错误
            raise HTTPException(status_code=400, detail=f"不支持的文件夹名称: {folder}")
        
        # 确保目录存在
        if not os.path.exists(target_dir):
            print(f"目录不存在，创建目录: {target_dir}")
            os.makedirs(target_dir, exist_ok=True)
            return {"files": []}
        
        # 获取目录中的所有文件
        files = []
        for filename in os.listdir(target_dir):
            file_path = os.path.join(target_dir, filename)
            if os.path.isfile(file_path):
                # 添加文件信息
                files.append({
                    "name": filename,
                    "size": os.path.getsize(file_path),
                    "last_modified": os.path.getmtime(file_path)
                })
        
        # 把文档文件夹中的PDF文件也添加到知识库
        if folder == "knowledge":
            documents_dir = os.path.join(DATA_DIR, "documents")
            if os.path.exists(documents_dir):
                for filename in os.listdir(documents_dir):
                    if filename.lower().endswith('.pdf'):
                        file_path = os.path.join(documents_dir, filename)
                        if os.path.isfile(file_path):
                            files.append({
                                "name": filename,
                                "size": os.path.getsize(file_path),
                                "last_modified": os.path.getmtime(file_path)
                            })
        
        print(f"找到{len(files)}个文件")
        # 按修改时间排序
        files.sort(key=lambda x: x["last_modified"], reverse=True)
        
        return {"files": files}
    except Exception as e:
        print(f"获取文件列表失败: {str(e)}")
        # 即使出错也返回空列表
        return {"files": []}

@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """
    删除上传的文件
    """
    try:
        # 查找文件
        for directory in [PERSONAL_DIR, KNOWLEDGE_DIR, IMAGES_DIR]:
            for filename in os.listdir(directory):
                if filename.startswith(file_id):
                    file_path = os.path.join(directory, filename)
                    # 删除文件
                    os.remove(file_path)
                    return {"status": "success", "message": "文件已删除"}
        
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")