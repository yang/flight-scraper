"""
Drives a browser to search for tickets across multiple airline sites,
scraping/emailing/plotting fare information.
"""

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import cPickle as pickle, cStringIO as StringIO, argparse, contextlib, \
    datetime as dt, functools, getpass, logging, ludibrio, os, re, smtplib, socket, \
    subprocess, sys, time
from email.mime.text import MIMEText
import dateutil.relativedelta as rd
from parsedatetime import parsedatetime as pdt, parsedatetime_consts as pdc

date_parser = pdt.Calendar(pdc.Constants())

def month_of(date): return date + rd.relativedelta(day=1)
def fmt_date(date): return date.strftime('%m/%d/%Y')
def parse_date(text):
  return dt.date(*date_parser.parse(text.split(' ', 1)[1])[0][:3])

def retry_if_nexist(f):
  @functools.wraps(f)
  def wrapper(self, x, retry = True, maxsec = 60, dummy = True):
    start = time.time()
    while 1:
      try: return f(self, x)
      except NoSuchElementException:
        if not retry: return ludibrio.Dummy() if dummy else None
        if time.time() - start > maxsec: raise timeout_exception()
        time.sleep(1)
  return wrapper

class timeout_exception(Exception): pass

def retry_if_timeout(f):
  @functools.wraps(f)
  def wrapper(*args, **kw):
    while 1:
      try: return f(*args, **kw)
      except timeout_exception: time.sleep(1)
  return wrapper

class rich_driver(object):
  def __init__(self, wd): self.wd = wd
  def __getattr__(self, attr): return getattr(self.wd, attr)
  @retry_if_nexist
  def xpath(self, x): return rich_web_elt(self.wd.find_element_by_xpath(x))
  @retry_if_nexist
  def xpaths(self, x): return map(rich_web_elt, self.wd.find_elements_by_xpath(x))
  @retry_if_nexist
  def getid(self, x): return rich_web_elt(self.wd.find_element_by_id(x))
  @retry_if_nexist
  def name(self, x): return rich_web_elt(self.xpath('//*[@name=%r]' % (x,)))
  @retry_if_nexist
  def css(self, x): return rich_web_elt(self.wd.find_element_by_css_selector(x))
  @retry_if_nexist
  def csss(self, x): return map(rich_web_elt, self.wd.find_elements_by_css_selector(x))

price_re = re.compile(r'\d+')
def toprc(x):
  return int(price_re.search(x.text
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
    self.elt.send_keys(Keys.TAB)
    return self
  def enter(self):
    self.elt.send_keys(Keys.ENTER)
    return self
  def option(self, val):
    self.elt.find_element_by_xpath('//option[@value=%r]' % str(val)).click()
    return self
  def slow_keys(self, keys):
    for k in keys:
      self.send_keys(k)
      time.sleep(.1)
    return self
  def __getattr__(self, attr):
    return getattr(self.elt, attr)

def fullcity(tla):
  return dict(ewr = 'Newark',
      sfo = 'San Francisco',
      phl = 'Philadelphia',
      oak = 'Oakland',
      sjc = 'San Jose')[tla.lower()]

@retry_if_timeout
def united(wd, org, dst, date, nearby=False):
  """
  Returns list of (best price, day) pairs for month around date.
  """
  wd.get('http://united.com')
  wd.getid('ctl00_ContentInfo_Booking1_rdoSearchType2').click()
  wd.getid('ctl00_ContentInfo_Booking1_Origin_txtOrigin').clear().send_keys(org)
  wd.getid('ctl00_ContentInfo_Booking1_Destination_txtDestination').clear().send_keys(dst)
  if nearby:
    wd.getid('ctl00_ContentInfo_Booking1_Nearbyair_chkFltOpt').click()
  wd.getid('ctl00_ContentInfo_Booking1_AltDate_chkFltOpt').click()
  wd.getid('ctl00_ContentInfo_Booking1_DepDateTime_rdoDateFlex').click()
  wd.getid('ctl00_ContentInfo_Booking1_DepDateTime_MonthList1_cboMonth').option(fmt_date(month_of(date))).click()
  wd.getid('ctl00_ContentInfo_Booking1_btnSearchFlight').click()
  def gen():
    for x in wd.find_elements_by_css_selector('.on'):
      date, _, prc = x.text.split('\n')
      yield toprc(prc), parse_date(date)
  return list(gen())

@retry_if_timeout
def aa(wd, org, dst, date, dist_org=0, dist_dst=0):
  """
  dist_org and dist_dst are either 0, 30, 60, or 90 (miles).

  Returns list of (best price, day) pairs for +/- 3 days around date.
  """
  for dist in dist_org, dist_dst:
    if dist not in [None, 0, 30, 60, 90]:
      raise Exception('dist_org/dist_dst must be in [0,30,60,90]')
  wd.get('http://www.aa.com/reservation/oneWaySearchAccess.do')
  wd.getid('flightSearchForm.originAirport').clear().send_keys(org)
  wd.getid('flightSearchForm.destinationAirport').clear().send_keys(dst)
  wd.getid('flightSearchForm.originAlternateAirportDistance').option(dist_org)
  wd.getid('flightSearchForm.destinationAlternateAirportDistance').option(dist_dst)
  wd.getid('flightSearchForm.searchType.matrix').click()
  wd.getid('flightSearchForm.flightParams.flightDateParams.travelMonth').option(date.month)
  wd.getid('flightSearchForm.flightParams.flightDateParams.travelDay').option(date.day)
  wd.getid('flightSearchForm.flightParams.flightDateParams.searchTime').option(120001)
  wd.getid('flightSearchForm.carrierAll').click()
  wd.getid('flightSearchForm').submit()
  def gen():
    for x in wd.csss('.tabNotActive, .highlightSubHeader'):
      date, prc = x.text.split('from')
      yield toprc(prc), parse_date(date)
  return list(gen())

@retry_if_timeout
def virginamerica(wd, org, dst, date):
  """
  Note that this airline has very limited airport options.

  Returns list of (best price, day) pairs for +/- 3 days around date.
  """
  wd.get('http://virginamerica.com')
  wd.getid('owRadio').click()
  wd.xpath('//select[@name="flightSearch.origin"]/option[@value=%r]' % org.upper()).click()
  wd.xpath('//select[@name="flightSearch.destination"]/option[@value=%r]' % dst.upper()).click()
  wd.name('flightSearch.depDate.MMDDYYYY').clear().send_keys(fmt_date(date)).tab().delay()
  wd.getid('SearchFlightBt').click()
  return [(toprc(prc), parse_date(day.text))
      for prc, day in zip(wd.xpaths('//*[@class="fsCarouselCost"]'),
                          wd.xpaths('//*[@class="fsCarouselDate"]'))]

@retry_if_timeout
def bing(wd, org, dst, date, near_org=False, near_dst=False):
  """
  Returns best price for given date.
  """
  wd.get('http://bing.com/travel')
  wd.getid('oneWayLabel').click()
  wd.getid('orig1Text').click().clear().send_keys(org).tab()
  wd.getid('dest1Text').click().clear().send_keys(dst).tab()
  if near_org: wd.getid('no1').click()
  if near_dst: wd.getid('ne1').click()
  wd.getid('leave1').clear().send_keys(fmt_date(date))
  wd.getid('PRI-HP').click()
  wd.find_element_by_css_selector('.sbmtBtn').click()
  # Wait for "still searching" to disappear.
  while wd.getid('searching').is_displayed(): time.sleep(1)
  return toprc(wd.xpath('//span[@class="price"]'))

@retry_if_timeout
def southwest(wd, org, dst, date):
  """
  Returns list of (best price, date) pairs for month around date.
  """
  wd.get('http://www.southwest.com/cgi-bin/lowFareFinderEntry')
  wd.getid('oneWay').click()
  wd.getid('originAirport_displayed').clear().send_keys(org).tab()
  wd.getid('destinationAirport_displayed').clear().send_keys(dst).tab()
  wd.getid('outboundDate').option(fmt_date(month_of(date)))
  wd.getid('submitButton').click()
  month = wd.css('.carouselTodaySodaIneligible .carouselBody').text
  def gen():
    for x in wd.csss('.fareAvailableDay'):
      day, prc = x.text.split('\n')
      yield toprc(prc), parse_date('%s %s' % (month, day))
  return list(gen())

@retry_if_timeout
def delta(wd, org, dst, date, nearby=False):
  """
  Returns best price for given date.
  """
  wd.get('http://www.delta.com/booking/searchFlights.do')
  wd.getid('oneway_link').click()
  wd.getid('departureCity_0').clear().send_keys(org)
  wd.getid('destinationCity_0').clear().send_keys(dst)
  if nearby: wd.getid('flexAirports').click()
  wd.getid('departureDate_0').clear().send_keys(fmt_date(date))
  wd.getid('Go').click()
  return toprc(wd.css('.lowest .fares').text)

@retry_if_timeout
def farecmp():
  pass

@retry_if_timeout
def jetblue():
  pass

@contextlib.contextmanager
def quitting(x):
  try: yield x
  finally: x.quit()

@contextlib.contextmanager
def subproc(*args, **kwargs):
  p = subprocess.Popen(*args, **kwargs)
  try: yield p
  finally: p.terminate(); p.wait()

def scrshot(name):
  tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
  fname = '%s %s.png' % (tstamp, name)
  wd.save_screenshot(fname)

def scrape(wd, cfg):
  out = StringIO.StringIO()
  logging.basicConfig()
  newres = {}

  orgs = cfg.origin.split()
  dsts = cfg.destination.split()
  date = dt.date(2012,12,22)
  defaultports = [(org, dst) for org in orgs for dst in dsts]
  airline2orgdsts = dict(virginamerica = [('jfk','sfo')])
  airlines = cfg.websites
  query_date = date

  for airline in airlines:
    for org, dst in airline2orgdsts.get(airline, defaultports):
      res = globals()[airline](wd, org, dst, query_date)
      if not type(res) is list: res = [(date, res)]
      for price, date in res:
        msg = '%s to %s on %s.com: %s $%s ' % (org, dst, airline, date, price)
        print msg
        print >> out, msg
      if cfg.screenshots:
        scrshot('%s to %s on %s.com' % (org, dst, airline))

  return out

def main(argv = sys.argv):
  default_from = '%s@%s' % (getpass.getuser(), socket.getfqdn())

  p = argparse.ArgumentParser(description=__doc__)
  p.add_argument('-d', '--debug', action='store_true',
      help='Run browser directly, without Xvfb.')
  p.add_argument('-T', '--mailto',
      help='''Email addresses where results should be sent. Without this, just
      print results to stdout.''')
  p.add_argument('-F', '--mailfrom', default=default_from,
      help='Email address results are sent from. (default: %s)' % default_from)
  p.add_argument('-s', '--screenshots',
      help='Take screenshots of every final page.')
  p.add_argument('-f', '--origin',
      help='Space-separated origin airports.')
  p.add_argument('-t', '--destination',
      help='Space-separated destination airports.')
  p.add_argument('websites', nargs='+',
      help='''Websites to scrape (aa/united/bing/virginamerica). You can also
      override the airports searched on particular websites with parenthesized
      space-separated origin-destination pairs, e.g. 'virginamerica(jfk-sfo
      jfk-las)'.''')
  cfg = p.parse_args(argv[1:])

  cmd = 'sleep 99999999' if cfg.debug else 'Xvfb :10 -screen 0 1600x1200x24'
  with subproc(cmd.split()) as xvfb:
    if not cfg.debug: os.environ['DISPLAY'] = ':10'
    # This silencing isn't working
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout = open('/dev/null','w')
    sys.stderr = open('/dev/null','w')
    with quitting(rich_driver(webdriver.Chrome())) as wd:
      sys.stdout, sys.stderr = stdout, stderr
      out = scrape(wd, cfg)

  # TODO: aggregate stats

  #with open(os.path.expanduser('~/.flights.pickle')) as f:
  #  oldres = pickle.load(f)

  #for airline in airlines:
  #  (newval, newres), (oldval, oldres) = newres[airline], oldres[airline]
  #  if newval != oldval and newval <= 180:
  #    if val <= 180: found = True
  #    print >> out, org, dst, airline, res

  if not cfg.debug and cfg.mailto:
    mail = MIMEText(out.getvalue())
    mail['From'] = cfg.mailfrom
    mail['To'] = cfg.mailto
    mail['Subject'] = 'Flight alert for %s' % \
        (dt.datetime.now().strftime('%a %Y-%m-%d %I:%M %p'),)
    with contextlib.closing(smtplib.SMTP('localhost')) as smtp:
      smtp.sendmail(mail['From'], mail['To'].split(','), mail.as_string())

  #with open(os.path.expanduser('~/.flights.pickle'), 'w') as f:
  #  pickle.dump(newres, f)
