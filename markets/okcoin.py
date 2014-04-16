#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import urllib2
import hashlib
import simplejson
from market import *

class OKCoin(Market):
  def __init__(self):
    Market.__init__(self, 'OKCoin')
    self.api = 'www.okcoin.com/api/'
    self.interval = 2
    self.fiat = kCNY
    self.trade_fee = 0.0
    self.transaction_fee = 0.0
    self.min_lots = 0.01  # minimum lots
    self.max_lag = 20 # maximum lag of market

  def update_book(self):
    Market.update_book(self)
    book = self._book("btc_cny")
    self.bids.clear()
    self.asks.clear()
    for ask in book['asks']:
      price = float(ask[0])
      if not price in self.asks:
        self.asks[price] = 0
      self.asks[price] += float(ask[1])
    for bid in book['bids']:
      price = float(bid[0])
      if not price in self.bids:
        self.bids[price] = 0
      self.bids[price] += float(bid[1])

  def _get_json(self, url):
    response = urllib2.urlopen(url, timeout = kTimeout)
    data = simplejson.load(response)
    return(data)

  def _ticker(self, symbol="btc_cny"):
    r = self._get_json("http://" + self.api + "ticker.do?symbol=" + symbol)
    return r

  def _book(self, symbol="btcusd"):
    r = self._get_json("http://" + self.api + "depth.do?symbol=" + symbol)
    return r


if __name__ == '__main__':
  okcoin = OKCoin()
  okcoin.update_status()
  print okcoin.unified_bids
  print okcoin.unified_asks
  print okcoin.best_bid
  print okcoin.best_ask
