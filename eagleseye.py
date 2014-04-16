import os, sys, time, threading, datetime
sys.path.append('.')
sys.path.append('..')
from markets.okcoin import *
from markets.bitfinex import *
from util.util import *
from common.common import *
from secret import *

class MarketWatcher(threading.Thread):
  def __init__(self, market):
    threading.Thread.__init__(self)
    self.market = market

  def run(self):
    while True:
      try:
        self.market.update_status()
      except Exception as e:
        print e
        print "Market update failed"
      # print 'Market %s updated' %self.market.name
      time.sleep(self.market.interval)

class EaglesEye(threading.Thread):
  def __init__(self):
    self.markets = {}
    self.markets['okcoin'] = OKCoin()
    self.markets['bitfinex'] = Bitfinex()
    self.market_watchers = {}
    # world best bid and offer
    self.WBBO = {kCNY: {'ask': -1, 'iask': -1, 'bid': -1, 'ibid': -1, 'ask_market': None, 'bid_market': None}, kUSD: {'ask': -1, 'iask': -1, 'bid': -1, 'ibid': -1, 'ask_market': None, 'bid_market': None}}

    for key in self.markets:
      self.market_watchers[key] = MarketWatcher(self.markets[key])
      self.market_watchers[key].setDaemon(True)
      self.market_watchers[key].start()

    self.env_worker = EnvWorker(env)
    self.env_worker.setDaemon(True)
    self.env_worker.start()
    
  def timestamp(self):
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

  def update_WBBO(self, fiat):
    best_bid = -1
    best_ask = 1e9
    has_best_bid = False
    has_best_ask = False
    best_bid_market = None
    best_ask_market = None
    for key in self.markets:
      market = self.markets[key]
      if market.fiat != fiat or (not market.success) or market.lagged():
        continue
      bid = market.best_bid
      ask = market.best_ask
      if bid > best_bid:
        best_bid = bid
        best_bid_market = market
        has_best_bid = True
      if ask < best_ask:
        best_ask = ask
        best_ask_market = market
        has_best_ask = True
    if has_best_bid and has_best_ask:
      self.WBBO[fiat]['ask'] = best_ask
      self.WBBO[fiat]['bid'] = best_bid
      self.WBBO[fiat]['iask'] = best_ask * env.fiat_rate[best_ask_market.fiat] / (1 - best_ask_market.trade_fee) / (1 - best_ask_market.transaction_fee)
      self.WBBO[fiat]['ibid'] = best_bid * env.fiat_rate[best_bid_market.fiat] * (1 - best_bid_market.trade_fee) * (1 - best_bid_market.transaction_fee)
      self.WBBO[fiat]['ask_market'] = best_ask_market
      self.WBBO[fiat]['bid_market'] = best_bid_market
      return True
    else:
      self.WBBO[fiat]['ask'] = -1
      self.WBBO[fiat]['bid'] = -1
      self.WBBO[fiat]['iask'] = -1
      self.WBBO[fiat]['ibid'] = -1
      self.WBBO[fiat]['ask_market'] = None
      self.WBBO[fiat]['bid_market'] = None
      return False

  def calc_profit(self, fiat1, fiat2):
    if fiat1 == fiat2: return -1
    profit = (self.WBBO[fiat2]['ibid'] - self.WBBO[fiat1]['iask']) / self.WBBO[fiat1]['iask']
    print "[%s] Arbitrage: %s => %s, %.02f => %.02f, profit: %.02f%%" %(self.timestamp(), self.WBBO[fiat1]['ask_market'].name, self.WBBO[fiat2]['bid_market'].name, self.WBBO[fiat1]['iask'], self.WBBO[fiat2]['ibid'], profit * 100)
    return profit

  def watch(self):
    f = open('data.txt', 'w')
    while True:
      if not self.update_WBBO(kCNY) or not self.update_WBBO(kUSD): 
        time.sleep(1)
        continue
 
      profit_cny2usd = self.calc_profit(kCNY, kUSD)
      profit_usd2cny = self.calc_profit(kUSD, kCNY)
      f.write("%f\t%f\t%f\t%f\t%f\t%f\t%f\n" %(time.time(),
                                       self.WBBO[kCNY]['iask'],
                                       self.WBBO[kUSD]['ibid'],
                                       profit_cny2usd,
                                       self.WBBO[kUSD]['iask'],
                                       self.WBBO[kCNY]['ibid'],
                                       profit_usd2cny))
      f.flush()

      if False:
        profit = (best_bid - best_ask) / best_ask
        if ask_market.can_buy(0.01) and bid_market.can_sell(0.01):
          ask_market.buy(0.01)
          bid_market.sell(0.01)

      portfolio = {kBTC: 0, kCNY: 0, kUSD: 0}
      for key in self.markets:
        for equity in portfolio:
          portfolio[equity] += self.markets[key].balance[equity]
      print "[%s] Portfolio: %.02f CNY, %.02f USD, %02f BTC" %(self.timestamp(), portfolio[kCNY], portfolio[kUSD], portfolio[kBTC])
      time.sleep(1)
    f.close()

if __name__ == '__main__':
  eagle = EaglesEye()
  eagle.watch()

