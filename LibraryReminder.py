#!/usr/bin/python
import mechanize
from mechanize import Browser
from BeautifulSoup import BeautifulSoup
from elementtree import ElementTree
import json
from datetime import datetime, date
from EmailSender import EmailSender

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
            dueDate = tds[3].find('a').contents[0]
            if not dueDate in books:
                books[dueDate] = []
            books[dueDate].append({'title': title,'author': author,'dueDate': dueDate})
        return books


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
            dueDate = tds[3].find('a').contents[0]
            if not dueDate in books:
                books[dueDate] = []
            books[dueDate].append({'title': title,'author': author,'dueDate': dueDate})
        return books

class PolarisInterface:
    def __init__(self, username, password, site):
        self.username = username
        self.password = password
        self.site = site
        self.browser = Browser(factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True))
        self.browser.addheaders = [('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36')]
        self.browser.open(self.site)
        self.browser.select_form(name="formMain")
        self.browser["textboxBarcodeUsername"] = self.username
        self.browser["textboxPassword"] = self.password
        self.browser.submit()


    def getCheckedOutBooks(self):
        response = self.browser.follow_link(text_regex=r"^Items Out.*$")
        bs = BeautifulSoup(response.read())
        tables = bs.findAll('table', {'class': 'patrongrid'})
        books = {}
        if(len(tables) < 1):
            return books

        trs = tables[0].fetch('tr', recursive=False)
        for i in xrange(1, len(trs)):
            if not trs[i].has_key('class'):
                continue
            tds = trs[i].fetch('td', recursive=False)
            title = tds[4].find('a',).contents[0]
            dueDate = tds[6].find('span').contents[0]
            dueDate = datetime.strptime(dueDate, "%m/%d/%Y").strftime("%m/%d/%Y")
            infoLink = tds[1].find('a')['href']
            response2 = self.browser.open(infoLink)
            bs2 = BeautifulSoup(response2.read())
            ajaxTrs = bs2.findAll('tr')
            authorTds = ajaxTrs[1].findAll('td', recursive=False)
            author = authorTds[2].text
            author = "by %s" % (author, )
            if not dueDate in books:
                books[dueDate] = []
            books[dueDate].append({'title': title,'author': author,'dueDate': dueDate})
        return books

class GoogleCalendarInterface:
    def __init__(self, username, password):
        self.client = gdata.calendar.client.CalendarClient(source='org.phuff-HorizonGCalInterface-v1')
        print "About to try and log in %s %s" % (username, password)
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
            content += "%s\n" % (self.getCalendarTextForBook(book), )

        event.content = atom.data.Content(text=content)
        when = gdata.calendar.data.When(start=date, end=date)
        when.reminder.append(gdata.data.Reminder(hours='6'))
        event.when.append(when)
        new_event = self.client.InsertEvent(event)

    def getCalendarTextForBook(self, book):
      return "%s %s" % (book['title'], book['author'])

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
          line = self.getCalendarTextForBook(book)
          # Ghetto way of handling both a book in the middle of the
          # blob and the end of the blob by replacing both cases with
          # empty string.  I didn't want to fiddle with regex escaping
          # for the calendartext of a book, since it could techincally
          # be a bunch of things that I don't have a spec for so I'm
          # not sure what or if I need to escape #lazyProgrammer :)
          newContent = event.content.text.replace(line + "\n", "")
          newContent = event.content.text.replace(line, "")
          newContent = newContent.strip()
          if newContent.strip() == '':
            self.client.Delete(event)
          elif newContent != event.content.text:
            event.content = atom.data.Content(text=newContent)
            self.client.Update(event)

    def removeOldBooks(self, oldBooks, currentBooks):
      for dueDate in oldBooks:
        for book in oldBooks[dueDate]:
          if not self.bookIsDue(book, dueDate, currentBooks):
            self.removeBookFromFeed(book, dueDate)


class EmailInterface:
    def emailAboutBooksIfNecessary(self, toAccount, fromAccount, books):
      overdueBooks = []
      dueTodayBooks = []
      for dueDate in books:
        if datetime.strptime(dueDate, "%m/%d/%Y").date() < date.today():
          for book in books[dueDate]:
            overdueBooks.append({'dueDate': dueDate, 'book': book})
        if datetime.strptime(dueDate, "%m/%d/%Y").date() == date.today():
          for book in books[dueDate]:
            dueTodayBooks.append(book)
      if len(overdueBooks) > 0 or len(dueTodayBooks) > 0:
        es = EmailSender()
        dueTodayString = ""
        overdueString = ""
        if len(dueTodayBooks) > 0:
          dueTodayString = "%d book%s due today" % (len(dueTodayBooks), "s" if len(dueTodayBooks) > 0 else "")
        if len(overdueBooks) > 0:
          overdueString = "%d book%s overdue" % (len(overdueBooks), "s" if len(overdueBooks) > 0 else "")
        summaryString = ""
        subjectString = ""
        if len(dueTodayBooks) > 0 and len(overdueBooks) > 0:
          summaryString = "%s and %s" % (dueTodayString, overdueString)
        else:
          summaryString = "%s%s" % (dueTodayString, overdueString)
        subject = message = "There %s %s at the library!" % ("is" if len(dueTodayBooks) + len(overdueBooks) == 1 else "are", summaryString, )
        message += "\n"
        if len(dueTodayBooks) > 0:
          booksDueTodayString = "Due today:\n"
          for book in dueTodayBooks:
            booksDueTodayString += "%s %s\n" % (book["title"], book["author"])
          message += booksDueTodayString
        if len(overdueBooks) > 0:
          overdueBooksString = "Overdue:\n"
          for bookStruct in overdueBooks:
            overdueBooksString += "%s %s - Due: %s\n" % (bookStruct["book"]["title"], bookStruct["book"]["author"], bookStruct["dueDate"])
          message += overdueBooksString

        es.sendEmail(toAccount, fromAccount, subject, message)

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
  email = ""
  for line in library_accounts:
    (library_site, library_account, library_pin, gcal_account, gcal_password) = line.split(',')
    email = gcal_account
    agent = PolarisInterface(library_account, library_pin, library_site)
    books = agent.getCheckedOutBooks()
    #gcalInterface = GoogleCalendarInterface(gcal_account, gcal_password)
    #gcalInterface.ensureAppropriateEventsExistForBooks(books)
    merge_dictionaries(allBooks, books)

  try:
    with open("library_books.json") as f:
      oldBooks = json.load(f)
  except IOError as e:
    oldBooks = {}

  #gcalInterface.removeOldBooks(oldBooks, allBooks)
  with open("library_books.json", "w") as f:
    f.write(json.dumps(allBooks))

  if datetime.now().hour == 9 or datetime.now().hour == 14:
    ei = EmailInterface()
    ei.emailAboutBooksIfNecessary(email, email, allBooks)
