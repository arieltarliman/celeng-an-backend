from typing import List, Dict

def calculate_split(items: List[Dict], participants: List[str], tax_percent: float, service_charge: float):
    """
    Core logic for TUGAS-04.
    items: List of item dicts with 'price' and 'assigned_to' (list of user_ids)
    """
    subtotal = sum(item['price'] for item in items)
    
    # Calculate Tax/Service absolute values
    tax_amount = subtotal * (tax_percent / 100)
    service_amount = subtotal * (service_charge / 100)
    
    user_totals = {user: 0 for user in participants}
    
    for item in items:
        # If an item is shared by 2 people, split price by 2
        split_count = len(item['assigned_to'])
        if split_count > 0:
            price_per_person = item['price'] / split_count
            for user in item['assigned_to']:
                user_totals[user] += price_per_person
    
    # Distribute Tax & Service proportionally
    final_totals = {}
    for user, amount in user_totals.items():
        user_ratio = amount / subtotal if subtotal > 0 else 0
        user_tax = tax_amount * user_ratio
        user_service = service_amount * user_ratio
        
        final_totals[user] = round(amount + user_tax + user_service)
        
    return final_totals