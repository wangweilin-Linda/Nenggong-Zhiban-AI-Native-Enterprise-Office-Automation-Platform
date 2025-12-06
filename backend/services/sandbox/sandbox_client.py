import httpx
from typing import Optional, Dict, Any
from loguru import logger # type: ignore

class SandboxClient:
    def __init__(self, base_url: str = "http://localhost:8002/api"):
        """初始化沙盒客户端
        
        Args:
            base_url: sandbox服务的基础URL
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def upload_file(self, file_content: bytes) -> Dict[str, Any]:
        """上传文件到沙盒服务
        
        Args:
            file_content: 文件内容
            
        Returns:
            包含task_id的响应字典
        """
        try:
            files = {"file": ("input.csv", file_content, "text/csv")}
            response = await self.client.post(f"{self.base_url}/sandbox/v1/analysis/upload", files=files)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"上传文件到沙盒服务失败: {str(e)}")
            raise
    
    async def start_analysis(self, task_id: str, code: Optional[str] = None) -> Dict[str, Any]:
        """启动分析任务
        
        Args:
            task_id: 任务ID
            code: 可选的Python分析代码
            
        Returns:
            任务状态响应
        """
        try:
            # 如果提供了代码，则将代码发送到沙盒服务
            if code:
                logger.info(f"发送自定义分析代码到沙盒服务，代码长度: {len(code)}")
                data = {"code": code}
                # 打印请求URL，便于调试
                request_url = f"{self.base_url}/sandbox/v1/analysis/{task_id}/analyze"
                logger.info(f"请求URL: {request_url}")
                
                try:
                    response = await self.client.post(
                        request_url,
                        json=data
                    )
                    logger.info(f"沙盒服务响应状态码: {response.status_code}")
                except Exception as e:
                    logger.error(f"请求沙盒服务失败: {str(e)}")
                    raise
            else:
                # 使用默认分析脚本
                logger.info(f"使用默认分析脚本")
                response = await self.client.post(f"{self.base_url}/sandbox/v1/analysis/{task_id}/analyze")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"启动分析任务失败: {str(e)}")
            raise
    
    async def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取分析结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            分析结果字典，如果任务未完成则返回None
        """
        try:
            response = await self.client.get(f"{self.base_url}/sandbox/v1/result/{task_id}")
            
            # 如果返回状态码是202（处理中），返回None
            if response.status_code == 202:
                return None
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取分析结果失败: {str(e)}")
            raise
            
    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典
        """
        try:
            response = await self.client.get(f"{self.base_url}/sandbox/v1/status/{task_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}")
            raise
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()