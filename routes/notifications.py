from flask import Blueprint, jsonify, request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Bill, Transaction, RecurringExpense, Goal, Budget
from datetime import datetime, timedelta
from sqlalchemy import func
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

notifications = Blueprint('notifications', __name__)

# Add Notification class to store user notifications
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # transaction, budget, goal
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = current_app.config['MAIL_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@notifications.route('/api/notifications/preferences', methods=['GET', 'PUT'])
@login_required
def notification_preferences():
    if request.method == 'GET':
        return jsonify(current_user.notification_preferences)
    
    data = request.get_json()
    current_user.notification_preferences.update(data)
    db.session.commit()
    return jsonify({"message": "Preferences updated successfully"})

@notifications.route('/api/notifications/bills', methods=['GET'])
@login_required
def get_bill_reminders():
    if not current_user.notification_preferences.get('bill_reminders'):
        return jsonify({"reminders": []})
    
    upcoming_bills = Bill.query.filter(
        Bill.user_id == current_user.id,
        Bill.is_paid == False,
        Bill.due_date <= datetime.utcnow() + timedelta(days=7)
    ).all()
    
    reminders = [{
        'id': bill.id,
        'name': bill.name,
        'amount': bill.amount,
        'due_date': bill.due_date.strftime('%Y-%m-%d'),
        'days_remaining': (bill.due_date - datetime.utcnow()).days
    } for bill in upcoming_bills]
    
    return jsonify({"reminders": reminders})

@notifications.route('/api/notifications/spending', methods=['GET'])
@login_required
def get_spending_alerts():
    if not current_user.notification_preferences.get('spending_alerts'):
        return jsonify({"alerts": []})
    
    # Get monthly spending
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_spending = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'Expense',
        Transaction.date >= current_month
    ).with_entities(func.sum(Transaction.amount)).scalar() or 0
    
    # Get budget
    budget = current_user.budget.amount if current_user.budget else 0
    
    alerts = []
    if budget > 0:
        percentage = (monthly_spending / budget) * 100
        if percentage >= 80:
            alerts.append({
                'type': 'budget_warning',
                'message': f'You have used {percentage:.1f}% of your monthly budget',
                'percentage': percentage
            })
    
    return jsonify({"alerts": alerts})

@notifications.route('/api/notifications/recurring', methods=['GET'])
@login_required
def get_recurring_expenses():
    upcoming_expenses = RecurringExpense.query.filter(
        RecurringExpense.user_id == current_user.id,
        RecurringExpense.is_active == True,
        RecurringExpense.next_date <= datetime.utcnow() + timedelta(days=7)
    ).all()
    
    reminders = [{
        'id': expense.id,
        'name': expense.name,
        'amount': expense.amount,
        'next_date': expense.next_date.strftime('%Y-%m-%d'),
        'frequency': expense.frequency
    } for expense in upcoming_expenses]
    
    return jsonify({"reminders": reminders})

@notifications.route('/api/notifications/goals', methods=['GET'])
@login_required
def get_goal_notifications():
    # Check goals that are near completion or deadline
    goals = Goal.query.filter(
        Goal.user_id == current_user.id,
        Goal.current_amount < Goal.target_amount  # Not yet completed
    ).all()
    
    notifications = []
    for goal in goals:
        # Check for goals near completion (>80%)
        if goal.progress_percentage >= 80:
            notifications.append({
                'type': 'goal_progress',
                'goal_id': goal.id,
                'name': goal.name,
                'progress': goal.progress_percentage,
                'message': f'You are {goal.progress_percentage}% toward your goal: {goal.name}'
            })
        
        # Check for goals near deadline (within 7 days)
        if goal.deadline and goal.days_remaining is not None and 0 < goal.days_remaining <= 7:
            notifications.append({
                'type': 'goal_deadline',
                'goal_id': goal.id,
                'name': goal.name,
                'days_remaining': goal.days_remaining,
                'message': f'Only {goal.days_remaining} days left to reach your goal: {goal.name}'
            })
    
    return jsonify({"notifications": notifications})

@notifications.route('/api/notifications/send-test', methods=['POST'])
@login_required
def send_test_notification():
    notification_type = request.json.get('type', 'email')
    
    if notification_type == 'email' and current_user.notification_preferences.get('email_notifications'):
        subject = "Test Notification"
        body = """
        <h2>Test Notification</h2>
        <p>This is a test notification from your Personal Finance Manager.</p>
        <p>If you received this, your email notifications are working correctly!</p>
        """
        success = send_email(current_user.email, subject, body)
        return jsonify({"success": success, "message": "Test email sent" if success else "Failed to send test email"})
    
    return jsonify({"success": False, "message": "Notification type not supported or not enabled"})

@notifications.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notification_read():
    notification_id = request.json.get('id')
    if not notification_id:
        return jsonify({"success": False, "message": "Notification ID required"}), 400
        
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({"success": False, "message": "Notification not found"}), 404
        
    notification.read = True
    db.session.commit()
    return jsonify({"success": True, "message": "Notification marked as read"})

@notifications.route('/api/notifications/all', methods=['GET'])
@login_required
def get_all_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page)
    
    return jsonify({
        "notifications": [{
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "read": n.read,
            "created_at": n.created_at.strftime('%Y-%m-%d %H:%M')
        } for n in notifications.items],
        "total": notifications.total,
        "pages": notifications.pages,
        "current_page": page
    })

@notifications.route('/notifications')
@login_required
def show_notifications():
    # Convert the notification preferences to the specific format expected by the template
    settings = {
        'email_transactions': current_user.notification_preferences.get('email_notifications', False) and 
                              current_user.notification_preferences.get('email_transactions', False),
        'email_budgets': current_user.notification_preferences.get('email_notifications', False) and 
                         current_user.notification_preferences.get('email_budgets', False),
        'email_goals': current_user.notification_preferences.get('email_notifications', False) and 
                       current_user.notification_preferences.get('email_goals', False),
        'push_transactions': current_user.notification_preferences.get('push_transactions', False),
        'push_budgets': current_user.notification_preferences.get('push_budgets', False),
        'push_goals': current_user.notification_preferences.get('push_goals', False)
    }
    
    # Get the most recent notifications
    user_notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(10).all()
    
    return render_template('notifications/notifications.html', settings=settings, notifications=user_notifications)

@notifications.route('/notifications/update', methods=['POST'])
@login_required
def update_settings():
    # Initialize notification_preferences if it doesn't exist
    if not hasattr(current_user, 'notification_preferences') or current_user.notification_preferences is None:
        current_user.notification_preferences = {}
    
    # Update based on form data for specific notification channels
    current_user.notification_preferences.update({
        'email_transactions': 'email_transactions' in request.form,
        'email_budgets': 'email_budgets' in request.form,
        'email_goals': 'email_goals' in request.form,
        'push_transactions': 'push_transactions' in request.form,
        'push_budgets': 'push_budgets' in request.form,
        'push_goals': 'push_goals' in request.form
    })
    
    # Also update the general notification settings
    current_user.notification_preferences.update({
        'email_notifications': any([
            'email_transactions' in request.form,
            'email_budgets' in request.form,
            'email_goals' in request.form
        ]),
        'bill_reminders': True,  # Keep these enabled by default
        'spending_alerts': True  # Keep these enabled by default
    })
    
    db.session.commit()
    flash('Notification settings updated successfully', 'success')
    return redirect(url_for('notifications.show_notifications'))

def create_notification(user_id, title, message, notification_type):
    """Helper function to create a new notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type
    )
    db.session.add(notification)
    db.session.commit()
    return notification