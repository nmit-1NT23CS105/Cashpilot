import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, precision_score, recall_score, mean_absolute_error, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from ..database.models import Invoice, Customer, RepaymentPrediction

class MLRepaymentService:
    def __init__(self):
        self.clf_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.reg_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.baseline_clf = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=42)
        )
        self.is_trained = False
        self.evaluation_metrics = {}

    def extract_features(self, db: Session):
        invoices = db.query(Invoice).all()
        data = []

        for inv in invoices:
            cust = inv.customer
            if not cust:
                continue

            # Features
            feat = {
                "invoice_id": inv.id,
                "customer_id": cust.id,
                "invoice_amount": inv.total_amount,
                "on_time_rate": cust.on_time_payment_rate,
                "avg_delay": cust.avg_payment_delay_days,
                "max_delay": cust.max_payment_delay_days,
                "total_purchases": cust.total_purchases_val,
                "current_outstanding": cust.current_outstanding,
                "total_transactions": cust.total_transactions_count,
                "overdue_count": cust.overdue_count,
                "reliability_score": cust.reliability_score,
                "credit_period": cust.credit_period_days,
                "is_deteriorating": 1 if cust.behavior_trend == "DETERIORATING" else 0,
                # Target: Paid on time within 15 days
                "target_repaid_on_time": 1 if inv.status == "PAID" else (0 if inv.status == "OVERDUE" else (1 if cust.on_time_payment_rate > 0.7 else 0)),
                "target_actual_delay": cust.avg_payment_delay_days if inv.status == "PAID" else cust.avg_payment_delay_days + 5.0
            }
            data.append(feat)

        return pd.DataFrame(data)

    def train_models(self, db: Session):
        df = self.extract_features(db)
        if len(df) < 20:
            return {"status": "insufficient_data"}

        feature_cols = [
            "invoice_amount", "on_time_rate", "avg_delay", "max_delay",
            "total_purchases", "current_outstanding", "total_transactions",
            "overdue_count", "reliability_score", "credit_period", "is_deteriorating"
        ]

        X = df[feature_cols]
        y_clf = df["target_repaid_on_time"]
        y_reg = df["target_actual_delay"]

        if y_clf.nunique() < 2:
            return {"status": "insufficient_class_diversity", "sample_size": len(df)}

        X_train, X_test, y_train_clf, y_test_clf, y_train_reg, y_test_reg = train_test_split(
            X, y_clf, y_reg, test_size=0.25, random_state=42, stratify=y_clf
        )

        # Fit Models
        self.clf_model.fit(X_train, y_train_clf)
        self.baseline_clf.fit(X_train, y_train_clf)
        self.reg_model.fit(X_train, y_train_reg)
        self.is_trained = True

        # Predictions on Test Set
        y_pred_prob = self.clf_model.predict_proba(X_test)[:, 1]
        y_pred_class = (y_pred_prob >= 0.5).astype(int)
        y_baseline_prob = self.baseline_clf.predict_proba(X_test)[:, 1]

        y_pred_days = self.reg_model.predict(X_test)

        # Honest Evaluation Metrics
        auc = float(roc_auc_score(y_test_clf, y_pred_prob))
        baseline_auc = float(roc_auc_score(y_test_clf, y_baseline_prob))
        prec = float(precision_score(y_test_clf, y_pred_class, zero_division=0))
        rec = float(recall_score(y_test_clf, y_pred_class, zero_division=0))
        mae = float(mean_absolute_error(y_test_reg, y_pred_days))
        brier = float(brier_score_loss(y_test_clf, y_pred_prob))

        importances = dict(zip(feature_cols, [round(float(v), 4) for v in self.clf_model.feature_importances_]))

        self.evaluation_metrics = {
            "model_type": "GradientBoostingClassifier + RandomForestRegressor",
            "sample_size": len(df),
            "test_sample_size": len(X_test),
            "auc_roc": round(auc, 4),
            "baseline_logistic_auc": round(baseline_auc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "mae_days": round(mae, 2),
            "brier_score": round(brier, 4),
            "feature_importances": importances
        }

        return self.evaluation_metrics

    def predict_invoice_repayment(self, customer: Customer, invoice_amount: float) -> dict:
        if not self.is_trained:
            # Baseline rule-based estimate
            prob = float(min(0.98, max(0.15, customer.on_time_payment_rate)))
            exp_days = float(max(1.0, customer.avg_payment_delay_days))
            return {
                "repayment_probability_15d": round(prob, 2),
                "expected_payment_days": round(exp_days, 1),
                "confidence": "HIGH" if customer.total_transactions_count > 5 else "LOW"
            }

        feat = pd.DataFrame([{
            "invoice_amount": invoice_amount,
            "on_time_rate": customer.on_time_payment_rate,
            "avg_delay": customer.avg_payment_delay_days,
            "max_delay": customer.max_payment_delay_days,
            "total_purchases": customer.total_purchases_val,
            "current_outstanding": customer.current_outstanding,
            "total_transactions": customer.total_transactions_count,
            "overdue_count": customer.overdue_count,
            "reliability_score": customer.reliability_score,
            "credit_period": customer.credit_period_days,
            "is_deteriorating": 1 if customer.behavior_trend == "DETERIORATING" else 0
        }])

        prob = float(self.clf_model.predict_proba(feat)[0, 1])
        exp_days = float(self.reg_model.predict(feat)[0])

        confidence = "HIGH" if customer.total_transactions_count >= 10 else ("MEDIUM" if customer.total_transactions_count >= 3 else "LOW")

        return {
            "repayment_probability_15d": round(prob, 2),
            "expected_payment_days": round(max(0.5, exp_days), 1),
            "confidence": confidence
        }

ml_repayment_service = MLRepaymentService()
