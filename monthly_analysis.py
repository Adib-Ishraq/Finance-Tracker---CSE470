"""
Monthly Transaction and Budget Analysis Module
This module provides functions to analyze transaction data on a monthly basis
and implement monthly budget features including rollover.
"""

from models import Transaction, Budget, db
from sqlalchemy import func, extract
from datetime import datetime
import calendar

def get_month_name(month_number):
    """Convert month number to name"""
    return calendar.month_name[month_number]

def get_month_year_options():
    """Get list of available months and years for dropdowns
    
    Returns a list of dictionaries with month, year and display label
    that can be used in dropdown menus for month selection.
    """
    from models import Transaction, db
    from sqlalchemy import distinct, extract
    
    options = []
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    # First, add all months from current year and previous year
    for year in range(current_year-1, current_year+1):
        for month in range(1, 13):
            # Skip future months
            if year == current_year and month > current_month:
                continue
                
            month_name = get_month_name(month)
            options.append({
                'year': year,
                'month': month,
                'label': f"{month_name} {year}"
            })
    
    # Then add any additional years/months from transaction history
    years_months = db.session.query(
        extract('year', Transaction.date),
        extract('month', Transaction.date)
    ).distinct().all()
    
    # Add any historical transactions not already in the list
    for year, month in years_months:
        if year and month:
            year = int(year)
            month = int(month)
            
            # Skip if already in options
            if any(o['year'] == year and o['month'] == month for o in options):
                continue
                
            month_name = get_month_name(month)
            options.append({
                'year': year,
                'month': month,
                'label': f"{month_name} {year}"
            })
    
    # Sort options by year and month (newest first)
    return sorted(options, key=lambda x: (x['year'], x['month']), reverse=True)

def get_monthly_budget_data(user_id, month=None, year=None):
    """Get all budget and transaction data for a specific month"""
    if month is None:
        month = datetime.utcnow().month
    if year is None:
        year = datetime.utcnow().year
    
    # Get or create budget for the month
    budget = Budget.get_budget_by_month(user_id, month, year)
    
    if not budget:
        # If no budget exists, create a new one
        prev_month = 12 if month == 1 else month - 1
        prev_year = year - 1 if month == 1 else year
        prev_budget = Budget.get_budget_by_month(user_id, prev_month, prev_year)
        
        # Use previous budget amount or default to 0
        budget_amount = prev_budget.amount if prev_budget else 0
        rollover = 0
        
        # Calculate rollover from previous month if enabled
        if prev_budget and prev_budget.enable_rollover:
            # Get previous month's expenses
            prev_expenses = Transaction.get_monthly_totals(user_id, prev_month, prev_year)['expenses']
            remaining = prev_budget.amount + prev_budget.rollover_amount - prev_expenses
            rollover = max(0, remaining)  # Only positive values
        
        # Create new budget
        budget = Budget(
            user_id=user_id,
            amount=budget_amount,
            month=month,
            year=year,
            rollover_amount=rollover,
            enable_rollover=True
        )
        db.session.add(budget)
        db.session.commit()
    
    # Get transactions data for the month
    monthly_totals = Transaction.get_monthly_totals(user_id, month, year)
    
    # Get category breakdown for the month
    expense_categories = Transaction.get_monthly_category_totals(user_id, "Expense", month, year)
    income_categories = Transaction.get_monthly_category_totals(user_id, "Income", month, year)
    
    # Get daily spending data for chart
    daily_spending = get_daily_spending(user_id, month, year)
    
    # Calculate budget metrics
    total_budget = budget.amount + budget.rollover_amount
    remaining_budget = total_budget - monthly_totals['expenses']
    budget_percent_used = (monthly_totals['expenses'] / total_budget * 100) if total_budget > 0 else 0
    
    # Format month name
    month_name = get_month_name(month)
    
    return {
        'budget': budget,
        'monthly_totals': monthly_totals,
        'expense_categories': expense_categories,
        'income_categories': income_categories,
        'daily_spending': daily_spending,
        'total_budget': total_budget,
        'remaining_budget': remaining_budget,
        'budget_percent_used': budget_percent_used,
        'month_name': month_name,
        'year': year
    }

def get_daily_spending(user_id, month, year):
    """Get daily spending totals for a month"""
    # Get number of days in the month
    num_days = calendar.monthrange(year, month)[1]
    
    # Query for daily expense totals
    daily_totals = db.session.query(
        extract('day', Transaction.date),
        func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'Expense',
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).group_by(
        extract('day', Transaction.date)
    ).all()
    
    # Convert to dict with day as key
    daily_data = {day: 0 for day in range(1, num_days + 1)}
    for day, total in daily_totals:
        daily_data[int(day)] = float(total)
    
    # Format for chart
    return {
        'labels': list(range(1, num_days + 1)),
        'data': list(daily_data.values())
    }

def compare_months(user_id, first_month, first_year, second_month, second_year):
    """Compare two months' financial data"""
    # Get data for both months
    first_month_data = get_monthly_budget_data(user_id, first_month, first_year)
    second_month_data = get_monthly_budget_data(user_id, second_month, second_year)
    
    # Calculate differences
    income_diff = second_month_data['monthly_totals']['income'] - first_month_data['monthly_totals']['income']
    income_percent = (income_diff / first_month_data['monthly_totals']['income'] * 100) if first_month_data['monthly_totals']['income'] > 0 else 0
    
    expense_diff = second_month_data['monthly_totals']['expenses'] - first_month_data['monthly_totals']['expenses']
    expense_percent = (expense_diff / first_month_data['monthly_totals']['expenses'] * 100) if first_month_data['monthly_totals']['expenses'] > 0 else 0
    
    # Compare category spending
    first_categories = {cat[0]: cat[1] for cat in first_month_data['expense_categories']}
    second_categories = {cat[0]: cat[1] for cat in second_month_data['expense_categories']}
    
    # All unique categories
    all_categories = set(list(first_categories.keys()) + list(second_categories.keys()))
    
    category_comparison = []
    for category in all_categories:
        first_amount = first_categories.get(category, 0)
        second_amount = second_categories.get(category, 0)
        diff = second_amount - first_amount
        percent = (diff / first_amount * 100) if first_amount > 0 else 0 if diff == 0 else 100
        
        category_comparison.append({
            'category': category,
            'first_amount': first_amount,
            'second_amount': second_amount,
            'difference': diff,
            'percent_change': percent
        })
    
    # Sort by absolute difference
    category_comparison.sort(key=lambda x: abs(x['difference']), reverse=True)
    
    return {
        'first_month': first_month_data,
        'second_month': second_month_data,
        'income_difference': income_diff,
        'income_percent_change': income_percent,
        'expense_difference': expense_diff,
        'expense_percent_change': expense_percent,
        'category_comparison': category_comparison,
        'first_month_name': get_month_name(first_month),
        'second_month_name': get_month_name(second_month)
    }
