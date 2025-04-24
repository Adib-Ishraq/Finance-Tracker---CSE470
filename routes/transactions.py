from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import Transaction, Budget, db
from forms import TransactionForm
from sqlalchemy import func
from datetime import datetime

transactions = Blueprint('transactions', __name__)

@transactions.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        new_transaction = Transaction(
            user_id=current_user.id,
            type=form.type.data,
            category=form.category.data,
            amount=form.amount.data,
            date=form.date.data
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('add_transaction.html', form=form)

@transactions.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Ensure user owns this transaction
    if transaction.user_id != current_user.id:
        flash('You do not have permission to edit this transaction.', 'danger')
        return redirect(url_for('transactions.filter_transactions'))
    
    form = TransactionForm(obj=transaction)
    
    if form.validate_on_submit():
        transaction.type = form.type.data
        transaction.category = form.category.data
        transaction.amount = form.amount.data
        transaction.date = form.date.data
        
        db.session.commit()
        flash('Transaction updated successfully!', 'success')
        return redirect(url_for('transactions.filter_transactions'))
    
    return render_template('edit_transaction.html', form=form, transaction=transaction)

@transactions.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Ensure user owns this transaction
    if transaction.user_id != current_user.id:
        flash('You do not have permission to delete this transaction.', 'danger')
        return redirect(url_for('transactions.filter_transactions'))
    
    db.session.delete(transaction)
    db.session.commit()
    
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('transactions.filter_transactions'))

@transactions.route('/transactions/filter', methods=['GET', 'POST'])
@login_required
def filter_transactions():
    categories = db.session.query(Transaction.category).distinct().all()
    categories = [cat[0] for cat in categories]

    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    transactions = Transaction.get_transactions_by_category(
        current_user.id,
        category=category,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None
    )

    return render_template(
        'transactions.html',
        transactions=transactions,
        categories=categories,
        selected_category=category,
        start_date=start_date,
        end_date=end_date
    )

@transactions.route('/api/spending-data')
@login_required
def spending_data():
    category_totals = Transaction.get_category_totals(current_user.id)
    monthly_totals = Transaction.get_monthly_totals(current_user.id)

    category_data = {
        'labels': [item.category for item in category_totals],
        'datasets': [{
            'data': [float(item.total) for item in category_totals],
            'backgroundColor': [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                '#FF9F40', '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'
            ]
        }]
    }

    trend_data = {
        'labels': [item.month for item in monthly_totals],
        'datasets': [{
            'label': 'Monthly Spending',
            'data': [float(item.total) for item in monthly_totals],
            'borderColor': '#36A2EB',
            'fill': False
        }]
    }

    return jsonify({
        'categoryData': category_data,
        'trendData': trend_data
    })

@transactions.route('/budget-summary')
@login_required
def budget_summary():
    # Get the user's budget
    budget = db.session.query(Budget).filter_by(user_id=current_user.id).first()
    budget_amount = budget.amount if budget else 0
    
    # Get current month's expenses by category
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    category_expenses = db.session.query(
        Transaction.category, 
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'Expense',
        Transaction.date >= current_month
    ).group_by(Transaction.category).all()
    
    # Total expenses this month
    total_expenses = sum(expense.total for expense in category_expenses)
    
    # Calculate remaining budget
    remaining_budget = budget_amount - total_expenses
    budget_percentage = (total_expenses / budget_amount) * 100 if budget_amount > 0 else 0
    
    # Get previous month's expenses for comparison
    last_month_start = current_month.replace(month=current_month.month-1 if current_month.month > 1 else 12)
    last_month_expenses = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'Expense',
        Transaction.date >= last_month_start,
        Transaction.date < current_month
    ).scalar() or 0
    
    # Calculate trend (positive means spending less than last month - good)
    spending_trend = ((last_month_expenses - total_expenses) / last_month_expenses) * 100 if last_month_expenses > 0 else 0
    
    return render_template(
        'budget_summary.html',
        budget_amount=budget_amount,
        total_expenses=total_expenses,
        remaining_budget=remaining_budget,
        budget_percentage=budget_percentage,
        category_expenses=category_expenses,
        spending_trend=spending_trend,
        last_month_expenses=last_month_expenses
    )