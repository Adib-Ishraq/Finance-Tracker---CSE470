from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Debt, DebtPayment
from datetime import datetime
from forms import DebtForm, DebtPaymentForm
from sqlalchemy import desc

debts = Blueprint('debts', __name__)

@debts.route('/debts')
@login_required
def view_debts():
    debts_owed = Debt.query.filter_by(user_id=current_user.id, type='Debt').all()
    loans_given = Debt.query.filter_by(user_id=current_user.id, type='Loan').all()
    return render_template('debt/view_debts.html', debts=debts_owed, loans=loans_given)

@debts.route('/debts/add', methods=['GET', 'POST'])
@login_required
def add_debt():
    form = DebtForm()
    if form.validate_on_submit():
        new_debt = Debt(
            user_id=current_user.id,
            type=form.type.data,
            person=form.person.data,
            amount=float(form.amount.data),
            debt_date=form.debt_date.data,
            repayment_date=form.repayment_date.data
        )
        db.session.add(new_debt)
        db.session.commit()
        flash(f"{'Debt' if form.type.data == 'Debt' else 'Loan'} added successfully!", 'success')
        return redirect(url_for('debts.view_debts'))
    return render_template('debt/add_debt.html', form=form)

@debts.route('/debts/payment/<int:debt_id>', methods=['GET', 'POST'])
@login_required
def add_payment(debt_id):
    debt = Debt.query.get_or_404(debt_id)
    if debt.user_id != current_user.id:
        flash("You don't have permission to access this debt.", 'danger')
        return redirect(url_for('debts.view_debts'))
    
    form = DebtPaymentForm()
    if form.validate_on_submit():
        payment = DebtPayment(
            debt_id=debt.id,
            payment_date=datetime.utcnow(),
            amount_paid=float(form.amount_paid.data)
        )
        db.session.add(payment)
        db.session.commit()
        flash('Payment added successfully!', 'success')
        return redirect(url_for('debts.view_debts'))
    return render_template('debt/add_payment.html', form=form, debt=debt)

@debts.route('/debts/history')
@login_required
def debt_history():
    # Get all debts for the current user that have payments
    debts = Debt.query.filter_by(user_id=current_user.id).all()
    
    # Initialize empty payments dictionary
    payments = {}
    
    # For each debt, get all its payments and add to dictionary if payments exist
    for debt in debts:
        debt_payments = DebtPayment.query.filter_by(debt_id=debt.id).order_by(desc(DebtPayment.payment_date)).all()
        if debt_payments:
            payments[debt.id] = debt_payments
    
    # Add debug flash message to see what we've got
    if not payments:
        flash('No payment history found. Make payments on your debts/loans to see them here.', 'info')
    
    return render_template('debt/debt_history.html', debts=debts, payments=payments)

@debts.route('/debts/reminder')
@login_required
def debt_reminder():
    today = datetime.utcnow().date()
    upcoming_debts = Debt.query.filter_by(user_id=current_user.id).all()
    reminders = []
    for debt in upcoming_debts:
        if debt.outstanding > 0:  # Only consider debts with outstanding amounts
            days_left = (debt.repayment_date.date() - today).days if debt.repayment_date else 0
            if days_left <= 30:  # Show reminders for debts due in the next 30 days
                reminders.append({
                    'debt': debt,
                    'days_left': days_left
                })
    return render_template('debt/reminder.html', reminders=reminders)

@debts.route('/debts/delete/<int:debt_id>', methods=['GET', 'POST'])
@login_required
def delete_debt(debt_id):
    debt = Debt.query.get_or_404(debt_id)
    if debt.user_id != current_user.id:
        flash("You don't have permission to delete this debt.", 'danger')
        return redirect(url_for('debts.view_debts'))
    
    db.session.delete(debt)
    db.session.commit()
    flash('Debt deleted successfully!', 'success')
    return redirect(url_for('debts.view_debts'))