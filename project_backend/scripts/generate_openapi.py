# \scripts\generate_openapi.py
import json
from fastapi.openapi.utils import get_openapi
from project_backend.app.main import app


def generate_openapi_spec():
    """生成最新的OpenAPI规范文件"""
    spec = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description=app.description,
        contact=app.contact,
        tags=app.openapi_tags
    )

    with open("docs/openapi.json", "w") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    generate_openapi_spec()