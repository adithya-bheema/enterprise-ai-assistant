from langchain_core.messages import AIMessage

from app.agent.graph import FALLBACK_ANSWER, GradeResult, RouteDecision, build_graph


class _Structured:
    def __init__(self, value):
        self.value = value

    def invoke(self, _messages):
        return self.value


class StubLLM:
    """Minimal stand-in for ChatGoogleGenerativeAI."""

    def __init__(self, needs_retrieval=True, relevant_ids=(1,), text="Answer [1]"):
        self.needs_retrieval = needs_retrieval
        self.relevant_ids = list(relevant_ids)
        self.text = text

    def with_structured_output(self, schema):
        if schema is RouteDecision:
            return _Structured(RouteDecision(needs_retrieval=self.needs_retrieval))
        if schema is GradeResult:
            return _Structured(GradeResult(relevant_ids=self.relevant_ids))
        raise AssertionError(f"unexpected schema {schema}")

    def invoke(self, _messages):
        return AIMessage(content=self.text)


class CountingRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.calls = []

    def __call__(self, query, config):
        self.calls.append(query)
        return self.docs


DOCS = [
    {"chunk_id": 1, "document_id": 10, "filename": "handbook.pdf", "page": 4,
     "content": "Employees receive 25 days of paid leave.", "rrf": 0.03},
    {"chunk_id": 2, "document_id": 11, "filename": "faq.md", "page": None,
     "content": "Unrelated text about parking.", "rrf": 0.02},
]
START_STATE = {"question": "How much leave do I get?", "history": [], "attempts": 0}


def test_chitchat_skips_retrieval():
    retriever = CountingRetriever(DOCS)
    graph = build_graph(StubLLM(needs_retrieval=False, text="Hi there!"), retriever)
    result = graph.invoke({**START_STATE, "question": "hello"})
    assert result["answer"] == "Hi there!"
    assert result["citations"] == []
    assert retriever.calls == []


def test_grounded_answer_returns_only_cited_relevant_sources():
    retriever = CountingRetriever(DOCS)
    graph = build_graph(StubLLM(relevant_ids=[1], text="25 days [1]"), retriever)
    result = graph.invoke(START_STATE)
    assert result["answer"] == "25 days [1]"
    assert [c["filename"] for c in result["citations"]] == ["handbook.pdf"]
    assert result["citations"][0]["page"] == 4
    assert len(retriever.calls) == 1


def test_irrelevant_results_trigger_one_rewrite_then_fallback():
    retriever = CountingRetriever(DOCS)
    graph = build_graph(StubLLM(relevant_ids=[], text="rewritten query"), retriever, max_rewrites=1)
    result = graph.invoke(START_STATE)
    assert result["answer"] == FALLBACK_ANSWER
    assert result["citations"] == []
    assert retriever.calls == ["How much leave do I get?", "rewritten query"]


def test_empty_retrieval_goes_to_fallback_without_rewrites_when_disabled():
    retriever = CountingRetriever([])
    graph = build_graph(StubLLM(), retriever, max_rewrites=0)
    result = graph.invoke(START_STATE)
    assert result["answer"] == FALLBACK_ANSWER
    assert len(retriever.calls) == 1
