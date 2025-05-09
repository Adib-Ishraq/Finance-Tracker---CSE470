from collections import defaultdict

# Dictionary of common expense patterns and their categories
CATEGORY_PATTERNS = {
    'groceries': ['grocery', 'supermarket', 'food', 'market', 'shop', 'aldi', 'lidl', 'kroger', 'publix', 'walmart', 'target', 'costco', 'safeway', 'whole foods', 'trader joe', 'albertsons'],
    'dining': ['restaurant', 'café', 'cafe', 'coffee', 'diner', 'pizza', 'burger', 'starbucks', 'mcdonald', 'dining', 'doordash', 'ubereats', 'grubhub'],
    'transportation': ['uber', 'lyft', 'taxi', 'cab', 'bus', 'train', 'subway', 'metro', 'transport', 'gas', 'fuel', 'gasoline', 'parking', 'toll'],
    'utilities': ['electricity', 'water', 'gas', 'internet', 'cable', 'phone', 'mobile', 'utility', 'bill', 'netflix', 'spotify', 'hulu', 'disney+'],
    'housing': ['rent', 'mortgage', 'apartment', 'house', 'home', 'condo', 'lease', 'property'],
    'healthcare': ['doctor', 'hospital', 'clinic', 'medical', 'dental', 'pharmacy', 'medicine', 'health', 'insurance', 'prescription'],
    'entertainment': ['movie', 'theater', 'cinema', 'concert', 'show', 'ticket', 'event', 'festival', 'game', 'subscription', 'spotify', 'netflix'],
    'shopping': ['amazon', 'ebay', 'online', 'store', 'mall', 'retail', 'clothing', 'fashion', 'electronics'],
    'education': ['school', 'college', 'university', 'tuition', 'book', 'course', 'class', 'education', 'student', 'loan'],
    'personal': ['haircut', 'salon', 'spa', 'gym', 'fitness', 'personal', 'hygiene'],
    'travel': ['hotel', 'flight', 'airline', 'vacation', 'trip', 'booking', 'airbnb', 'travel', 'holiday']
}

# Income patterns
INCOME_PATTERNS = {
    'salary': ['salary', 'payroll', 'wage', 'income', 'pay', 'direct deposit', 'company name'],
    'investment': ['dividend', 'interest', 'capital gain', 'investment', 'stock', 'bond', 'fund', 'yield'],
    'refund': ['refund', 'rebate', 'cashback', 'return'],
    'gift': ['gift', 'present', 'donation'],
    'other income': []  # Fallback category
}

def get_category_confidence(transaction_description, patterns):
    """
    Calculate confidence scores for different categories based on transaction description.
    Returns the most likely category and confidence score (0-100).
    """
    scores = defaultdict(int)
    description_lower = transaction_description.lower()
    
    # Calculate match scores for each category
    for category, keywords in patterns.items():
        for keyword in keywords:
            if keyword.lower() in description_lower:
                # Add points for each keyword match
                scores[category] += 20  # Base points per match
                
                # Exact word matches get more points (vs substring matches)
                if any(keyword.lower() == word.lower() for word in description_lower.split()):
                    scores[category] += 10  # Extra points for exact word matches
    
    # Find the category with the highest score
    if scores:
        best_category = max(scores.items(), key=lambda x: x[1])
        category_name = best_category[0]
        confidence = min(100, best_category[1])  # Cap at 100%
        return category_name, confidence
    
    return None, 0

def suggest_category(description, transaction_type='Expense'):
    """
    Suggest a category based on the transaction description.
    Returns a tuple of (suggested_category, confidence_score)
    """
    if not description:
        return None, 0
        
    # Choose the right pattern dictionary based on transaction type
    patterns = INCOME_PATTERNS if transaction_type == 'Income' else CATEGORY_PATTERNS
    
    # Get category and confidence
    category, confidence = get_category_confidence(description, patterns)
    
    # If no match found, provide default category based on type
    if not category:
        category = 'Other Income' if transaction_type == 'Income' else 'Miscellaneous'
        confidence = 0
    
    return category, confidence

def get_similar_transactions(description, transactions, limit=3):
    """
    Find similar transactions by description to help with categorization
    """
    scores = []
    description_lower = description.lower()
    
    for transaction in transactions:
        if not hasattr(transaction, 'description') or not transaction.description:
            continue
            
        # Simple similarity score based on common words
        trans_desc_lower = transaction.description.lower()
        
        # Split into words and count common ones
        desc_words = set(description_lower.split())
        trans_words = set(trans_desc_lower.split())
        common_words = desc_words.intersection(trans_words)
        
        if common_words:
            # Calculate Jaccard similarity (intersection over union)
            similarity = len(common_words) / len(desc_words.union(trans_words))
            scores.append((transaction, similarity))
    
    # Sort by similarity score and return top matches
    scores.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in scores[:limit]]
