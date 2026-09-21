"""/query response carries scope_flag / answer_type / matched_entity_count.

graph_rag is stubbed (no Neo4j / LLM), so this checks only main.py's wiring
of confidence_tier into the response model.
"""
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_RESULT = {}


def _fake_graph_rag(question):
    return dict(_RESULT)


@pytest.fixture()
def client(monkeypatch):
    fake = types.ModuleType("graph_rag")
    fake.graph_rag = _fake_graph_rag
    fake._get_pipeline = lambda: None
    monkeypatch.setitem(sys.modules, "graph_rag", fake)
    try:  # main.py patches st.cache_resource at import; a stub is enough here
        import streamlit  # noqa: F401
    except ImportError:
        monkeypatch.setitem(sys.modules, "streamlit", types.ModuleType("streamlit"))
    sys.modules.pop("main", None)
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    import main
    yield fastapi_testclient.TestClient(main.app)
    sys.modules.pop("main", None)


def _ask(client, **result):
    _RESULT.clear()
    _RESULT.update(result)
    r = client.post("/query", json={"question": "q"})
    assert r.status_code == 200
    return r.json()


def test_in_domain_is_standard_and_substantive(client):
    b = _ask(client, answer="A steady drop indicates an oil leak. [D3_c19]",
             matched_entities=[{"id": "SY_oil"}])
    assert (b["scope_flag"], b["answer_type"], b["matched_entity_count"]) == ("STANDARD", "substantive", 1)


def test_out_of_domain_is_low_and_refusal(client):
    b = _ask(client, answer="I'm sorry, but I don't have any information on that.", matched_entities=[])
    assert (b["scope_flag"], b["answer_type"], b["matched_entity_count"]) == ("LOW", "refusal", 0)


def test_degraded_is_low_even_with_entities(client):
    b = _ask(client, answer="Retrieval failed before an answer could be generated.",
             matched_entities=[{"id": "x"}], retrieval_error="boom")
    assert b["scope_flag"] == "LOW" and b["degraded"] is True


def test_standard_refusal_is_reported_separately(client):
    b = _ask(client, answer="The graph facts do not contain any information about X.",
             matched_entities=[{"id": "a"}, {"id": "b"}])
    assert (b["scope_flag"], b["answer_type"]) == ("STANDARD", "refusal")


@pytest.mark.parametrize("blank", [None, "", "  " + chr(10)])
def test_empty_llm_answer_is_degraded_not_500(client, blank):
    b = _ask(client, answer=blank, matched_entities=[{"id": "x"}])
    assert b["degraded"] is True and "generation_error" in b["degraded_fields"]
    assert (b["scope_flag"], b["answer_type"]) == ("LOW", "empty")
    assert b["answer"]
