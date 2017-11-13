from typing import Union
from typing import Optional

from merchant_sdk.models.PricewarsObject import PricewarsObject
from merchant_sdk.models import Product


class Order(PricewarsObject):
    def __init__(self, price: float, stock: int, product: Union[Product, dict], left_in_stock: Optional[int] = None):
        self.price = price
        self.stock = stock
        self.left_in_stock = left_in_stock
        if type(product) == dict:
            self.product = Product.from_dict(product)
        else:
            self.product = product
