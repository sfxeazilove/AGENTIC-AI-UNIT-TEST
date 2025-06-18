def calculate_discount(price: float, discount_percent: int) -> tuple:
    '''Calculate discount amount and final price
    
    Args:
        price: Original price of the item
        discount_percent: Percentage discount to apply (0-100)
        
    Returns:
        tuple: (final_price, discount_amount)
        
    Raises:
        ValueError: If price is negative or discount is out of range
    '''
    if price < 0:
        raise ValueError("Price cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount percent must be between 0 and 100")
    
    discount_amount = price * (discount_percent / 100)
    final_price = price - discount_amount
    return final_price, discount_amount


def apply_bulk_discount(total_amount: float, item_count: int = 1) -> float:
    '''Apply bulk discount based on item count'''
    if item_count >= 10:
        return total_amount * 0.9  # 10% discount
    elif item_count >= 5:
        return total_amount * 0.95  # 5% discount
    return total_amount


class ShoppingCart:
    '''Shopping cart to manage items and calculate totals'''
    
    def __init__(self):
        self.items = []
        self.tax_rate = 0.08
    
    def add_item(self, item: str, price: float, quantity: int = 1):
        '''Add an item to the cart'''
        if price < 0:
            raise ValueError("Price cannot be negative")
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")
            
        self.items.append({
            'item': item,
            'price': price,
            'quantity': quantity
        })
    
    def remove_item(self, item: str) -> bool:
        '''Remove an item from the cart'''
        for i, cart_item in enumerate(self.items):
            if cart_item['item'] == item:
                self.items.pop(i)
                return True
        return False
    
    def get_subtotal(self) -> float:
        '''Calculate subtotal before tax'''
        return sum(item['price'] * item['quantity'] for item in self.items)
    
    def get_tax_amount(self) -> float:
        '''Calculate tax amount'''
        return self.get_subtotal() * self.tax_rate
    
    def get_total(self) -> float:
        '''Calculate total including tax'''
        return self.get_subtotal() + self.get_tax_amount()
    
    def clear_cart(self):
        '''Empty the shopping cart'''
        self.items = []