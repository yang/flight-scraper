Flight Scraper
==============

Flight Scraper drives a browser to search for tickets across multiple airline
sites, scraping/emailing/plotting fare information.

Setup
-----

Requires Python 2.7.

Install Xvfb:

    sudo aptitude install xvfb

Install [Google Chrome] and [ChromeDriver].

[Google Chrome]: https://www.google.com/chrome/
[ChromeDriver]: http://code.google.com/p/chromedriver/downloads/list

For the web reports, install Less and fetch/build the resources:

    npm install -g less
    make

Install flight-scraper:

    pip install flight-scraper

Usage
-----

To use the program for yourself, for now you'll just have to edit the program,
namely the `gen()` function inside the `script()` function.  A query processor
that is flexible enough to accommodate a good variety of possible requests and
understands how to dispatch this meta-query by quering each of the different
airlines is beyond the scope of the current code.

The program aggregates the results of the queries into an HTML report, then
sends an email summary which links to the report (specify a --url-base).
