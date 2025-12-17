# Changelog

All notable changes to this project will be documented in this file.

## main branch v1.1 (2025-12-17)

### Prvious Version
- Albert Public Demo v1.0 (2025-12-2)

### 🚀 New Features
- **Semantic Caching (SQLite)**: Implemented a local persistent cache (`data/embeddings.db`) in `EmailAggregator`. This stores email and query embeddings to reduce Gemini API calls and improve search latency.
- **Context Caching**: Enabled `ContextCacheConfig` in the `ConciergeAgent` (TTL: 3600s). This offloads repetitive context processing to Google's ADK infrastructure, improving performance for long sessions.
- **Smart Logging**: Implemented "Smart Logging" logic. The system now defaults to minimal summary logs for successful interactions to reduce noise, while retaining full verbose logging for errors or debug sessions.

### 🧹 Refactoring & Improvements
- **Simplified Email Fetching**: Refactored `fetch_emails` in `email_aggregator.py`. Removed complex legacy label resolution logic in favor of a clean, date-based broad fetch for semantic search candidates.
- **Agent Initialization**: Updated `ConciergeAgent` to use the correct `albert_concierge` app name and fixed `InMemoryRunner` initialization.
- **E2E Testing**: Updated `test_e2e.py` to match the new synchronous `process_request` signature and validated the agent workflow.

### 📖 Documentation
- **Repo URL**: Corrected the repository URL in `README.md` to point to `nomadmanhattan/Albert_Public_Demo`.


