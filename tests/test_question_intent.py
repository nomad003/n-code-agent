"""Tests for question-type prompt policy."""
from code_agent.core import question_intent


def test_classify_crash_stack():
    q = "#0  SceneMgr::Update() at scene.cpp:10\n#1  main() at main.cpp:2"
    assert question_intent.classify(q) == "crash_stack"


def test_classify_outage_log():
    assert question_intent.classify("[ERROR] ASSERT_FALSE player id invalid 1001") == "outage_log"


def test_classify_config_impl():
    assert question_intent.classify("这个配置项怎么加载和生效？") == "config_impl"


def test_classify_table_like_identifier_as_config_impl():
    assert question_intent.classify("SpawnFollow 和 SpawnLimit 数量不对怎么查？") == "config_impl"


def test_classify_feature_impl():
    assert question_intent.classify("匹配功能是怎么实现的，调用链是什么？") == "feature_impl"


def test_classify_unclear_question_requires_clarification():
    assert question_intent.classify("看一下") == "clarify"
    assert question_intent.classify("怎么配置") == "clarify"
    assert question_intent.classify("这个问题怎么处理") == "clarify"


def test_classify_clear_config_and_feature_do_not_clarify():
    assert question_intent.classify("怪物技能怎么配置？") == "config_impl"
    assert question_intent.classify("Buff 添加流程怎么走？") == "feature_impl"


def test_prompt_contains_best_practice():
    p = question_intent.prompt("宕机日志 ASSERT failed")
    assert "当前问题类型：宕机/错误日志分析" in p
    assert "find_assert_context" in p


def test_config_prompt_requires_table_fields_in_plain():
    p = question_intent.prompt("怪物怎么配置？", "config_impl")
    assert "配置明细表格" in p
    assert "配置面、对应表/配置项、核心字段、字段用途" in p
    assert "Mermaid 关系图" in p
    assert "technical 模式再补加载文件、函数名和代码位置" in p
    assert "不要只输出抽象模块说明" in p


def test_feature_prompt_requires_flow_not_config_details_in_plain():
    p = question_intent.prompt("怪物索敌功能流程是什么？", "feature_impl")
    assert "Mermaid 图解" in p
    assert "结构化步骤" in p
    assert "配置只作为输入点说明，不展开字段明细，除非用户追问配置" in p


def test_clarify_prompt_asks_before_tools():
    p = question_intent.prompt("看一下")
    assert "当前问题类型：需要澄清的问题" in p
    assert "不要调用代码检索工具" in p
    assert "crash 堆栈、宕机/错误日志、配置实现、功能实现" in p


def test_clarifying_response_lists_required_inputs():
    r = question_intent.clarifying_response("看一下")
    assert "我还不能确定" in r
    assert "配置实现" in r
    assert "配置表名或字段名" in r
    assert "功能实现" in r
