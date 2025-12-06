import os
from PyPDF2 import PdfReader
from langchain.docstore.document import Document as LangchainDocument

def load_documents():
    # 从数据库加载公文内容
    from database import SessionLocal
    from models import Document as DBDocument
    import json

    db = SessionLocal()
    docs = db.query(DBDocument).all()
    documents = []

    for doc in docs:
        # 添加公文内容
        content = f"标题: {doc.title}\n发布时间: {doc.publish_time}\n发布单位: {doc.publish_unit}\n内容: {doc.content}"
        documents.append(LangchainDocument(page_content=content, metadata={"id": doc.id}))

        # 添加PDF附件内容
        attachments = json.loads(doc.attachments)
        for attachment in attachments:
            pdf_path = os.path.join("../knowledgeBase", attachment)
            if os.path.exists(pdf_path):
                reader = PdfReader(pdf_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                documents.append(LangchainDocument(page_content=text, metadata={"source": attachment}))
    
    db.close()
    return documents