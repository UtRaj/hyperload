# Product Importer - Acme Inc

A high-performance web application for importing and managing products from CSV files, built for scalability and designed to handle large datasets (up to 500,000+ records).

## Features

### Story 1: CSV File Upload with Real-time Progress
- Upload large CSV files (up to 500,000 products) through an intuitive drag-and-drop interface
- Real-time progress tracking with Server-Sent Events (SSE)
- Automatic duplicate handling based on case-insensitive SKU matching
- Background processing with Celery for handling long-running imports
- Visual feedback: progress bar, percentage, and status messages

### Story 2: Product Management
- Complete CRUD operations for products
- Advanced filtering by SKU, name, description, and active status
- Paginated product listing with clean navigation
- Inline editing with modal forms
- Active/Inactive status management
- Responsive, minimalist design

### Story 3: Bulk Delete Operations
- Delete all products with double confirmation
- Protected with confirmation dialogs
- Real-time feedback and success notifications
- Optimized for large-scale deletions

### Story 4: Webhook Configuration
- Add, edit, test, and delete webhooks through the UI
- Support for multiple event types:
  - `product.created`
  - `product.updated`
  - `product.deleted`
- Enable/disable webhooks individually
- Test webhooks with response time and status code feedback
- Async webhook dispatching for non-blocking operations

## Technology Stack

**Backend:**
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **PostgreSQL** - Production-grade relational database
- **Celery** - Distributed task queue for async processing
- **Redis** - Message broker and result backend
- **Pandas** - Efficient CSV parsing for large files
- **SSE-Starlette** - Server-Sent Events for real-time updates

**Frontend:**
- **Bootstrap 5** - Responsive UI framework
- **Vanilla JavaScript** - No framework overhead
- **EventSource API** - Real-time progress updates

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis

### Local Development

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables:**
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost/dbname"
   export REDIS_URL="redis://localhost:6379/0"
   ```

3. **Initialize Database:**
   ```bash
   python -c "from app.database import init_db; init_db()"
   ```

4. **Start Services:**
   
   Option 1 - All-in-one (recommended for development):
   ```bash
   bash start_all.sh
   ```
   
   Option 2 - Individual services:
   ```bash
   # Terminal 1: Start Redis
   redis-server --port 6379
   
   # Terminal 2: Start Celery Worker
   celery -A app.celery_app worker --loglevel=info --concurrency=2
   
   # Terminal 3: Start FastAPI Application
   uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
   ```

5. **Access the Application:**
   - Web UI: http://localhost:5000
   - API Docs: http://localhost:5000/docs

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and endpoints
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── database.py          # Database connection and session
│   ├── celery_app.py        # Celery configuration
│   └── tasks.py             # Celery async tasks
├── static/
│   ├── css/
│   │   └── style.css        # Custom styles
│   └── js/
│       └── app.js           # Frontend JavaScript
├── templates/
│   └── index.html           # Main UI template
├── requirements.txt         # Python dependencies
├── start_all.sh            # Combined startup script
├── sample_products.csv     # Sample CSV for testing
└── README.md               # This file
```

## Database Schema

### Products Table
- `id`: Integer (Primary Key)
- `sku`: String (Unique, Case-Insensitive Index)
- `name`: String (Required)
- `description`: Text (Optional)
- `active`: Boolean (Default: True)
- `created_at`: DateTime
- `updated_at`: DateTime

### Webhooks Table
- `id`: Integer (Primary Key)
- `url`: String (Required)
- `event_type`: String (Required)
- `enabled`: Boolean (Default: True)
- `created_at`: DateTime
- `updated_at`: DateTime

## API Endpoints

### Products
- `GET /api/products` - List products (with pagination and filters)
- `POST /api/products` - Create a new product
- `GET /api/products/{id}` - Get product by ID
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product
- `DELETE /api/products` - Bulk delete all products

### File Upload
- `POST /api/upload` - Upload CSV file for import
- `GET /api/progress/{task_id}` - SSE stream for progress updates

### Webhooks
- `GET /api/webhooks` - List all webhooks
- `POST /api/webhooks` - Create new webhook
- `PUT /api/webhooks/{id}` - Update webhook
- `DELETE /api/webhooks/{id}` - Delete webhook
- `POST /api/webhooks/{id}/test` - Test webhook

## CSV File Format

The CSV file should contain the following columns:

```csv
sku,name,description
PROD-001,Product Name,Product description (optional)
PROD-002,Another Product,Another description
```

**Required Columns:**
- `sku`: Unique product identifier (case-insensitive)
- `name`: Product name

**Optional Columns:**
- `description`: Product description

## Key Features & Implementation Details

### Scalability
- **Streaming CSV Reading**: Uses Python's native csv.DictReader for row-by-row streaming, avoiding full-file memory load
- **Chunked Processing**: CSV imports process 1,000 rows per chunk to optimize memory usage and database throughput
- **In-Memory Deduplication**: Maintains a set of seen SKUs (~10-20MB for 500K SKUs) for cross-chunk deduplication
- **Bulk Database Operations**: Uses batch queries (IN clause) instead of row-by-row queries
- **Connection Pooling**: Database connection pool (10 connections, 20 max overflow)
- **Async Workers**: Celery workers handle long-running tasks without blocking the main application
- **Efficient Queries**: Case-insensitive SKU indexing for fast lookups

### Performance Optimizations
- **Native CSV Parsing**: Python's csv module for memory-efficient streaming
- **Bulk Operations**: Batch database queries using SQLAlchemy IN clauses and add_all()
- **Redis Caching**: Task status cached for quick retrieval
- **Async Webhooks**: Non-blocking webhook dispatching via Celery tasks

### Real-time Updates
- **Server-Sent Events (SSE)**: Live progress updates without polling
- **Redis Pub/Sub**: Efficient message broadcasting
- **Status Persistence**: Progress cached for 1 hour

### Production-Ready Features
- **Error Handling**: Comprehensive error messages and validation
- **Duplicate Management**: Automatic SKU-based deduplication
- **Transaction Safety**: Database rollback on errors
- **Graceful Degradation**: Webhook failures don't block operations

## Deployment

The application is designed to be deployed on any platform that supports:
- Python applications
- PostgreSQL databases
- Redis instances
- Worker processes (Celery)

### Recommended Platforms
- **Render.com**: Free tier supports all requirements
- **Railway.app**: Easy deployment with PostgreSQL and Redis
- **Heroku**: Classic PaaS with worker dynos
- **AWS/GCP**: Full control with EC2/Compute Engine

### Deployment Configuration

Set the following environment variables:
```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

### Handling Platform Timeouts

Platforms like Heroku have 30-second request timeouts. This application handles this elegantly:

1. **File Upload**: Immediately returns with a task ID (< 1 second)
2. **Background Processing**: Celery worker processes the CSV asynchronously
3. **Progress Updates**: SSE stream provides real-time updates without maintaining HTTP connection
4. **Result Retrieval**: Progress persisted in Redis for later queries

## Testing

### Sample CSV Upload
A `sample_products.csv` file is included for testing the upload functionality.

### Test Webhook
You can use services like webhook.site or requestbin.com to test webhook functionality:
1. Go to https://webhook.site
2. Copy the unique URL
3. Add it as a webhook in the application
4. Perform product operations to trigger webhooks

## Security Considerations

- **Input Validation**: All inputs validated with Pydantic schemas
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **XSS Protection**: Frontend sanitizes user inputs
- **CORS**: Configure allowed origins in production
- **Environment Variables**: Sensitive data stored in environment variables

## Code Quality

The codebase follows Python best practices:
- **PEP 8** style guide compliance
- **Type hints** for better IDE support
- **Modular architecture** for maintainability
- **Clear separation of concerns** (models, schemas, endpoints, tasks)
- **Comprehensive error handling**
- **Clean, readable code** over clever hacks

## Future Enhancements

- Batch validation reporting with detailed error logs
- Advanced filtering with date ranges
- CSV export functionality
- Webhook retry mechanism with exponential backoff
- Audit logging for all operations
- User authentication and authorization
- API rate limiting
- Metrics and monitoring dashboard

## License

Proprietary - Acme Inc.

## Support

For issues or questions, please contact the development team.
