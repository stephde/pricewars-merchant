import sys

sys.path.insert(0, '/var/www/pricewars-merchant/current/')
sys.path.insert(0, '/var/www/pricewars-merchant/current/simple_competition_logic/')

sys.path.insert(0, here)
sys.path.insert(0, simple_competition_logic_path)

from MerchantApp import app as application
