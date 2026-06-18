from code_agent import response_policy


def test_allows_structured_description():
    text = "能力：崩溃诊断\n约束：栈和日志不能同时为空\n下一步：确认服务地址"
    assert response_policy.enforce(text) == text
    assert response_policy.contains_forbidden_content(text) is False


def test_removes_fenced_code_block():
    text = "说明：\n```python\nprint('x')\n```\n结论：只保留描述"
    out = response_policy.enforce(text)
    assert "print" not in out
    assert "```" not in out
    assert "输出策略" in out


def test_removes_shell_commands():
    text = "步骤：\ncurl http://127.0.0.1:8900/health\n完成后检查结果"
    out = response_policy.enforce(text)
    assert "curl" not in out
    assert "完成后检查结果" in out


def test_removes_json_config_sample():
    text = '{\n  "mcpServers": {\n    "code-agent": {"url": "http://x"}\n  }\n}'
    out = response_policy.enforce(text)
    assert "mcpServers" not in out
    assert "url" not in out
    assert out == "（已按输出策略省略实现内容，仅保留结构化描述。）"


def test_removes_function_like_code():
    text = "实现：\ndef run():\n    return 1\n说明：不要展开实现"
    out = response_policy.enforce(text)
    assert "def run" not in out
    assert "return 1" not in out
    assert "说明：不要展开实现" in out


def test_technical_mode_keeps_implementation_content():
    text = "实现：\n```python\nprint(1)\n```"
    assert response_policy.enforce(text, mode="technical") == text


def test_keeps_chinese_field_description_lines():
    """A structured field description must not be mistaken for a YAML config."""
    text = "字段说明：\n- host: 主机地址\n- port: 端口号是 8900\n- path: 资源路径"
    out = response_policy.enforce(text)
    assert out == text
    assert response_policy.contains_forbidden_content(text) is False


def test_keeps_prose_starting_with_english_keyword():
    text = "return 字段在配置中表示返回点。\ndef 命令未被使用。"
    assert response_policy.enforce(text) == text


def test_keeps_indented_yaml_like_chinese_kv():
    text = "映射关系：\n  host: 主机地址\n  type: 战斗类型"
    assert response_policy.enforce(text) == text
