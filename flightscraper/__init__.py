"""
Drives a browser to search for tickets across multiple airline sites,
scraping/emailing/plotting fare information.
"""

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import cPickle as pickle, cStringIO as StringIO, argparse, contextlib, \
    datetime, functools, getpass, logging, ludibrio, os, re, smtplib, socket, \
    subprocess, sys, time
from email.mime.text import MIMEText

near_org, near_dst = False, False

def retry_if_nexist(f):
  @functools.wraps(f)
  def wrapper(x, retry = True, maxsec = 60, dummy = True):
    start = time.time()
    while 1:
      try: return f(x)
      except NoSuchElementException:
        if not retry: return ludibrio.Dummy() if dummy else None
        if time.time() - start > maxsec: raise timeout_exception()
        time.sleep(1)
  return wrapper

class timeout_exception(Exception): pass

def retry_if_timeout(f):
  @functools.wraps(f)
  def wrapper(org, dst):
    while 1:
      try: return f(org, dst)
      except timeout_exception: time.sleep(1)
  return wrapper

@retry_if_nexist
def xpath(x): return rich_web_elt(wd.find_element_by_xpath(x))
@retry_if_nexist
def xpaths(x): return map(rich_web_elt, wd.find_elements_by_xpath(x))
@retry_if_nexist
def getid(x): return rich_web_elt(wd.find_element_by_id(x))
@retry_if_nexist
def name(x): return rich_web_elt(xpath('//*[@name=%r]' % (x,)))

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
def united(org, dst, nearby=False):
  wd.get('http://united.com')
  getid('ctl00_ContentInfo_Booking1_rdoSearchType2').click()
  getid('ctl00_ContentInfo_Booking1_Origin_txtOrigin').clear().send_keys(org)
  getid('ctl00_ContentInfo_Booking1_Destination_txtDestination').clear().send_keys(dst)
  if nearby:
    getid('ctl00_ContentInfo_Booking1_Nearbyair_chkFltOpt').click()
  getid('ctl00_ContentInfo_Booking1_AltDate_chkFltOpt').click()
  getid('ctl00_ContentInfo_Booking1_DepDateTime_rdoDateFlex').click()
  getid('ctl00_ContentInfo_Booking1_DepDateTime_MonthList1_cboMonth').option('12/1/2012').click()
  getid('ctl00_ContentInfo_Booking1_btnSearchFlight').click()
  def gen():
    for x in wd.find_elements_by_css_selector('.on'):
      date, _, prc = x.text.split('\n')
      yield toprc(prc), date
  # TODO not the price for the requested target date
  return toprc(min(b for a,b in gen())), min(gen())

# +/-3d
@retry_if_timeout
def aa(org, dst):
  wd.get('http://www.aa.com/reservation/oneWaySearchAccess.do')
  getid('flightSearchForm.originAirport').clear().send_keys(org)
  getid('flightSearchForm.destinationAirport').clear().send_keys(dst)
  if near_org:
    getid('flightSearchForm.originAlternateAirportDistance').option(60)
  if near_dst:
    getid('flightSearchForm.destinationAlternateAirportDistance').option(60)
  getid('flightSearchForm.searchType.matrix').click()
  getid('flightSearchForm.flightParams.flightDateParams.travelMonth').option(12)
  getid('flightSearchForm.flightParams.flightDateParams.travelDay').option(31)
  getid('flightSearchForm.flightParams.flightDateParams.searchTime').option(120001)
  getid('flightSearchForm.carrierAll').click()
  getid('flightSearchForm').submit()
  val = toprc(xpath('//span[@class="highlightSubHeader"]/a/span'))
  minday = min((toprc(prc), day.text)
               for prc, day in
               zip(xpaths('//li[@class="tabNotActive"]/a/span'),
                   xpaths('//li[@class="tabNotActive"]/a/u')))
  return val, minday

# +/-3d
@retry_if_timeout
def virginamerica(org, dst):
  wd.get('http://virginamerica.com')
  getid('owRadio').click()
  xpath('//select[@name="flightSearch.origin"]/option[@value=%r]' % org.upper()).click()
  xpath('//select[@name="flightSearch.destination"]/option[@value=%r]' % dst.upper()).click()
  name ('flightSearch.depDate.MMDDYYYY').clear().send_keys('12/21/2012').tab().delay()
  getid('SearchFlightBt').click()
  prcs = xpaths('//*[@class="fsCarouselCost"]')
  minday = min((toprc(prc), day.text)
               for prc, day in
               zip(prcs, xpaths('//*[@class="fsCarouselDate"]')))
  return toprc(prcs[3]), minday

@retry_if_timeout
def bing(org, dst):
  wd.get('http://bing.com/travel')
  getid('labelOW').click()
  getid('orig1Text').click().clear().send_keys(org).delay(5).tab()
  xpath('//span[@class="ac_portName"]/..', False).click().delay(1)
  getid('dest1Text').click().clear().send_keys(dst).delay(5).tab()
  xpath('//span[@class="ac_portName"]/..', False).click().delay(1)
  if near_org: getid('no').click()
  if near_dst: getid('ne').click()
  getid('leave1').clear().send_keys('12/31/10').delay()
  getid('submitBtn').click()
  # Wait for "still searching" to disappear.
  while getid('stillSearching', False).get_attribute('style') != 'display: none;':
    time.sleep(1)
  return toprc(xpath('//table[@class="resultsTable"]//span[@class="price"]'))

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
  if cfg.screenshots:
    tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    fname = '%s %s.png' % (tstamp, name)
    wd.save_screenshot(fname)

def scrape():
  out = StringIO.StringIO()
  logging.basicConfig()
  newres = {}

  orgs = 'ewr phl'.split()
  dsts = 'oak sfo sjc'.split()
  defaultports = [(org, dst) for org in orgs for dst in dsts]
  airline2orgdsts = dict(virginamerica = [('jfk','sfo')])
  airlines = 'aa united bing virginamerica'.split()

  for airline in airlines:
    for org, dst in airline2orgdsts.get(airline, defaultports):
      res = globals()[airline](org, dst)
      val = res[0] if type(res) is tuple else res
      newres[airline] = val, res
      msg = '%s to %s on %s.com: %s' % (org, dst, airline, res)
      print msg
      print >> out, msg
      scrshot('%s to %s on %s.com - %s' % (org, dst, airline, val))

  return out

def main(argv = sys.argv):
  global wd, cfg

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
  p.add_argument('websites',
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
    with quitting(webdriver.Chrome()) as wd:
      sys.stdout, sys.stderr = stdout, stderr
      out = scrape()

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
        (datetime.datetime.now().strftime('%a %Y-%m-%d %I:%M %p'),)
    with contextlib.closing(smtplib.SMTP('localhost')) as smtp:
      smtp.sendmail(mail['From'], mail['To'].split(','), mail.as_string())

  #with open(os.path.expanduser('~/.flights.pickle'), 'w') as f:
  #  pickle.dump(newres, f)
