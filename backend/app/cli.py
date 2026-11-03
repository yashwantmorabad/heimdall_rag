"CLI for heimdall-rag: ingest documents, ask questions (dev tool)."

import sys
import time
import asyncio
from pathlib import Path
from uuid import UUID

import typer

from app.rag.ingestion.pipeline import ingest_file
from app.rag.retrieval.vector_search import search_chunks
from app.rag.generation.llm import OllamaLLM
from app.rag.generation.prompt import generate_answer

#default dev tenant
DEFAULT_TENANT_ID=UUID("00000000-0000-0000-0000-000000000001")
app=typer.Typer(help="Heimdall RAG CLI: ingest documents, ask questions.")

@app.command()
def ask(
    question:str=typer.Argument(...,help="Question to ask"),
    tenant_id:UUID=typer.Option(DEFAULT_TENANT_ID,"--tenant-id",help="Tenant UUID"),
    top_k:int=typer.Option(20,"--top-k",help="Number of chunks to retrieve"),
    ):
    """
    Ask a question and get an answer with sources and per-step timings.

    Example:
        python -m app.cli ask "What is the library late fee?"
    """
    typer.echo(f"Question:{question}")
    typer.echo(f"Tenant:{tenant_id}")

    llm=OllamaLLM()
    timings={}

    try:
        #step 1: Embed+vector search
        t0=time.perf_counter()
        chunks=asyncio.run(search_chunks(tenant_id,question,top_k))
        timings["search_ms"]=int((time.perf_counter()-t0)*1000)
        typer.echo(f"Retrieved {len(chunks)} chunks in {timings['search_ms']}ms")

        if not chunks:
            typer.echo("No relevant chunks found for the question.")
            return

        #step 2: Build prompt+call llm
        t1=time.perf_counter()
        result=asyncio.run(generate_answer(question,chunks,llm))
        timings["llm_ms"]=int((time.perf_counter()-t1)*1000)

        #output
        typer.echo(f"Answer:\n{result.answer}")

        if result.sources:
            typer.echo("\n--- Sources ---")
            for i, src in enumerate(result.sources, 1):
                page = src.page if src.page else "N/A"
                typer.echo(f"  [{i}] {src.filename} (page {page}) — distance: {src.distance:.4f}")

        typer.echo(f"\nTimings (ms): {timings}")
        typer.echo(f"Search: {timings['search_ms']}ms,") 
        typer.echo(f"LLM: {timings['llm_ms']}ms")
        typer.echo(f"Total: {timings['search_ms']+timings['llm_ms']}ms")

    except RuntimeError as e:
        if "Cannot reach Ollama" in str(e):
            typer.echo(f"\nError: {e}", err=True)
            typer.echo("Start Ollama with: ollama serve", err=True)
        else:
            typer.echo(f"\nError: {e}", err=True)
        sys.exit(1)

    except Exception as e:
        typer.echo(f"\nUnexpected error: {e}", err=True)
        sys.exit(1)
@app.command()
def ingest(
    file_path: Path = typer.Argument(..., exists=True, readable=True, help="File to ingest"),
    tenant_id: UUID = typer.Option(DEFAULT_TENANT_ID, "--tenant-id", help="Tenant UUID"),
):
    """
    Ingest a document: parse, clean, chunk, embed, store.

    Example:
    python -m app.cli ingest ./sample.pdf --tenant-id 00000000-0000-0000-0000-000000000001
    """
    typer.echo(f"Ingesting {file_path} for tenant {tenant_id}...")

    try:
        import asyncio
        stored = asyncio.run(ingest_file(file_path, tenant_id))
        typer.echo(f"Done. Chunks stored: {stored}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    app()