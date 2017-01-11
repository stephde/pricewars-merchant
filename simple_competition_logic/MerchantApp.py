import argparse
import sys

sys.path.append('../')
from merchant_sdk import MerchantBaseLogic, MerchantServer
from merchant_sdk.api import PricewarsRequester, MarketplaceApi, ProducerApi
from merchant_sdk.models import Offer

'''
    Template for Ruby deployment to insert defined tokens
'''
merchant_token = "{{API_TOKEN}}"
merchant_token = '28ycOMCcBxoDmbIQaOoaMB1tPiVKTBIVIH8gdKJnI824jJVKhJu4VuxueTF8eXcw'

settings = {
    'merchant_id': MerchantBaseLogic.calculate_id(merchant_token),
    'merchant_url': 'http://vm-mpws2016hp1-06.eaalab.hpi.uni-potsdam.de',
    'marketplace_url': 'http://vm-mpws2016hp1-04.eaalab.hpi.uni-potsdam.de:8080/marketplace',
    'producerEndpoint': 'http://vm-mpws2016hp1-03.eaalab.hpi.uni-potsdam.de',
    'priceDecrease': 1,
    'intervalMin': 1.0,
    'intervalMax': 1.0,
    'initialProducts': 3,
    'minPriceMargin': 16,
    'maxPriceMargin': 32,
    'shipping': 5,
    'primeShipping': 1,
    'debug': True,
    'tick': 100.0,
    'max_req_per_sec': 10
}


def get_from_list_by_key(dict_list, key, value):
    elements = [elem for elem in dict_list if elem[key] == value]
    if elements:
        return elements[0]
    return None


class MerchantSampleLogic(MerchantBaseLogic):
    def __init__(self):
        MerchantBaseLogic.__init__(self)
        global settings
        self.settings = settings

        '''
            Internal state handling
        '''
        self.execQueue = []

        '''
            Information store
        '''
        self.products = {}
        self.offers = {}

        '''
            Predefined API token
        '''
        self.merchant_id = settings['merchant_id']
        self.merchant_token = merchant_token

        '''
            Setup API
        '''
        PricewarsRequester.add_api_token(self.merchant_token)
        self.marketplace_api = MarketplaceApi(host=self.settings['marketplace_url'])
        self.producer_api = ProducerApi(host=self.settings['producerEndpoint'])

        '''
            Start Logic Loop
        '''
        self.run_logic_loop()

    def update_api_endpoints(self):
        """
        Updated settings may contain new endpoints, so they need to be set in the api client as well.
        However, changing the endpoint (after simulation start) may lead to an inconsistent state
        :return: None
        """
        self.marketplace_api.host = self.settings['marketplace_url']
        self.producer_api.host = self.settings['producerEndpoint']

    '''
        Implement Abstract methods / Interface
    '''

    def get_settings(self):
        return self.settings

    def update_settings(self, new_settings):
        def cast_to_expected_type(key, value, def_settings=self.settings):
            if key in def_settings:
                return type(def_settings[key])(value)
            else:
                return value

        new_settings_casted = dict([
            (key, cast_to_expected_type(key, new_settings[key]))
            for key in new_settings
        ])

        self.settings.update(new_settings_casted)
        self.update_api_endpoints()
        return self.settings

    def sold_offer(self, offer_json):
        offer_id = offer_json['offer_id']
        amount = offer_json['amount']
        price = offer_json['price']
        self.execQueue.append((self.sold_product, (offer_id, amount, price)))

    '''
        Merchant Logic
    '''

    def setup(self):
        try:
            for i in range(settings['initialProducts']):
                self.buy_product_and_update_offer()
        except Exception as e:
            print('error on setup:', e)

    def execute_logic(self):
        # execute queued methods
        tmp_queue = [e for e in self.execQueue]
        self.execQueue = []
        for method, kwargs in tmp_queue:
            method(*kwargs)

        offers = self.marketplace_api.get_offers()
        for product in self.products.values():
            competitor_offers = []
            for offer in offers:
                if offer.merchant_id != self.merchant_id and offer.uid == product.uid:
                    competitor_offers.append(offer.price)
            if len(competitor_offers) > 0:
                offer = self.offers[product.uid]
                self.adjust_prices(offer=offer, product=product, lowest_competitor_price=min(competitor_offers))

        # returns sleep value; higher tick is proportional to higher sleep value
        return settings['tick']/settings['max_req_per_sec']
        #return random.uniform(self.settings['intervalMin'],self.settings['intervalMax'])

    def adjust_prices(self, offer=None, product=None, lowest_competitor_price=0):
        if not offer or not product:
            return
        min_price = product.price + settings['minPriceMargin']
        max_price = product.price + settings['maxPriceMargin']
        price = lowest_competitor_price - settings['priceDecrease']
        price = min(price, max_price)
        if price < min_price:
            price = max_price
        offer.price = price
        self.marketplace_api.update_offer(offer)

    def sold_product(self, offer_id, amount, price):
        print('soldProduct', price)
        if offer_id in self.offers:
            offer = self.offers[offer_id]
            offer.amount -= amount
            product = self.products[offer.uid]
            product.amount -= amount
            if product.amount <= 0:
                print('product {:d} is out of stock!'.format(product.uid))
            self.buy_product_and_update_offer()

    def add_new_product_to_offers(self, new_product):
        new_offer = Offer.from_product(new_product)
        new_offer.price += settings['maxPriceMargin']
        new_offer.shipping_time = {
            'standard': settings['shipping'],
            'prime': settings['primeShipping']
        }
        new_offer.prime = True
        self.products[new_product.uid] = new_product
        new_offer.offer_id = self.marketplace_api.add_offer(new_offer).offer_id
        self.offers[new_product.uid] = new_offer

    def restock_existing_product(self, new_product):
        print('restock product', new_product)
        product = self.products[new_product.uid]
        product.amount += new_product.amount
        product.signature = new_product.signature

        offer = self.offers[product.uid]
        print('in this offer:', offer)
        offer.amount = product.amount
        offer.signature = product.signature
        self.marketplace_api.restock(offer.id, new_product.amount, offer.signature)

    def buy_product_and_update_offer(self):
        print('buy Product and update')
        new_product = self.producer_api.buy_product(merchant_token=self.merchant_token)

        if new_product.uid in self.products:
            self.restock_existing_product(new_product)
        else:
            self.add_new_product_to_offers(new_product)


merchant_logic = MerchantSampleLogic()
merchant_server = MerchantServer(merchant_logic)
app = merchant_server.app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PriceWars Merchant')
    parser.add_argument('--port', type=int,
                        help='port to bind flask App to')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
