import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from sqlalchemy.orm import Session
from database.session import get_db
from models import Document as DBDocument
import json

# 修复导入，使用新版本的OllamaEmbeddings
try:
    from langchain_ollama import OllamaEmbeddings
    print("成功导入langchain_ollama.OllamaEmbeddings")
except ImportError:
    # 兼容旧版本
    try:
        from langchain_community.embeddings import OllamaEmbeddings
        print("警告：使用已弃用的OllamaEmbeddings，建议升级: pip install langchain_ollama")
    except ImportError:
        print("无法导入OllamaEmbeddings")

# 尝试导入新版本的HuggingFaceEmbeddings
try:
    from langchain_huggingface import HuggingFaceEmbeddings # type: ignore
    print("成功导入langchain_huggingface.HuggingFaceEmbeddings")
except ImportError:
    # 如果导入失败，尝试使用旧版本的HuggingFaceEmbeddings
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        print("使用旧版本的HuggingFaceEmbeddings")
    except ImportError:
        print("无法导入HuggingFaceEmbeddings，将使用备选方案")

# 导入FakeEmbeddings作为备选方案
try:
    from langchain_community.embeddings import FakeEmbeddings
    print("成功导入FakeEmbeddings")
except ImportError:
    print("无法导入FakeEmbeddings")

vector_store = None

# 保存向量存储的文件夹路径
VECTOR_STORE_PATH = "faiss_index"

# 文档目录
DOCS_DIR = os.path.join(os.getcwd(), "data/docs")

def load_documents(directory=None):  # 添加参数
    """加载文档"""
    try:
        documents = []
        base_dir = os.getcwd()
        print(f"当前工作目录: {base_dir}")
        
        # 从数据库加载公文内容
        try:
            db = next(get_db())
            docs = db.query(DBDocument).all()

            for doc in docs:
                # 添加公文内容
                content = f"标题: {doc.title}\n发布时间: {doc.publish_time}\n发布单位: {doc.publish_unit}\n内容: {doc.content}"
                documents.append(Document(page_content=content, metadata={"id": doc.id}))
        except Exception as e:
            print(f"从数据库加载文档失败: {str(e)}")
            
        # 确保所有数据目录存在
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        knowledge_dir = os.path.join(data_dir, "knowledge")
        os.makedirs(knowledge_dir, exist_ok=True)
        
        personal_dir = os.path.join(data_dir, "personal")
        os.makedirs(personal_dir, exist_ok=True)
        
        documents_dir = os.path.join(data_dir, "documents")
        os.makedirs(documents_dir, exist_ok=True)

        # 加载知识库目录中的PDF文件
        if os.path.exists(knowledge_dir):
            for filename in os.listdir(knowledge_dir):
                if filename.lower().endswith('.pdf'):
                    file_path = os.path.join(knowledge_dir, filename)
                    try:
                        print(f"正在加载PDF文件: {file_path}")
                        loader = PyPDFLoader(file_path)
                        pdf_docs = loader.load()
                        # 为每个文档添加来源元数据
                        for doc in pdf_docs:
                            doc.metadata["source"] = filename
                            doc.metadata["path"] = file_path
                        documents.extend(pdf_docs)
                        print(f"成功加载PDF文件: {filename}, 页数: {len(pdf_docs)}")
                    except Exception as e:
                        print(f"加载知识库PDF文件失败 {filename}: {str(e)}")
                        import traceback
                        traceback.print_exc()

        # 加载个人目录中的PDF文件
        if os.path.exists(personal_dir):
            for filename in os.listdir(personal_dir):
                if filename.lower().endswith('.pdf'):
                    file_path = os.path.join(personal_dir, filename)
                    try:
                        print(f"正在加载PDF文件: {file_path}")
                        loader = PyPDFLoader(file_path)
                        pdf_docs = loader.load()
                        # 为每个文档添加来源元数据
                        for doc in pdf_docs:
                            doc.metadata["source"] = filename
                            doc.metadata["path"] = file_path
                        documents.extend(pdf_docs)
                        print(f"成功加载PDF文件: {filename}, 页数: {len(pdf_docs)}")
                    except Exception as e:
                        print(f"加载个人PDF文件失败 {filename}: {str(e)}")
                        import traceback
                        traceback.print_exc()

        # 加载文档目录中的PDF文件
        if os.path.exists(documents_dir):
            for filename in os.listdir(documents_dir):
                if filename.lower().endswith('.pdf'):
                    file_path = os.path.join(documents_dir, filename)
                    try:
                        print(f"正在加载PDF文件: {file_path}")
                        loader = PyPDFLoader(file_path)
                        pdf_docs = loader.load()
                        # 为每个文档添加来源元数据
                        for doc in pdf_docs:
                            doc.metadata["source"] = filename
                            doc.metadata["path"] = file_path
                        documents.extend(pdf_docs)
                        print(f"成功加载PDF文件: {filename}, 页数: {len(pdf_docs)}")
                    except Exception as e:
                        print(f"加载文档目录PDF文件失败 {filename}: {str(e)}")
                        import traceback
                        traceback.print_exc()

        # 如果指定了目录，加载目录中的PDF文件
        if directory and os.path.exists(directory):
            for filename in os.listdir(directory):
                if filename.lower().endswith('.pdf'):
                    file_path = os.path.join(directory, filename)
                    try:
                        loader = PyPDFLoader(file_path)
                        pdf_docs = loader.load()
                        for doc in pdf_docs:
                            doc.metadata["source"] = filename
                            doc.metadata["path"] = file_path
                        documents.extend(pdf_docs)
                    except Exception as e:
                        print(f"加载指定目录PDF文件失败 {filename}: {str(e)}")
                        import traceback
                        traceback.print_exc()

        print(f"总共加载了 {len(documents)} 个文档")
        return documents
    except Exception as e:
        print(f"加载文档失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def initialize_vector_store():
    """初始化向量存储"""
    try:
        # 首先检查是否已经存在向量存储
        if os.path.exists(VECTOR_STORE_PATH):
            print(f"向量存储已存在于 {VECTOR_STORE_PATH}")
            return
        
        # 加载文档
        documents = load_documents()
        if not documents or len(documents) == 0:
            print("没有找到文档，创建空向量存储")
            
            # 创建空向量存储
            try:
                # 首先尝试Ollama嵌入
                try:
                    embeddings = OllamaEmbeddings(
                        model="nomic-embed-text", 
                        base_url="http://localhost:11434"
                    )
                    vector_store = FAISS.from_documents(
                        [Document(page_content="初始化文档", metadata={"source": "system"})], 
                        embeddings
                    )
                    vector_store.save_local(VECTOR_STORE_PATH)
                    print("已创建空向量存储，包含一个占位文档")
                    return
                except Exception as e:
                    print(f"使用Ollama创建空向量存储失败: {e}")
                    
                # 尝试使用HuggingFace嵌入
                try:
                    print("尝试使用HuggingFaceEmbeddings创建空向量存储...")
                    embeddings = HuggingFaceEmbeddings(
                        model_name="shibing624/text2vec-base-chinese",
                        cache_folder="./models_embeddings"
                    )
                    vector_store = FAISS.from_documents(
                        [Document(page_content="初始化文档", metadata={"source": "system"})], 
                        embeddings
                    )
                    vector_store.save_local(VECTOR_STORE_PATH)
                    print("已使用HuggingFace创建空向量存储")
                    return
                except Exception as e:
                    print(f"使用HuggingFace创建空向量存储失败: {e}")
                
                # 最后使用FakeEmbeddings
                print("使用FakeEmbeddings创建最小向量存储...")
                dummy_embedding = FakeEmbeddings(size=768)
                empty_store = FAISS.from_documents(
                    [Document(page_content="系统初始化", metadata={"source": "system"})], 
                    dummy_embedding
                )
                empty_store.save_local(VECTOR_STORE_PATH)
                print("已创建最小向量存储")
                return
            except Exception as e:
                print(f"创建空向量存储失败: {e}")
                return
        
        print(f"加载了 {len(documents)} 个文档")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        print(f"将文档分成了 {len(chunks)} 块")
        
        # 创建向量存储
        try:
            # 首先尝试使用Ollama嵌入（本地选项）
            try:
                print("尝试使用OllamaEmbeddings创建向量存储...")
                embeddings = OllamaEmbeddings(
                    model="nomic-embed-text", 
                    base_url="http://localhost:11434"
                )
                vector_store = FAISS.from_documents(chunks, embeddings)
                vector_store.save_local(VECTOR_STORE_PATH)
                print("成功使用OllamaEmbeddings创建向量存储")
                return
            except Exception as e:
                print(f"OllamaEmbeddings创建向量存储失败: {e}")
            
            # 如果Ollama失败，尝试使用HuggingFace（需要网络连接）
            try:
                print("尝试使用HuggingFaceEmbeddings创建向量存储...")
                embeddings = HuggingFaceEmbeddings(
                    model_name="shibing624/text2vec-base-chinese",
                    cache_folder="./models_embeddings"
                )
                vector_store = FAISS.from_documents(chunks, embeddings)
                vector_store.save_local(VECTOR_STORE_PATH)
                print("成功使用HuggingFaceEmbeddings创建向量存储")
                return
            except Exception as e:
                print(f"HuggingFaceEmbeddings创建向量存储失败: {e}")
        except Exception as e:
            print(f"创建向量存储失败: {e}")
            
            # 创建最小向量存储以允许系统运行
            try:
                print("创建最小向量存储...")
                dummy_embedding = FakeEmbeddings(size=768)
                empty_store = FAISS.from_texts(["系统初始化"], dummy_embedding)
                empty_store.save_local(VECTOR_STORE_PATH)
                print("已创建最小向量存储")
            except Exception as e:
                print(f"创建最小向量存储失败: {e}")
    except Exception as e:
        print(f"向量存储初始化过程中发生错误: {e}")

# 清除损坏的向量存储
def clear_vector_store():
    """清除向量存储文件夹"""
    try:
        if os.path.exists(VECTOR_STORE_PATH):
            import shutil
            shutil.rmtree(VECTOR_STORE_PATH)
            print(f"已清除向量存储文件夹: {VECTOR_STORE_PATH}")
    except Exception as e:
        print(f"清除向量存储文件夹失败: {e}")

def get_vector_store():
    """获取向量存储实例"""
    global vector_store
    
    # 如果已经初始化，直接返回
    if vector_store is not None:
        return vector_store
        
    try:
        # 检查向量存储是否已存在
        if os.path.exists(VECTOR_STORE_PATH):
            print(f"加载现有向量存储: {VECTOR_STORE_PATH}")
            
            # 尝试使用不同的嵌入模型（优先使用本地模型）
            embedding_models = [
                # 1. 优先使用Ollama嵌入（本地模型）
                lambda: OllamaEmbeddings(
                    model="nomic-embed-text",
                    base_url="http://localhost:11434"
                ),
                # 2. 尝试使用备用Ollama模型
                lambda: OllamaEmbeddings(
                    model="deepseek-r1:7b", 
                    base_url="http://localhost:11434"
                ),
                # 3. 尝试使用HuggingFace嵌入（需要网络连接）
                lambda: HuggingFaceEmbeddings(
                    model_name="shibing624/text2vec-base-chinese",
                    cache_folder="./models_embeddings"
                ),
                # 4. 兜底使用FakeEmbeddings
                lambda: FakeEmbeddings(size=768)
            ]
            
            # 尝试每个嵌入模型
            embeddings = None
            last_error = None
            
            for create_embeddings in embedding_models:
                try:
                    embeddings = create_embeddings()
                    # 测试嵌入模型是否可用
                    _ = embeddings.embed_query("测试")
                    print(f"成功初始化嵌入模型: {embeddings.__class__.__name__}")
                    break
                except Exception as e:
                    last_error = e
                    print(f"嵌入模型初始化失败: {str(e)}")
                    continue
            
            if embeddings is None:
                print(f"所有嵌入模型初始化失败，最后错误: {last_error}")
                
                # 强制使用FakeEmbeddings作为最后的备选
                embeddings = FakeEmbeddings(size=768)
                print("使用FakeEmbeddings作为备选")
            
            # 加载向量存储
            try:
                vector_store = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
                print(f"向量存储加载成功，索引大小: {vector_store.index.ntotal if hasattr(vector_store, 'index') else '未知'}")
                return vector_store
            except Exception as e:
                print(f"加载向量存储失败: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # 出错时尝试重建向量存储
                print("尝试重建向量存储...")
                clear_vector_store()
                return initialize_vector_store()
        else:
            # 如果向量存储不存在，初始化一个新的
            print(f"向量存储不存在，初始化新的向量存储")
            return initialize_vector_store()
    except Exception as e:
        print(f"获取向量存储失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 兜底返回空值
        vector_store = None
        return vector_store
        
def update_vector_store():
    """更新向量存储"""
    try:
        global vector_store
        
        # 加载文档
        documents = load_documents()
        if not documents or len(documents) == 0:
            print("警告: 没有找到文档，无法更新向量存储")
            return False
        
        print(f"找到 {len(documents)} 个文档，准备更新向量存储")
        
        # 文本分割
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        print(f"将文档分成了 {len(chunks)} 块")
        
        # 如果向量存储已存在，获取它
        if vector_store is None:
            vector_store = get_vector_store()
            
        # 如果仍然不存在，创建一个新的
        if vector_store is None:
            print("无法获取向量存储，将重新创建")
            clear_vector_store()
            initialize_vector_store()
            return False
            
        # 将文档添加到现有向量存储
        try:
            print("向现有向量存储添加文档...")
            vector_store.add_documents(chunks)
            vector_store.save_local(VECTOR_STORE_PATH)
            print(f"成功更新向量存储，当前索引大小: {vector_store.index.ntotal if hasattr(vector_store, 'index') else '未知'}")
            return True
        except Exception as e:
            print(f"向向量存储添加文档失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"更新向量存储失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 创建路由器
from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.get("/vector-store/update")
def api_update_vector_store():
    """API端点，用于更新向量存储"""
    try:
        success = update_vector_store()
        if success:
            return {"status": "success", "message": "向量存储已更新"}
        else:
            return {"status": "error", "message": "更新向量存储失败"}
    except Exception as e:
        return {"status": "error", "message": f"更新向量存储时出错: {str(e)}"}

@router.get("/vector-store/rebuild")
def api_rebuild_vector_store():
    """API端点，用于重建向量存储"""
    try:
        # 清除现有向量存储
        clear_vector_store()
            
        # 重新初始化向量存储
        initialize_vector_store()
        return {"status": "success", "message": "向量存储已重建"}
    except Exception as e:
        return {"status": "error", "message": f"重建向量存储时出错: {str(e)}"}
