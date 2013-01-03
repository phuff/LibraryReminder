#!/usr/bin/python

from mechanize import Browser
from BeautifulSoup import BeautifulSoup
from elementtree import ElementTree
import json

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


    def getFeedForDate(self, dueDate):
      (month, day, year) = dueDate.split('/')
      googleStartDate = '%s-%s-%02d' % (year,month,int(day))
      googleEndDate = '%s-%s-%02d' % (year,month,int(day) + 1)
      query = gdata.calendar.client.CalendarEventQuery()
      query.start_min = googleStartDate
      query.start_max = googleEndDate
      feed = self.client.GetCalendarEventFeed(q=query)
      return feed

    def ensureAppropriateEventsExistForBooks(self, books):
        for dueDate in books:
          feed = self.getFeedForDate(dueDate)
          found = False

          for event in feed.entry:
            if event.title.text == self.booksDueTitle:
              self.ensureEventIsAccurate(event, books[dueDate])
              found = True
          if not found:
            (month, day, year) = dueDate.split('/')
            googleStartDate = '%s-%s-%02d' % (year,month,int(day))
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

    def getCalendarTextForBook(self, book):
      return "%s %s %s" % (book[0], book[1], book[3], )

    def ensureEventIsAccurate(self, event, booksForDate):
        dirty = False
        for book in booksForDate:
            line = self.getCalendarTextForBook(book)
            if event.content.text.find(line) < 0:
                dirty = True
                content = event.content.text
                content += line + "\n"
                event.content = atom.data.Content(text=content)
        if dirty:
            self.client.Update(event)

    def bookIsDue(self, oldBook, dueDate, currentBooks):
      if not currentBooks.has_key(dueDate):
        return False

      for book in currentBooks[dueDate]:
        if oldBook == book:
          return True

      return False


    def removeBookFromFeed(self, book, dueDate):
      feed = self.getFeedForDate(dueDate)
      for event in feed.entry:
        if event.title.text == self.booksDueTitle:
          print "Found the old event text: %s" % (event.content.text, )
          line = self.getCalendarTextForBook(book)
          # Ghetto way of handling both the middle and the end.  I didn't want to fiddle with regex escaping for the calendartext
          # of a book, since it could techincally be a bunch of things that I don't have a spec for so I'm not sure what or if I need to escape
          # #lazyProgrammer :)
          newContent = event.content.text.replace(line + "\n", "")
          newContent = event.content.text.replace(line, "")
          newContent = newContent.strip()
          print "newContent afterwards: %s" % (newContent, )
          if newContent.strip() == '':
            print "newContent stripped is empty, so I'm deleting the event."
            self.client.Delete(event)
          elif newContent != event.content.text:
            print "newContent text is not equivalent to the old one, so I'm updating it."
            event.content = atom.data.Content(text=newContent)
            self.client.Update(event)

    def removeOldBooks(self, oldBooks, currentBooks):
      for dueDate in oldBooks:
        for book in oldBooks[dueDate]:
          print "checking book: %s" % (book, )
          if not self.bookIsDue(book, dueDate, currentBooks):
            print "%s is not due any more on %s" % (book, dueDate, )
            self.removeBookFromFeed(book, dueDate)

if __name__ == '__main__':

  def merge_dictionaries(dict1, dict2):
    '''Merges book duedate dict2 into dict1 and returns dict1'''
    for dueDate in dict2:
      if not dueDate in dict1:
        dict1[dueDate] = []

      for book in dict2[dueDate]:
        dict1[dueDate].append(book)

  library_accounts = open("library_accounts.txt")

  allBooks = {}

  for line in library_accounts:
    (library_site, library_account, library_pin, gcal_account, gcal_password) = line.split(',')
    horizon = HorizonInterface(library_account, library_pin, library_site)
    books = horizon.getCheckedOutBooks()
    gcalInterface = GoogleCalendarInterface(gcal_account, gcal_password)
    gcalInterface.ensureAppropriateEventsExistForBooks(books)
    merge_dictionaries(allBooks, books)

  try:
    with open("library_books.json") as f:
      oldBooks = json.load(f)
  except IOError as e:
    oldBooks = {}

  gcalInterface.removeOldBooks(oldBooks, allBooks)
  with open("library_books.json", "w") as f:
    f.write(json.dumps(allBooks))
