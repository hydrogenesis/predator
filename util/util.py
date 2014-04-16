import urllib2
import simplejson
import threading, time, sys
sys.path.append('..')
from common.common import *

kUSDCNYUrl = 'http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20yahoo.finance.xchange%20where%20pair%20in%20(%22USDCNY%22)&format=json&env=store://datatables.org/alltableswithkeys&callback='

class Env(object):
  fiat_rate = {kUSD: 6.21, kCNY: 1}

class EnvWorker(threading.Thread):
  def __init__(self, env):
    threading.Thread.__init__(self)
    self.env = env

  def run(self):
    while True:
      latest_value = self.GetTicker()
      if latest_value != -1:
        self.env.fiat_rate[kUSD] = latest_value
      time.sleep(5)
      
  def GetTicker(self):
    try:
      response = urllib2.urlopen(kUSDCNYUrl, timeout = kTimeout)
      result = simplejson.load(response)
      return float(result['query']['results']['rate']['Rate'])
    except:
      return -1

env = Env()
