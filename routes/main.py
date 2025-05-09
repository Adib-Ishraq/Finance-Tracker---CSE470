from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Transaction, Budget, Goal, db
from sqlalchemy import func, extract
from datetime import datetime
import calendar

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    # Get recent transactions
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(5).all()
    
    # Get goals
    goals = Goal.query.filter_by(user_id=current_user.id).all()

    # Get current month and year
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    month_name = calendar.month_name[current_month]
    
    # Get monthly budget (for current month)
    monthly_budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        year=current_year
    ).first()
    
    # If no budget for current month, get or create one
    if not monthly_budget:
        monthly_budget = Budget.get_current_month_budget(current_user.id)
    
    # Get monthly income and expense totals
    monthly_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'Income',
        extract('month', Transaction.date) == current_month,
        extract('year', Transaction.date) == current_year
    ).scalar() or 0
    
    monthly_expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'Expense',
        extract('month', Transaction.date) == current_month,
        extract('year', Transaction.date) == current_year
    ).scalar() or 0
    
    monthly_balance = monthly_income - monthly_expense
    
    # Get overall totals (all time)
    total_income = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='Income').scalar() or 0
    total_expense = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='Expense').scalar() or 0
    overall_balance = total_income - total_expense
    
    # Calculate remaining budget (including rollover)
    total_budget = monthly_budget.amount + monthly_budget.rollover_amount
    remaining_budget = total_budget - monthly_expense
    budget_percent = (monthly_expense / total_budget * 100) if total_budget > 0 else 0
    
    # Get daily spending for the current month
    from monthly_analysis import get_daily_spending
    daily_spending = get_daily_spending(current_user.id, current_month, current_year)

    return render_template('dashboard.html',
                           transactions=transactions,
                           monthly_balance=monthly_balance,
                           overall_balance=overall_balance,
                           budget=monthly_budget,
                           total_budget=total_budget,
                           monthly_income=monthly_income,
                           monthly_expense=monthly_expense,
                           remaining_budget=remaining_budget,
                           budget_percent=budget_percent,
                           goals=goals,
                           month_name=month_name,
                           year=current_year,
                           daily_spending=daily_spending)