import asyncpg
import pytest
import logging

logging.basicConfig(level=logging.DEBUG)

@pytest.mark.asyncio
async def test_connection():
    try:
        # 记录连接参数
        logging.debug(f"尝试连接: postgres://postgres:***@localhost:5432/postgres")

        conn = await asyncpg.connect(
            user="root",
            password="zgyd10086",  # 请确认实际密码
            database="sys",
            host="localhost",
            timeout=10  # 增加超时设置
        )

        # 验证连接存活
        logging.debug(f"连接状态: {'开启' if not conn.is_closed() else '关闭'}")
        assert not conn.is_closed(), "连接未激活"

        # 执行扩展测试
        version = await conn.fetchval("SELECT version()")
        logging.debug(f"PostgreSQL版本: {version}")

    except Exception as e:
        logging.error(f"连接异常: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            await conn.close()
            logging.debug("连接已关闭")
