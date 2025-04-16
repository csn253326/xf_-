# {{ title }} API 文档

版本: {{ version }}

{% for path, methods in paths.items() %}
## `{{ path }}`

{% for method, spec in methods.items() %}
### {{ method|upper }} {{ spec.summary }}

​**​功能描述​**​  
{{ spec.description|default("该接口暂无详细描述", true)|trim|safe }}

{% if spec.requestBody %}
​**​请求参数​**​  
```json
{{ spec.requestBody|tojson(indent=2, ensure_ascii=False) }}