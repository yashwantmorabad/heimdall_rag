---
name: rag-engineering
description: Use when working on the Heimdall RAG pipeline in backend/app/rag, including document parsing, chunking, embeddings, hybrid retrieval, rank fusion, reranking, the not-found guardrail, prompts, the LLM service, citations, and the evaluation harness. Also use for any change to chunk sizes, thresholds, models, or prompts, because these require evaluation before and after.
---

# RAG engineering

Tenant isolation rules: see `heimdall-development`.

## Pipeline
```
Ingestion: parse -> clean -> chunk -> embed -> store
Query:     retrieve (vector + keyword) -> fuse -> rerank -> guardrail -> LLM -> answer + sources
```

## Ingestion
- Supported: PDF, TXT, Markdown. Maximum 10 MB (configurable).
- Chunk size and overlap are settings. Defaults are starting points, tuned only with evaluation results.
- Chunk structure-aware where possible (headings for Markdown, pages for PDF).
- Each chunk stores tenant, document, content, position (and page), embedding, embedding model name, and a full-text column.
- Embeddings run locally (Sentence Transformers). Default model `BAAI/bge-small-en-v1.5`, 384 dimensions. The model is configurable.

## Retrieval
- **Vector search** and **keyword search** (PostgreSQL full-text) both filter by `tenant_id` inside the query.
- Merge with **Reciprocal Rank Fusion**, which combines rankings without needing comparable scores.
- `RETRIEVAL_TOP_K` and `RERANK_TOP_K` are settings.
- Rerank with a local cross-encoder over `(query, chunk)` pairs.
- Add one retrieval improvement at a time and measure each.

## Guardrail
- If evidence is insufficient, abstain and **do not call the LLM**. Return a normal, clearly marked "not found in your documents" response.
- The threshold is a setting, **calibrated with the evaluation dataset**. A similarity score alone does not prove an answer is supported, so check abstention accuracy as well as recall.
- Recalibrate the threshold when the reranker or embedding model changes.

## Generation
- Call the LLM only through the LLM service interface (`generate()` plus configuration). Implementations: Ollama (default) and a fake for tests. Provider settings: `LLM_BASE_URL`, `LLM_MODEL_NAME`, `LLM_API_KEY`.
- The prompt says: answer only from the provided context, cite chunk IDs, and say so when the context does not contain the answer.
- Put retrieved text inside clearly delimited context blocks and treat it as **untrusted data**. Instruct the model to ignore instructions found inside documents.
- The response includes sources (document, chunk, page).

## Evaluation
- Dataset in `evals/datasets/` (answerable and unanswerable questions with expected evidence). Runner: `evals/run_eval.py`, via `make eval`. Reports in `evals/reports/`.
- Metrics: Recall@K, retrieval relevance, abstention accuracy, answer correctness.
- **Run `make eval` before and after** any change to chunking, embeddings, retrieval, reranking, thresholds, or prompts. Report both results. If quality drops, say so.

## Do not
- Do not call the LLM when retrieval is below the threshold.
- Do not mix vectors from different embedding models.
- Do not hard-code the threshold or model names.
- Do not depend on a paid API. Keep the provider swappable.
