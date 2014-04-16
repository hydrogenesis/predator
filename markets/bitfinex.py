#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import json
import base64
import hmac
import hashlib
import time
import types
from market import *

class Bitfinex(Market):
  def __init__(self):
    Market.__init__(self, 'Bitfinex')
    self.api = 'api.bitfinex.com/'
    self.interval = 2
    self.fiat = kUSD
    self.trade_fee = 0.002
    self.transaction_fee = 0.0
    self.min_lots = 0.01  # minimum lots
    self.max_lag = 20 # maximum lag of market

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

  def _get(self, url, headers = None, verify = False):
    return requests.get(url, headers = headers, verify = verify, timeout = kTimeout).json()

  def _ticker(self, symbol="btcusd"):
    return self._get("https://" + api + "/v1/ticker/" + symbol, verify=False)

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

if __name__ == '__main__':
  bitfinex = Bitfinex()
  bitfinex.update_status()
  print bitfinex.unified_bids
  print bitfinex.unified_asks
  print bitfinex.best_bid
  print bitfinex.best_ask
