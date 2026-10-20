"CLI for heimdall-rag ingestion (dev tool)"

from sqlalchemy import true
import sys
from pathlib import Path
from uuid import UUID

import typer

from app.rag.ingestion.pipeline import ingest_file

#Defualt dec tenant(fixed UUID for local development)
DEFAULT_TENANT_ID=UUID("00000000-0000-0000-0000-000000000001")

app= typer.Typer(help="Heimdall ingestion CLI")

@app.command()
def ingest(
    file_path: Path=typer.Argument(..., exists=True,readable=True,help="File to ingest"),
    tenant_id: UUID=typer.Option(DEFAULT_TENANT_ID,"--tenant-id",help="Tenant UUID"),
):
    """
    Ingest a document: parse, clean, chunk, embed, store.

    Example:
    python -m app.cli ingest ./sample.pdf --tenant-id 00000000-0000-0000-0000-000000000001
    """
    typer.echo(f"Ingesting {file_path} for tenant{tenant_id}...")

    try:
        #Run async pipeline
        import asyncio
        stored = asyncio.run(ingest_file(file_path,tenant_id))
        typer.echo(f"Done. Chunks stored:{stored}")
    except Exception as e:
        typer.echo(f"Error: {e}",err=True)
        sys.exit(1)

if __name__ == "__main__":
    app()

# Line-by-line explanation
# Line(s):	What it does
# import typer: 	Modern CLI library using type hints
# DEFAULT_TENANT_ID: 	Fixed UUID for local dev (no auth needed)
# app = typer.Typer(): 	Creates CLI app
# @app.command(): 	Decorator: makes ingest a subcommand
# file_path: Path = typer.Argument(..., exists=True, readable=True)	: Required positional arg. Typer validates file exists & is readable.
# tenant_id: UUID = typer.Option(DEFAULT_TENANT_ID, "--tenant-id")	: Optional flag --tenant-id, defaults to dev tenant
# asyncio.run(ingest_file(...))	: Runs async function from sync context (CLI is sync)
# typer.echo(...)	: Prints to stdout (or stderr with err=True)
# sys.exit(1)	: Exits with error code on failure

# Key Python features for beginners
# 1. typer.Argument / typer.Option — Declarative CLI: type hints + metadata = automatic parsing, validation, help text.
# 2. Path with exists=True, readable=True — Typer validates the file before your code runs.
# 3. UUID type hint — Typer parses string → UUID object automatically.
# 4. asyncio.run() — Bridge from sync (CLI) to async (pipeline). Creates event loop, runs coroutine, closes loop.
# 5. if __name__ == "__main__": app() — Allows python -m app.cli entry point.