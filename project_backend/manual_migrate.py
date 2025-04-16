# 在项目根目录创建 manual_migrate.py
import sys
import asyncio
from project_backend.app.database.base import async_engine, Base
from project_backend.app.database.models.frame import FrameResult
from project_backend.app.database.models.task import Task
from project_backend.app.database.models.metadata import ModelMetadata
from sqlalchemy import text

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    try:
        async with async_engine.connect() as conn:
            ping = await conn.scalar(text("SELECT 1"))
            print(f"✅ 数据库心跳检测成功: {ping}")
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()
            tables = await conn.scalar(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
            )
            print(f"✅ 表结构创建完成，当前共有 {tables} 张表")
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
