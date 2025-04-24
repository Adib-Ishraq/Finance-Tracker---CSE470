from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import Goal, Transaction, db
from forms import GoalForm, ContributeForm
from datetime import datetime, timedelta
from sqlalchemy import func

goals = Blueprint('goals', __name__)

@goals.route('/goals')
@login_required
def view_goals():
    goals = Goal.query.filter_by(user_id=current_user.id).all()
    return render_template('goals/goals.html', goals=goals)

@goals.route('/goals/add', methods=['GET', 'POST'])
@login_required
def add_goal():
    form = GoalForm()
    if form.validate_on_submit():
        new_goal = Goal(
            user_id=current_user.id,
            name=form.name.data,
            target_amount=form.target_amount.data,
            current_amount=form.current_amount.data if form.current_amount.data else 0,
            deadline=form.deadline.data
        )
        db.session.add(new_goal)
        db.session.commit()
        flash('New financial goal created!', 'success')
        return redirect(url_for('goals.view_goals'))
    return render_template('goals/add_goal.html', form=form)

@goals.route('/goals/<int:goal_id>')
@login_required
def view_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('goals.view_goals'))
    form = ContributeForm()
    return render_template('goals/goal_detail.html', goal=goal, form=form)

@goals.route('/goals/<int:goal_id>/contribute', methods=['POST'])
@login_required
def contribute_to_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('goals.view_goals'))

    form = ContributeForm()
    if form.validate_on_submit():
        goal.current_amount += float(form.amount.data)

        # Create a transaction record for this contribution
        new_transaction = Transaction(
            user_id=current_user.id,
            type='Expense',  # It's an expense since money is being set aside
            category='Goal Contribution: ' + goal.name,
            amount=form.amount.data,
            date=datetime.utcnow()
        )

        db.session.add(new_transaction)
        db.session.commit()

        if goal.is_completed:
            flash(f'Congratulations! You\'ve reached your goal: {goal.name}', 'success')
        else:
            flash(f'Added ${form.amount.data:.2f} to {goal.name}', 'success')

        return redirect(url_for('goals.view_goal', goal_id=goal.id))

    return redirect(url_for('goals.view_goal', goal_id=goal.id))

@goals.route('/goals/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('goals.view_goals'))

    form = GoalForm(obj=goal)
    if form.validate_on_submit():
        goal.name = form.name.data
        goal.target_amount = form.target_amount.data
        goal.current_amount = form.current_amount.data
        goal.deadline = form.deadline.data

        db.session.commit()
        flash('Goal updated successfully!', 'success')
        return redirect(url_for('goals.view_goal', goal_id=goal.id))

    return render_template('goals/edit_goals.html', form=form, goal=goal)

@goals.route('/goals/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('goals.view_goals'))

    db.session.delete(goal)
    db.session.commit()
    flash('Goal deleted successfully!', 'success')
    return redirect(url_for('goals.view_goals'))

@goals.route('/api/goal-reminders')
@login_required
def goal_reminders():
    """Get reminders for goals with upcoming deadlines"""
    # Find goals with deadlines within the next 7 days
    current_date = datetime.utcnow()
    deadline_threshold = current_date + timedelta(days=7)

    upcoming_goals = Goal.query.filter(
        Goal.user_id == current_user.id,
        Goal.deadline <= deadline_threshold,
        Goal.deadline >= current_date,
        Goal.current_amount < Goal.target_amount
    ).all()

    reminders = []
    for goal in upcoming_goals:
        days_left = (goal.deadline - current_date).days
        amount_needed = goal.target_amount - goal.current_amount
        reminders.append({
            'id': goal.id,
            'name': goal.name,
            'days_left': days_left,
            'amount_needed': amount_needed
        })

    return jsonify({'reminders': reminders})

@goals.route('/goal-suggestions')
@login_required
def goal_suggestions():
    """Generate personalized goal suggestions based on spending patterns"""
    # Calculate average monthly spending
    total_expense = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='Expense').scalar() or 0

    # Get expenses in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_expenses = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'Expense',
        Transaction.date >= thirty_days_ago
    ).all()

    monthly_expense = sum(expense.amount for expense in recent_expenses)

    # Get category breakdown
    category_totals = Transaction.get_category_totals(current_user.id)

    suggestions = []

    # Emergency fund suggestion (3-6 months of expenses)
    emergency_fund_suggestion = {
        'name': 'Emergency Fund',
        'description': 'Save 3-6 months of living expenses for emergencies',
        'target_amount': monthly_expense * 3,
        'priority': 'High'
    }
    suggestions.append(emergency_fund_suggestion)

    # Debt reduction if there are any debt-related categories
    debt_categories = ['Debt', 'Loan', 'Credit Card']
    for category in category_totals:
        if any(debt_term in category.category for debt_term in debt_categories):
            debt_suggestion = {
                'name': f'Pay off {category.category}',
                'description': 'Reduce high-interest debt to save money',
                'target_amount': category.total * 1.2,  # Estimate total debt as 120% of monthly payment
                'priority': 'High'
            }
            suggestions.append(debt_suggestion)

    # Vacation fund based on discretionary spending
    entertainment_expenses = sum(
        t.amount for t in recent_expenses if t.category in ['Entertainment', 'Dining', 'Shopping'])
    if entertainment_expenses > 0:
        vacation_suggestion = {
            'name': 'Vacation Fund',
            'description': 'Save for your next vacation',
            'target_amount': entertainment_expenses * 3,
            'priority': 'Medium'
        }
        suggestions.append(vacation_suggestion)

    # Retirement fund suggestion
    retirement_suggestion = {
        'name': 'Retirement Savings',
        'description': 'Build your retirement nest egg',
        'target_amount': monthly_expense * 12,  # Start with a year's worth of expenses
        'priority': 'Medium'
    }
    suggestions.append(retirement_suggestion)

    return render_template('goals/goal_suggestions.html', suggestions=suggestions)