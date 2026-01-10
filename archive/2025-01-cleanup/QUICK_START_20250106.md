# 🚀 Quick Start Guide - ONIX Catalog API

**Date**: 2025-01-06

---

## ⚡ 60-Second Setup

### 1. Install Dependencies
```bash
cd /home/ubuntu/onix_project
pip install -r requirements.txt
```

### 2. Configure Database
```bash
# Create .env file (if not exists)
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/onix_db
DEBUG=False
EOF
```

### 3. Start Server
```bash
python main.py
```

### 4. Test API
```bash
# Health check
curl http://localhost:8000/health

# List products
curl http://localhost:8000/api/v1/products

# OpenAPI docs
open http://localhost:8000/docs
```

---

## 📡 API Endpoints

### GET /api/v1/products
**List all active products**

```bash
curl 'http://localhost:8000/api/v1/products?page=1&limit=20'
```

**Parameters:**
- `page` (int, default=1): Page number
- `limit` (int, default=20): Items per page (1-100)

**Response:**
```json
{
  "total": 103,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": "uuid-...",
      "isbn": "978-...",
      "title": "Book Title",
      "format": "BB",
      "format_label": "Cloth over boards",
      "type": "physical",
      "is_buyable": true,
      "is_archived": false
    }
  ]
}
```

---

### GET /api/v1/products/{id}
**Get full product details**

```bash
curl 'http://localhost:8000/api/v1/products/[product-uuid]'
```

**Response:**
```json
{
  "id": "...",
  "isbn": "978-...",
  "ean": "...",
  "title": {
    "title": "Book Title",
    "subtitle": "Subtitle"
  },
  "description": "Long description...",
  "format": "BB",
  "format_label": "Cloth over boards",
  "type": "physical",
  "status": "04",
  "status_label": "Active",
  "languages": ["uk", "en"],
  "subjects": [
    {"code": "Y", "label": "Fiction"}
  ],
  "contributors": [
    {
      "name": "Author Name",
      "role": "A01",
      "role_label": "By (author)"
    }
  ],
  "pages": 256,
  "height_mm": 210,
  "width_mm": 140,
  "weight_g": 320,
  "publisher": "Publisher Name",
  "created_at": "2025-01-06T10:00:00",
  "updated_at": "2025-01-06T10:00:00"
}
```

---

### GET /api/v1/search
**Search products with filters**

```bash
# Text search
curl 'http://localhost:8000/api/v1/search?q=Quantum'

# Filter by THEMA code
curl 'http://localhost:8000/api/v1/search?thema=Y'

# Filter by format
curl 'http://localhost:8000/api/v1/search?format=BB'

# Combined search
curl 'http://localhost:8000/api/v1/search?q=Quantum&thema=Y&format=BB&page=1&limit=20'
```

**Parameters:**
- `q` (string, optional): Text search (title, author)
- `thema` (string, optional): THEMA subject code (e.g., "Y", "YF", "YFB")
- `format` (string, optional): ONIX product format (e.g., "BB", "BC", "EA")
- `page` (int, default=1): Page number
- `limit` (int, default=20): Items per page (1-100)

**Response:** Same as `/products` list endpoint

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run API Tests Only
```bash
pytest tests/test_api_layers.py -v
```

### Check Test Coverage
```bash
pytest --cov=app tests/
```

### Result
```
14 passed ✅
```

---

## 📊 Database Info

**Active Products**: 103  
**ONIX Codes**: 4,748  
**THEMA Subjects**: 9,187  

### Database Tables
```
catalog_products          (103 rows)
catalog_titles           (103 rows)
catalog_subjects         (103 rows)
catalog_contributors     (~206 rows)
catalog_extents          (~103 rows)
catalog_languages        (~103 rows)
catalog_publishing_dates (~103 rows)
catalog_text_contents    (~30 rows)
catalog_measures         (~206 rows)
ref_onix_codelists       (4,748 rows)
ref_thema_subjects       (9,187 rows)
```

---

## 🔧 Architecture Layers

```
┌─────────────────────────────────┐
│  FastAPI Router Layer           │ HTTP endpoints
├─────────────────────────────────┤
│  CatalogService Layer           │ Business logic + DTO mapping
├─────────────────────────────────┤
│  ProductRepository Layer        │ Database queries
├─────────────────────────────────┤
│  PostgreSQL Database            │ Data persistence
└─────────────────────────────────┘
```

---

## 🐛 Common Issues

### Issue: "Can't connect to database"
```bash
# Check DATABASE_URL in .env
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### Issue: "ModuleNotFoundError"
```bash
# Ensure you're in project directory
cd /home/ubuntu/onix_project

# Set PYTHONPATH
export PYTHONPATH=/home/ubuntu/onix_project:$PYTHONPATH

# Try again
python main.py
```

### Issue: "Port 8000 already in use"
```bash
# Use different port
python main.py --port 8001

# Or kill existing process
lsof -i :8000
kill -9 <PID>
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [API_IMPLEMENTATION_20250106.md](API_IMPLEMENTATION_20250106.md) | Detailed architecture |
| [API_COMPLETE_STACK_20250106.md](API_COMPLETE_STACK_20250106.md) | Full technical spec |
| [docs/DB_SCHEMA.md](docs/DB_SCHEMA.md) | Database schema |
| [docs/EXAMPLES.md](docs/EXAMPLES.md) | Code examples |

---

## 🚢 Deployment

### Development
```bash
python main.py
```

### Production (Gunicorn)
```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker
```bash
docker build -t onix-api .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  onix-api
```

### Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
kubectl port-forward svc/onix-api 8000:8000
```

---

## 📞 Support

**GitHub**: [onix_project](https://github.com/your-org/onix_project)  
**Issues**: Report bugs and feature requests  
**Discord**: Join community chat  

---

## ✅ Checklist

Before going to production:

- [ ] Database backed up
- [ ] Tests passing (14/14)
- [ ] Rate limiting configured
- [ ] Authentication enabled
- [ ] Monitoring set up
- [ ] Error logging enabled
- [ ] CORS configured properly
- [ ] API documentation reviewed
- [ ] Load testing completed
- [ ] Security audit passed

---

**Happy coding! 🎉**

