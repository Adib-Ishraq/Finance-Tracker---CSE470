from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Budget, Transaction, db
from forms import BudgetForm
from datetime import datetime
import calendar
from monthly_analysis import get_monthly_budget_data, get_month_year_options

budgets = Blueprint('budgets', __name__)

@budgets.route('/set_budget', methods=['GET', 'POST'])
@login_required
def set_budget():
    form = BudgetForm()
    
    # Get month and year from request or use current
    month = request.args.get('month', type=int) or datetime.utcnow().month
    year = request.args.get('year', type=int) or datetime.utcnow().year
    
    # Format month name for display
    month_name = calendar.month_name[month]
    
    # Get the budget for the specified month/year
    current_budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=month,
        year=year
    ).first()

    if form.validate_on_submit():
        # Handle rollover setting
        enable_rollover = 'enable_rollover' in request.form
        
        if current_budget:
            current_budget.amount = form.amount.data
            current_budget.enable_rollover = enable_rollover
        else:
            new_budget = Budget(
                user_id=current_user.id,
                amount=form.amount.data,
                month=month,
                year=year,
                enable_rollover=enable_rollover
            )
            db.session.add(new_budget)
        
        db.session.commit()
        flash(f'Budget for {month_name} {year} updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    if current_budget:
        form.amount.data = current_budget.amount

    # Get list of available months for the dropdown
    month_options = get_month_year_options()
    
    return render_template(
        'budgets/set_budget.html', 
        form=form, 
        budget=current_budget,
        month=month,
        year=year,
        month_name=month_name,
        month_options=month_options,
        enable_rollover=current_budget.enable_rollover if current_budget else True
    )

@budgets.route('/monthly_budget')
@login_required
def monthly_budget():
    # Get month and year from request or use current
    month = request.args.get('month', type=int) or datetime.utcnow().month
    year = request.args.get('year', type=int) or datetime.utcnow().year
    
    # Get budget data for the specified month
    budget_data = get_monthly_budget_data(current_user.id, month, year)
    
    # Get available months for dropdown
    month_options = get_month_year_options()
    
    return render_template(
        'budgets/monthly_budget.html',
        budget_data=budget_data,
        month_options=month_options
    )

@budgets.route('/compare_months')
@login_required
def compare_months():
    # Get months from request or default to current and previous
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    # Default to comparing current month with previous month
    prev_month = 12 if current_month == 1 else current_month - 1
    prev_year = current_year - 1 if current_month == 1 else current_year
    
    # Get selected months from request
    month1 = request.args.get('month1', type=int) or prev_month
    year1 = request.args.get('year1', type=int) or prev_year
    month2 = request.args.get('month2', type=int) or current_month
    year2 = request.args.get('year2', type=int) or current_year
    
    # Get comparison data
    from monthly_analysis import compare_months
    comparison_data = compare_months(current_user.id, month1, year1, month2, year2)
    
    # Get available months for dropdowns
    month_options = get_month_year_options()
    
    return render_template(
        'budgets/compare_months.html',
        comparison_data=comparison_data,
        month_options=month_options,
        selected_month1=month1,
        selected_year1=year1,
        selected_month2=month2,
        selected_year2=year2
    )