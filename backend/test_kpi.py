import sys, traceback
sys.path.append('.')
from app.database.db import SessionLocal
from app.api.routes import get_dashboard_kpis

db = SessionLocal()
try:
    res = get_dashboard_kpis(db)
    print("SUCCESS:", res)
except Exception as e:
    traceback.print_exc()
