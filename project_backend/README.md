# 智能视觉分析平台后端系统

[![FastAPI](https://img.shields.io/badge/FastAPI-0.68.2-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.10](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://www.python.org/)

> 基于深度学习的实时视频流分析系统，提供图像分类、边缘检测和实时视频处理能力

---

##  核心特性

- ​**​多模态处理​**​  
   支持图像分类（性别识别）  
   Canny边缘检测算法  
   实时视频流分析（WebSocket）

- ​**​智能资源管控​**​  
   令牌桶算法流量控制  
   JWT安全认证体系  
   Prometheus性能监控

- ​**​高效架构设计​**​  
   异步数据库访问（AsyncPG）  
   模块化微服务架构  
   Celery分布式任务队列

---

## 🛠 技术栈

| 领域           | 技术选型                      |
|--------------|---------------------------|
| ​**​核心框架​**​ | FastAPI, SQLAlchemy, Celery |
| ​**​存储系统​**​ | PostgreSQL, MinIO, Redis  |
| ​**​AI推理​**​ | ONNX Runtime, OpenCV      |
| ​**​运维监控​**​ | Prometheus, Grafana, Docker |
| ​**​部署架构​**​ | Nginx反向代理   |

---

##  项目结构

```bash
project_backend/
├── app/                 # 核心应用模块
│   ├── config/          # 配置管理中心
│   ├── database/        # 数据持久层
│   ├── ml_models/       # 模型管理引擎
│   ├── routes/          # API端点服务
│   └── services/        # 底层服务组件
├── docker/              # 容器化配置
├── docs/                # 系统文档
├── github/              # API文档的自动化生成与同步
├── scripts/             # 自动化运维脚本
├── test_images/         # 测试图集
├── tests/               # 测试用例
├── docker-compose.yml   # 服务架构及组件说明
├── pyproject.toml       # 项目依赖管理
└── README.md            # 项目介绍