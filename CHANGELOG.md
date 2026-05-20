# Changelog

All notable changes to StartupIntel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- User Management & Authentication system with JWT tokens
- Organization-based multi-tenant architecture
- API key management with scoped permissions
- File upload support with S3/MinIO backends
- Virus scanning integration (ClamAV)
- Image thumbnail generation
- Email notification system (SendGrid, AWS SES)
- Slack notification integration
- Elasticsearch integration for advanced search
- Feature flag system for gradual rollouts
- Prometheus metrics endpoint
- Redis response caching
- Batch operations endpoint
- WebSocket support for real-time updates
- Full-text search with PostgreSQL
- Soft delete functionality
- Export functionality (CSV, JSON)
- Production-ready Docker setup
- Kubernetes manifests
- GitHub Actions CI/CD pipeline

### Security
- Implemented JWT-based authentication
- Added API key authentication alternative
- Password strength validation
- Role-based access control (RBAC)
- Input sanitization
- Rate limiting
- CORS configuration
- Circuit breaker pattern for external APIs

### Infrastructure
- Multi-stage Dockerfile for production
- Complete docker-compose stack
- Kubernetes deployment manifests
- Horizontal Pod Autoscaler
- Pod Disruption Budget
- SSL/TLS with cert-manager
- Prometheus monitoring
- Grafana dashboards

## [0.3.0] - 2024-XX-XX

### Added
- All 8 bot implementations (Runway, Obituary, Term, Pivot, PMF, Accelerator, Investor, Acqui)
- FastAPI REST API with full CRUD operations
- PostgreSQL database with SQLAlchemy async
- Neo4j graph database integration
- Redis caching layer
- FAISS-based RAG retrieval
- LLM clients for Groq and Ollama
- Data ingestion connectors (Crunchbase, GitHub, LinkedIn, etc.)
- Event streaming foundation
- Health check endpoints
- Request ID middleware
- Gzip compression

## [0.2.0] - 2024-XX-XX

### Added
- BaseBot abstraction layer
- RunwayBot initial implementation
- Database models for startups, investors, accelerators
- Alembic migrations
- Database seeding script
- Basic FastAPI setup

## [0.1.0] - 2024-XX-XX

### Added
- Initial project structure
- Basic documentation
- Requirements and dependencies
- Docker setup

