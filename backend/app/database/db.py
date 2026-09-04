import os
from contextvars import ContextVar
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, with_loader_criteria
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cashpilot.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

# Enable Foreign Keys for SQLite
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
current_merchant_id: ContextVar[str | None] = ContextVar("current_merchant_id", default=None)

@event.listens_for(Session, "do_orm_execute")
def add_workspace_scope(execute_state):
    merchant_id = current_merchant_id.get()
    if not merchant_id or not execute_state.is_select:
        return
    from .models import ActionApproval, AuditLog, AIAction, CashflowForecast, Customer, Expense, Invoice, LedgerEntry, Manufacturer, Merchant, Payment, RazorpayWebhookLog, RepaymentPrediction, SimulationRun, Supplier, SupplierPayable
    statement = execute_state.statement.options(with_loader_criteria(Merchant, lambda cls: cls.id == merchant_id, include_aliases=True))
    scoped_models = (ActionApproval, AuditLog, AIAction, CashflowForecast, Customer, Expense, Invoice, LedgerEntry, Manufacturer, Payment, RazorpayWebhookLog, RepaymentPrediction, SimulationRun, Supplier, SupplierPayable)
    for model in scoped_models:
        statement = statement.options(with_loader_criteria(model, lambda cls: cls.merchant_id == merchant_id, include_aliases=True))
    execute_state.statement = statement

@event.listens_for(Session, "before_flush")
def assign_workspace_to_new_records(session, flush_context, instances):
    merchant_id = current_merchant_id.get()
    if not merchant_id:
        return
    for record in session.new:
        if hasattr(record, "merchant_id") and getattr(record, "merchant_id", None) is None:
            record.merchant_id = merchant_id

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
