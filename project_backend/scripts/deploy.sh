#!/usr/bin/env bash

set -euo pipefail

ENV=${1:-dev}  # 默认开发环境
COMPOSE_FILE="docker-compose.$ENV.yml"
TIMEOUT=60

# 环境校验
declare -A ENV_MAP=(
    ["dev"]="开发环境"
    ["prod"]="生产环境"
)
if [[ ! -v ENV_MAP[$ENV] ]]; then
    echo "❌ 错误环境参数: $ENV"
    exit 1
fi

echo "🚀 正在部署 ${ENV_MAP[$ENV]}..."

# 清理旧容器
cleanup() {
    echo "🧹 清理旧部署..."
    docker-compose -f $COMPOSE_FILE down --volumes --remove-orphans
}

# 等待服务就绪
wait_for_service() {
    local host=$1 port=$2
    echo "⌛ 正在等待 $host:$port..."
    while ! nc -z $host $port; do
        sleep 1
        ((TIMEOUT--))
        if [[ $TIMEOUT -le 0 ]]; then
            echo "❌ 服务 $host:$port 启动超时"
            exit 1
        fi
    done
    echo "✅ $host:$port 已就绪"
}

# 执行数据库迁移
run_migrations() {
    echo "💾 正在执行数据库迁移..."
    docker-compose -f $COMPOSE_FILE run --rm \
        -e TARGET_ENV=$ENV \
        app python scripts/migrate_db.py --env $ENV --seed
}

main() {
    cleanup

    echo "🔧 构建Docker镜像..."
    docker-compose -f $COMPOSE_FILE build

    echo "🛫 启动服务..."
    docker-compose -f $COMPOSE_FILE up -d

    # 等待核心服务
    wait_for_service postgres 5432
    wait_for_service redis 6379
    wait_for_service minio 9000

    run_migrations

    echo "📊 初始化存储桶..."
    docker-compose -f $COMPOSE_FILE run --rm minio-mc \
        mc alias set minio http://minio:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
    docker-compose -f $COMPOSE_FILE run --rm minio-mc \
        mc mb --ignore-existing minio/user-uploads

    echo "🎉 部署成功完成！"
}

main