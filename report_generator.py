import pandas as pd
import io
import csv
import json
from datetime import datetime
from flask import Response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_csv(data, filename):
    """Generate a CSV file from data"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    if data and len(data) > 0:
        if isinstance(data[0], dict):
            headers = data[0].keys()
            writer.writerow(headers)
            
            # Write data rows
            for row in data:
                writer.writerow(row.values())
        else:
            # Handle custom data format
            if hasattr(data, 'headers') and hasattr(data, 'rows'):
                writer.writerow(data.headers)
                writer.writerows(data.rows)
    
    # Create response
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def generate_json(data, filename):
    """Generate a JSON file from data"""
    if hasattr(data, 'to_dict'):
        # Handle pandas dataframes
        json_data = data.to_dict(orient='records')
    elif hasattr(data, '__dict__'):
        # Handle objects
        json_data = [item.__dict__ for item in data]
    else:
        # Assume data is already in correct format
        json_data = data
        
    response = Response(
        json.dumps(json_data, indent=4, default=str),
        mimetype='application/json'
    )
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

def generate_pdf_report(title, data_sections, filename, user_name=None):
    """
    Generate a PDF report with multiple data sections
    
    data_sections: List of dictionaries with keys:
        - title: Section title
        - data: Data to be displayed in a table
        - headers: Column headers for the table
        - summary: Optional summary text to display after the table
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(name='Title', fontSize=18, alignment=1, spaceAfter=12))
    styles.add(ParagraphStyle(name='Heading2', fontSize=14, alignment=0, spaceAfter=10, spaceBefore=10))
    styles.add(ParagraphStyle(name='Normal', fontSize=10, alignment=0, spaceAfter=6))
    styles.add(ParagraphStyle(name='Footer', fontSize=8, alignment=1, textColor=colors.gray))
    
    # Add title
    elements.append(Paragraph(title, styles['Title']))
    
    # Add date and user info
    current_date = datetime.now().strftime("%Y-%m-%d")
    elements.append(Paragraph(f"Report Date: {current_date}", styles['Normal']))
    if user_name:
        elements.append(Paragraph(f"User: {user_name}", styles['Normal']))
    
    # Add spacer
    elements.append(Spacer(1, 20))
    
    # Process each data section
    for section in data_sections:
        # Add section title
        elements.append(Paragraph(section['title'], styles['Heading2']))
        
        # Create table
        if 'data' in section and section['data'] and 'headers' in section:
            # Prepare table data with headers
            table_data = [section['headers']]
            
            # Process data based on type
            rows = section['data']
            if isinstance(rows, list) and len(rows) > 0:
                if isinstance(rows[0], dict):
                    # Extract values based on headers
                    header_keys = section.get('header_keys', section['headers'])
                    for row in rows:
                        table_data.append([row.get(key, '') for key in header_keys])
                else:
                    # Assume data is already formatted as rows
                    table_data.extend(rows)
                
                # Create and style the table
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lavender),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ]))
                
                elements.append(table)
        
            # Add section summary if available
            if 'summary' in section and section['summary']:
                elements.append(Paragraph(section['summary'], styles['Normal']))
        
        # Add spacer between sections
        elements.append(Spacer(1, 15))
    
    # Add footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Generated by Finance Tracker", styles['Footer']))
    elements.append(Paragraph(f"Report generated on {current_date}", styles['Footer']))
    
    # Build and save PDF
    doc.build(elements)
    
    # Create response with PDF
    buffer.seek(0)
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:.2f}"

def prepare_transaction_report_data(transactions, start_date=None, end_date=None):
    """Prepare transaction data for report generation"""
    # Filter transactions by date if specified
    filtered_transactions = transactions
    if start_date:
        filtered_transactions = [t for t in filtered_transactions if t.date >= start_date]
    if end_date:
        filtered_transactions = [t for t in filtered_transactions if t.date <= end_date]
    
    # Calculate summary statistics
    total_income = sum(t.amount for t in filtered_transactions if t.type == 'Income')
    total_expenses = sum(t.amount for t in filtered_transactions if t.type == 'Expense')
    net_cashflow = total_income - total_expenses
    
    # Prepare transaction data
    transaction_data = []
    for t in filtered_transactions:
        transaction_data.append({
            'date': t.date.strftime('%Y-%m-%d'),
            'type': t.type,
            'category': t.category,
            'description': getattr(t, 'description', ''),
            'amount': format_currency(t.amount)
        })
    
    # Prepare category summary data
    category_summary = {}
    for t in filtered_transactions:
        if t.category not in category_summary:
            category_summary[t.category] = {
                'type': t.type,
                'total': 0
            }
        category_summary[t.category]['total'] += t.amount
    
    category_data = []
    for category, data in category_summary.items():
        category_data.append({
            'category': category,
            'type': data['type'],
            'amount': format_currency(data['total'])
        })
    
    # Sort by amount
    category_data.sort(key=lambda x: float(x['amount'].replace('$', '')), reverse=True)
    
    return {
        'transactions': transaction_data,
        'categories': category_data,
        'summary': {
            'total_income': format_currency(total_income),
            'total_expenses': format_currency(total_expenses),
            'net_cashflow': format_currency(net_cashflow),
            'transaction_count': len(filtered_transactions)
        }
    }

def prepare_investment_report_data(accounts, investments):
    """Prepare investment data for report generation"""
    # Calculate summary statistics
    total_invested = sum(investment.initial_investment for investment in investments)
    total_current_value = sum(investment.current_value for investment in investments)
    total_profit_loss = total_current_value - total_invested
    profit_percentage = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
    
    # Prepare account data
    account_data = []
    for account in accounts:
        account_data.append({
            'name': account.name,
            'type': account.account_type,
            'current_value': format_currency(account.total_current_value),
            'invested': format_currency(account.total_invested_amount),
            'profit_loss': format_currency(account.total_profit_loss),
            'return_percentage': f"{account.total_profit_loss_percentage:.2f}%"
        })
    
    # Prepare investment data
    investment_data = []
    for inv in investments:
        investment_data.append({
            'name': inv.name,
            'symbol': inv.symbol or '',
            'account': inv.account.name,
            'type': inv.investment_type,
            'risk': inv.risk_category,
            'purchase_date': inv.purchase_date.strftime('%Y-%m-%d'),
            'invested': format_currency(inv.initial_investment),
            'current_value': format_currency(inv.current_value),
            'profit_loss': format_currency(inv.profit_loss),
            'return': f"{inv.profit_loss_percentage:.2f}%"
        })
    
    # Sort by profit/loss
    investment_data.sort(key=lambda x: float(x['profit_loss'].replace('$', '').replace(',', '')), reverse=True)
    
    return {
        'accounts': account_data,
        'investments': investment_data,
        'summary': {
            'total_invested': format_currency(total_invested),
            'total_current_value': format_currency(total_current_value),
            'total_profit_loss': format_currency(total_profit_loss),
            'return_percentage': f"{profit_percentage:.2f}%",
            'account_count': len(accounts),
            'investment_count': len(investments)
        }
    }

def prepare_financial_report_data(user, transactions, accounts, investments, start_date=None, end_date=None):
    """Prepare comprehensive financial report data"""
    transaction_data = prepare_transaction_report_data(transactions, start_date, end_date)
    investment_data = prepare_investment_report_data(accounts, investments)
    
    # Calculate net worth
    cash_flow = float(transaction_data['summary']['net_cashflow'].replace('$', '').replace(',', ''))
    investments_value = float(investment_data['summary']['total_current_value'].replace('$', '').replace(',', ''))
    
    # Get account balances (simplified)
    account_balances = sum(account.total_current_value for account in accounts)
    
    # Prepare data sections for PDF report
    data_sections = [
        {
            'title': 'Financial Summary',
            'data': [
                ['Total Income', transaction_data['summary']['total_income']],
                ['Total Expenses', transaction_data['summary']['total_expenses']],
                ['Net Cash Flow', transaction_data['summary']['net_cashflow']],
                ['Investment Value', investment_data['summary']['total_current_value']],
                ['Investment Return', investment_data['summary']['return_percentage']],
                ['Net Worth', format_currency(cash_flow + investments_value)]
            ],
            'headers': ['Item', 'Value']
        },
        {
            'title': 'Transaction Categories',
            'data': transaction_data['categories'],
            'headers': ['Category', 'Type', 'Amount'],
            'header_keys': ['category', 'type', 'amount']
        },
        {
            'title': 'Investment Accounts',
            'data': investment_data['accounts'],
            'headers': ['Account', 'Type', 'Current Value', 'Return'],
            'header_keys': ['name', 'type', 'current_value', 'return_percentage']
        },
        {
            'title': 'Top Investments',
            'data': investment_data['investments'][:10],  # Show top 10
            'headers': ['Investment', 'Type', 'Risk Level', 'Current Value', 'Profit/Loss'],
            'header_keys': ['name', 'type', 'risk', 'current_value', 'profit_loss']
        }
    ]
    
    return {
        'user': {
            'name': user.username,
            'email': user.email
        },
        'data_sections': data_sections,
        'summary': {
            'net_worth': format_currency(cash_flow + investments_value),
            'report_period': f"{start_date.strftime('%Y-%m-%d') if start_date else 'All time'} to {end_date.strftime('%Y-%m-%d') if end_date else 'Present'}"
        }
    }
