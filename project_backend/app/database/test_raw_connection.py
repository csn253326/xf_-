import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect(
            user="postgres",
            password="zgyd10086",
            database="postgres",
            host="localhost",
            port=5432,
            ssl="prefer",
            timeout=60
        )
        version = await conn.fetchval("SELECT version()")
        print(f"✅ 连接成功！PostgreSQL版本: {version}")
        await conn.close()
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test())
