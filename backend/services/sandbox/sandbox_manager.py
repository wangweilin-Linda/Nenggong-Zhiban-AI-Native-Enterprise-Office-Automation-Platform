import os
import uuid
import pandas as pd
from typing import Optional
from loguru import logger # type: ignore
from config.settings import settings

class SandboxManager:
    def __init__(self):
        self.sandbox_base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'sandboxes')
        os.makedirs(self.sandbox_base, exist_ok=True)

    async def create_sandbox(self, content: bytes) -> str:
        """创建一个新的沙盒环境"""
        try:
            # 生成唯一的沙盒ID
            sandbox_id = str(uuid.uuid4())
            sandbox_dir = os.path.join(self.sandbox_base, sandbox_id)
            os.makedirs(sandbox_dir, exist_ok=True)

            # 保存上传的文件
            file_path = os.path.join(sandbox_dir, 'input.csv')
            with open(file_path, 'wb') as f:
                f.write(content)

            # 创建结果文件
            result_path = os.path.join(sandbox_dir, 'result.json')
            with open(result_path, 'w', encoding='utf-8') as f:
                f.write('{"status": "pending"}')

            return sandbox_id
        except Exception as e:
            logger.error(f"创建沙盒失败: {str(e)}")
            raise

    async def run_analysis(self, sandbox_id: str) -> bool:
        """运行分析任务"""
        try:
            sandbox_dir = os.path.join(self.sandbox_base, sandbox_id)
            if not os.path.exists(sandbox_dir):
                raise ValueError(f"沙盒不存在: {sandbox_id}")

            input_file = os.path.join(sandbox_dir, 'input.csv')
            result_file = os.path.join(sandbox_dir, 'result.json')

            # 读取CSV文件
            df = pd.read_csv(input_file)

            # 执行基本统计分析
            analysis_result = {
                'status': 'completed',
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'summary': df.describe().to_dict(),
                'missing_values': df.isnull().sum().to_dict()
            }

            # 保存分析结果
            import json
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            logger.error(f"运行分析失败: {str(e)}")
            return False

    async def get_result(self, sandbox_id: str) -> Optional[dict]:
        """获取分析结果"""
        try:
            result_file = os.path.join(self.sandbox_base, sandbox_id, 'result.json')
            if not os.path.exists(result_file):
                raise ValueError(f"结果文件不存在: {result_file}")

            import json
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)

            if result.get('status') == 'completed':
                return result
            return None
        except Exception as e:
            logger.error(f"获取结果失败: {str(e)}")
            raise