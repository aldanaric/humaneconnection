# Managed Humane Connection RAG Index

This directory is generated from `data/rag/source_documents/` by
`python scripts/rebuild_rag.py`. Do not edit generated vector files manually.

The index combines sparse TF-IDF retrieval with dense LSA retrieval. It is rebuilt
as a complete unit whenever a source document, build schema, or chunking setting
changes.
