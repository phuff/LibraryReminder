LibraryReminder.py
==================

LibraryReminder.py looks at your Horizon library account and finds when books are due, and then inserts google calendar events in your google calendar with a reminder for one day before.
Eventually it might auto-renew, or do things like save things into a database so you can keep track of which books you've read.


Dependencies
------------
Install these first:
* Python Mechanize (http://wwwsearch.sourceforge.net/mechanize/)
* Beautiful Soup (http://www.crummy.com/software/BeautifulSoup/)
* Element Tree (http://effbot.org/zone/element-index.htm)
* Google Data Python API (http://code.google.com/p/gdata-python-client/downloads/list)

Usage
-----

Create a text file called library_accounts.txt in the same directory as LibraryReminder.py that looks like the example_accounts.txt file:

       http://library-website.org/ipac20/ipac.jsp?profile=dial&menu=account,<library-card-barcode>,<library-pin>,<google-cal-account>,<google-calendar-password>

You'll probably have to browse around to find the login screen to your library's website.  You can do multiple accounts if you put each one on it's own line.  Then run: python LibraryReminder.py


