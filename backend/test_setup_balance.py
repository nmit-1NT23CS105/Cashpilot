from app.database.db import SessionLocal
from app.database.models import LedgerAccount, Owner
from app.api.routes import setup_owner


def test_setup_owner_defaults_to_positive_cash_balance():
    db = SessionLocal()
    try:
        db.query(Owner).delete()
        db.query(LedgerAccount).delete()
        db.commit()

        result = setup_owner({"username": "owner2", "password": "owner1234", "business_name": "Demo Business"}, db)

        assert result["username"] == "owner2"
        cash = db.query(LedgerAccount).filter(LedgerAccount.code == "1010").one()
        assert cash.balance > 0
    finally:
        db.close()
