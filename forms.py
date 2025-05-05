from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, SelectField, DateField, TextAreaField
from wtforms.validators import InputRequired, Length, EqualTo, Email
from datetime import datetime

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[InputRequired(), Email(), Length(max=150)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=20)])
    confirm_password = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

class TransactionForm(FlaskForm):
    type = SelectField('Type', choices=[('Income', 'Income'), ('Expense', 'Expense')], validators=[InputRequired()])
    category = StringField('Category', validators=[InputRequired()])
    amount = DecimalField('Amount', validators=[InputRequired()])
    date = DateField('Date', validators=[InputRequired()], default=datetime.utcnow)
    submit = SubmitField('Add Transaction')

class BudgetForm(FlaskForm):
    amount = DecimalField('Budget Amount', validators=[InputRequired()])
    submit = SubmitField('Set Budget')

class GoalForm(FlaskForm):
    name = StringField('Goal Name', validators=[InputRequired(), Length(max=100)])
    target_amount = DecimalField('Target Amount', validators=[InputRequired()])
    current_amount = DecimalField('Current Amount', default=0.0)
    deadline = DateField('Deadline (Optional)', validators=[], format='%Y-%m-%d')
    submit = SubmitField('Save Goal')

class ContributeForm(FlaskForm):
    amount = DecimalField('Contribution Amount', validators=[InputRequired()])
    submit = SubmitField('Add Contribution')

# Investment Forms
class InvestmentAccountForm(FlaskForm):
    name = StringField('Account Name', validators=[InputRequired(), Length(max=100)])
    account_type = SelectField('Account Type', choices=[
        ('Brokerage', 'Brokerage'),
        ('IRA', 'IRA'),
        ('401k', '401(k)'),
        ('Roth_IRA', 'Roth IRA'),
        ('Crypto_Wallet', 'Crypto Wallet'),
        ('Other', 'Other')
    ], validators=[InputRequired()])
    description = TextAreaField('Description', validators=[Length(max=255)])
    submit = SubmitField('Save Account')

class InvestmentForm(FlaskForm):
    name = StringField('Investment Name', validators=[InputRequired(), Length(max=100)])
    symbol = StringField('Symbol/Ticker', validators=[Length(max=20)])
    investment_type = SelectField('Investment Type', choices=[
        ('stock', 'Stock'),
        ('crypto', 'Cryptocurrency'),
        ('mutual_fund', 'Mutual Fund'),
        ('etf', 'ETF'),
        ('bond', 'Bond'),
        ('other', 'Other')
    ], validators=[InputRequired()])
    risk_category = SelectField('Risk Category', choices=[
        ('low_risk', 'Low Risk'),
        ('medium_risk', 'Medium Risk'),
        ('high_risk', 'High Risk')
    ], validators=[InputRequired()])
    initial_investment = DecimalField('Initial Investment ($)', validators=[InputRequired()])
    quantity = DecimalField('Quantity', validators=[InputRequired()], default=1.0)
    purchase_date = DateField('Purchase Date', validators=[InputRequired()], default=datetime.utcnow)
    current_value = DecimalField('Current Value ($)', validators=[InputRequired()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Investment')

# Debt Forms
class DebtForm(FlaskForm):
    type = SelectField('Type', choices=[('Debt', 'Debt (I Owe)'), ('Loan', 'Loan (Lent Out)')], validators=[InputRequired()])
    person = StringField('Person', validators=[InputRequired(), Length(max=100)])
    amount = DecimalField('Amount', validators=[InputRequired()])
    debt_date = DateField('Debt/Loan Date', validators=[InputRequired()], default=datetime.utcnow)
    repayment_date = DateField('Repayment Date', validators=[InputRequired()])
    submit = SubmitField('Add Debt/Loan')

class DebtPaymentForm(FlaskForm):
    amount_paid = DecimalField('Amount Paid', validators=[InputRequired()])
    submit = SubmitField('Add Payment')