"""
Automatically search a variety of websites for the best flight deals.
"""

from selenium.firefox.webdriver import WebDriver
from selenium.firefox.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
import time, re

wd = WebDriver()

def xpath(x): return wd.find_element_by_xpath(x)
def xpaths(x): return wd.find_elements_by_xpath(x)
def getid(x): return wd.find_element_by_id(x)
def name(x): return xpath('//*[@name=%r]' % (x,))
def option(id, val):
  getid(id).find_element_by_xpath('//option[@value="%s"]' % val).set_selected()

pat = re.compile(r'\d+')
def toprc(x):
  return pat.search(x.get_text() if type(x) is WebElement else x).group()

def united(org, dst):
  wd.get('http://united.com')
  getid('shop_from0_temp').send_keys(org)
  getid('shop_to0_temp').send_keys(dst)
  getid('fromnearby1').click()
  getid('tonearby1').click()
  getid('wayOne').click()
  time.sleep(1)
  getid('shop_depart0').clear()
  getid('shop_depart0').send_keys('12/31/10')
  getid('SearchByPRICE').click()
  getid('sideform').submit()
  while 1:
    try: return toprc(xpath('//div[@class="cloudAmt"]'))
    except NoSuchElementException: time.sleep(1)

def aa(org, dst):
  wd.get('http://aa.com')
  while 1:
    try: getid('flightSearchForm.tripType.oneWay')
    except NoSuchElementException: time.sleep(1)
    else: break
  getid('flightSearchForm.tripType.oneWay').click()
  getid('reservationFlightSearchForm.originAirport').send_keys(org)
  getid('reservationFlightSearchForm.destinationAirport').send_keys(dst)
  option('flightSearchForm.originAlternateAirportDistance', 60)
  option('flightSearchForm.destinationAlternateAirportDistance', 60)
  option('reservationFlightSearchForm.flightParams.flightDateParams.travelMonth', 12)
  option('reservationFlightSearchForm.flightParams.flightDateParams.travelDay', 31)
  option('reservationFlightSearchForm.flightParams.flightDateParams.searchTime', 120001)
  getid('reservationFlightSearchForm').submit()
  while 1:
    try: val = toprc(xpath('//span[@class="highlightSubHeader"]/a/span'))
    except NoSuchElementException: time.sleep(1)
    else:
      minday = min((toprc(prc), day.get_text())
                   for day, prc in
                   zip(xpaths('//li[@class="tabNotActive"]/a/u'),
                       xpaths('//li[@class="tabNotActive"]/a/span')))
      return toprc(val), minday

def virgin(org, dst):
  wd.get('http://virginamerica.com')
  getid('owRadio').click()
  xpath('//select[@name="flightSearch.origin"]/option[@value=%r]' % org.upper()).set_selected()
  xpath('//select[@name="flightSearch.destination"]/option[@value=%r]' % dst.upper()).set_selected()
  getid('bookFlightCollapseExpandBtn').click()
  time.sleep(1)
  name ('flightSearch.depDate.MMDDYYYY').clear()
  name ('flightSearch.depDate.MMDDYYYY').send_keys('12/31/2010')
  time.sleep(1)
  try: getid('idclose').click()
  except NoSuchElementException: pass
  else: time.sleep(1)
  getid('SearchFlightBt').click()
  while 1:
    try: prcs = xpaths('//*[@class="fsCarouselCost"]')
    except NoSuchElementException: time.sleep(1)
    else:
      minday = min((toprc(prc), day.get_text())
                   for day, prc in
                   zip(xpaths('//*[@class="fsCarouselDate"]'), prcs))
      return toprc(prcs[3]), minday

def jetblue():
  pass

def bing(org, dst):
  wd.get('http://bing.com/travel')

  getid('labelOW').click()

  getid('orig1Text').send_keys(org)
  time.sleep(1)
  getid('orig1Text').send_keys('\n')

  getid('dest1Text').send_keys(dst)
  time.sleep(1)
  getid('orig1Text').send_keys('\n')

  getid('no').click()
  getid('ne').click()
  getid('leave1').clear()
  getid('leave1').send_keys('12/31/10')
  time.sleep(1)
  getid('submitBtn').click()
  while 1:
    # DEBUG map(toprc, xpaths('//table[@class="resultsTable"]//span[@class="price"]'))
    try: return toprc(xpath('//table[@class="resultsTable"]//span[@class="price"]'))
    except NoSuchElementException: time.sleep(1)

def farecmp():
  pass

def main():
  for org, dst in [('phl','sfo'),('ewr','sfo')]:
    print 'united %r' % (united(org, dst),)
    print 'aa %r' % (aa(org, dst),)
    print 'bing %r' % (bing(org, dst),)
  print 'virgin %r' % (virgin('jfk', 'sfo'),)

main()
