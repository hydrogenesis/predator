#!/usr/bin/python
# -*- coding: utf-8 -*-

from decimal import Decimal
import requests
import json
import base64
import hmac
import hashlib
import time
import types
from market import *
import sys
sys.path.append('../..')
from secret import *

class Bitfinex(Market):
  def __init__(self, key, secret):
    Market.__init__(self, 'Bitfinex')
    self.api = 'api.bitfinex.com/'
    self.interval = 2
    self.fiat = kUSD
    self.trade_fee = 0.002
    self.transaction_fee = 0.0
    self.min_lots = 0.01  # minimum lots
    self.max_lag = 20 # maximum lag of market
    self.key = key
    self.secret = secret

  def update_book(self):
    Market.update_book(self)
    book = self._book(10, 10, "btcusd")
    self.bids.clear()
    self.asks.clear()
    for ask in book[u'asks']:
      price = float(ask[u'price'])
      if not price in self.asks:
        self.asks[price] = 0
      self.asks[price] += float(ask[u'amount'])
    for bid in book[u'bids']:
      price = float(bid[u'price'])
      if not price in self.bids:
        self.bids[price] = 0
      self.bids[price] += float(bid[u'amount'])

  def balances(self):
    payload = {}
    payload["request"] = "/v1/balances"
    payload["nonce"] = str(long(time.time() * 100000))
    headers = self._prepare_payload(True, payload)
    return self._get("https://" + self.api + "/v1/balances", headers=headers, verify=False)

  def lendbook(self, currency):
    return self._get("https://" + self.api + "/v1/lendbook/" + currency, verify=False)

  def offers(self):
    payload = {}
    payload["request"] = "/v1/offers"
    payload["nonce"] = str(long(time.time() * 100000))
    headers = self._prepare_payload(True, payload)
    return self._get("https://" + self.api + "/v1/offers", headers=headers, verify=False)

  def cancel_offer(self, offer_id):
    payload = {}
    payload["request"] = "/v1/offer/cancel"
    payload["nonce"] = str(long(time.time() * 100000))
    payload["offer_id"] = offer_id
    headers = self._prepare_payload(True, payload)
    return self._post("https://" + self.api + "/v1/offer/cancel", headers=headers, verify=False)

  def new_offer(self, amount, rate, period = 2, currency = 'USD', direction = 'lend'):
    payload = {}
    payload["request"] = "/v1/offer/new"
    payload["nonce"] = str(long(time.time() * 100000))
    payload["currency"] = currency
    payload["amount"] = '%.02f' %amount
    payload["rate"] = '%.04f' %rate
    payload["period"] = period
    payload["direction"] = direction
    headers = self._prepare_payload(True, payload)
    print payload
    return self._post("https://" + self.api + "/v1/offer/new", headers=headers, verify=False)

  def credits(self):
    payload = {}
    payload["request"] = "/v1/credits"
    payload["nonce"] = str(long(time.time() * 100000))
    headers = self._prepare_payload(True, payload)
    return self._get("https://" + self.api + "/v1/credits", headers=headers, verify=False)
    
  def _get(self, url, headers = None, verify = False):
    ret = requests.get(url, headers = headers, verify = verify, timeout = kTimeout)
    return ret.json()

  def _post(self, url, headers = None, verify = False):
    ret = requests.post(url, headers = headers, verify = verify, timeout = kTimeout)
    return ret.json()

  def _ticker(self, symbol="btcusd"):
    return self._get("https://" + self.api + "/v1/ticker/" + symbol, verify=False)

  def _book(self, bids=10, asks=10, symbol="btcusd"):
    payload = {}
    payload['limit_bids'] = bids
    payload['limit_asks'] = asks
    headers = self._prepare_payload(False, payload)
    return self._get("https://" + self.api + "/v1/book/" + symbol, headers=headers, verify=False)

  def _prepare_payload(self, should_sign, d):
    j = json.dumps(d)
    data = base64.standard_b64encode(j)

    if should_sign:
      h = hmac.new(self.secret, data, hashlib.sha384)
      signature = h.hexdigest()
      return {
          "X-BFX-APIKEY": self.key,
          "X-BFX-SIGNATURE": signature,
          "X-BFX-PAYLOAD": data,
      }
    else:
      return {
          "X-BFX-PAYLOAD": data,
      }

def auto_renew(bitfinex, max_ask = 50000):
  '''Automatically places the offer at a rate that is maximum
     below |max_ask| depth of USD'''
  print '***** Credits ******'
  credits = bitfinex.credits()
  for credit in credits:
    print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(credit[u'id'], credit[u'timestamp'], float(credit[u'amount']), float(credit[u'rate']), credit[u'period'])

  print '***** Offers ******'
  offers = bitfinex.offers()
  for offer in offers:
    print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'amount']), float(offer[u'rate']), offer[u'period'])

  asks = bitfinex.lendbook('usd')[u'asks']
  max_rate = 10000.0
  ask_sum = 0.0
  for ask in asks:
    for offer in offers:
      if offer[u'direction'] == u'lend':
        if ask[u'timestamp'] == offer[u'timestamp'] and ask[u'rate'] == offer[u'rate'] and ask[u'amount'] == offer[u'remaining_amount'] and ask[u'period'] == offer[u'period']:
          # bypass my own offers
          print '***** Ignoring the following orders ******'
          print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'amount']), float(offer[u'rate']), offer[u'period'])
          continue
    max_rate = float(ask[u'rate'])
    if ask_sum > max_ask:
      break
    ask_sum += float(ask[u'amount'])
  target_rate = max_rate - 0.05
  print '***** Statistics ******'
  print 'Maximum lending rate:', max_rate
  print 'Total usd ask lower than max_rate:', ask_sum
  print 'Our target lending rate:', target_rate
  if target_rate < 10.0 or target_rate > 999.0:
    print 'unreasonable target_rate:', target_rate
    return
  # begin lending
  for offer in offers:
    if float(offer[u'rate']) > target_rate:
      print '***** Canceling offer *****'
      print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'amount']), float(offer[u'rate']), offer[u'period'])
      print bitfinex.cancel_offer(offer[u'id'])
  print '***** Available funds ******'
  time.sleep(3)
  balances = bitfinex.balances()
  available_funds = 0
  for account in balances:
    if account[u'type'] == u'deposit':
      available_funds = float(account[u'available'])
  print available_funds
  if available_funds < 100:
    print "Not enough funds"
    return
  lend_funds = available_funds - 0.01
  days = 2
  if target_rate > 36.5:
    days = 7
  elif target_rate > 73:
    days = 30
  print '***** Lending out %f usd at yearly rate %f for %d days ******' %(lend_funds, target_rate, days)
  print bitfinex.new_offer(amount = lend_funds, rate = target_rate, period = days)
  print '***** Offers ******'
  time.sleep(3)
  offers = bitfinex.offers()
  for offer in offers:
    print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'amount']), float(offer[u'rate']), offer[u'period'])

if __name__ == '__main__':
  # this is not a unit test, but a useful feature
  bitfinex = Bitfinex(bitfinex_key, bitfinex_secret)
  while True:
    print "***************** Bitfinex Begin ********************"
    auto_renew(bitfinex, 100000)
    print "***************** Bitfinex End ********************"
    time.sleep(60)

  # bitfinex.update_status()
  # print bitfinex.unified_bids
  # print bitfinex.unified_asks
  # print bitfinex.best_bid
  # print bitfinex.best_ask
