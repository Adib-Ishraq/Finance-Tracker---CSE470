from datetime import datetime, timedelta

def calculate_holding_period(purchase_date):
    """Calculate the holding period in days for an investment"""
    current_date = datetime.now()
    holding_period = (current_date - purchase_date).days
    return holding_period

def calculate_tax_status(purchase_date):
    """Determine if a holding is long-term or short-term for tax purposes"""
    holding_period = calculate_holding_period(purchase_date)
    
    # In most tax jurisdictions, holdings become long-term after 1 year (365 days)
    if holding_period >= 365:
        return "Long-term", holding_period
    else:
        return "Short-term", holding_period

def calculate_capital_gains_tax(profit, tax_status, income_bracket="medium"):
    """
    Estimate capital gains tax based on tax status and income bracket.
    These are approximate rates for educational purposes only.
    """
    # Approximate tax rates (these should be adjusted for actual tax laws)
    tax_rates = {
        "Short-term": {
            "low": 0.10,     # 10% for lower income brackets
            "medium": 0.22,  # 22% for middle income brackets
            "high": 0.35     # 35% for higher income brackets
        },
        "Long-term": {
            "low": 0.0,      # 0% for lower income brackets
            "medium": 0.15,  # 15% for middle income brackets
            "high": 0.20     # 20% for higher income brackets
        }
    }
    
    # Get applicable tax rate
    tax_rate = tax_rates[tax_status][income_bracket]
    
    # Calculate estimated tax
    estimated_tax = profit * tax_rate
    
    return estimated_tax, tax_rate

def analyze_tax_lots(investments, income_bracket="medium"):
    """
    Analyze all investment tax lots and provide tax optimization insights
    """
    tax_analysis = {
        "short_term_holdings": [],
        "long_term_holdings": [],
        "approaching_long_term": [],  # Holdings within 30 days of becoming long-term
        "tax_saving_opportunities": [],
        "total_estimated_tax": 0,
        "potential_tax_savings": 0
    }
    
    for investment in investments:
        profit = investment.profit_loss
        tax_status, holding_period = calculate_tax_status(investment.purchase_date)
        
        # Calculate estimated tax
        estimated_tax, tax_rate = calculate_capital_gains_tax(profit, tax_status, income_bracket)
        
        # Add to appropriate holdings list
        holding_info = {
            "id": investment.id,
            "name": investment.name,
            "symbol": investment.symbol,
            "profit": profit,
            "purchase_date": investment.purchase_date,
            "holding_period": holding_period,
            "estimated_tax": estimated_tax,
            "tax_rate": tax_rate * 100  # Convert to percentage
        }
        
        if tax_status == "Long-term":
            tax_analysis["long_term_holdings"].append(holding_info)
        else:
            tax_analysis["short_term_holdings"].append(holding_info)
            
            # Check if approaching long-term status (within 30 days)
            days_to_long_term = 365 - holding_period
            if days_to_long_term <= 30 and days_to_long_term > 0 and profit > 0:
                holding_info["days_to_long_term"] = days_to_long_term
                
                # Calculate potential tax savings by waiting
                _, long_term_rate = calculate_capital_gains_tax(profit, "Long-term", income_bracket)
                potential_savings = profit * (tax_rate - long_term_rate)
                holding_info["potential_savings"] = potential_savings
                
                tax_analysis["approaching_long_term"].append(holding_info)
                tax_analysis["potential_tax_savings"] += potential_savings
        
        # Add to total estimated tax if profit is positive
        if profit > 0:
            tax_analysis["total_estimated_tax"] += estimated_tax
    
    # Sort the lists by potential tax impact
    tax_analysis["short_term_holdings"].sort(key=lambda x: x["estimated_tax"], reverse=True)
    tax_analysis["long_term_holdings"].sort(key=lambda x: x["estimated_tax"], reverse=True)
    tax_analysis["approaching_long_term"].sort(key=lambda x: x.get("potential_savings", 0), reverse=True)
    
    return tax_analysis

def get_tax_loss_harvesting_opportunities(investments, income_bracket="medium"):
    """
    Identify tax loss harvesting opportunities
    """
    # Group investments by type to find potential replacements
    investment_types = {}
    
    for inv in investments:
        if inv.investment_type not in investment_types:
            investment_types[inv.investment_type] = []
        investment_types[inv.investment_type].append(inv)
    
    opportunities = []
    
    # Find investments with losses
    for inv in investments:
        if inv.profit_loss < 0:
            loss_amount = abs(inv.profit_loss)
            tax_status, _ = calculate_tax_status(inv.purchase_date)
            
            # Calculate tax benefit from harvesting this loss
            _, tax_rate = calculate_capital_gains_tax(loss_amount, tax_status, income_bracket)
            tax_benefit = loss_amount * tax_rate
            
            # Find similar investments that could be used as a replacement
            similar_investments = []
            if inv.investment_type in investment_types:
                for similar in investment_types[inv.investment_type]:
                    # Don't include the same investment or other significant losers
                    if similar.id != inv.id and similar.profit_loss_percentage > -10:
                        similar_investments.append({
                            "id": similar.id,
                            "name": similar.name,
                            "symbol": similar.symbol,
                            "performance": similar.profit_loss_percentage
                        })
            
            # Add this opportunity if the tax benefit is significant (e.g., over $100)
            if tax_benefit > 100 and similar_investments:
                opportunities.append({
                    "investment": {
                        "id": inv.id,
                        "name": inv.name,
                        "symbol": inv.symbol,
                        "loss": loss_amount,
                        "loss_percentage": inv.profit_loss_percentage
                    },
                    "tax_benefit": tax_benefit,
                    "similar_investments": similar_investments[:3]  # Top 3 alternatives
                })
    
    # Sort opportunities by tax benefit
    opportunities.sort(key=lambda x: x["tax_benefit"], reverse=True)
    
    return opportunities
