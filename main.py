"""Entry point for RFP Intelligence Platform CLI and API Server."""

import argparse
import sys
from pathlib import Path
import uvicorn

from app.config import get_settings
from app.indexing.service import IndexingService
from app.ingestion.service import IngestionService
from app.logging import logger
from app.retrieval.hybrid import HybridSearchEngine
from app.schemas.canonical import SearchFilters


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Start the FastAPI application with Uvicorn."""
    logger.info(f"Starting RFP Intelligence Platform API server on {host}:{port}")
    uvicorn.run("app.api.main:app", host=host, port=port, reload=reload)


def run_ingest(bid_path: str, output_dir: str = "outputs/ingestion"):
    """Ingest a bid directory and output canonical JSON."""
    target_path = Path(bid_path).resolve()
    if not target_path.exists():
        logger.error(f"Target bid path does not exist: {target_path}")
        sys.exit(1)

    logger.info(f"Ingesting bid documents from: {target_path}")
    result = IngestionService.ingest_folder(target_path)
    out_file = IngestionService.save_canonical_json(result, output_dir=output_dir)

    print("\n" + "=" * 60)
    print(f"INGESTION SUMMARY FOR BID: {result.bid_id}")
    print("=" * 60)
    print(f"Files Discovered:      {result.summary.get('total_files_discovered', 0)}")
    print(f"Documents Ingested:    {result.summary.get('total_documents_ingested', 0)}")
    print("Classifications:")
    for doc_type, count in result.summary.get("documents_by_type", {}).items():
        print(f"  - {doc_type:15s}: {count}")
    print(f"Total Pages Processed: {result.summary.get('total_pages', 0)}")
    print(f"Tables Extracted:      {result.summary.get('total_tables', 0)}")
    print(f"Total Characters:      {result.summary.get('total_characters', 0)}")
    print(f"Warnings:              {result.summary.get('warnings_count', 0)}")
    print(f"Errors:                {result.summary.get('errors_count', 0)}")
    print(f"Canonical JSON Saved:  {out_file}")
    print("=" * 60 + "\n")


def run_index(bid_path: str, bid_id: str | None = None):
    """Index an RFP folder through ingestion -> chunking -> vector & BM25 indexing."""
    target_path = Path(bid_path).resolve()
    if not target_path.exists():
        logger.error(f"Target path does not exist: {target_path}")
        sys.exit(1)

    service = IndexingService()
    report = service.index_folder(folder_path=target_path, bid_id=bid_id)

    print("\n" + "=" * 60)
    print(f"INDEXING REPORT FOR BID: {report.bid_id}")
    print("=" * 60)
    print(f"Status:                {report.status}")
    print(f"Documents Ingested:    {report.documents_ingested}")
    print(f"Chunks Created:        {report.chunks_created}")
    print(f"Embeddings Cached:     {report.embeddings_cached}")
    print(f"New Embeddings Gen:    {report.embeddings_requested}")
    print(f"Vectors Upserted:      {report.vectors_upserted}")
    print(f"BM25 Corpus Size:      {report.bm25_indexed_chunks}")
    print(f"Elapsed Time:          {report.elapsed_seconds}s")
    print("=" * 60 + "\n")


def run_search(
    query: str,
    top_k: int = 5,
    bid_id: str | None = None,
    doc_type: str | None = None,
    addendum: int | None = None,
    use_reranker: bool = True,
):
    """Execute hybrid search with optional reranker and display formatted results with provenance."""
    filters = SearchFilters(
        bid_id=bid_id,
        document_type=doc_type,
        addendum_number=addendum,
    )
    engine = HybridSearchEngine()
    response = engine.search(
        query=query,
        top_k=top_k,
        filters=filters,
        use_reranker=use_reranker,
    )

    meta = response.retrieval_metadata
    print("\n" + "=" * 80)
    print(f"RETRIEVAL RESULTS: \"{response.query}\"")
    print(
        f"Total: {response.total_results} | Reranker: {meta.get('reranking_status')} ({meta.get('reranker_model', 'None')}) | "
        f"Latency: {meta.get('total_latency_ms')}ms (dense: {meta.get('dense_latency_ms')}ms, bm25: {meta.get('bm25_latency_ms')}ms, rerank: {meta.get('rerank_latency_ms', 0)}ms)"
    )
    print("=" * 80)

    if not response.results:
        print("No matching evidence found.")
        print("=" * 80 + "\n")
        return

    for res in response.results:
        ev = res.evidence
        print("\n" + "-" * 50)
        print(f"Rank:             {res.rank}")
        print(f"Score:            {res.score:.4f}" + (f" (RRF score: {res.previous_score:.4f})" if res.previous_score is not None else ""))
        print(f"Retrieval source: {ev.retrieval_source or res.retrieval_source}")
        print(f"Bid:              {ev.bid_id}")
        print(f"File:             {ev.file_name}")
        print(f"Page:             {ev.page_number}")
        print(f"Document type:    {ev.document_type}")
        print(f"Section:          {ev.section}")
        print(f"Addendum:         {ev.addendum_number}")
        print(f"Chunk ID:         {res.chunk_id}")
        print("\nTEXT:")
        print(res.text)
        print("-" * 50)
    print("=" * 80 + "\n")


def main():
    """Main CLI entrypoint parser."""
    parser = argparse.ArgumentParser(
        description="RFP Intelligence Platform — RAG Search Engine & Multi-Agent System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a bid document folder")
    ingest_parser.add_argument("--bid", type=str, required=True, help="Path to bid folder")
    ingest_parser.add_argument("--output-dir", type=str, default="outputs/ingestion")

    # Index command
    index_parser = subparsers.add_parser("index", help="Index an RFP folder into Qdrant & BM25")
    index_parser.add_argument("--bid", type=str, required=True, help="Path to bid folder")
    index_parser.add_argument("--bid-id", type=str, default=None, help="Explicit bid ID override")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search indexed documents")
    search_parser.add_argument("query", type=str, help="Search query string")
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    search_parser.add_argument("--bid-id", type=str, default=None, help="Filter by bid ID")
    search_parser.add_argument("--doc-type", type=str, default=None, help="Filter by doc type")
    search_parser.add_argument("--addendum", type=int, default=None, help="Filter by addendum number")
    search_parser.add_argument("--no-rerank", action="store_true", help="Disable Jina listwise reranker")

    # Server command
    server_parser = subparsers.add_parser("server", help="Run the FastAPI application server")
    server_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address")
    server_parser.add_argument("--port", type=int, default=8000, help="Port number")
    server_parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    args = parser.parse_args()

    if args.command == "ingest":
        run_ingest(bid_path=args.bid, output_dir=args.output_dir)
    elif args.command == "index":
        run_index(bid_path=args.bid, bid_id=args.bid_id)
    elif args.command == "search":
        run_search(
            query=args.query,
            top_k=args.top_k,
            bid_id=args.bid_id,
            doc_type=args.doc_type,
            addendum=args.addendum,
            use_reranker=not args.no_rerank,
        )
    elif args.command == "server":
        run_server(host=args.host, port=args.port, reload=not args.no_reload)
    else:
        run_server()


if __name__ == "__main__":
    main()

