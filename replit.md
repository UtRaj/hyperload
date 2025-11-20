# Product Importer - Replit Project

## Overview
This is a production-ready product importer web application built for Acme Inc. It handles large-scale CSV imports (500,000+ products) with real-time progress tracking, complete product management, and webhook integration.

## Recent Changes (November 20, 2025)
- Initial project setup with FastAPI, SQLAlchemy, Celery, and Redis
- Implemented all 4 user stories from requirements
- Created database models with case-insensitive SKU handling
- Built async CSV import with chunked processing and SSE progress updates
- Developed complete REST API with product CRUD and webhook management
- Created responsive frontend UI with Bootstrap 5
- Configured workflows for Redis, Celery worker, and FastAPI server
- Added comprehensive documentation and sample files

## Project Architecture

### Backend Stack
- **FastAPI**: Modern async web framework for high-performance APIs
- **SQLAlchemy**: ORM for database operations with PostgreSQL
- **Celery**: Distributed task queue for async CSV processing
- **Redis**: Message broker for Celery and SSE pub/sub
- **Pandas**: Efficient CSV parsing for large files
- **Pydantic**: Data validation and serialization

### Frontend Stack
- **Bootstrap 5**: Responsive UI components
- **Vanilla JavaScript**: Event-driven UI with Fetch API
- **Server-Sent Events**: Real-time progress updates

### Database
- **PostgreSQL**: Production database with case-insensitive indexing
- **Models**: 
  - Product (sku, name, description, active)
  - Webhook (url, event_type, enabled)

## Key Features Implemented

### Story 1: CSV Upload with Progress
- Drag-and-drop file upload interface
- Real-time progress bar with SSE
- Async processing with Celery (handles 30s timeout limits)
- Automatic SKU-based deduplication (case-insensitive)
- Chunked processing (1000 rows per batch) for memory efficiency

### Story 2: Product Management
- CRUD operations for products
- Advanced filtering (SKU, name, description, active status)
- Pagination (20 items per page)
- Modal forms for create/edit
- Active/Inactive status toggle

### Story 3: Bulk Delete
- Delete all products with double confirmation
- Visual feedback and notifications
- Safe transaction handling

### Story 4: Webhook Management
- Add/Edit/Delete webhooks through UI
- Event types: product.created, product.updated, product.deleted
- Test webhooks with response time and status
- Async webhook dispatching (non-blocking)

## Development Workflow

### Running the Application
The workflow "Product Importer" starts all required services:
1. Redis server (background)
2. Celery worker (background)
3. FastAPI application (port 5000)

Access at: https://[replit-url]/

### Making Changes
- Backend: Edit files in `app/` directory
- Frontend: Edit `templates/index.html`, `static/css/style.css`, `static/js/app.js`
- Auto-reload: FastAPI runs with `--reload` flag for development

### Database Operations
- Models: `app/models.py`
- Initialize: `python -c "from app.database import init_db; init_db()"`
- Migrations: Can use Alembic for production migrations

## Environment Variables
Required environment variables (already configured in Replit):
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string (defaults to localhost:6379)
- `SESSION_SECRET`: For future session management

## File Structure
```
/
├── app/                    # Backend application
│   ├── main.py            # FastAPI app & API endpoints
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── database.py        # DB connection
│   ├── celery_app.py      # Celery config
│   └── tasks.py           # Async tasks
├── static/                # Frontend assets
│   ├── css/style.css      # Custom styles
│   └── js/app.js          # Frontend logic
├── templates/             # HTML templates
│   └── index.html         # Main UI
├── start_all.sh           # Combined startup script
├── sample_products.csv    # Test data
├── requirements.txt       # Python dependencies
└── README.md             # Full documentation
```

## Technical Decisions

### Why Celery?
- Handles long-running CSV imports (exceeds platform timeouts)
- Distributed processing for scalability
- Task progress tracking and status updates
- Non-blocking webhook dispatching

### Why SSE over WebSockets?
- Simpler one-way communication for progress updates
- No need for bidirectional messaging
- Better compatibility with HTTP infrastructure
- Automatic reconnection handling

### Why Chunked Processing?
- Prevents memory issues with large files
- Provides granular progress updates
- Allows transaction management per chunk
- Better error recovery

### Case-Insensitive SKU Handling
- Index on `LOWER(sku)` for fast lookups
- Prevents duplicate SKUs with different cases
- Maintains original SKU casing in database

## User Preferences
- No specific preferences recorded yet
- Follow Python PEP 8 style guide
- Prefer clear, documented code over clever solutions
- Prioritize scalability and maintainability

## Deployment Notes

### Platform Compatibility
Designed for deployment on:
- Render.com (recommended)
- Railway.app
- Heroku
- AWS/GCP

### Production Checklist
- [ ] Set production environment variables
- [ ] Configure CORS allowed origins
- [ ] Use production-grade WSGI server (Gunicorn)
- [ ] Set up monitoring and logging
- [ ] Configure Redis persistence
- [ ] Set up database backups
- [ ] Add SSL/TLS certificates
- [ ] Implement rate limiting
- [ ] Add user authentication (future)

## Testing
- Sample CSV file included: `sample_products.csv`
- Test webhooks using webhook.site or requestbin.com
- All API endpoints documented at `/docs` (Swagger UI)

## Next Steps / Future Enhancements
1. Batch validation with error reporting
2. CSV export functionality
3. Webhook retry mechanism
4. User authentication & authorization
5. API rate limiting
6. Audit logging
7. Metrics dashboard
8. Advanced search with full-text search

## Commit Strategy
- Clean, descriptive commits
- Each feature in separate commit
- Meaningful commit messages following conventions
- Regular commits showing development progress

## Notes
- Application built for backend engineer assessment
- Emphasizes code quality, scalability, and production-readiness
- All requirements from specification document implemented
- Ready for deployment and demonstration
