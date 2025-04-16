# app/database/base.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio
from sqlalchemy import text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from project_backend.app.config.settings import settings
from contextlib import asynccontextmanager
from sqlalchemy import select, JSON
from project_backend.app.database.declarative_base import Base
import logging
import pymysql

# ------------------------- 核心配置 -------------------------
# 异步引擎配置（优化连接池）
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG_MODE,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # MySQL需要更频繁回收连接
    pool_pre_ping=True,
    connect_args={
        "charset": "utf8mb4",  # 强制字符集
        "ssl": {"ca": "/path/to/ca.pem"} if settings.DB_USE_SSL else {}
    }
)


# 异步会话工厂（优化自动提交策略）
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 避免异步中对象状态问题
    autoflush=False,
    future=True
    )

# ------------------------- 生命周期管理 -------------------------
async def init_db():
    """验证数据库连接池可用性"""
    from project_backend.app.database.models.frame import FrameResult
    from project_backend.app.database.models.task import Task
    from project_backend.app.database.models.metadata import ModelMetadata
    try:
        async with async_engine.connect() as conn:
            # 设置MySQL字符集
            await conn.execute(text("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"))
            await conn.run_sync(Base.metadata.create_all)
            logging.info("数据库连接池初始化完成")
    except Exception as e:
        logging.critical("数据库连接失败: %s", str(e))
        raise

async def close_db():
    """释放连接池资源"""
    await async_engine.dispose()
    logging.info("数据库连接池已关闭")

# ------------------------- 依赖注入增强 -------------------------
@asynccontextmanager
async def get_db() -> AsyncSession:
    """支持重试机制的数据库会话获取"""
    max_retries = 3
    for attempt in range(max_retries):
        session = None
        try:
            session = AsyncSessionLocal()
            yield session
            await session.commit()
            break
        except Exception as e:
            if session:
                await session.rollback()
            if attempt == max_retries - 1:
                logging.error(f"数据库连接失败（重试{max_retries}次）: {str(e)}")
                raise
            logging.warning(f"数据库连接重试 {attempt + 1}/{max_retries}")
            await asyncio.sleep(0.1 * (attempt + 1))  # 指数退避
        finally:
            if session:
                await session.close()

# ------------------------- 视频处理专用扩展 -------------------------
class VideoProcessingDAL:
    """视频处理数据访问层（封装常见操作）"""
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_save_results(self, frame_results: list, batch_size=1000):
        # 修改为MySQL的UPSERT语法
        from project_backend.app.database.models.frame import FrameResult

        # 分批次处理
        for i in range(0, len(frame_results), batch_size):
            batch = frame_results[i:i + batch_size]
            insert_stmt = mysql_insert(FrameResult).values(
                [r.to_dict() for r in batch]
            )

            # 冲突处理（假设主键为id）
            on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(
                {k: insert_stmt.inserted[k] for k in batch[0].to_dict().keys() if k != 'id'}
            )
            await self.db.execute(on_duplicate_key_stmt)
            await self.db.commit()

    async def get_model_metadata(self, model_name: str):
        """获取模型元数据（增加缓存机制）"""
        from project_backend.app.database.models.metadata import ModelMetadata

        # 使用带缓存的查询
        result = await self.db.execute(
            select(ModelMetadata)
            .execution_options(populate_existing=True)  # 强制刷新缓存
            .where(ModelMetadata.name == model_name)
        )
        return result.scalars().first()

    # 新增分页查询方法
    async def paginated_query(self, model_class, page: int = 1, per_page: int = 100):
        """MySQL优化分页查询"""
        offset_val = (page - 1) * per_page
        result = await self.db.execute(
            select(model_class)
            .order_by(model_class.id)
            .limit(per_page)
            .offset(offset_val)
        )
        return result.scalars().all()