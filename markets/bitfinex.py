#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
import traceback
if __name__ == '__main__':
  os.chdir(os.path.dirname(sys.argv[0]))

from decimal import Decimal
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from datetime import timedelta, date
import json
from pytz import timezone
import base64
import hmac
import hashlib
import time
import StringIO
import csv
import types
from market import *
from okcoin import OKCoin
from tlsadapter import *
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

  def interest_history(self, since_days, limit=1000):
    payload = {}
    payload["request"] = "/v1/history"
    payload["currency"] = "USD"
    d = datetime.datetime.now() + timedelta(days=since_days)
    payload["since"] = str(long((d - datetime.datetime(1970, 1, 1)).total_seconds()))
    payload["limit"] = limit
    payload["nonce"] = str(long(time.time() * 100000))
    payload["wallet"] = "deposit"
    headers = self._prepare_payload(True, payload)
    print payload
    return self._post("https://" + self.api + "/v1/history", headers=headers, verify=False)

  def cryptowatch(self, api):
    return self._get('https://api.cryptowat.ch/' + api)
  def yunbi(self, symbol):
    return self._get('https://plugin.sosobtc.com/widgetembed/data/depth?symbol=yunbi' + symbol)
  def poloniex(self, api):
    return self._get('https://poloniex.com/public?command=' + api)
    
  def _get(self, url, headers = None, verify = False):
    #s = requests.Session()
    #s.mount('https://', TlsAdapter())
    ret = requests.get(url, headers = headers, verify = verify, timeout = kTimeout)
    #print ret.text
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
  # fund on offer
  for offer in offers:
    print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'remaining_amount']), float(offer[u'rate']), offer[u'period'])

  asks = bitfinex.lendbook('usd')[u'asks']
  max_rate = 10000.0
  ask_sum = 0.0
  for ask in asks:
    # TODO: bypassing flash return rate, EXPERIMENTAL
    if ask[u'frr'] == u'Yes':
      continue
    for offer in offers:
      if offer[u'direction'] == u'lend':
        if ask[u'timestamp'] == offer[u'timestamp'] and ask[u'rate'] == offer[u'rate'] and ask[u'amount'] == offer[u'remaining_amount'] and ask[u'period'] == offer[u'period']:
          # bypass my own offers
          print '***** Ignoring the following orders ******'
          print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'remaining_amount']), float(offer[u'rate']), offer[u'period'])
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
  if target_rate < 1.0 or target_rate > 999.0:
    print 'unreasonable target_rate:', target_rate
    return
  # begin lending
  on_offer = 0.0
  for offer in offers:
    if float(offer[u'rate']) > target_rate:
      print '***** Canceling offer *****'
      print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'remaining_amount']), float(offer[u'rate']), offer[u'period'])
      print bitfinex.cancel_offer(offer[u'id'])
    else:
      on_offer += float(offer[u'remaining_amount'])
  print '***** Available funds ******'
  time.sleep(3)
  balances = bitfinex.balances()
  available_funds = 0
  for account in balances:
    if account[u'currency'] == u'usd' and account[u'type'] == u'deposit':
      available_funds = float(account[u'available'])
  print available_funds
  # Lend usd when balance is greater than kMinLendingFund
  kMinLendingFund = 100.0
  # max offer on order
  kMaxOnLendingOffer = 2500.0
  # Always keep kKeepFund usd in hand
  kKeepFund = 0.01

  #kKeepFund = 0.01
  if available_funds < kMinLendingFund:
    print "Available funds less than minimum lend amount: %.02f vs %.02f" %(available_funds, kMinLendingFund)
    return
  lend_funds = available_funds - kKeepFund
  if lend_funds < 0.01:
    print "Available funds less than reserved amount: %.02f vs %.02f" %(available_funds, kKeepFund)
    return
  if lend_funds + on_offer > kMaxOnLendingOffer:
    print "Testing lending %.02f" %lend_funds
    lend_funds = kMaxOnLendingOffer - on_offer
    if lend_funds < 0.01:
      print "No, I'd rather not lend"
      return
    print "Yes, I'd lend %.02f" %lend_funds
  days = 2
  if target_rate > 36.5:
    days = 7
  elif target_rate > 73:
    days = 30
  if target_rate < 8:
    print "Target rate too low. I'd rather not offer: %.02f%%" % target_rate
    return
  print '***** Lending out %f usd at yearly rate %f for %d days ******' %(lend_funds, target_rate, days)
  print bitfinex.new_offer(amount = lend_funds, rate = target_rate, period = days)
  print '***** Offers ******'
  time.sleep(3)
  offers = bitfinex.offers()
  for offer in offers:
    print "id: %d\ttime: %s\tamount:%.02f\trate: %.04f\tperiod: %d" %(offer[u'id'], offer[u'timestamp'], float(offer[u'remaining_amount']), float(offer[u'rate']), offer[u'period'])

def get_exchange_rate():
  url = 'http://download.finance.yahoo.com/d/quotes.csv?e=.csv&f=sl1d1t1&s=USDCNY=x'
  ret = requests.get(url, verify = False, timeout = 30)
  f = StringIO.StringIO(ret.text)
  reader = csv.reader(f, delimiter=',')
  for row in reader:
    return row[1]
  return "N/A"

def get_ticker(bitfinex, okc):
  ticker_bitfinex = bitfinex._ticker()
  bfxusd = bitfinex._ticker("bfxusd")
  bfxbtc = bitfinex._ticker("bfxbtc")
  rrtusd = bitfinex._ticker("rrtusd")
  rrtbtc = bitfinex._ticker("rrtbtc")
  ticker_okcoin = okc._ticker()
  print bfxusd
  print bfxbtc
  result = {
      'USD': ticker_bitfinex['last_price'],
      'CNY': ticker_okcoin['ticker']['last'],
      #'BFXUSD': bfxusd['last_price'],
      #'BFXBTC': bfxbtc['last_price'],
      'RRTUSD': rrtusd['last_price'],
      'RRTBTC': rrtbtc['last_price']
      }
  return result
  
def check_interest(bitfinex, html_file):
  result = bitfinex.interest_history(-30)
  parsed = []
  for item in result:
    if 'description' in item:
      if item['description'] == 'Margin Funding Payment on wallet Deposit':
        item['interest rate'] = round(36500 * float(item['amount']) / float(item['balance']), 2)
        parsed.append(item)
  #print parsed
  if len(parsed) <= 0: return
  #print json.dumps(parsed, indent=2)
  try:
    cryptowatch = bitfinex.cryptowatch('markets/prices')['result']
    yunbi_zeccny = bitfinex.yunbi('zeccny')
    yunbi_btccny = bitfinex.yunbi('btccny')
    yunbi_ethcny = bitfinex.yunbi('ethcny')
    yunbi_sccny = bitfinex.yunbi('sccny')
    poloniex = bitfinex.poloniex('returnTicker')
  except:
    pass
  exchange_rate_str = get_exchange_rate()
  ex_rate = float(exchange_rate_str)
  tickers = get_ticker(bitfinex, OKCoin('', ''))
  btc_rate = float(tickers['CNY'])/float(tickers['USD'])
  intermediate_file = html_file + ".tmp"
  f = open(intermediate_file, 'w')
  f.write("""<html><head>
      <title>Bitfinex Funding Fund for NM</title>
      <link rel="apple-touch-icon" href="/nemo.ico" />
      <meta charset="UTF-8">
      <style>
      tbody tr:nth-child(even)  td { background-color: #eee; }
      @media screen and (max-width: 1024px) {
        table {
          width: 96%;
          margin: 2%; 
          overflow-x: auto;
          display: block;
        }   
      }   
      </style>
      </head><body>""")
  tz = timezone("Asia/Shanghai")
  f.write("Last update: " + datetime.datetime.now(tz).strftime("%Y/%m/%d %H:%M:%S") + "<br />")
  f.write("USD vs CNY in fiat: " + exchange_rate_str + "<br />")
  f.write("USD vs CNY in btc: %.04f<br />" % btc_rate)
  f.write("Bitcoin price: $%.02f(¥%.02f) vs ¥%.02f($%.02f)<br />" % \
      (float(tickers['USD']), float(tickers['USD'])*ex_rate, \
      float(tickers['CNY']), float(tickers['CNY'])/ex_rate))
  f.write("Bitcoin delta: %.04f%%<br />" % ((btc_rate / ex_rate - 1)*100))
  try:
    zeccny = (float(yunbi_zeccny['asks'][-1][0]) + float(yunbi_zeccny['bids'][0][0])) / 2.0
    btccny = (float(yunbi_btccny['asks'][-1][0]) + float(yunbi_btccny['bids'][0][0])) / 2.0
    ethcny = (float(yunbi_ethcny['asks'][-1][0]) + float(yunbi_ethcny['bids'][0][0])) / 2.0
    sccny = (float(yunbi_sccny['asks'][-1][0]) + float(yunbi_sccny['bids'][0][0])) / 2.0
    f.write("Poloniex zec/btc %.06f, zec-btc-sc-cny-zec %.02f%%<br />" % (cryptowatch['poloniex:zecbtc'],
      float(poloniex['BTC_ZEC']['last']) / float(poloniex['BTC_SC']['last']) * sccny / zeccny * 100 - 100))
    f.write("Yunbi/Poloniex ZEC price: $%.02f(¥%.02f) vs ¥%.02f($%.02f)<br />" % (
      cryptowatch['poloniex:zecusd'], cryptowatch['poloniex:zecusd'] * ex_rate,
      zeccny, zeccny / ex_rate,
    ))
    f.write("Yunbi/Poloniex ETH price: $%.02f(¥%.02f) vs ¥%.02f($%.02f)<br />" % (
      cryptowatch['poloniex:ethusd'], cryptowatch['poloniex:ethusd'] * ex_rate,
      ethcny, ethcny / ex_rate,
    ))
    f.write("Yunbi/Poloniex BTC price: $%.02f(¥%.02f) vs ¥%.02f($%.02f)<br />" % (
      cryptowatch['poloniex:btcusd'], cryptowatch['poloniex:btcusd'] * ex_rate,
      btccny, btccny / ex_rate,
    ))
    f.write("Yunbi/Poloniex delta: btc %.02f%%, eth %.02f%%, zec %.02f%%<br />" % (
      100*(cryptowatch['poloniex:btcusd'] * ex_rate / btccny - 1),
      100*(cryptowatch['poloniex:ethusd'] * ex_rate / ethcny - 1),
      100*(cryptowatch['poloniex:zecusd'] * ex_rate / zeccny - 1)
    ))
  except:
    pass
  balances = bitfinex.balances()
  total_balance = 0
  bfx_balance = 0
  rrt_balance = 0
  for account in balances:
    print account
    if account[u'currency'] == u'usd' and account[u'type'] == u'deposit':
      total_balance = float(account[u'amount'])
    if account[u'currency'] == u'bfx':
      bfx_balance += float(account[u'amount'])
    if account[u'currency'] == u'rrt':
      rrt_balance += float(account[u'amount'])
  print "TOTAL", total_balance
  #print "TOTAL BFX", bfx_balance
  print "TOTAL RRT", rrt_balance
  portfolio_total = 0
  portfolio_weight = 0
  portfolio_average = 0
  credits = bitfinex.credits()
  for credit in credits:
    portfolio_weight += (float(credit[u'amount']) * float(credit[u'rate']))
    portfolio_total += float(credit[u'amount'])
  if portfolio_total > 0:
    portfolio_average = portfolio_weight / portfolio_total

  f.write("Current portfolio: $%.02f on %.04f%%<br />" % (portfolio_total, portfolio_average))
  #f.write("BFX price: $%.04f(¥%.04f), B%.06f($%.04f, ¥%.04f)<br />" % \
  #    (float(tickers['BFXUSD']), float(tickers['BFXUSD'])*ex_rate, \
  #    float(tickers['BFXBTC']), float(tickers['BFXBTC'])*float(tickers['USD']), \
  #    float(tickers['BFXBTC'])*float(tickers['CNY'])))
  #f.write("BFX balance: %.02f = $%.02f(¥%.02f)<br />" % \
  #    (bfx_balance, bfx_balance * float(tickers['BFXUSD']), bfx_balance * float(tickers['BFXUSD'])*ex_rate))
  f.write("RRT price: $%.04f(¥%.04f), B%.06f($%.04f, ¥%.04f)<br />" % \
      (float(tickers['RRTUSD']), float(tickers['RRTUSD'])*ex_rate, \
      float(tickers['RRTBTC']), float(tickers['RRTBTC'])*float(tickers['USD']), \
      float(tickers['RRTBTC'])*float(tickers['CNY'])))
  f.write("RRT balance: %.02f = $%.02f(¥%.02f)<br />" % \
      (rrt_balance, rrt_balance * float(tickers['RRTUSD']), rrt_balance * float(tickers['RRTUSD'])*ex_rate))
  #tbalance = total_balance + bfx_balance * float(tickers['BFXUSD']) + rrt_balance * float(tickers['RRTUSD'])
  tbalance = total_balance + rrt_balance * float(tickers['RRTUSD'])
  f.write("USD balance: $%.02f(¥%.02f)<br />" % \
      (total_balance, total_balance*ex_rate))
  f.write("Total balance: $%.02f(¥%.02f)<br />" % \
      (tbalance, tbalance*ex_rate))
  # in fact it's 100050
  # n_init = 100050
  # m_init = 108195.16
  # on 2016/3/23
  #nemo_init = 100027
  #nemo_percentage = 0.4804433389952496
  #nemo_init_date = datetime.datetime(2016, 3, 23, tzinfo = tz)
  #nemo_init = 40000
  #nemo_percentage = 0.445220928404126
  #nemo_init_date = datetime.datetime(2016, 6, 3, tzinfo = tz)

  # on 2016/6/24
  # m_init = 103359.91
  # nemo_init = 133013.43
  # nemo_percentage = 0.5627260248554258
  # nemo_init_date = datetime.datetime(2016, 6, 24, tzinfo = tz)

  # on 2016/7/26
  # m_init = 304563.72
  # nemo_init = 134974.26
  # nemo_last_percentage = 0.5627260248554258
  # nemo_percentage = 0.3070821320150764
  # nemo_init_date = datetime.datetime(2016, 7, 26, tzinfo = tz)

  # on 2016/8/13
  # m_init = 304563.72
  # nemo_init = 135197.36
  # nemo_last_percentage = 0.3070821320150764
  # nemo_percentage = 0.5397653755389125
  # nemo_init_date = datetime.datetime(2016, 8, 13, tzinfo = tz)

  # on 2016/9/27
  # m_init = 116516.25
  # nemo_init = 136650.81
  # nemo_last_percentage = 0.5397653755389125
  # nemo_percentage = 0
  # nemo_init_date = datetime.datetime(2016, 6, 24, tzinfo = tz)

  # on 2016/11/3
  # m_init = 115938.92
  # nemo_init = 137701.10
  # nemo_last_percentage = 0.5428997364168074
  # nemo_percentage = 0.5428997364059505
  # nemo_percentage = 0.5428997578102919
  # nemo_init_date = datetime.datetime(2016, 11, 4, tzinfo = tz)

  # on 2016/11/3
  # m_init = 118849.28928659
  # nemo_init = 138362.50
  # nemo_last_percentage = 0.5428997578102919
  # nemo_percentage = 0.5379321857048862
  # nemo_init_date = datetime.datetime(2016, 11, 17, tzinfo = tz)

  # on 2016/11/3
  # m_init = 118849.28928659
  # nemo_init = 138362.50
  # nemo_last_percentage = 0.5379321857048862
  # nemo_percentage = 0.5379321857048862
  # nemo_init_date = datetime.datetime(2016, 11, 17, tzinfo = tz)

  # on 2017/1/5
  # m_init = 252683.35
  # nemo_init = 142182.54
  # nemo_last_percentage = 0.5379321857048862
  # nemo_percentage = 0.3600780508035272
  # nemo_init_date = datetime.datetime(2017, 1, 5, tzinfo = tz)

  # on 2017/2/9
  # m_init = 164214.15
  #nemo_init = 145080.04
  # nemo_init = 174047.61
  # nemo_last_percentage = 0.3600780508035272
  # #nemo_percentage = 0.47117256430596005
  # nemo_percentage = 0.5145571423449429
  # nemo_init_date = datetime.datetime(2017, 2, 9, tzinfo = tz)

  # on 2017/3/30
  # m_init = 86865.28
  # nemo_init = 176872.99
  # nemo_last_percentage = 0.5145571423449429
  # nemo_percentage = 0.6706383188150888
  # nemo_init_date = datetime.datetime(2017, 3, 29, tzinfo = tz)

  # on 2017/5/14
  # m_init = 0
  nemo_init = 178022.63
  nemo_last_percentage = 0.6706383188150888
  nemo_percentage = 1.0
  nemo_init_date = datetime.datetime(2017, 5, 14, tzinfo = tz)

  nemo_days = (datetime.datetime.fromtimestamp(long(float(parsed[0]['timestamp'])), tz) - nemo_init_date).days + 1
  if nemo_days <= 1:
     nemo_days = 1
     nemo_last_usd = float(parsed[0]['amount']) * nemo_last_percentage
  else:
     nemo_last_usd = float(parsed[0]['amount']) * nemo_percentage
  nemo_now_usd = total_balance * nemo_percentage
  nemo_gain_usd = nemo_now_usd - nemo_init
  if nemo_gain_usd < 0: nemo_gain_usd = 0
  nemo_last_cny = nemo_last_usd * ex_rate
  nemo_now_cny = nemo_now_usd * ex_rate
  nemo_gain_cny = nemo_gain_usd * ex_rate
  nemo_ratio = nemo_gain_usd / nemo_init / nemo_days * 365 * 100
  nemo_last_ratio = nemo_last_usd / nemo_now_usd * 365 * 100

  # Nemo natural
  #f.write("N last profit: $%.02f(¥%.02f)<br />" % (nemo_last_usd, nemo_last_cny))
  #f.write("N total profit: $%.02f(¥%.02f)<br />" % (nemo_gain_usd, nemo_gain_cny))
  #f.write("N balance: $%.02f(¥%.02f)<br />" % (nemo_now_usd, nemo_now_cny))
  #f.write("N last ratio: %.02f%%<br />" % (nemo_last_ratio))
  #f.write("N total ratio: %.02f%%<br />" % (nemo_ratio))
  #f.write("N days since the beginning: %d<br />" % (nemo_days))
  # Nemo fixed
  f.write("N last profit: $%.02f(¥%.02f)<br />" % (0, 0))
  f.write("N total profit: $%.02f(¥%.02f)<br />" % (1099.39, 1099.39*ex_rate))
  f.write("N balance: $%.02f(¥%.02f)<br />" % (177972.38, 177972.38*ex_rate))
  f.write("N last ratio: %.02f%%<br />" % (4.92))
  f.write("N total ratio: %.02f%%<br />" % (6.13))
  f.write("N days since the beginning: %d<br />" % (37))

  f.write("""<table border="1" cellpadding="0" cellspacing="0" style="font-size:20pt;min-width:900px; ">
           <tr><td>Rate</td><td>Amount($)</td><td>Amount(¥)</td><td>Balance($)</td><td>Balance(¥)</td><td>Date</td></tr>\n
        """)
  for item in parsed:
    f.write("<tr><td>%s%%</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n" % \
        ('{:,.2f}'.format(item['interest rate']), '${:,.2f}'.format(float(item['amount'])), \
        '¥{:,.2f}'.format(float(item['amount']) * ex_rate), \
        '${:,.2f}'.format(float(item['balance'])), \
        '¥{:,.2f}'.format(float(item['balance']) * ex_rate), \
        datetime.datetime.fromtimestamp(long(float(item['timestamp'])), tz).strftime("%Y/%m/%d %H:%M:%S")))
  f.write("</table></body></html>")
  f.close()
  os.rename(intermediate_file, html_file)

if __name__ == '__main__':
  # this is not a unit test, but a useful feature
  requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
  bitfinex = Bitfinex(bitfinex_key, bitfinex_secret)
  while True:
    print "***************** Bitfinex Begin ********************"
    try:
      auto_renew(bitfinex, 25000)
      check_interest(bitfinex, 'interest_log.html')
    except Exception as e:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print '--------ERROR BEGIN---------'
      print e
      print repr(traceback.format_exception(exc_type, exc_value,
			exc_traceback))
      print '--------ERROR END-----------'
      pass
    print "***************** Bitfinex End ********************"
    time.sleep(1)

  # bitfinex.update_status()
  # print bitfinex.unified_bids
  # print bitfinex.unified_asks
  # print bitfinex.best_bid
  # print bitfinex.best_ask
