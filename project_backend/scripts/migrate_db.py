# \scripts\migrate_db.py
import argparse
import subprocess
import logging
import os
import time
from pathlib import Path
from alembic.config import Config
from alembic import command
from project_backend.app.config.settings import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db-migrate")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class MigrationManager:
    def __init__(self, env: str = "dev"):
        self.alembic_cfg = self._get_alembic_config(env)

    def _get_alembic_config(self, env: str) -> Config:
        """动态加载环境配置"""
        env_mapping = {
            "dev": "DEV_DATABASE_URL",
            "test": "TEST_DATABASE_URL",
            "prod": "PROD_DATABASE_URL"
        }
        os.environ["TARGET_DB"] = os.getenv(env_mapping[env], settings.DATABASE_URL)

        cfg = Config(PROJECT_ROOT / "alembic.ini")
        cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
        cfg.set_main_option("sqlalchemy.url", os.environ["TARGET_DB"])
        return cfg

    def check_database_health(self, timeout: int = 30):
        """数据库健康检查"""
        logger.info("正在检查数据库连接...")
        retries = 0
        while retries < timeout:
            try:
                subprocess.run(
                    ["pg_isready", "-d", os.environ["TARGET_DB"]],
                    check=True,
                    capture_output=True
                )
                logger.info("数据库连接正常")
                return True
            except subprocess.CalledProcessError:
                retries += 1
                logger.warning(f"数据库未就绪，重试 {retries}/{timeout}")
                time.sleep(1)
        logger.error("数据库连接失败")
        return False

    def run_migration(self, revision: str = "head", autogenerate: bool = False):
        """执行迁移操作"""
        if autogenerate:
            command.revision(self.alembic_cfg, autogenerate=True, message="auto-generate")
        command.upgrade(self.alembic_cfg, revision)

    def seed_initial_data(self):
        """初始化基础数据"""
        logger.info("正在初始化种子数据...")
        subprocess.run(
            ["python", "app/database/seed_data.py"],
            check=True
        )


def main():
    parser = argparse.ArgumentParser(description="智能数据库迁移工具")
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev", help="目标环境")
    parser.add_argument("--seed", action="store_true", help="是否初始化种子数据")
    args = parser.parse_args()

    migrator = MigrationManager(args.env)

    if not migrator.check_database_health():
        exit(1)

    try:
        logger.info(f"开始 {args.env} 环境数据库迁移")
        migrator.run_migration()

        if args.seed:
            migrator.seed_initial_data()

        logger.info("数据库迁移成功完成")
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()