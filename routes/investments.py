from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime

from models import db, InvestmentAccount, Investment, Transaction
from forms import InvestmentAccountForm, InvestmentForm

investments = Blueprint('investments', __name__)

@investments.route('/investments')
@login_required
def investment_dashboard():
    accounts = InvestmentAccount.query.filter_by(user_id=current_user.id).all()
    
    # Calculate portfolio summary
    total_invested = sum([account.total_invested_amount for account in accounts])
    total_current_value = sum([account.total_current_value for account in accounts])
    total_profit_loss = total_current_value - total_invested
    
    profit_percentage = 0
    if total_invested > 0:
        profit_percentage = (total_profit_loss / total_invested) * 100
    
    # Group investments by risk category
    all_investments = []
    for account in accounts:
        all_investments.extend(account.investments)
        
    risk_categories = {}
    for investment in all_investments:
        if investment.risk_category not in risk_categories:
            risk_categories[investment.risk_category] = {
                'count': 0,
                'total_value': 0,
                'total_invested': 0,
                'profit_loss': 0
            }
        
        risk_categories[investment.risk_category]['count'] += 1
        risk_categories[investment.risk_category]['total_value'] += investment.current_value
        risk_categories[investment.risk_category]['total_invested'] += investment.initial_investment
        risk_categories[investment.risk_category]['profit_loss'] += investment.profit_loss
    
    return render_template('investments/dashboard.html', 
                          accounts=accounts, 
                          total_invested=total_invested,
                          total_current_value=total_current_value,
                          total_profit_loss=total_profit_loss,
                          profit_percentage=profit_percentage,
                          risk_categories=risk_categories)

@investments.route('/investments/account/new', methods=['GET', 'POST'])
@login_required
def add_account():
    form = InvestmentAccountForm()
    
    if form.validate_on_submit():
        account = InvestmentAccount(
            user_id=current_user.id,
            name=form.name.data,
            account_type=form.account_type.data,
            description=form.description.data
        )
        
        db.session.add(account)
        db.session.commit()
        
        flash('Investment account added successfully!', 'success')
        return redirect(url_for('investments.investment_dashboard'))
    
    return render_template('investments/add_account.html', form=form)

@investments.route('/investments/account/<int:account_id>')
@login_required
def account_detail(account_id):
    account = InvestmentAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    return render_template('investments/account_detail.html', account=account)

@investments.route('/investments/account/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = InvestmentAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    form = InvestmentAccountForm(obj=account)
    
    if form.validate_on_submit():
        account.name = form.name.data
        account.account_type = form.account_type.data
        account.description = form.description.data
        
        db.session.commit()
        
        flash('Investment account updated successfully!', 'success')
        return redirect(url_for('investments.account_detail', account_id=account.id))
    
    return render_template('investments/edit_account.html', form=form, account=account)

@investments.route('/investments/account/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    account = InvestmentAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    db.session.delete(account)
    db.session.commit()
    
    flash('Investment account deleted successfully!', 'success')
    return redirect(url_for('investments.investment_dashboard'))

@investments.route('/investments/account/<int:account_id>/add', methods=['GET', 'POST'])
@login_required
def add_investment(account_id):
    account = InvestmentAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    form = InvestmentForm()
    
    if form.validate_on_submit():
        investment = Investment(
            account_id=account.id,
            name=form.name.data,
            symbol=form.symbol.data,
            investment_type=form.investment_type.data,
            risk_category=form.risk_category.data,
            initial_investment=form.initial_investment.data,
            quantity=form.quantity.data,
            purchase_date=form.purchase_date.data,
            current_value=form.current_value.data,
            notes=form.notes.data
        )
        
        # Create a transaction to deduct the investment amount from main balance
        transaction = Transaction(
            user_id=current_user.id,
            type="Expense",
            category="Investment",
            amount=form.initial_investment.data,
            date=form.purchase_date.data
        )
        
        db.session.add(investment)
        db.session.add(transaction)
        db.session.commit()
        
        flash('Investment added successfully and amount deducted from your balance!', 'success')
        return redirect(url_for('investments.account_detail', account_id=account.id))
    
    return render_template('investments/add_investment.html', form=form, account=account)

@investments.route('/investments/<int:investment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_investment(investment_id):
    investment = Investment.query.join(InvestmentAccount).filter(
        Investment.id == investment_id,
        InvestmentAccount.user_id == current_user.id
    ).first_or_404()
    
    form = InvestmentForm(obj=investment)
    
    if form.validate_on_submit():
        investment.name = form.name.data
        investment.symbol = form.symbol.data
        investment.investment_type = form.investment_type.data
        investment.risk_category = form.risk_category.data
        investment.initial_investment = form.initial_investment.data
        investment.quantity = form.quantity.data
        investment.purchase_date = form.purchase_date.data
        investment.current_value = form.current_value.data
        investment.notes = form.notes.data
        
        db.session.commit()
        
        flash('Investment updated successfully!', 'success')
        return redirect(url_for('investments.account_detail', account_id=investment.account_id))
    
    return render_template('investments/edit_investment.html', form=form, investment=investment)

@investments.route('/investments/<int:investment_id>/delete', methods=['POST'])
@login_required
def delete_investment(investment_id):
    investment = Investment.query.join(InvestmentAccount).filter(
        Investment.id == investment_id,
        InvestmentAccount.user_id == current_user.id
    ).first_or_404()
    
    account_id = investment.account_id
    
    db.session.delete(investment)
    db.session.commit()
    
    flash('Investment deleted successfully!', 'success')
    return redirect(url_for('investments.account_detail', account_id=account_id))

@investments.route('/investments/portfolio/performance')
@login_required
def portfolio_performance():
    accounts = InvestmentAccount.query.filter_by(user_id=current_user.id).all()
    
    all_investments = []
    for account in accounts:
        all_investments.extend(account.investments)
    
    # Group by type
    investment_types = {}
    for investment in all_investments:
        if investment.investment_type not in investment_types:
            investment_types[investment.investment_type] = {
                'count': 0,
                'total_value': 0,
                'total_invested': 0,
                'profit_loss': 0,
                'investments': []
            }
        
        investment_types[investment.investment_type]['count'] += 1
        investment_types[investment.investment_type]['total_value'] += investment.current_value
        investment_types[investment.investment_type]['total_invested'] += investment.initial_investment
        investment_types[investment.investment_type]['profit_loss'] += investment.profit_loss
        investment_types[investment.investment_type]['investments'].append(investment)
    
    return render_template('investments/performance.html', 
                          accounts=accounts,
                          investment_types=investment_types)

@investments.route('/investments/<int:investment_id>')
@login_required
def investment_detail(investment_id):
    investment = Investment.query.join(InvestmentAccount).filter(
        Investment.id == investment_id,
        InvestmentAccount.user_id == current_user.id
    ).first_or_404()
    
    return render_template('investments/investment_detail.html', investment=investment)