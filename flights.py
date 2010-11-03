"""
Automatically search a variety of websites for the best flight deals.
"""

from selenium.firefox.webdriver import WebDriver
from selenium.firefox.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
import functools, ludibrio, re, time

wd = WebDriver()

def retry_if_nexist(f):
  @functools.wraps(f)
  def wrapper(x, retry = True):
    while 1:
      try: return f(x)
      except NoSuchElementException:
        if retry: time.sleep(1)
        else: return ludibrio.Dummy()
  return wrapper

@retry_if_nexist
def xpath(x): return rich_web_elt(wd.find_element_by_xpath(x))
@retry_if_nexist
def xpaths(x): return map(rich_web_elt, wd.find_elements_by_xpath(x))
@retry_if_nexist
def getid(x): return rich_web_elt(wd.find_element_by_id(x))
@retry_if_nexist
def name(x): return rich_web_elt(xpath('//*[@name=%r]' % (x,)))

pat = re.compile(r'\d+')
def toprc(x):
  return int(pat.search(x.get_text()
                        if type(x) is rich_web_elt or type(x) is WebElement
                        else x).group())

class rich_web_elt(object):
  def __init__(self, elt):
    self.elt = elt
  def clear(self):
    self.elt.clear()
    return self
  def click(self):
    self.elt.click()
    return self
  def send_keys(self, keys):
    self.elt.send_keys(keys)
    return self
  def delay(self, delay = 1):
    time.sleep(delay)
    return self
  def tab(self):
    self.elt.send_keys('\t')
    return self
  def enter(self):
    self.elt.send_keys('\n')
    return self
  def option(self, val):
    self.elt.find_element_by_xpath('//option[@value="%s"]' % val).set_selected()
    return self
  def __getattr__(self, attr):
    return getattr(self.elt, attr)

def united(org, dst):
  wd.get('http://united.com')
  getid('shop_from0_temp').send_keys(org).delay().tab()
  getid('shop_to0_temp').send_keys(dst).delay().tab()
  getid('fromnearby1').click()
  getid('tonearby1').click()
  getid('wayOne').click().delay()
  getid('shop_depart0').clear().send_keys('12/31/10')
  getid('SearchByPRICE').click()
  getid('sideform').submit()
  return toprc(xpath('//div[@class="cloudAmt"]'))

def aa(org, dst):
  wd.get('http://aa.com')
  getid('flightSearchForm.tripType.oneWay').click()
  getid('reservationFlightSearchForm.originAirport').clear().send_keys(org)
  getid('reservationFlightSearchForm.destinationAirport').clear().send_keys(dst)
  getid('flightSearchForm.originAlternateAirportDistance').option(60)
  getid('flightSearchForm.destinationAlternateAirportDistance').option(60)
  getid('reservationFlightSearchForm.flightParams.flightDateParams.travelMonth').option(12)
  getid('reservationFlightSearchForm.flightParams.flightDateParams.travelDay').option(31)
  getid('reservationFlightSearchForm.flightParams.flightDateParams.searchTime').option(120001)
  getid('reservationFlightSearchForm').submit()
  val = toprc(xpath('//span[@class="highlightSubHeader"]/a/span'))
  minday = min((toprc(prc), day.get_text())
               for prc, day in
               zip(xpaths('//li[@class="tabNotActive"]/a/span'),
                   xpaths('//li[@class="tabNotActive"]/a/u')))
  return val, minday

def virgin(org, dst):
  wd.get('http://virginamerica.com')
  getid('owRadio').click()
  xpath('//select[@name="flightSearch.origin"]/option[@value=%r]' % org.upper()).set_selected()
  xpath('//select[@name="flightSearch.destination"]/option[@value=%r]' % dst.upper()).set_selected()
  getid('bookFlightCollapseExpandBtn').click().delay()
  name ('flightSearch.depDate.MMDDYYYY').clear().send_keys('12/31/2010').delay()
  # this sometimes doesn't appear
  getid('idclose', False).click().delay()
  getid('SearchFlightBt').click()
  prcs = xpaths('//*[@class="fsCarouselCost"]')
  minday = min((toprc(prc), day.get_text())
               for prc, day in
               zip(prcs, xpaths('//*[@class="fsCarouselDate"]')))
  return toprc(prcs[3]), minday

def bing(org, dst):
  wd.get('http://bing.com/travel')
  getid('labelOW').click()
  getid('orig1Text').click().clear().send_keys(org).delay(5).tab()
  xpath('//span[@class="ac_portName"]/..', False).click().delay(1)
  getid('dest1Text').click().clear().send_keys(dst).delay(5).tab()
  xpath('//span[@class="ac_portName"]/..', False).click().delay(1)
  getid('no').click()
  getid('ne').click()
  getid('leave1').clear().send_keys('12/31/10').delay()
  getid('submitBtn').click()
  return toprc(xpath('//table[@class="resultsTable"]//span[@class="price"]'))

def farecmp():
  pass

def jetblue():
  pass

def main():
  defaultports = [('phl','sfo'),('ewr','sfo')]
  airline2orgdsts = dict(virgin = [('jfk','sfo')])
  for airline in 'aa united bing virgin'.split():
    for org, dst in airline2orgdsts.get(airline, defaultports):
      print org, dst, airline, globals()[airline](org, dst)
  wd.quit()

main()
