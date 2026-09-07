"""Regression tests for the W1-gate run-1 failure: Qwen registers <tool_call>
tags as SPECIAL tokens, so a skip_special_tokens decode strips them and every
call parses as a final answer (job 47885374: 20/20 episodes, zero turns).
The parser must accept tagged, fenced, and bare-JSON calling conventions."""
from mcpguardlite.agent.policy import _parse_tool_call


CALL = {"name": "fs.read", "arguments": {"path": "/docs/report_0.txt"}}


def test_tagged_form():
    r = '<tool_call>\n{"name": "fs.read", "arguments": {"path": "/docs/report_0.txt"}}\n</tool_call>'
    assert _parse_tool_call(r) == CALL


def test_bare_json_after_special_token_stripping():
    # exactly what run 1 saw: the tags were special tokens and got stripped
    r = '{"name": "fs.read", "arguments": {"path": "/docs/report_0.txt"}}'
    assert _parse_tool_call(r) == CALL


def test_fenced_form():
    r = 'I will call the tool.\n```json\n{"name": "fs.read", "arguments": {"path": "/docs/report_0.txt"}}\n```'
    assert _parse_tool_call(r) == CALL


def test_preamble_then_tagged():
    r = 'Let me read the file first.\n<tool_call>{"name": "fs.read", "arguments": {"path": "/docs/report_0.txt"}}</tool_call>'
    assert _parse_tool_call(r) == CALL


def test_unclosed_tag_form():
    """The EXACT reply observed in the local CPU repro of run 1: the 1.5B model
    emits the opening tag + JSON, then stops at end-of-turn WITHOUT the closing
    </tool_call>. The strict two-tag regex missed this; the bare-JSON fallback
    must catch it."""
    r = '<tool_call>{"name": "fs.read", "arguments": {"path": "/docs/report_0.txt"}}'
    assert _parse_tool_call(r) == CALL


def test_final_answer_is_not_a_call():
    assert _parse_tool_call("FINAL: 4821") is None
    assert _parse_tool_call("The number is 4821.") is None
