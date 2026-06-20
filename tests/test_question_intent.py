"""Tests for question-type prompt policy."""
from code_agent import question_intent


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


def test_prompt_contains_best_practice():
    p = question_intent.prompt("宕机日志 ASSERT failed")
    assert "当前问题类型：宕机/错误日志分析" in p
    assert "find_assert_context" in p
