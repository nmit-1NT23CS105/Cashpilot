# CashPilot AI

CashPilot AI is a financial operations and liquidity intelligence platform for distributors and small businesses. It helps an owner record business activity, monitor cash, identify collection and payment priorities, and use AI-assisted insights based on the company's own data.

## Problem Statement

Distributors commonly manage sales, purchases, receivables, payables, and expenses across spreadsheets, messages, and disconnected accounting tools. This makes it difficult to answer important questions quickly:

- Which buyers should be contacted first?
- Which invoices are at risk of late payment?
- Can upcoming seller bills be paid without breaking the cash buffer?
- Which expenses need review?
- What actions should the owner approve today?

CashPilot brings these records into one workspace and turns them into forecasts, recommendations, reports, and an auditable ledger.

## Solution

The application combines:

- Owner authentication and protected business APIs
- Buyer and seller management
- Sales and invoice tracking
- Purchases and supplier bill tracking
- Expense categorization and recurring-expense forecasting
- Cash-flow forecasting and safety-buffer analysis
- Receivable repayment scoring
- AI action recommendations with approval controls
- Copilot answers based on live database records
- Double-entry ledger and audit trail
- CSV, Excel, PDF, DOCX, and image import
- Import preview and confirmation before records are saved

The financial calculations remain deterministic and database-driven. The Copilot explains current data and recommendations; it does not invent business figures.

## Project Structure

```text
backend/
  app/
    main.py                 FastAPI application and database startup
    api/routes.py           Authentication, business, AI, and import endpoints
    database/db.py          SQLAlchemy engine and sessions
    database/models.py      Database models
    services/               Forecasting, ledger, AI, simulation, and import logic
  requirements.txt
  sample_business_data.csv

frontend/
  src/
    App.tsx                 Application shell and authenticated data loading
    index.css               Shared glass-effect theme
    services/api.ts         Frontend API client
    components/             Dashboard and workflow views
    types/index.ts          TypeScript data contracts
  package.json
  vite.config.ts

README.md
```

## Technology

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite by default
- Pydantic
- pandas, NumPy, and scikit-learn
- pypdf, python-docx, openpyxl, Pillow, and pytesseract for imports

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- lucide-react

## Run Locally on Windows

### Backend

Open PowerShell:

```powershell
cd C:\razorpay_build\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The backend runs at:

- API: http://127.0.0.1:8001
- Swagger documentation: http://127.0.0.1:8001/docs
- Health check: http://127.0.0.1:8001/api/health

If PowerShell blocks script activation, run this for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### Frontend

Open a second PowerShell window:

```powershell
cd C:\razorpay_build\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3001
```

Open http://127.0.0.1:3001/ in the browser.

The Vite development server proxies `/api` requests to `http://127.0.0.1:8001`.

## First-Use Flow

1. Open the frontend.
2. Select **Sign up** on the login page.
3. Enter company name, username, password, and current balance.
4. Create the owner account.
5. Sign in using the new username and password.
6. Open the Owner workspace.
7. Add records manually or import a file.
8. Review the dashboard, forecasts, AI actions, reports, and Copilot.

Only one owner account is supported by the current local workspace. Signup refuses to overwrite an existing owner account.

## Owner Data Entry

The Owner workspace supports manual records for:

- Buyers: name, phone, email, address, credit period, and credit limit
- Sales: buyer, invoice number, total, paid amount, issue date, and due date
- Sellers: name, contact person, phone, email, category, criticality, and payment terms
- Purchases: seller, bill number, total, paid amount, purchase date, and due date
- Expenses: title, category, type, amount, date, and recurring status

Saved records immediately affect the dashboard and AI calculations.

## File Import

Use **Owner -> Import file**. The process is:

1. Select a supported file.
2. Review the preview and valid-row count.
3. Confirm the import.
4. The records are categorized and saved.

Supported formats:

- `.csv`
- `.xlsx`
- `.xlsm`
- `.pdf`
- `.docx`
- `.png`
- `.jpg` / `.jpeg`
- `.webp`

CSV and Excel files should use a header row. Recommended columns:

```text
type,name,amount,phone,email,address,credit_days,credit_limit,
invoice_number,bill_number,due_days,contact_person,category,
criticality,payment_terms,paid_amount,recurring,category_type
```

Supported `type` values:

- `buyer` or `customer`
- `seller` or `supplier`
- `sale`, `sales`, or `invoice`
- `purchase`, `purchases`, or `bill`
- `expense`

Buyer and seller rows may have an amount of `0`. Sales, purchases, and expenses require a positive amount. Duplicate buyer/seller names and invoice/bill identifiers are skipped safely and returned in the import result.

The backend limits uploads to 10 MB. PDF and DOCX files use text extraction. Image files use OCR through Tesseract. The Python `pytesseract` package is installed by `requirements.txt`, but the Tesseract application must also be installed and available on the Windows PATH for image OCR.

A ready-to-import example is available at [backend/sample_business_data.csv](backend/sample_business_data.csv).

## AI and Analytics

### Cash Flow

Forecasts combine:

- Current cash balance
- Outstanding buyer invoices
- Buyer repayment probability
- Expected collection timing
- Supplier bills and due dates
- Recurring expenses
- Configured minimum cash buffer

### AI Actions

The decision engine can recommend:

- Payment links
- Buyer reminders
- Human escalation
- Supplier prioritization
- Expense review
- Waiting when action is not valuable

High-value or policy-sensitive actions can require owner approval.

### Copilot

Copilot answers questions using current database records, including:

- Collection priorities
- Buyer risk
- Upcoming supplier obligations
- Cash sufficiency
- Largest expenses
- General financial status

It avoids the old hard-coded demo entities and uses live buyer, seller, invoice, payable, and expense values.

## Security

Current protections include:

- Password hashing with PBKDF2-HMAC-SHA256 and per-password salts
- Signed bearer sessions
- Authentication required for business APIs
- Login failure throttling after repeated failures
- Automatic browser session removal after a `401` response
- Upload size limits
- Duplicate invoice and bill protection
- Audit records for owner changes and imports
- No default owner credentials

Set a strong secret in production:

```powershell
$env:CASHPILOT_AUTH_SECRET = "replace-with-a-long-random-secret"
```

The default SQLite database is `backend/cashpilot.db` when the backend is started from the backend directory. Set `DATABASE_URL` to use another database connection string.

## Important Local Operations

Clear all business records through the authenticated Owner workspace using **Clear**. This is destructive and cannot be undone. It preserves the database schema and owner table.

The old synthetic demo seeding endpoint is disabled. Business data should come from owner entry or a reviewed import.

## Testing and Validation

Frontend production build:

```powershell
cd C:\razorpay_build\frontend
npm run build
```

Frontend type check:

```powershell
npm run lint
```

Backend compilation:

```powershell
cd C:\razorpay_build\backend
.\.venv\Scripts\python.exe -m py_compile app\main.py app\api\routes.py app\database\models.py
```

The backend also includes `test_kpi.py` for a direct KPI service check:

```powershell
cd C:\razorpay_build\backend
.\.venv\Scripts\python.exe test_kpi.py
```

## Production Roadmap

For production deployment, add:

- PostgreSQL and Alembic migrations
- HTTPS behind a reverse proxy
- A production identity provider or secure server-side sessions
- Secret management rather than shell-only environment variables
- Persistent rate limiting shared across workers
- Automated backups and restore testing
- Malware scanning and stronger content validation for uploads
- Full unit, integration, and browser tests
- Error monitoring and structured logs
- CI/CD checks for build, type checking, and security scanning
- Tesseract installation or a managed OCR service for image documents

## License

No license is specified in this repository.
