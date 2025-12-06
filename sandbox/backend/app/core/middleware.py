from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
import time
from typing import Callable
from .exceptions import AppException

async def error_handler_middleware(request: Request, call_next: Callable):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request processed in {process_time:.2f}s: {request.method} {request.url}")
        return response
    except AppException as e:
        logger.warning(
            f"Application error: {str(e)}\n"
            f"URL: {request.url}\n"
            f"Method: {request.method}\n"
            f"Client: {request.client.host}"
        )
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.detail, "data": e.data}
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error: {str(e)}\n"
            f"URL: {request.url}\n"
            f"Method: {request.method}\n"
            f"Client: {request.client.host}"
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )