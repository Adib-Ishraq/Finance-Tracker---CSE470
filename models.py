from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import UserMixin
from datetime import datetime, timedelta
from sqlalchemy import func, extract, false
import pyotp

# CREATE DB
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    two_factor_secret = db.Column(db.String(32), nullable=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=True)
    notification_preferences = db.Column(db.JSON, default={
        'email_notifications': True,
        'sms_notifications': False,
        'weekly_reports': True,
        'monthly_reports': True,
        'bill_reminders': True,
        'spending_alerts': True
    })
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    budget = db.relationship('Budget', backref='user', uselist=False)
    goals = db.relationship('Goal', backref='user', lazy=True)
    bills = db.relationship('Bill', backref='user', lazy=True)
    recurring_expenses = db.relationship('RecurringExpense', backref='user', lazy=True)

    def generate_2fa_secret(self):
        self.two_factor_secret = pyotp.random_base32()
        return self.two_factor_secret

    def verify_2fa(self, code):
        if not self.two_factor_secret:
            return False
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(code)

class Family(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    members = db.relationship('User', backref='family', lazy=True)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), nullable=False)
    receipt_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class RecurringExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, yearly
    next_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @classmethod
    def get_transactions_by_category(cls, user_id, category=None, start_date=None, end_date=None):
        query = cls.query.filter_by(user_id=user_id)

        if category:
            query = query.filter_by(category=category)
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(cls.date >= start_date)
            except (ValueError, TypeError):
                pass
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(cls.date <= end_date)
            except (ValueError, TypeError):
                pass

        return query.order_by(cls.date.desc()).all()

    @classmethod
    def get_category_totals(cls, user_id, transaction_type="Expense"):
        return db.session.query(
            cls.category,
            func.sum(cls.amount).label('total')
        ).filter_by(
            user_id=user_id,
            type=transaction_type
        ).group_by(cls.category).all()

    @classmethod
    def get_monthly_totals(cls, user_id, months=6):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30 * months)

        return db.session.query(
            func.strftime('%Y-%m', cls.date).label('month'),
            func.sum(cls.amount).label('total')
        ).filter(
            cls.user_id == user_id,
            cls.type == 'Expense',
            cls.date.between(start_date, end_date)
        ).group_by('month').order_by('month').all()

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0)
    deadline = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def progress_percentage(self):
        if self.target_amount <= 0:
            return 0
        return min(100, int((self.current_amount / self.target_amount) * 100))

    @property
    def days_remaining(self):
        if not self.deadline:
            return None
        return (self.deadline - datetime.utcnow()).days

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount