#!/usr/bin/python

from mechanize import Browser
from BeautifulSoup import BeautifulSoup
from elementtree import ElementTree

try:
  from xml.etree import ElementTree
except ImportError:
  from elementtree import ElementTree
import gdata.calendar.data
import gdata.calendar.client
import gdata.acl.data
import atom.data
import time

class HorizonInterface:
    def __init__(self, username, password, site):
        self.username = username
        self.password = password
        self.site = site
        self.browser = Browser()
        self.browser.open(self.site)
        self.browser.select_form(name="security")
        self.browser["sec1"] = self.username
        self.browser["sec2"] = self.password
        self.browser.submit()

        
    def getCheckedOutBooks(self):
        response = self.browser.follow_link(text_regex=r"^Items Out$")
        bs = BeautifulSoup(response.read())
        tables = bs.findAll('table', {'class': 'tableBackgroundHighlight'})
        books = {}
        if(len(tables) <= 1):
            return books

        trs = tables[1].fetch('tr', recursive=False)
        for i in xrange(1, len(trs)):
            tds = trs[i].fetch('td', recursive=False)
            title = tds[1].find('a', {'class': 'mediumBoldAnchor'}).contents[0]
            author = tds[1].find('a', {'class': 'normalBlackFont1'}).contents[0]
            barcode = tds[2].find('a').contents[0]
            dueDate = tds[4].find('a').contents[0]
            if not dueDate in books:
                books[dueDate] = []
            books[dueDate].append([title,author,dueDate,barcode])
        return books

class GoogleCalendarInterface:
    def __init__(self, username, password):
        self.client = gdata.calendar.client.CalendarClient(source='org.phuff-HorizonGCalInterface-v1')
        self.client.ClientLogin(username, password, self.client.source)
        self.booksDueTitle = 'Library Books Due'
    
    def ensureAppropriateEventsExistForBooks(self, books):
        for dueDate in books:
            (month, day, year) = dueDate.split('/')
            googleStartDate = '%s-%s-%02d' % (year,month,int(day))
            googleEndDate = '%s-%s-%02d' % (year,month,int(day) + 1)
            query = gdata.calendar.client.CalendarEventQuery()
            query.start_min = googleStartDate
            query.start_max = googleEndDate
            feed = self.client.GetCalendarEventFeed(q=query)
            found = False

            for event in feed.entry:
                if event.title.text == self.booksDueTitle:
                    self.ensureEventIsAccurate(event, books[dueDate])
                    found = True
            if not found:
                self.createEvent(googleStartDate, books[dueDate])

    def createEvent(self, date, booksForDate):
        event = gdata.calendar.data.CalendarEventEntry()
        event.title = atom.data.Title(text=self.booksDueTitle)
        content = ""
        for book in booksForDate:
            content += "%s %s %s\n" % (book[0], book[1], book[3], )
        
        event.content = atom.data.Content(text=content)
        when = gdata.calendar.data.When(start=date, end=date)
        when.reminder.append(gdata.data.Reminder(days='1'))
        event.when.append(when)
        new_event = self.client.InsertEvent(event)

    def ensureEventIsAccurate(self, event, booksForDate):
        dirty = False
        for book in booksForDate:
            line = "%s %s %s" % (book[0], book[1], book[3], )
            if event.content.text.find(line) < 0:
                dirty = True
                content = event.content.text
                content += "\n" + line + "\n"
                event.content = atom.data.Content(text=content)
        if dirty:
            self.client.Update(event)


if __name__ == '__main__':
    library_accounts = open("library_accounts.txt")
    for line in library_accounts:
        (library_site, library_account, library_pin, gcal_account, gcal_password) = line.split(',')
        horizon = HorizonInterface(library_account, library_pin, library_site)
        books = horizon.getCheckedOutBooks()
        gcalInterface = GoogleCalendarInterface(gcal_account, gcal_password)
        gcalInterface.ensureAppropriateEventsExistForBooks(books)

    
