from routes.auth import auth
from routes.transactions import transactions
from routes.budgets import budgets
from routes.goals import goals
from routes.main import main

def register_blueprints(app):
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(transactions)
    app.register_blueprint(budgets)
    app.register_blueprint(goals)