from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from models import db, Transaction, RecurringExpense
from datetime import datetime, timedelta
import requests
import json

bank = Blueprint('bank', __name__)

# Mock bank API endpoints
MOCK_BANK_API = {
    'base_url': 'https://api.mockbank.com/v1',
    'endpoints': {
        'transactions': '/transactions',
        'accounts': '/accounts',
        'categories': '/categories'
    }
}

def categorize_transaction(description, amount):
    """
    Mock AI-powered transaction categorization
    In a real implementation, this would use a machine learning model
    """
    categories = {
        'food': ['restaurant', 'cafe', 'grocery', 'food', 'meal'],
        'transport': ['uber', 'lyft', 'taxi', 'transport', 'bus', 'train'],
        'shopping': ['amazon', 'walmart', 'target', 'shop', 'store'],
        'utilities': ['electric', 'water', 'gas', 'internet', 'phone'],
        'entertainment': ['netflix', 'spotify', 'movie', 'theatre', 'concert'],
        'health': ['pharmacy', 'doctor', 'medical', 'health', 'dental'],
        'housing': ['rent', 'mortgage', 'maintenance', 'repair'],
        'other': []
    }
    
    description = description.lower()
    for category, keywords in categories.items():
        if any(keyword in description for keyword in keywords):
            return category
    return 'other'

@bank.route('/api/bank/connect', methods=['POST'])
@login_required
def connect_bank():
    """
    Mock bank connection endpoint
    In a real implementation, this would handle OAuth flow with the bank
    """
    bank_name = request.json.get('bank_name')
    # In a real implementation, this would store bank credentials securely
    return jsonify({
        "success": True,
        "message": f"Successfully connected to {bank_name}",
        "bank_name": bank_name
    })

@bank.route('/api/bank/transactions', methods=['GET'])
@login_required
def get_bank_transactions():
    """
    Mock endpoint to fetch transactions from bank
    In a real implementation, this would call the bank's API
    """
    # Mock data
    mock_transactions = [
        {
            "id": "t1",
            "date": "2024-03-01",
            "description": "Grocery Store",
            "amount": -150.50,
            "category": "food"
        },
        {
            "id": "t2",
            "date": "2024-03-02",
            "description": "Salary Deposit",
            "amount": 3000.00,
            "category": "income"
        }
    ]
    
    return jsonify({"transactions": mock_transactions})

@bank.route('/api/bank/sync', methods=['POST'])
@login_required
def sync_transactions():
    """
    Sync transactions from bank to local database
    """
    # Get transactions from bank
    bank_transactions = get_bank_transactions().get_json()['transactions']
    
    new_transactions = []
    for t in bank_transactions:
        # Check if transaction already exists
        existing = Transaction.query.filter_by(
            user_id=current_user.id,
            date=datetime.strptime(t['date'], '%Y-%m-%d'),
            amount=abs(t['amount'])
        ).first()
        
        if not existing:
            # Categorize transaction using AI
            category = categorize_transaction(t['description'], t['amount'])
            
            new_transaction = Transaction(
                user_id=current_user.id,
                type='Income' if t['amount'] > 0 else 'Expense',
                category=category,
                amount=abs(t['amount']),
                date=datetime.strptime(t['date'], '%Y-%m-%d')
            )
            new_transactions.append(new_transaction)
    
    if new_transactions:
        db.session.bulk_save_objects(new_transactions)
        db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Synced {len(new_transactions)} new transactions"
    })

@bank.route('/api/recurring-expenses', methods=['GET', 'POST'])
@login_required
def handle_recurring_expenses():
    if request.method == 'GET':
        expenses = RecurringExpense.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()
        
        return jsonify({
            "expenses": [{
                'id': e.id,
                'name': e.name,
                'amount': e.amount,
                'category': e.category,
                'frequency': e.frequency,
                'next_date': e.next_date.strftime('%Y-%m-%d')
            } for e in expenses]
        })
    
    # POST - Create new recurring expense
    data = request.get_json()
    new_expense = RecurringExpense(
        user_id=current_user.id,
        name=data['name'],
        amount=data['amount'],
        category=data['category'],
        frequency=data['frequency'],
        next_date=datetime.strptime(data['next_date'], '%Y-%m-%d')
    )
    
    db.session.add(new_expense)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Recurring expense created successfully",
        "expense_id": new_expense.id
    })

@bank.route('/api/recurring-expenses/<int:expense_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_recurring_expense(expense_id):
    expense = RecurringExpense.query.get_or_404(expense_id)
    
    if expense.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    if request.method == 'DELETE':
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"message": "Recurring expense deleted successfully"})
    
    # PUT - Update recurring expense
    data = request.get_json()
    expense.name = data.get('name', expense.name)
    expense.amount = data.get('amount', expense.amount)
    expense.category = data.get('category', expense.category)
    expense.frequency = data.get('frequency', expense.frequency)
    expense.next_date = datetime.strptime(data['next_date'], '%Y-%m-%d') if 'next_date' in data else expense.next_date
    expense.is_active = data.get('is_active', expense.is_active)
    
    db.session.commit()
    return jsonify({"message": "Recurring expense updated successfully"}) 