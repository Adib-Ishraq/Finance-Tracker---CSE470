from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, SelectField, DateField
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