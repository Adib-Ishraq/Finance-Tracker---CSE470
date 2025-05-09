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
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    budget = db.relationship('Budget', backref='user', uselist=False)
    goals = db.relationship('Goal', backref='user', lazy=True)
    bills = db.relationship('Bill', backref='user', lazy=True)
    recurring_expenses = db.relationship('RecurringExpense', backref='user', lazy=True)
    investment_accounts = db.relationship('InvestmentAccount', backref='user', lazy=True)
    debts = db.relationship('Debt', backref='user', lazy=True)

    def generate_2fa_secret(self):
        self.two_factor_secret = pyotp.random_base32()
        return self.two_factor_secret

    def verify_2fa(self, code):
        if not self.two_factor_secret:
            return False
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(code)

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
    description = db.Column(db.String(255), nullable=True)
    auto_categorized = db.Column(db.Boolean, default=False)
    
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
    def get_monthly_totals(cls, user_id, month=None, year=None):
        """Get total income and expenses for a specific month, defaults to current month"""
        if month is None:
            month = datetime.utcnow().month
        if year is None:
            year = datetime.utcnow().year
            
        income = db.session.query(func.sum(cls.amount)).filter(
            cls.user_id == user_id,
            cls.type == 'Income',
            extract('month', cls.date) == month,
            extract('year', cls.date) == year
        ).scalar() or 0
        
        expenses = db.session.query(func.sum(cls.amount)).filter(
            cls.user_id == user_id,
            cls.type == 'Expense',
            extract('month', cls.date) == month,
            extract('year', cls.date) == year
        ).scalar() or 0
        
        return {
            'income': income,
            'expenses': expenses,
            'net': income - expenses,
            'month': month,
            'year': year
        }
    
    @classmethod
    def get_monthly_comparison(cls, user_id, month1, year1, month2, year2):
        """Compare two different months' income and expenses"""
        first_month = cls.get_monthly_totals(user_id, month1, year1)
        second_month = cls.get_monthly_totals(user_id, month2, year2)
        
        return {
            'first_month': first_month,
            'second_month': second_month,
            'income_difference': second_month['income'] - first_month['income'],
            'expense_difference': second_month['expenses'] - first_month['expenses'],
            'net_difference': second_month['net'] - first_month['net']
        }
        
    @classmethod
    def get_monthly_category_totals(cls, user_id, transaction_type="Expense", month=None, year=None):
        """Get category totals for a specific month"""
        try:
            query = db.session.query(
                cls.category,
                func.sum(cls.amount).label('total')
            ).filter_by(
                user_id=user_id,
                type=transaction_type
            )
            
            # Add month/year filter if provided
            if month and year:
                query = query.filter(
                    extract('month', cls.date) == month,
                    extract('year', cls.date) == year
                )
            
            return query.group_by(cls.category).all()
            
        except Exception as e:
            print(f"Error in get_monthly_category_totals: {str(e)}")
            return []
    
    @classmethod
    def get_monthly_totals(cls, user_id, month=None, year=None):
        """Get total income and expenses for a specific month, defaults to current month"""
        if month is None:
            month = datetime.utcnow().month
        if year is None:
            year = datetime.utcnow().year
            
        income = db.session.query(func.sum(cls.amount)).filter(
            cls.user_id == user_id,
            cls.type == 'Income',
            extract('month', cls.date) == month,
            extract('year', cls.date) == year
        ).scalar() or 0
        
        expenses = db.session.query(func.sum(cls.amount)).filter(
            cls.user_id == user_id,
            cls.type == 'Expense',
            extract('month', cls.date) == month,
            extract('year', cls.date) == year
        ).scalar() or 0
        
        return {
            'income': income,
            'expenses': expenses,
            'net': income - expenses,
            'month': month,
            'year': year
        }
    
    @classmethod
    def get_monthly_comparison(cls, user_id, month1, year1, month2, year2):
        """Compare two different months' income and expenses"""
        first_month = cls.get_monthly_totals(user_id, month1, year1)
        second_month = cls.get_monthly_totals(user_id, month2, year2)
        
        return {
            'first_month': first_month,
            'second_month': second_month,
            'income_difference': second_month['income'] - first_month['income'],
            'expense_difference': second_month['expenses'] - first_month['expenses'],
            'net_difference': second_month['net'] - first_month['net']
        }
        
    @classmethod
    def get_monthly_category_totals(cls, user_id, transaction_type="Expense", month=None, year=None):
        """Get category totals for a specific month"""
        try:
            query = db.session.query(
                cls.category,
                func.sum(cls.amount).label('total')
            ).filter_by(
                user_id=user_id,
                type=transaction_type
            )
            
            # Add month/year filter if provided
            if month and year:
                query = query.filter(
                    extract('month', cls.date) == month,
                    extract('year', cls.date) == year
                )
            
            return query.group_by(cls.category).all()
            
        except Exception as e:
            print(f"Error in get_monthly_category_totals: {str(e)}")
            return []
    
    @classmethod
    def get_category_totals(cls, user_id, transaction_type="Expense"):
        try:
            result = db.session.query(
                cls.category,
                func.sum(cls.amount).label('total')
            ).filter_by(
                user_id=user_id,
                type=transaction_type
            ).group_by(cls.category).all()
            
            # Check if we have any results
            if not result:
                # Check if user has any transactions at all
                transaction_count = db.session.query(func.count(cls.id)).filter_by(
                    user_id=user_id,
                    type=transaction_type
                ).scalar()
                print(f"User {user_id} has {transaction_count} {transaction_type} transactions, but no category totals")
                
                # If there are no transactions, we'll return an empty list
                # The API will handle providing sample data
            
            return result
        except Exception as e:
            print(f"Error in get_category_totals: {str(e)}")
            return []

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False, default=datetime.utcnow().month)
    year = db.Column(db.Integer, nullable=False, default=datetime.utcnow().year)
    rollover_amount = db.Column(db.Float, nullable=False, default=0.0)
    enable_rollover = db.Column(db.Boolean, nullable=False, default=True)
    
    @classmethod
    def get_current_month_budget(cls, user_id):
        """Get the budget for the current month, creating one if it doesn't exist"""
        current_month = datetime.utcnow().month
        current_year = datetime.utcnow().year
        
        budget = cls.query.filter_by(
            user_id=user_id,
            month=current_month,
            year=current_year
        ).first()
        
        if not budget:
            # Check if there was a budget for the previous month
            prev_month = 12 if current_month == 1 else current_month - 1
            prev_year = current_year - 1 if current_month == 1 else current_year
            
            prev_budget = cls.query.filter_by(
                user_id=user_id,
                month=prev_month,
                year=prev_year
            ).first()
            
            # Calculate rollover amount if previous budget exists
            rollover_amount = 0.0
            base_amount = 0.0
            
            if prev_budget:
                base_amount = prev_budget.amount
                
                # Get previous month's expenses
                from models import Transaction
                prev_month_expenses = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user_id,
                    Transaction.type == 'Expense',
                    extract('month', Transaction.date) == prev_month,
                    extract('year', Transaction.date) == prev_year
                ).scalar() or 0
                
                # Calculate rollover if enabled
                if prev_budget.enable_rollover:
                    remaining = prev_budget.amount + prev_budget.rollover_amount - prev_month_expenses
                    rollover_amount = max(0, remaining)  # Only rollover positive amounts
            
            # Create new budget with rollover from previous month
            budget = cls(
                user_id=user_id,
                amount=base_amount,
                month=current_month,
                year=current_year,
                rollover_amount=rollover_amount,
                enable_rollover=True if prev_budget else True
            )
            db.session.add(budget)
            db.session.commit()
            
        return budget
    
    @property
    def total_budget(self):
        """Get the total budget including rollover"""
        return self.amount + self.rollover_amount
    
    @classmethod
    def get_budget_by_month(cls, user_id, month, year):
        """Get budget for a specific month"""
        return cls.query.filter_by(
            user_id=user_id,
            month=month,
            year=year
        ).first()

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

# Investment Models
class InvestmentAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # e.g., Brokerage, IRA, 401(k), etc.
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    investments = db.relationship('Investment', backref='account', lazy=True, cascade="all, delete-orphan")
    
    @property
    def total_current_value(self):
        return sum(investment.current_value for investment in self.investments)
    
    @property
    def total_invested_amount(self):
        return sum(investment.initial_investment for investment in self.investments)
    
    @property
    def total_profit_loss(self):
        return self.total_current_value - self.total_invested_amount
    
    @property
    def total_profit_loss_percentage(self):
        if self.total_invested_amount == 0:
            return 0
        return (self.total_profit_loss / self.total_invested_amount) * 100

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('investment_account.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=True)  # Stock/crypto ticker symbol
    investment_type = db.Column(db.String(50), nullable=False)  # stock, crypto, mutual fund, etc.
    risk_category = db.Column(db.String(50), nullable=False)  # high-risk, medium-risk, low-risk
    initial_investment = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    current_value = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    tax_lot_id = db.Column(db.String(50), nullable=True)  # For tracking tax lots
    tax_status = db.Column(db.String(20), nullable=True)  # "Short-term" or "Long-term"
    
    @property
    def profit_loss(self):
        return self.current_value - self.initial_investment
    
    @property
    def profit_loss_percentage(self):
        if self.initial_investment == 0:
            return 0
        return (self.profit_loss / self.initial_investment) * 100
    
    @property
    def current_price(self):
        if self.quantity == 0:
            return 0
        return self.current_value / self.quantity

# Debt Models
class Debt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # "Debt" (I owe) or "Loan" (lent out)
    person = db.Column(db.String(100), nullable=False)  # Person to/from whom the debt/loan is related
    amount = db.Column(db.Float, nullable=False)  # Total debt/loan amount
    debt_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    repayment_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payments = db.relationship('DebtPayment', backref='debt', lazy=True, cascade="all, delete-orphan")
    
    @property
    def paid(self):
        return sum(payment.amount_paid for payment in self.payments)
    
    @property
    def outstanding(self):
        return self.amount - self.paid


class DebtPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    debt_id = db.Column(db.Integer, db.ForeignKey('debt.id'), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)
    
    @property
    def outstanding(self):
        # More efficient implementation to calculate outstanding amount after this payment
        debt = Debt.query.get(self.debt_id)
        if not debt:
            return 0
            
        # Get all payments for this debt up to and including this payment
        payments = DebtPayment.query.filter_by(debt_id=self.debt_id).filter(
            DebtPayment.payment_date <= self.payment_date
        ).all()
        
        # Sum all payments
        total_paid = sum(payment.amount_paid for payment in payments)
        
        # Calculate remaining amount
        return max(0, debt.amount - total_paid)
