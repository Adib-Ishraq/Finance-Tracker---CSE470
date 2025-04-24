from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Transaction, Budget, Goal, db
from sqlalchemy import func

main = Blueprint('main', __name__)

@main.route('/dashboard')
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(5).all()
    budget = Budget.query.filter_by(user_id=current_user.id).first()
    goals = Goal.query.filter_by(user_id=current_user.id).all()

    total_income = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='Income').scalar() or 0
    total_expense = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='Expense').scalar() or 0
    balance = total_income - total_expense
    
    # Calculate remaining budget
    remaining_budget = budget.amount - total_expense if budget else 0

    return render_template('dashboard.html',
                           transactions=transactions,
                           balance=balance,
                           budget=budget,
                           total_income=total_income,
                           total_expense=total_expense,
                           remaining_budget=remaining_budget,
                           goals=goals)