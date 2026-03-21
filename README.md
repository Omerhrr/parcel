# ParcelFlow - Multi-tenant Logistics Platform

A comprehensive logistics and e-commerce CRM platform built with FastAPI + SQLAlchemy backend and Flask + HTMX + AlpineJS + TailwindCSS frontend.

## Features

### Multi-tenant Architecture
- Business and branch isolation
- Tenant-scoped data access
- Role-based access control (RBAC)

### Logistics Management
- **Waybills**: Core logistics documents with full lifecycle tracking
- **Pickups**: Scheduled pickup management
- **Warehouse Processing**: Item receipt, sorting, and dispatch
- **Dispatch**: Agent assignment and delivery tracking
- **Delivery Confirmation**: Proof of delivery with signatures and photos
- **Public Tracking Portal**: Customer-facing tracking page

### Inventory Management
- Products with vendor association
- Multi-warehouse inventory tracking
- Stock movements (in/out/transfer/return)
- Low stock alerts

### Vendor Management
- Vendor profiles with banking details
- Vendor portal access
- Remittance tracking
- Vendor ledger

### Agent Management
- Logistic agents with vehicle assignment
- Performance metrics tracking
- COD collection tracking

### Order Management
- Customer orders with multiple items
- Order assignments
- WordPress landing page integration

### Accounting
- Chart of accounts
- Transaction tracking
- Expense management
- Vendor remittances
- Agent collections

### Security
- JWT authentication
- Role-based permissions
- Tenant isolation
- Audit logging

## Tech Stack

### Backend
- **Framework**: FastAPI 0.109.0
- **ORM**: SQLAlchemy 2.0
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Auth**: JWT with python-jose
- **Validation**: Pydantic v2

### Frontend
- **Framework**: Flask 3.0
- **Auth**: Flask-Login
- **CSS**: TailwindCSS
- **UI Components**: Flowbite
- **JavaScript**: AlpineJS + HTMX

## Project Structure

```
parcelflow/
├── backend/                    # FastAPI API
│   ├── app/
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   ├── services/          # Business logic
│   │   └── utils/             # Utilities
│   └── requirements.txt
│
├── frontend/                   # Flask Dashboard
│   ├── app/
│   │   ├── routes/            # Flask routes
│   │   ├── templates/         # Jinja2 templates
│   │   └── static/            # CSS, JS, images
│   └── requirements.txt
│
└── website/                    # Marketing website (future)
```

## Getting Started

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API will be available at http://localhost:8000
API Documentation at http://localhost:8000/api/docs

### Frontend Setup

```bash
cd frontend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

Dashboard will be available at http://localhost:5000

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - New business registration
- `POST /api/auth/logout` - User logout
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user

### Waybills
- `GET /api/waybills` - List waybills
- `POST /api/waybills` - Create waybill
- `GET /api/waybills/{id}` - Get waybill details
- `PUT /api/waybills/{id}/status` - Update waybill status

### Orders
- `GET /api/orders` - List orders
- `POST /api/orders` - Create order
- `GET /api/orders/{id}` - Get order details
- `PUT /api/orders/{id}/status` - Update order status

### Public API
- `POST /api/public/orders/landing` - WordPress landing page orders
- `GET /api/public/track/{waybill_number}` - Public tracking

## Default Roles

| Role | Description |
|------|-------------|
| super_admin | Full system access |
| admin | Business administrator |
| manager | Branch manager |
| sales_agent | Sales and leads |
| dispatcher | Delivery assignment |
| warehouse_staff | Inventory operations |
| viewer | Read-only access |
| vendor_user | Vendor portal access |

## License

MIT License
