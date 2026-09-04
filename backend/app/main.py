import os
from fastapi import FastAPI, Request
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware
from .database.db import engine, Base, SessionLocal, current_merchant_id
from .database.models import LedgerAccount, Merchant, Owner
from .api.routes import router, _owner

app = FastAPI(
    title="CashPilot AI — Financial Autopilot for Distributors",
    description="AI-powered financial decision and liquidity automation engine",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CASHPILOT_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/username-availability",
    "/api/auth/login",
    "/api/auth/setup",
}

@app.middleware("http")
async def protect_business_api(request: Request, call_next):
    token = None
    if request.url.path.startswith("/api/") and request.url.path not in PUBLIC_API_PATHS and request.method != "OPTIONS":
        db = SessionLocal()
        try:
            token = _owner(request.headers.get("authorization"), db)
            current_merchant_id.set(token.merchant_id)
        except Exception as exc:
            db.close()
            from fastapi.responses import JSONResponse
            status_code = getattr(exc, "status_code", 401)
            return JSONResponse(status_code=status_code, content={"detail": "Owner authentication required"})
        finally:
            if not db.is_active:
                db.close()
        db.close()
    try:
        return await call_next(request)
    finally:
        current_merchant_id.set(None)

def init_db():
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        migration_columns = {
            "owners": ["merchant_id"],
            "merchants": ["current_cash"],
            "payments": ["merchant_id"],
            "supplier_payables": ["merchant_id"],
            "repayment_predictions": ["merchant_id"],
            "cashflow_forecasts": ["merchant_id"],
            "ai_actions": ["merchant_id"],
            "action_approvals": ["merchant_id"],
            "audit_logs": ["merchant_id"],
            "simulation_runs": ["merchant_id"],
            "razorpay_webhook_logs": ["merchant_id"],
            "ledger_entries": ["merchant_id"],
        }
        with engine.begin() as connection:
            for table, names in migration_columns.items():
                columns = {column["name"] for column in inspect(engine).get_columns(table)}
                for name in names:
                    if name not in columns:
                        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} VARCHAR"))
            merchants = connection.execute(text("SELECT id FROM merchants ORDER BY created_at LIMIT 1")).fetchone()
            if merchants:
                merchant_id = merchants[0]
                connection.execute(text("UPDATE owners SET merchant_id = :merchant_id WHERE merchant_id IS NULL"), {"merchant_id": merchant_id})
                connection.execute(text("UPDATE merchants SET current_cash = (SELECT COALESCE(balance, 0) FROM ledger_accounts WHERE code = '1010') WHERE id = :merchant_id AND (current_cash IS NULL OR current_cash = 0)"), {"merchant_id": merchant_id})
                for table in migration_columns:
                    if table not in {"owners", "merchants"}:
                        connection.execute(text(f"UPDATE {table} SET merchant_id = :merchant_id WHERE merchant_id IS NULL"), {"merchant_id": merchant_id})
            columns = {column["name"] for column in inspect(engine).get_columns("suppliers")}
            for name in ("contact_person", "phone", "email"):
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE suppliers ADD COLUMN {name} VARCHAR"))

# Initialize DB
init_db()

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
