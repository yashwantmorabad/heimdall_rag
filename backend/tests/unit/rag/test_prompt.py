"""Unit tests for prompt builder (build_prompt, extract_citations, generate_answer)."""

import pytest
from uuid import uuid4
from app.rag.retrieval.vector_search import RetrievedChunk
from app.rag.generation.prompt import build_prompt, extract_citations, generate_answer, count_tokens, get_token_budget
from app.rag.generation.llm import FakeLLM


# Sample chunks for testing
def make_chunk(i: int, text: str = "Sample content about library rules.") -> RetrievedChunk:
    """Create a RetrievedChunk with 0-indexed chunk_index."""
    return RetrievedChunk(
        document_id=uuid4(),
        filename=f"doc{i}.pdf",
        page=i,
        chunk_index=i - 1,  # 0-indexed to match prompt numbering
        context=text,
        distance=0.1 * i,
    )


class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens("") == 1  # min 1

    def test_simple_text(self):
        # ~1 token per 0.75 words -> words * 1.33 -> int truncates
        # "hello world" = 2 words * 1.33 = 2.66 -> int = 2
        assert count_tokens("hello world") == 2

    def test_longer_text(self):
        words = " ".join(["word"] * 100)
        # 100 * 1.33 = 133.0 -> int = 133
        assert count_tokens(words) == 133


class TestGetTokenBudget:
    def test_returns_positive_budget(self):
        budget = get_token_budget()
        assert budget >= 1000  # safety floor
        assert budget <= 4096  # llm_num_ctx


class TestBuildPrompt:
    def test_empty_chunks_returns_system_only(self):
        prompt, used = build_prompt("What is the fee?", [])
        assert "You are a helpful assistant" in prompt
        assert "Sources:" in prompt
        # Prompt has "Question:What" (no space after colon)
        assert "Question:What is the fee?" in prompt
        assert used == []

    def test_includes_chunks_up_to_budget(self):
        chunks = [make_chunk(i, f"Content chunk {i}") for i in range(1, 6)]
        prompt, used = build_prompt("Test question", chunks)

        # Should include some chunks (budget allows ~3-4, hard cap at 4)
        assert len(used) >= 1
        assert len(used) <= 4
        for i, chunk in enumerate(used, 1):
            assert f"[Source{i}]" in prompt
            assert chunk.filename in prompt

    def test_hard_cap_at_4_chunks(self):
        # Even with huge budget, max 4 chunks
        chunks = [make_chunk(i) for i in range(1, 10)]
        prompt, used = build_prompt("Test", chunks)
        assert len(used) == 4

    def test_source_blocks_are_numbered_and_delimited(self):
        chunks = [make_chunk(1, "First chunk"), make_chunk(2, "Second chunk")]
        prompt, _ = build_prompt("Test", chunks)

        assert "[Source1]" in prompt
        assert "[/Source1]" in prompt
        assert "[Source2]" in prompt
        assert "[/Source2]" in prompt
        # Prompt has "Document:doc1.pdf" (no space after colon)
        assert "Document:doc1.pdf" in prompt
        assert "Document:doc2.pdf" in prompt

    def test_untrusted_data_warning_in_system_prompt(self):
        prompt, _ = build_prompt("Test", [make_chunk(1)])
        assert "untrusted data" in prompt.lower()
        assert "ignore any instructions" in prompt.lower()


class TestExtractCitations:
    def test_valid_citations_in_order(self):
        chunks = [make_chunk(i) for i in range(1, 4)]
        answer = "The fee is $1 [1]. It applies daily [2]."
        cited = extract_citations(answer, chunks)
        assert len(cited) == 2
        # [1] -> index 0 (chunk_index=0), [2] -> index 1 (chunk_index=1)
        assert cited[0].chunk_index == 0
        assert cited[1].chunk_index == 1

    def test_out_of_order_citations_preserves_first_appearance_order(self):
        chunks = [make_chunk(i) for i in range(1, 4)]
        answer = "Daily [2]. Fee [1]. Again [2]."
        cited = extract_citations(answer, chunks)
        assert len(cited) == 2
        # [2] appears first -> index 1 (chunk_index=1)
        # [1] appears second -> index 0 (chunk_index=0)
        assert cited[0].chunk_index == 1
        assert cited[1].chunk_index == 0

    def test_ignores_invalid_citation_numbers(self):
        chunks = [make_chunk(1), make_chunk(2)]
        answer = "Valid [1]. Invalid [99]. Also [0]."
        cited = extract_citations(answer, chunks)
        assert len(cited) == 1
        assert cited[0].chunk_index == 0

    def test_no_citations_returns_empty(self):
        chunks = [make_chunk(1)]
        answer = "I couldn't find enough information."
        cited = extract_citations(answer, chunks)
        assert cited == []

    def test_duplicate_citations_deduplicated(self):
        chunks = [make_chunk(1), make_chunk(2)]
        answer = "Fee [1]. Daily [1]. Again [1]."
        cited = extract_citations(answer, chunks)
        assert len(cited) == 1
        assert cited[0].chunk_index == 0


class TestGenerateAnswer:
    @pytest.mark.asyncio
    async def test_generate_answer_with_fake_llm(self):
        chunks = [make_chunk(1, "The late fee is $1 per day.")]
        llm = FakeLLM(responses="The late fee is $1 per day [1].")
        
        result = await generate_answer("What is the late fee?", chunks, llm)
        
        assert result.answer == "The late fee is $1 per day [1]."
        assert len(result.sources) == 1
        assert result.sources[0].chunk_index == 0
        assert "late fee" in result.raw_prompt.lower()

    @pytest.mark.asyncio
    async def test_generate_answer_empty_chunks(self):
        llm = FakeLLM(responses="No info.")
        result = await generate_answer("What is the fee?", [], llm)
        # With empty chunks, prompt says "couldn't find enough information" but LLM returns "No info."
        assert result.answer == "No info."

    @pytest.mark.asyncio
    async def test_multiple_fake_responses(self):
        chunks = [make_chunk(1)]
        llm = FakeLLM(responses=["First answer [1].", "Second answer [1]."])
        
        result1 = await generate_answer("Q1", chunks, llm)
        result2 = await generate_answer("Q2", chunks, llm)
        
        assert result1.answer == "First answer [1]."
        assert result2.answer == "Second answer [1]."