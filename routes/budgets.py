from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Budget, db
from forms import BudgetForm

budgets = Blueprint('budgets', __name__)

@budgets.route('/set_budget', methods=['GET', 'POST'])
@login_required
def set_budget():
    form = BudgetForm()
    current_budget = Budget.query.filter_by(user_id=current_user.id).first()

    if form.validate_on_submit():
        if current_budget:
            current_budget.amount = form.amount.data
        else:
            new_budget = Budget(user_id=current_user.id, amount=form.amount.data)
            db.session.add(new_budget)
        db.session.commit()
        flash('Budget updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    if current_budget:
        form.amount.data = current_budget.amount

    return render_template('set_budget.html', form=form, budget=current_budget)