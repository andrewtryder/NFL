# -*- coding: utf-8 -*-
###
# Copyright (c) 2012, spline
# All rights reserved.
#
#
###


from BeautifulSoup import BeautifulSoup
import urllib2
import urllib
import re
import collections
import string
from itertools import groupby, izip, count
import time
import datetime
import json
import sqlite3
import os
import unicodedata

# supybot libs
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('NFL')

@internationalizeDocstring
class NFL(callbacks.Plugin):
    """Add the help for "@plugin help NFL" here
    This should describe *how* to use this plugin."""
    threaded = True
    
    # http://code.activestate.com/recipes/303279/#c7
    def _batch(self, iterable, size):
        c = count()
        for k, g in groupby(iterable, lambda x:c.next()//size):
            yield g
            
    def _validate(self, date, format):
        """Return true or false for valid date based on format."""
        try:
            datetime.datetime.strptime(date, format) # format = "%m/%d/%Y"
            return True
        except ValueError:
            return False

    def _remove_accents(self, data):
        nkfd_form = unicodedata.normalize('NFKD', unicode(data))
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

    def _b64decode(self, string):
        """Returns base64 encoded string."""
        import base64
        return base64.b64decode(string)

    def _int_to_roman(self, i):
        """Returns a string containing the roman numeral from a number."""
        numeral_map = zip((1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
            ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I'))
        result = []
        for integer, numeral in numeral_map:
            count = int(i / integer)
            result.append(numeral * count)
            i -= integer * count
        return ''.join(result)

    def _smart_truncate(self, text, length, suffix='...'):
        """Truncates `text`, on a word boundary, as close to
        the target length it can come.
        """

        slen = len(suffix)
        pattern = r'^(.{0,%d}\S)\s+\S+' % (length-slen-1)
        if len(text) > length:
            match = re.match(pattern, text)
            if match:
                length0 = match.end(0)
                length1 = match.end(1)
                if abs(length0+slen-length) < abs(length1+slen-length):
                    return match.group(0) + suffix
                else:
                    return match.group(1) + suffix
        return text

    def _millify(self, num):
        for x in ['','k','M','B','T']:
            if num < 1000.0:
                return "%3.3f%s" % (num, x)
            num /= 1000.0

    def _shortenUrl(self, url):
        posturi = "https://www.googleapis.com/urlshortener/v1/url"
        headers = {'Content-Type' : 'application/json'}
        data = {'longUrl' : url}

        data = json.dumps(data)
        request = urllib2.Request(posturi,data,headers)
        response = urllib2.urlopen(request)
        response_data = response.read()
        shorturi = json.loads(response_data)['id']
        return shorturi

    def _validteams(self, conf=None, div=None):
        """Returns a list of valid teams for input verification."""
        db_filename = self.registryValue('dbLocation')
        
        if not os.path.exists(db_filename):
            self.log.error("ERROR: I could not find: %s" % db_filename)
            return
            
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        
        if conf and not div:
            cursor.execute("select team from nfl where conf=?", (conf,))
        elif conf and div:
            query = "select team from nfl where conf='%s' AND div='%s'" % (conf,div)
            self.log.info(query)
            cursor.execute(query)
        else:
            cursor.execute("select team from nfl")
        
        teamlist = []
        
        for row in cursor.fetchall():
            teamlist.append(str(row[0]))

        cursor.close()
        
        return teamlist
        
    def _translateTeam(self, db, column, optteam):
        """Returns a list of valid teams for input verification."""
        db_filename = self.registryValue('dbLocation')
        
        if not os.path.exists(db_filename):
            self.log.error("ERROR: I could not find: %s" % db_filename)
            return
            
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        query = "select %s from nfl where %s='%s'" % (db, column, optteam)
        cursor.execute(query)
        row = cursor.fetchone()

        cursor.close()            

        return (str(row[0]))


    ####################
    # public functions #
    ####################

    def football(self, irc, msg, args):
        """Display a silly football."""
        
        irc.reply("      _.-=\"\"=-._    ")
        irc.reply("    .'\\\\-++++-//'.  ")
        irc.reply("   (  ||      ||  ) ")
        irc.reply("    './/      \\\\.'  ")
        irc.reply("      `'-=..=-'`    ")

    football = wrap(football)
    
    
    def nflawards(self, irc, msg, args, optyear):
        """[year]
        Display NFL Awards for a specific year. Use a year from 1966 on. Ex: 2003
        """
        
        testdate = self._validate(optyear, '%Y')
        if not testdate or int(optyear) < 1966: # superbowl era and on. 
            irc.reply("Invalid year. Must be YYYY and after 1966.")
            return
            
        url = self._b64decode('aHR0cDovL3d3dy5wcm8tZm9vdGJhbGwtcmVmZXJlbmNlLmNvbS95ZWFycy8=') + '%s/' % optyear # 1966 on.

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        
        if soup.find('h2', text="Award Winners"):
            table = soup.find('h2', text="Award Winners").findParent('div', attrs={'id':'awards'}).find('table')
        else:
            irc.reply("Could not find NFL Awards for the %s season. Perhaps formatting changed or you are asking for the current season in-progress." % optyear)
            return
            
        rows = table.findAll('tr')

        append_list = []

        for row in rows:
            award = row.find('td')
            player = award.findNext('td')
            append_list.append(ircutils.bold(award.getText()) + ": " + player.getText())

        descstring = string.join([item for item in append_list], " | ")
        title = "%s NFL Awards" % optyear
        output = "{0} :: {1}".format(ircutils.mircColor(title, 'red'), descstring)       
        
        irc.reply(output)
    
    nflawards = wrap(nflawards, [('somethingWithoutSpaces')])
    
    
    def nflsuperbowl(self, irc, msg, args, optbowl):
        """[number]
        Display information from a specific Super Bowl. Ex: 39 or XXXIX
        """

        if optbowl.isdigit():
            try: 
                optbowl = self._int_to_roman(int(optbowl))
            except:
                irc.reply("Failed to convert %s to a roman numeral" % optbowl)
                return
                
        url = self._b64decode('aHR0cDovL3d3dy5wcm8tZm9vdGJhbGwtcmVmZXJlbmNlLmNvbS9zdXBlci1ib3dsLw==')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'id':'superbowls'}) 
        rows = table.findAll('tr')[1:]

        sb_data = collections.defaultdict(list)

        for row in rows:
            year = row.find('td')
            roman = year.findNext('td')
            t1 = roman.findNext('td')
            t1score = t1.findNext('td')
            t2 = t1score.findNext('td')
            t2score = t2.findNext('td')
            mvp = t2score.findNext('td')
            loc = mvp.findNext('td')
            city = loc.findNext('td')
            state = city.findNext('td')
            
            addString = year.getText() + " Super Bowl: " + roman.getText() + " :: " +  t1.getText() + " " + t1score.getText() + " " + t2.getText()\
                + " " + t2score.getText() + "  MVP: " + mvp.getText() + " " + " Location: " + loc.getText() + " (" + city.getText() + ", "\
                + state.getText() + ")"
                   
            sb_data[roman.getText()].append(str(addString))
                      
        output = sb_data.get(optbowl, None)
        
        if output is None:
            irc.reply("No Super Bowl found for: %s" % optbowl)
        else:
            irc.reply(" ".join(output))

    nflsuperbowl = wrap(nflsuperbowl, [('somethingWithoutSpaces')])
    
    
    def nflpracticereport (self, irc, msg, args, optteam):
        """[team]
        Display most recent practice report for team.
        """
        
        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
        
        url = self._b64decode('aHR0cDovL2hvc3RlZC5zdGF0cy5jb20vZmIvcHJhY3RpY2UuYXNw')

        try:
            request = urllib2.Request(url)
            html = (urllib2.urlopen(request)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        timeStamp = soup.find('div', attrs={'id':'shsTimestamp'}).getText()
        tds = soup.findAll('td', attrs={'class':'shsRow0Col shsNamD', 'nowrap':'nowrap'})

        practicereport = collections.defaultdict(list)

        for td in tds:
            team = td.findPrevious('h2', attrs={'class':'shsTableTitle'})
            team = self._translateTeam('team', 'full', str(team.getText())) # translate full team into abbr.
            player = td.find('a')
            appendString = str(ircutils.bold(player.getText()))
            report = td.findNext('td', attrs={'class':'shsRow0Col shsNamD'})
            if report:
                appendString += str("(" + report.getText() + ")")
        
            practicereport[team].append(appendString)

        output = practicereport.get(optteam, None)
                
        if output is None:
            irc.reply("No recent practice reports for: {0} as of {1}".format(ircutils.mircColor(optteam, 'red'), timeStamp.replace('Last updated ','')))
        else:
            irc.reply("{0} Practice Report ({1}) :: {2}".format(ircutils.mircColor(optteam, 'red'), timeStamp, " | ".join(output)))
    
    nflpracticereport = wrap(nflpracticereport, [('somethingWithoutSpaces')])
    
    
    def nflweather(self, irc, msg, args, optteam):
        """[team]
        Display weather for the next game. Ex: NE
        """
        
        optteam = optteam.upper()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
               
        url = self._b64decode('aHR0cDovL3d3dy5uZmx3ZWF0aGVyLmNvbS8=')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
            
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'class':'main'})
        if not table:
            irc.reply("Something broke in formatting with nflweather.")
            return
            
        tbody = table.find('tbody')
        rows = tbody.findAll('tr')

        weatherList = collections.defaultdict(list)

        for row in rows: # grab all, parse, throw into a defaultdict for get method.
            tds = row.findAll('td')
            awayTeam = str(self._translateTeam('team', 'short', tds[0].getText())) # translate into the team for each.
            homeTeam = str(self._translateTeam('team', 'short', tds[4].getText()))
            timeOrScore = tds[5].getText()
            gameTemp = tds[8].getText()
    
            appendString = "{0}@{1} - {2} - {3}".format(awayTeam, ircutils.bold(homeTeam), timeOrScore, gameTemp) # one string, put into key:value based on teams.
            weatherList[awayTeam].append(appendString)
            weatherList[homeTeam].append(appendString)
    
        output = weatherList.get(optteam, None)
        
        if output is None:
            irc.reply("No weather found for: %s. Team on bye?" % optteam)
        else:
            irc.reply(" ".join(output))

    nflweather = wrap(nflweather, [('somethingWithoutSpaces')])        
    
    
    def nflffpointleaders(self, irc, msg, args):
        """
        Display weekly FF point leaders.
        Note "Season Leaders" totals are not updated until each week is final (Tuesday AM).
        """
        
        url = self._b64decode('aHR0cDovL2dhbWVzLmVzcG4uZ28uY29tL2ZmbC9sZWFkZXJz')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        html = html.replace('&nbsp;',' ')
    
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'id':'playertable_0'})
        rows = table.findAll('tr')[2:12]

        append_list = []
        count = 1

        for row in rows:
            rank = count
            player = row.find('td').find('a')
            points = row.find('td', attrs={'class':'playertableStat appliedPoints sortedCell'})
            append_list.append(str(rank) + ". " + ircutils.bold(player.getText()) + " (" + points.getText() + ")")
            count += 1 # ++
    
        title = "Top 10 FF points:"
        descstring = string.join([item for item in append_list], " | ") # put the list together.
        output = "{0} :: {1}".format(ircutils.mircColor(title, 'red'), descstring)
        irc.reply(output)
    
    nflffpointleaders = wrap(nflffpointleaders)
    
    
    def nflffaddeddropped(self, irc, msg, args, opttype):
        """<position>
        Show the Top 15 most added / dropped. Add in optional position to show at each.
        Position must be one of:
        """
        
        validtypes = { 'QB':'0','RB':'2','WR':'4','TE':'6','D/ST':'16','K':'17','FLEX':'23'}
        
        if opttype and opttype not in validtypes:
            irc.reply("Type must be one of: %s" % validtypes.keys())
            return
        
        url = self._b64decode('aHR0cDovL2dhbWVzLmVzcG4uZ28uY29tL2ZmbC9hZGRlZGRyb3BwZWQ=')
            
        if opttype:
            url += '?&slotCategoryId=%s' % validtypes[opttype]
        
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'class':'tableBody'})
        rows = table.findAll('tr', attrs={'class':'tableBody'})[0:13] #15 is too many for a line.

        added_list = []
        dropped_list = []

        for row in rows:
            p1rank = row.find('td')
            p1 = p1rank.findNext('td')
            p1pos = p1.findNext('td')
            p1last = p1pos.findNext('td')
            p1cur = p1last.findNext('td')
            p17day = p1cur.findNext('td')
            space = p17day.findNext('td')
            p2rank = space.findNext('td')
            p2 = p2rank.findNext('td')
            p2pos = p2.findNext('td')
            p2last = p2pos.findNext('td')
            p2cur = p2last.findNext('td')
            p27day = p2cur.findNext('td')
            added_list.append(p1.getText() + " (" + p17day.getText() + ")")
            dropped_list.append(p2.getText() + " (" + p27day.getText() + ")")

        addedstring = string.join([item for item in added_list], " | ") 
        droppedstring = string.join([item for item in dropped_list], " | ") 

        if opttype:
            addedtitle = "Top 15 added at: %s" % opttype
            droppedtitle = "Top 15 dropped at: %s" % opttype
        else:
            addedtitle = "Top 15 added"
            droppedtitle = "Top 15 dropped"
            
        addedoutput = "{0} :: {1}".format(ircutils.mircColor(addedtitle, 'red'), addedstring)
        irc.reply(addedoutput)
        
        droppedoutput = "{0} :: {1}".format(ircutils.mircColor(droppedtitle, 'red'), droppedstring)
        irc.reply(droppedoutput)
        
    nflffaddeddropped = wrap(nflffaddeddropped, [optional('somethingWithoutSpaces')])        
    
    
    def nflffpointsagainst(self, irc, msg, args, optlist, optposition):
        """<--average|--totals> [position]
        Fantasy Football Points Against. Shows by position. Can show average and totals with
        switches.
        """
        
        validpositions = {'QB':'1','RB':'2','WR':'3','TE':'4','K':'5','D/ST':'16'}
        
        if optposition not in validpositions:
            irc.reply("Type must be one of: %s" % validpositions.keys())
            return

        averages, totals = True, False
        for (option, arg) in optlist:
            if option == 'averages':
                averages, totals = True, False
            if option == 'totals':
                averages, totals = False, True

        url = self._b64decode('aHR0cDovL2dhbWVzLmVzcG4uZ28uY29tL2ZmbC9wb2ludHNhZ2FpbnN0') + '?positionId=%s' % validpositions[optposition]
        
        if totals and not averages:
            url += '&statview=totals'
        elif averages and not totals:
            url += '&statview=averages'

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'id':'playertable_0'})
        rows = table.findAll('tr')[2:12]  

        append_list = []
        
        for row in rows:
            player = row.find('td').find('a')
            points = row.find('td', attrs={'class':'playertableStat appliedPoints'})
            append_list.append(ircutils.bold(player.getText()) + ": " + points.getText())
            
        descstring = string.join([item for item in append_list], " | ")
        
        irc.reply(descstring)
            
    nflffpointsagainst = wrap(nflffpointsagainst, [getopts({'averages':'','totals':''}), ('somethingWithoutSpaces')])
    
    
    def nflffprojections(self, irc, msg, args, opttype):
        """<position>
        Player projections is based on recommended draft rankings, which take into account projected total points as well as upside and risk.
        Position is optional. Can be one of: QB | RB | WR | TE | D/ST | K | FLEX
        """
  
        validtypes = { 'QB':'0','RB':'2','WR':'4','TE':'6','D/ST':'16','K':'17','FLEX':'23'}
        
        if opttype and opttype not in validtypes:
            irc.reply("Type must be one of: %s" % validtypes.keys())
            return
            
        url = self._b64decode('aHR0cDovL2dhbWVzLmVzcG4uZ28uY29tL2ZmbC90b29scy9wcm9qZWN0aW9ucz8=')

        if opttype:
            url += '?&slotCategoryId=%s' % validtypes[opttype]
 
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % opttype)
            return
            
        html = html.replace('&nbsp;',' ')
    
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'id':'playertable_0'})
        rows = table.findAll('tr')[2:12]

        append_list = []

        for row in rows:
            rank = row.find('td')
            player = rank.findNext('td')
            projections = row.find('td', attrs={'class':'playertableStat appliedPoints'})
            append_list.append(rank.getText() + ". " + ircutils.bold(player.getText()) + " (" + projections.getText() + ")")

        descstring = string.join([item for item in append_list], " | ") # put the list together.

        if opttype:
            title = "Top 10 FF projections at: %s" % opttype
        else:
            title = "Top 10 FF projections"
            
        output = "{0} :: {1}".format(ircutils.mircColor(title, 'red'), descstring)
        irc.reply(output)
    
    nflffprojections = wrap(nflffprojections, [optional('somethingWithoutSpaces')])
    
    
    def nflffdraftresults(self, irc, msg, args, opttype):
        """<position>
        Displays the average position players were selected by team owners in Fantasy Football online drafts.
        Position is optional. Can be one of: QB | TQB | RB | WR | TE | DT | DE | LB | CB | S | D/ST | K | P | HC | ALL
        """
        
        validtypes = ['QB','TQB','RB','WR','TE','DT','DE','LB','CB','S','D/ST','K','P','HC','ALL']
        
        if opttype and opttype not in validtypes:
            irc.reply("Type must be one of: %s" % validtypes)
            return

        url = self._b64decode('aHR0cDovL2dhbWVzLmVzcG4uZ28uY29tL2ZmbC9saXZlZHJhZnRyZXN1bHRz')
        
        if opttype:
            url += '?position=%s' % opttype
        

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'class':'tableBody'})
        headers = table.findAll('tr')[2]
        rows = table.findAll('tr')[3:13]

        append_list = []

        for row in rows:
            rank = row.find('td')
            player = rank.findNext('td')
            avgpick = player.findNext('td').findNext('td')
            append_list.append(rank.getText() + ". " + ircutils.bold(player.getText()) + " (" + avgpick.getText() + ")")

        descstring = string.join([item for item in append_list], " | ") # put the list together.

        if not opttype:
            opttype = 'ALL'

        title = "Top 10 drafted at: %s" % opttype
        output = "{0} :: {1}".format(ircutils.mircColor(title, 'red'), descstring)
        irc.reply(output)
        
    nflffdraftresults = wrap(nflffdraftresults, [optional('somethingWithoutSpaces')])
    
    
    def nflweeklyleaders(self, irc, msg, args):
        """
        Display weekly leaders in various categories.
        """
    
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC93ZWVrbHkvbGVhZGVycw==')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return

        html = html.replace('class="oddrow','class="evenrow')

        soup = BeautifulSoup(html)
        weeklytitle = soup.find('h1', attrs={'class':'h2'}).renderContents().strip()
        tables = soup.findAll('table', attrs={'class':'tablehead'})

        object_list = []

        for table in tables:
            statcategory = table.find('tr', attrs={'class':'stathead'}).find('td')
            rows = table.findAll('tr', attrs={'class': re.compile('evenrow.*')})
            for row in rows:
                player = row.find('td', attrs={'align':'left'})
                team = player.findNext('td')     
                d = collections.OrderedDict()
                d['category'] = statcategory.renderContents().strip()
                d['player'] = str(player.text.replace('.','. '))
                d['team'] = team.renderContents().strip()
                object_list.append(d)
        
        passinglist = []
        rushinglist = []
        receivinglist = []
        defensivelist = []

        for each in object_list:
            if each['category'] == "Passing Leaders":
                passinglist.append(each['player'] + "(" + each['team'] + ")")
            if each['category'] == "Rushing Leaders":
                rushinglist.append(each['player'] + "(" + each['team'] + ")")
            if each['category'] == "Receiving Leaders":
                receivinglist.append(each['player'] + "(" + each['team'] + ")")    
            if each['category'] == "Defensive Leaders":
                defensivelist.append(each['player'] + "(" + each['team'] + ")")
        
        irc.reply(ircutils.mircColor(weeklytitle, 'red'))
        irc.reply(ircutils.bold("Passing Leaders: ") + string.join([item for item in passinglist], " | "))
        irc.reply(ircutils.bold("Rushing Leaders: ") + string.join([item for item in rushinglist], " | "))
        irc.reply(ircutils.bold("Receiving Leaders: ") + string.join([item for item in receivinglist], " | "))
        irc.reply(ircutils.bold("Defensive Leaders: ") + string.join([item for item in defensivelist], " | "))
    
    nflweeklyleaders = wrap(nflweeklyleaders)
    
    
    def nfltopsalary(self, irc, msg, args, optlist, optposition):
        """<--average|--cap-hit> <position>
        Display various NFL player and team salary information. Use --average to display
        the highest average salary. Use --cap-hit to display highest cap-hit. Other option is: position. Use
        the command with an argument to display valid positions.
        """

        average, caphit = False, False
        for (option, arg) in optlist:
            if option == 'average':
                average, caphit = True, False
            if option == 'caphit':
                caphit, average = True, False

        positions = [ 'center','guard','tackle','tight-end','wide-receiver','fullback', 'running-back', 'quarterback',\
        'defensive-end', 'defensive-tackle', 'linebacker', 'cornerback', 'safety', 'kicker', 'punter', 'kick-returner', 'long-snapper' ]

        url = self._b64decode('aHR0cDovL3d3dy5zcG90cmFjLmNvbS90b3Atc2FsYXJpZXM=') + '/nfl/' 
        
        if average:
            url += 'average/'
        if caphit:
            url += 'cap-hit/'
        
        if optposition:
            if optposition not in positions:
                irc.reply("Position not found. Must be one of: %s" % positions)
                return
            else:
                url += '%s/' % optposition
        
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        params = urllib.urlencode({'ajax':'1'})
        request = urllib2.Request(url, params, headers)
        html = (urllib2.urlopen(request)).read()
        html = html.replace('\n','')

        soup = BeautifulSoup(html)
        tbody = soup.find('tbody')
        rows = tbody.findAll('tr')[0:5] # just do top5 because some lists are long.

        append_list = []
        
        for row in rows:
            rank = row.find('td', attrs={'style':'width:20px;'}).find('center')
            #team = rank.findNext('td', attrs={'class':re.compile('logo.*?')}).find('img')['src'].replace('http://www.spotrac.com/assets/images/thumb/','').replace('.png','')
            # self._translateTeam('st', 'team', str(team))
            player = row.find('td', attrs={'class':re.compile('player .*?')}).find('a')
            position = player.findNext('span', attrs={'class':'position'})
            salary = row.find('span', attrs={'class':'playersalary'}).renderContents().replace('$','').replace(',','')
            
            append_list.append(rank.renderContents().strip() + ". " + ircutils.bold(player.renderContents().strip()) + " " + self._millify(float(salary)))    
    
        descstring = string.join([item for item in append_list], " | ") # put the list together.
        
        title = ircutils.mircColor('NFL Top Salaries', 'red')
       
        # add to title, depending on what's going on  
        if caphit:
            title += " (cap-hit) "
        if average:
            title += " (average salaries) "
        if optposition:
            title += " at %s" % (optposition)       
                
        output = "{0}: {1}".format(title, descstring)
        irc.reply(output)
            
    nfltopsalary = wrap(nfltopsalary, [(getopts({'average':'', 'caphit':''})), optional('somethingWithoutSpaces')])
    
        
    def nflleagueleaders(self, irc, msg, args, optlist, optcategory, optstat, optyear):
        """<--postseason|--num20> [category] [stat] <year>
        Display NFL statistical leaders in a specific category for a stat. Year, which can go back until 2001, is optional. 
        Defaults to the current season. Ex: Passing td or Punting punts 2003. Stats show regular season. Can show postseason with --postseason
        prefix. Default output is top10 and top20 can be shown with --num20 prefix.
        """ 
        
        statsCategories = { 
                'Passing': { 
                    'qbr':'49', 
                    'comp':'1',
                    'att':'2',
                    'comp%':'41',
                    'yards':'4',
                    'yards/gm':'42',
                    'td':'5',
                    'int':'3',
                    'sacked':'8',
                    'sackedyardslost':'9',
                    'fumbles':'47',
                    'fumbleslost':'48'
                },
                'Rushing': {
                    'rushes':'16',
                    'yards':'17',
                    'yards/g':'39',
                    'avg':'40',
                    'td':'18',
                    'fumbles':'47',
                    'fumbleslost':'48'
                },
                'Receiving': {
                    'receptions':'27',
                    'recyards':'28',
                    'yards/gm':'44',
                    'yards/avg':'45',
                    'longest':'30',
                    'yac':'46',
                    '1stdowns':'33',
                    'tds':'29',
                    'fumbles':'47',
                    'fumbleslost':'48'
                },
                'Kicking': {
                    '0-19':'208',
                    '20-29':'210',
                    '30-39':'212',
                    '40-49':'214',
                    '50+':'216',
                    'fgm':'222',
                    'fga':'221',
                    'pct':'230',
                    'longest':'224',
                    'xpm':'225',
                    'xpa':'226',
                    'xp%':'231'            
                },
                'Returns':{
                    'kickoffreturns':'311',
                    'kickoffyards':'312',
                    'kickoffavg':'319',
                    'kickofflongest':'314',
                    'kickofftd':'315',
                    'puntreturns':'301',
                    'puntreturnyards':'302',
                    'puntreturnavg':'320',
                    'puntreturnlongest':'304',
                    'puntreturntds':'305'
                },
                'Punting': {
                    'punts':'402',
                    'puntyards':'403',
                    'puntavg':'411',
                    'puntlong':'408',
                    'puntwithin20':'404',
                    'puntwithin10':'405',
                    'faircatch':'401',
                    'touchback':'406',
                    'blocked':'407'            
                },
                'Defense':{
                    'solotackles':'128',
                    'assistedtackles':'129',
                    'totaltackles':'130',
                    'sacks':'106',
                    'sacksyardslost':'107',
                    'stuffs':'101',
                    'stuffsyardslost':'102',
                    'int':'108',
                    'intyards':'109',
                    'inttds':'110',
                    'deftd':'103',
                    'forcedfumbles':'114',
                    'pd':'113',
                    'safety':'115'            
                }                         
            }
        
        optcategory = optcategory.title() # must title this category
        
        if optcategory not in statsCategories:
            irc.reply("Category must be one of: %s" % statsCategories.keys())
            return
        
        optstat = optstat.lower() # stat key is lower. value is #. 
        
        if optstat not in statsCategories[optcategory]:
            irc.reply("Stat for %s must be one of: %s" % (optcategory, statsCategories[optcategory].keys()))
            return
            
        if optyear: 
            testdate = self._validate(optyear, '%Y')
            if not testdate:
                irc.reply("Invalid year. Must be YYYY.")
                return
            if int(optyear) < 2000:
                irc.reply("Year must be 2001 or after.")
                return

        postseason, outlimit = False, '10'
        for (option, arg) in optlist:
            if option == 'postseason':
                postseason = True
            if option == 'num20':
                outlimit = '20'
                        
        url = self._b64decode('aHR0cDovL3Nwb3J0cy55YWhvby5jb20vbmZsL3N0YXRzL2J5Y2F0ZWdvcnk=')
        url += '?cat=%s&conference=NFL&sort=%s&timeframe=All' % (optcategory, statsCategories[optcategory][optstat])
        
        if optyear: # don't need year for most current.
            if not postseason:
                url += '&year=season_%s' % optyear
            else:
                url += '&year=postseason_%s' % optyear 
        
        #self.log.info(url)
        
        try:        
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return

        html = html.replace('&nbsp;','')
        
        soup = BeautifulSoup(html)
        selectedyear = soup.find('select', attrs={'name':'year'}).find('option', attrs={'selected':'selected'}) # creative way to find the year.
        table = soup.find('tr', attrs={'class':'ysptblthmsts', 'align':'center'}).findParent('table')
        header = table.findAll('tr')[1].findAll('td')
        rows = table.findAll('tr')[2:]

        append_list = []

        for row in rows[0:int(outlimit)]:
            name = str(row.findAll('td')[0].getText()) # always first
            team = str(row.findAll('td')[1].getText()) # always next
            sortfield = row.find('span', attrs={'class':'yspscores'}) # whatever field you are sorting by will have this span inside the td. 
            append_list.append(ircutils.bold(name) + "(" + team + ") - " + str(sortfield.getText()))

        title = "Top %s in %s(%s) for %s" % (outlimit, optcategory, optstat, selectedyear.getText())
        descstring = string.join([item for item in append_list], " | ")
        
        output = "{0} :: {1}".format(ircutils.mircColor(title, 'red'), descstring)
        irc.reply(output)            

    nflleagueleaders = wrap(nflleagueleaders, [(getopts({'postseason':'','num20':''})), ('somethingWithoutSpaces'), ('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])
    

    def nflteams(self, irc, msg, args, optconf, optdiv):
        """<conf> <div>
        Display a list of NFL teams for input. Optional: use AFC or NFC for conference.
        Optionally, it can also display specific divisions with North, South, East or West. Ex: nflteams AFC East
        """
        
        if optconf and not optdiv:
            optconf = optconf.lower().strip()
            if optconf == "afc" or optconf == "nfc":
                teams = self._validteams(conf=optconf)
            else:
                irc.reply("Conference must be AFC or NFC")
                return
                
        if optconf and optdiv:
            optconf = optconf.lower().strip()
            optdiv = optdiv.lower().strip()
            
            if optconf == "afc" or optconf == "nfc":
                if optdiv == "north" or optdiv == "south" or optdiv == "east" or optdiv == "west":
                    teams = self._validteams(conf=optconf, div=optdiv)
                else:
                    irc.reply("Division must be: North, South, East or West")
                    return
            else:
                irc.reply("Conference must be AFC or NFC")
                return

        if not optconf and not optdiv:
            teams = self._validteams()
                
        irc.reply("Valid teams are: %s" % (string.join([ircutils.bold(item) for item in teams], " | ")))
        
    nflteams = wrap(nflteams, [optional('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])


    def nflteamrankings(self, irc, msg, args, optteam):
        """[team]
        Display team rankings for off/def versus the rest of the NFL.
        """
        
        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC90ZWFtL18vbmFtZQ==') + '/%s/' % optteam

        try:
            request = urllib2.Request(url)
            html = (urllib2.urlopen(request)).read()
        except:
            irc.reply("Cannot open page: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        div = soup.find('div', attrs={'class':'mod-container mod-stat'}) 
        h3 = div.find('h3')
        statsfind = div.findAll('div', attrs={'class':re.compile('span-1.*?')})

        append_list = []
        
        for stats in statsfind:
            header = stats.find('h4')
            stat = stats.find('span', attrs={'class':'stat'})
            rank = stat.findNext('strong')
            append_list.append(ircutils.bold(header.text) + " " + stat.text + " (" + rank.text + ")")
            
        descstring = string.join([item for item in append_list], " | ")
        irc.reply(ircutils.mircColor(optteam,'red') + " :: " + ircutils.underline(h3.text) + " :: " + descstring)         
        
    nflteamrankings = wrap(nflteamrankings, [('somethingWithoutSpaces')])
    
    
    def nflweek(self, irc, msg, args, optlist, optweek):
        """<week #|next>
        Display this week's schedule in the NFL. Use --pre or --post to display pre/post season games.
        """
        
        url = self._b64decode('aHR0cDovL3MzLmFtYXpvbmF3cy5jb20vbmZsZ2MvYWxsU2NoZWR1bGUuanM=')
        
        usePre, useNext, outputWeek = False, False, False
        for (option, arg) in optlist:
            if option == 'pre':
                usePre = True
        
        if optweek:
            if optweek == "next":
                useNext = True
            elif optweek.isdigit():
                if usePre: 
                    if 1 <= int(optweek) <= 4:
                       outputWeek = "Preseason Week %s" % optweek
                    else:
                        irc.reply("ERROR: Preseason week number must be between 1 and 4.")
                        return
                else:
                    if 1 <= int(optweek) <= 17:
                        outputWeek = "Week %s" % optweek
                    else:
                        irc.reply("ERROR: Week must be between 1-17")
                        return 

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        jsondata = json.loads(html)

        week = jsondata.get('week', None) # work with the week data so we know where we are.

        if week is None:
            irc.reply("Failed to load schedule.")
            return

        currentWeekName = week.get('current', {'current': None}).get('weekName', None) 
        nextWeekName = week.get('next', {'next': None}).get('weekName', None) 

        if currentWeekName is None:
            irc.reply("Cannot figure out the current week.")
            return

        games = jsondata.get('content', None) # data in games.
        
        if games is None:
            irc.reply("Failed to load the games data.")
            return
        
        if outputWeek:
            games = [item['games'] for item in games if item['weekName'] == outputWeek]
            weekOutput = outputWeek
        elif useNext:
            games = [item['games'] for item in games if item['weekName'] == nextWeekName]
            weekOutput = nextWeekName
        else:
            games = [item['games'] for item in games if item['weekName'] == currentWeekName]
            weekOutput = currentWeekName
            
        append_list = []

        for games in games:
            for t in games:
                awayTeam = self._translateTeam('team', 'nid', t['awayTeamId'])
                homeTeam = self._translateTeam('team', 'nid', t['homeTeamId'])
                append_list.append("[" + t['date']['num'] + "] " + awayTeam + "@" + homeTeam + " " + t['date']['time'])
        
        descstring = string.join([item for item in append_list], " | ")
        output = "{0} :: {1}".format(ircutils.bold(weekOutput), descstring)
        
        irc.reply(output)
    
    nflweek = wrap(nflweek, [(getopts({'pre':''})), optional('somethingWithoutSpaces')])
    
    
    def nflstandings(self, irc, msg, args, optlist, optconf, optdiv):
        """<--detailed> [conf] [division]
        Display NFL standings for a division. Requires a conference and division.
        Ex: AFC East
        """
        
        detailed = False
        for (option, arg) in optlist:
            if option == 'detailed':
                detailed = True
        
        optconf = optconf.upper()
        optdiv = optdiv.title()
        
        if optconf != "AFC" and optconf != "NFC":
            irc.reply("Conference must be AFC or NFC.")
            return
        
        if optdiv != "North" and optdiv != "South" and optdiv != "East" and optdiv != "West":
            irc.reply("Division must be North, South, East or West.")
            return
        
        if not detailed:
            url = self._b64decode('aHR0cDovL3MzLmFtYXpvbmF3cy5jb20vbmZsZ2MvZGl2X3N0YW5kaW5nczIuanM=')
        else:
            url = self._b64decode('aHR0cDovL3MzLmFtYXpvbmF3cy5jb20vbmZsZ2MvZGl2X3N0YW5kaW5ncy5qcw==')
            
        req = urllib2.Request(url)
        html = (urllib2.urlopen(req)).read()
        jsondata = json.loads(html)
        
        standings = jsondata.get('content', None)

        if standings is None:
            irc.reply("Failed to load standings.")
            return
        
        teams = [item['teams'] for item in standings if item['conference'] == optconf and item['division'] == optdiv]
        
        if not detailed: # switch for detailed. this is the short-form.
        
            append_list = []

            for item in teams: # teams is a list of dicts
                for team in item: # so we recurse
                    append_list.append(self._translateTeam('team', 'nid', team['teamId']) + " " + team['winLossRecord'] + "(" + team['percentage'] + ")")
                
            descstring = string.join([item for item in append_list], " | ")
            output = "{0} {1} :: {2}".format(ircutils.bold(optconf), ircutils.bold(optdiv), descstring)
            irc.reply(output)
        else:
            
            header = "{0:11} {1:>3} {2:>3} {3:>3} {4:<6} {5:<5} {6:<5} {7:<5} {8:<5} {9:<4} {10:<4} {11:<4} {11:<5}"\
            .format(ircutils.underline(optconf + " " + optdiv),'W','L','T','PCT','HOME','ROAD','DIV','CONF','PF','PA','DIFF','STRK') 

            irc.reply(header)

            for item in teams: # teams is a list of dicts
                for t in item: # so we recurse
                    output = "{0:9} {1:3} {2:3} {3:3} {4:6} {5:5} {6:5} {7:5} {8:5} {9:4} {10:4} {11:4} {11:5}".format(t['team']['abbreviation'],\
                        t['wins'], t['losses'], t['ties'], t['percentage'], t['extra']['home_record'], t['extra']['road_record'],\
                        t['extra']['division_record'], t['extra']['conference_record'], t['extra']['points_for'], t['extra']['points_against'],\
                        t['extra']['home_record'], t['extra']['net_points'], t['extra']['last_5_record'])
                    
                    irc.reply(output) 
                
    nflstandings = wrap(nflstandings, [getopts({'detailed':''}), ('somethingWithoutSpaces'), ('somethingWithoutSpaces')])
    
    
    def nflcap(self, irc, msg, args, optteam):
        """[team]
        Display team's NFL cap situation. Ex: GB
        """
        
        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('spotrac', 'team', optteam)
        
        url = self._b64decode('aHR0cDovL3d3dy5zcG90cmFjLmNvbS9uZmwv') + '%s/cap-hit/' % lookupteam
        
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        params = urllib.urlencode({'ajax':'1'})
        request = urllib2.Request(url, params, headers)
        html = (urllib2.urlopen(request)).read()

        soup = BeautifulSoup(html)
        tbody = soup.find('tbody')
        rows = tbody.findAll('tr')
        caphit = str(rows[-1].find('td', attrs={'class':'total figure'}).text).replace(',','')
        rows = rows[-4:-1]
        
        append_list = []
        
        for row in rows:
            title = row.find('td', attrs={'colspan':'2'}).text
            figure = str(row.find('td', attrs={'class':'total figure'}).text).replace(',','')

            if figure.isdigit():
                append_list.append(ircutils.underline(title) + ": " + self._millify(float(figure)))
            else:
                append_list.append(ircutils.underline(title) + ": " + figure)
            
        descstring = string.join([item for item in append_list], " | ")
        output = "{0} :: {1}  TOTAL: {2}".format(ircutils.bold(optteam), descstring, ircutils.mircColor(self._millify(float(caphit)), 'blue'))
        irc.reply(output)

    nflcap = wrap(nflcap, [('somethingWithoutSpaces')])
    
    
    def nflcoachingstaff(self, irc, msg, args, optteam):
        """[team]
        Display a NFL team's coaching staff.
        """
        
        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
        
        url = self._b64decode('aHR0cDovL2VuLndpa2lwZWRpYS5vcmcvd2lraS9MaXN0X29mX2N1cnJlbnRfTmF0aW9uYWxfRm9vdGJhbGxfTGVhZ3VlX3N0YWZmcw==')

        try:
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        tables = soup.findAll('table', attrs={'style':'text-align: left;'})

        coachingstaff = collections.defaultdict(list)

        for table in tables:
            listitems = table.findAll('li')[3:]
            for li in listitems:
                team = li.findPrevious('h3')
                team = self._translateTeam('team', 'full', team.getText())
                coachingString = li.getText().replace(u' –',': ') #.replace(' –',': ') #.replace(u' –',': ')
                self.log.info(team)
                coachingstaff[team].append(coachingString)

        output = coachingstaff.get(team, None)
        
        if not output:
            irc.reply("Failed to find coaching staff for: %s. Maybe something broke?" % optteam)
        else:
            descstring = string.join([item for item in output], " | ")
            irc.reply("{0} Coaching Staff :: {1}".format(optteam, descstring))
    
    nflcoachingstaff = wrap(nflcoachingstaff, [('somethingWithoutSpaces')])

    
    def nfldepthchart(self, irc, msg, args, optteam, opttype):
        """[team] [offense|defense|special]
        Display team's depth chart for unit.
        """
        
        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('yahoo', 'team', optteam)
        
        opttype = opttype.lower().strip()
        
        if opttype != "offense" and opttype != "defense" and opttype != "special":
            irc.reply("Type must be offense, defense or special.")
            return
        
        url = self._b64decode('aHR0cDovL3Nwb3J0cy55YWhvby5jb20vbmZsL3RlYW1z') + '/%s/depthchart?nfl-pos=%s' % (lookupteam, opttype)
        
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to fetch: %s")
            return

        soup = BeautifulSoup(html)

        if opttype == "offense":        
            h4 = soup.find('h4', text="Offensive Depth Chart")
        elif opttype == "defense":
            h4 = soup.find('h4', text="Defensive Depth Chart")
        elif opttype == "special":
            h4 = soup.find('h4', text="Special Teams Depth Chart")
        else:
            irc.reply("Something broke.")
            return

        table = h4.findNext('table').find('tbody')
        rows = table.findAll('tr')

        object_list = []

        for row in rows:
            position = row.find('th', attrs={'class':'title'})
            players = row.findAll('td', attrs={'class':'title'})
    
            d = collections.OrderedDict()
            d['position'] = position.renderContents().strip()
            d['players'] = string.join([item.find('a').text for item in players], " | ")
            object_list.append(d)   

        for N in self._batch(object_list, 3):
            irc.reply(' '.join(str(ircutils.underline(n['position'])) + ":" + " " + str(n['players']) for n in N))   
            
    nfldepthchart = wrap(nfldepthchart, [('somethingWithoutSpaces'), ('somethingWithoutSpaces')])
    
    
    def nflroster(self, irc, msg, args, optlist, optteam, optposition):
        """[team] [position]
        Display roster for team by position. Ex: NE QB.
        Position must be one of: QB, RB, WR, TE, OL, DL, LB, SD, ST
        """

        optteam = optteam.upper()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('yahoo', 'team', optteam)
        
        validpositions = { 'QB':'Quarterbacks', 'RB':'Running Backs', 'ST':'Special Teams' }
        
        if optposition not in postable:
            irc.reply("Position must be one of: %s" % validpositions.keys())
            return
        
        url = self._b64decode('aHR0cDovL3Nwb3J0cy55YWhvby5jb20vbmZsL3RlYW1z') + '/%s/roster' % lookupteam
        
        self.log.info(url)

        try:        
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Could not fetch: %s" % url)
            return

        soup = BeautifulSoup(html)
        tbodys = soup.findAll('tbody')[1:] #skip search header.

        nflroster = collections.defaultdict(list)
        roster_age = []
        roster_exp = []
        roster_weight = []
        roster_height = []

        for tbody in tbodys:
            rows = tbody.findAll('tr')
            for row in rows:
                number = row.find('td')
                playertype = row.findPrevious('h5')
                player = number.findNext('th', attrs={'class':'title'}).findNext('a')
                position = number.findNext('td')
                height = position.findNext('td')
                weight = height.findNext('td')
                age = weight.findNext('td')
                exp = age.findNext('td')
        
                if optnumber:
                    keyString = str(number.getText())
                    appendString = str(player.getText() + " " + position.getText())    
                else:
                    keyString = str(position.getText())
                    appendString = str(number.getText() + ". " + player.getText())
                    roster_age.append(int(age.getText()))
                    roster_exp.append(int(exp.getText().replace('R','0')))
        
                nflroster[keyString].append(appendString)
            
        for i,x in nflroster.iteritems():
            print i,x
        
        averageAge = ("%.2f" % (sum(roster_age) / float(len(roster_age))))
        averageExp = ("%.2f" % (sum(roster_exp) / float(len(roster_exp))))

        print averageAge
        print averageExp
        
    nflroster = wrap(nflroster, [(getopts({'number': ('int')})), ('somethingWithoutSpaces'), ('somethingWithoutSpaces')])


    def nflteamnews(self, irc, msg, args, optteam):
        """Display the most recent news and articles about a team."""

        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('fanfeedr', 'team', optteam) # (db, column, optteam)

        # need ff apikey.
        apiKey = self.registryValue('ffApiKey')
        if not apiKey or apiKey == "Not set":
            irc.reply("API key not set. see 'config help supybot.plugins.NFL.ffApiKey'.")
            return
        
        # construct url
        url = 'http://ffapi.fanfeedr.com/basic/api/teams/%s/content' % lookupteam
        url += '?api_key=%s' % apiKey
        
        self.log.info(url)

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        try:
            jsondata = json.loads(html)
        except:
            irc.reply("Could not parse json data")
            return

        for each in jsondata[0:6]:
            origin = each['origin']['name']
            title = each['title']
            linkurl = each['url']
            output = "{0} - {1} {2}".format(ircutils.underline(origin), self._smart_truncate(title, 40),\
                ircutils.mircColor(linkurl, 'blue'))
            irc.reply(output)

    nflteamnews = wrap(nflteamnews, [('somethingWithoutSpaces')])


    def nflteamtrans(self, irc, msg, args, optteam):
        """[team]
        Shows recent NFL transactions for [team]. Ex: CHI
        """
        
        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('eid', 'team', optteam) 
        
        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL3RlYW10cmFuc2FjdGlvbnM=') + '?teamId=%s&wjb=' % lookupteam

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to load: %s" % url)
            return
        
        html = html.replace('<div class="ind tL"','<div class="ind"').replace('<div class="ind alt"','<div class="ind"')

        soup = BeautifulSoup(html)
        t1 = soup.findAll('div', attrs={'class': 'ind'})

        if len(t1) < 1:
            irc.reply("No transactions found for %s" % optteam)
            return

        for item in t1:
            if "href=" not in str(item):
                trans = item.findAll(text=True)
                irc.reply("{0:8} {1}".format(ircutils.bold(str(trans[0])), str(trans[1])))

    nflteamtrans = wrap(nflteamtrans, [('somethingWithoutSpaces')])

    def nflinjury(self, irc, msg, args, optlist, optteam):
        """<--details> [TEAM]
        Show all injuries for team. Example: NYG or NE. Use --details to 
        display full table with team injuries.
        """
        
        details = False
        for (option, arg) in optlist:
            if option == 'details':
                details = True
        
        optteam = optteam.upper().strip()
        
        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
        
        lookupteam = self._translateTeam('roto', 'team', optteam) 

        url = self._b64decode('aHR0cDovL3d3dy5yb3Rvd29ybGQuY29tL3RlYW1zL2luanVyaWVzL25mbA==') + '/%s/' % lookupteam

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to grab: %s" % url)
            return

        soup = BeautifulSoup(html)
        
        if soup.find('div', attrs={'class': 'player'}):
            team = soup.find('div', attrs={'class': 'player'}).find('a').text
        else:
            irc.reply("No injuries found for: %s" % optteam)
            return
        table = soup.find('table', attrs={'align': 'center', 'width': '600px;'})
        t1 = table.findAll('tr')

        object_list = []

        for row in t1[1:]:
            td = row.findAll('td')
            d = collections.OrderedDict()
            d['name'] = td[0].find('a').text
            d['position'] = td[2].renderContents().strip()
            d['status'] = td[3].renderContents().strip()
            d['date'] = td[4].renderContents().strip().replace("&nbsp;", " ")
            d['injury'] = td[5].renderContents().strip()
            d['returns'] = td[6].renderContents().strip()
            object_list.append(d)

        if len(object_list) < 1:
            irc.reply("No injuries for: %s" % optteam)

        if details:
            irc.reply(ircutils.underline(str(team)) + " - " + str(len(object_list)) + " total injuries")
            irc.reply("{0:25} {1:3} {2:15} {3:<7} {4:<15} {5:<10}".format("Name","POS","Status","Date","Injury","Returns"))

            for inj in object_list:
                output = "{0:27} {1:<3} {2:<15} {3:<7} {4:<15} {5:<10}".format(ircutils.bold( \
                    inj['name']),inj['position'],inj['status'],inj['date'],inj['injury'],inj['returns'])
                irc.reply(output)
        else:
            irc.reply(ircutils.underline(str(team)) + " - " + str(len(object_list)) + " total injuries")
            irc.reply(string.join([item['name'] + " (" + item['returns'] + ")" for item in object_list], " | "))

    nflinjury = wrap(nflinjury, [getopts({'details':''}), ('somethingWithoutSpaces')])

    def nflvaluations(self, irc, msg, args):
        """
        Display current NFL team valuations from Forbes.
        """
        
        url = self._b64decode('aHR0cDovL3d3dy5mb3JiZXMuY29tL25mbC12YWx1YXRpb25zL2xpc3Qv')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to load: %s" % url)
            return
 
        soup = BeautifulSoup(html)
        tbody = soup.find('tbody', attrs={'id':'listbody'})
        rows = tbody.findAll('tr')

        append_list = []

        for row in rows:
            tds = row.findAll('td')
            rank = tds[0].getText()
            team = tds[1].getText()
            value = tds[2].getText().replace(',','') # value needs some mixing and to a float. 
            append_list.append("{0}. {1} ({2})".format(rank, ircutils.bold(team), self._millify(float(value)*(1000000))))
        
        header = ircutils.mircColor("Current NFL Team Values", 'red')
        irc.reply("{0} :: {1}".format(header, " | ".join(append_list)))
              
            
    nflvaluations = wrap(nflvaluations)

    def nflpowerrankings(self, irc, msg, args):
        """
        Display this week's NFL Power Rankings.
        """
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wb3dlcnJhbmtpbmdz')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
            html = html.replace("evenrow", "oddrow")
        except:
            irc.reply("Failed to fetch: %s" % url)
            return

        soup = BeautifulSoup(html)
        updated = soup.find('div', attrs={'class':'date floatleft'}).text.replace('Updated:','- ')
        table = soup.find('table', attrs={'class': 'tablehead'})
        prdate = table.find('td', attrs={'colspan': '5'}).renderContents()
        t1 = table.findAll('tr', attrs={'class': 'oddrow'})

        if len(t1) < 30:
            irc.reply("Failed to parse NFL Power Rankings. Did something break?")
            return

        object_list = []

        for row in t1:
            rowrank = row.find('td', attrs={'class': 'pr-rank'}).renderContents()
            rowteam = row.find('div', attrs={'style': re.compile('^padding.*')}).find('a').text
            rowrecord = row.find('span', attrs={'class': 'pr-record'}).renderContents()
            rowlastweek = row.find('span', attrs={'class': 'pr-last'}).renderContents().replace("Last Week", "prev") 

            d = collections.OrderedDict()
            d['rank'] = int(rowrank)
            d['team'] = self._translateTeam('team', 'short', str(rowteam).strip())
            d['record'] = str(rowrecord).strip()
            d['lastweek'] = str(rowlastweek).strip()
            object_list.append(d)

        if prdate:
            irc.reply(ircutils.mircColor(prdate, 'blue') + " " + updated)

        for N in self._batch(object_list, 8):
            irc.reply(' '.join(str(str(n['rank']) + "." + " " + ircutils.bold(n['team'])) + " (" + n['lastweek'] + ")" for n in N))
        
    nflpowerrankings = wrap(nflpowerrankings)

    def nflschedule(self, irc, msg, args, optlist, optteam):
        """[team]
        Display the last and next five upcoming games for team.
        """
        
        fullSchedule = False
        for (option, arg) in optlist:
            if option == 'full':
                fullSchedule = True
        
        optteam = optteam.upper()
        
        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('yahoo', 'team', optteam) # don't need a check for 0 here because we validate prior.
        
        if fullSchedule: # diff url/method.
            url = self._b64decode('aHR0cDovL3Nwb3J0cy55YWhvby5jb20vbmZsL3RlYW1z') + '/%s/schedule' % lookupteam

            try:
                request = urllib2.Request(url)
                html = (urllib2.urlopen(request)).read()
            except:
                irc.reply("Failed to open: %s" % url)
                return
                
            soup = BeautifulSoup(html)
            table = soup.find('table', attrs={'summary':'Regular Season Games'})
            
            if not table:
                irc.reply("ERROR: Failed to find schedule for: %s") % optteam
                return
                
            tbody = table.find('tbody')
            rows = tbody.findAll('tr')

            append_list = []

            for row in rows:
                tds = row.findAll('td')
                week = tds[0]
                
                if row.find('td', attrs={'class':'title bye'}):
                    date = "BYE"
                    opp = ""
                    score = ""
                    appendString = "W{0}-{1}".format(ircutils.bold(week.getText()), ircutils.underline("BYE"))
                else:
                    date = tds[1].getText()
                    dateSplit = date.split(',', 1) # take the date, dump the rest.
                    date = dateSplit[1]
                    opp = tds[2] # with how the Tag/string comes in, we need to extract one part and format the other.
                    oppName = opp.find('span')
                    if oppName:
                        oppName.extract()
                    oppTeam = opp.find('a').getText() 
                    #opp = tds[2].find('span').getText()
                    #opp = self._translateTeam('team','full', opp) # use the db to make a full team small.
                    score = tds[3].getText().replace('EDT','').replace('EST','').replace('pm','').replace('am','') # strip the garbage
                    #score = score.replace('W', ircutils.mircColor('W', 'green')).replace('L', ircutils.mircColor('L', 'red'))
                    appendString = "W{0}-{1} {2} {3}".format(ircutils.bold(week.getText()), date.strip(), oppTeam.strip(), score.strip())
                
                append_list.append(appendString)

            descstring = string.join([item for item in append_list], " | ")
            output = "{0} SCHED :: {1}".format(ircutils.mircColor(optteam, 'red'), descstring)
            irc.reply(output)
        else:
            url = self._b64decode('aHR0cDovL3Nwb3J0cy55YWhvby5jb20vbmZsL3RlYW1z') + '/%s/calendar/rss.xml' % lookupteam
        
            try:
                req = urllib2.Request(url)
                response = urllib2.urlopen(req)
                html = response.read()
            except:
                irc.reply("Cannot open: %s" % url)
                return

            # clean this stuff up
            html = html.replace('<![CDATA[','').replace(']]>','').replace('EDT','').replace('\xc2\xa0',' ')

            soup = BeautifulSoup(html)
            items = soup.find('channel').findAll('item')
        
            append_list = []

            for item in items:
                title = item.find('title').renderContents().strip() # title is good.
                day, date = title.split(',')
                desc = item.find('description') # everything in desc but its messy.
                desctext = desc.findAll(text=True) # get all text, first, but its in a list.
                descappend = (''.join(desctext).strip()) # list transform into a string.
                if not descappend.startswith('@'): # if something is @, it's before, but vs. otherwise.
                    descappend = 'vs. ' + descappend
                descappend += " [" + date.strip() + "]"
                append_list.append(descappend) # put all into a list.

        
            descstring = string.join([item for item in append_list], " | ")
            output = "{0} {1}".format(ircutils.bold(optteam), descstring)
            irc.reply(output)

    nflschedule = wrap(nflschedule, [(getopts({'full':''})), ('somethingWithoutSpaces')])


    def nfldraft(self, irc, msg, args, optyear, optround):
        """<year> <round>
        Show the NFL draft round from year. Year must be 1996 or after and optional round must be between 1 and 7.
        Defaults to round 1 if round is not given. Ex: nfldraft 2000 6 (Would show the 6th round of the 2000 draft)
        """
        
        if optyear: # if optyear is there, test for valid and if after 2003.
            testdate = self._validate(optyear, '%Y')
            if not testdate:
                irc.reply("Invalid year. Must be YYYY.")
                return
            if optyear < 1996:
                irc.reply("Year must be after 1996.")
                return
                
        if optround:
            if 1 <= optround <= 7:
                irc.reply("Draft round must be 1 or 7.")
                return
        
        url = self._b64decode('aHR0cDovL2luc2lkZXIuZXNwbi5nby5jb20vbmZsL2RyYWZ0L3JvdW5kcw==')

        if optyear: # add year if we have it.
            url += '?year=%s' % (optyear)

        if optround: # optional round.
            url += '&round=%s' % (optround)

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to fetch: %s" % url)
            return

        soup = BeautifulSoup(html)

        # check and make sure we have a table, otherwise error.
        if not soup.find('table', attrs={'class':'tablehead draft-tracker'}): 
            irc.reply("error: could not find any draft information. Bad year or round?")
            return
        else:
            table = soup.find('table', attrs={'class':'tablehead draft-tracker'})
            
        h2 = soup.find('h2')
        rows = table.findAll('tr', attrs={'class': re.compile('^oddrow.*?|^evenrow.*?')})

        object_list = []
               
        for row in rows:
            pickNumber = row.find('p', attrs={'class':'round-number'})
            pickName = row.find('p', attrs={'class':'player-name'})
            pickPos = row.find('li', attrs={'class':'li-position'})
            pickTeam = row.find('p', attrs={'class':'team-name'})
    
            appendString = ircutils.bold(pickNumber.getText()) + ". " + pickName.getText() + " - " + pickTeam.getText()
    
            if row.find('p', attrs={'class':'notes'}):
                appendString += " (" + row.find('p', attrs={'class':'notes'}).getText() + ")"
    
            object_list.append(appendString)            
        
        irc.reply(ircutils.mircColor(h2.getText().strip(), 'red') + ": ") # print header.
        
        for N in self._batch(object_list, 6):
            irc.reply(' | '.join(str(n) for n in N)) 

    nfldraft = wrap(nfldraft, [optional('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])
    
    
    def nfltrades(self, irc, msg, args):
        """
        Display the last NFL 10 trades.
        """
    
        url = self._b64decode('aHR0cDovL3d3dy5zcG90cmFjLmNvbS9uZmwtdHJhZGUtdHJhY2tlci8=')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        soup = BeautifulSoup(html)
        title = soup.find('title')
        table = soup.find('table', attrs={'border':'0'})
        tbodys = table.findAll('tbody')

        object_list = []

        for tbody in tbodys:
            rows = tbody.findAll('tr')
            for row in rows:
                player = row.find('td', attrs={'class':'player'}).find('a')
                data = row.find('span', attrs={'class':'data'})
                date = row.findPrevious('th', attrs={'class':'tracker-date'})
                fromteam = row.findAll('td', attrs={'class':'playerend'})[0].find('img')['src'].replace('http://www.spotrac.com/assets/images/thumb/','').replace('.png','')
                toteam = row.findAll('td', attrs={'class':'playerend'})[1].find('img')['src'].replace('http://www.spotrac.com/assets/images/thumb/','').replace('.png','')
                #print player, data, date, fromteam, toteam
                d = collections.OrderedDict()
                d['player'] = player.renderContents().strip()
                d['date'] = date.renderContents().strip()
                d['data'] = data.renderContents().strip()
                d['fromteam'] = self._translateTeam('team','st',fromteam)
                d['toteam'] = self._translateTeam('team','st',toteam)
                object_list.append(d)
        
        for each in object_list[0:10]:
            output = "{0} - {1} - {2}->{3} :: {4}".format(ircutils.bold(each['date']), ircutils.mircColor(each['player'],'red'), each['fromteam'],each['toteam'],each['data'])
            irc.reply(output)
            
    nfltrades = wrap(nfltrades)
    
    
    def nflarrests(self, irc, msg, args):
        """Display the last 5 NFL Arrests from PFT."""
        
        url = self._b64decode('aHR0cDovL3Byb2Zvb3RiYWxsdGFsay5uYmNzcG9ydHMuY29tL3BvbGljZS1ibG90dGVyLw==')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)

        soup = BeautifulSoup(html)
        
        dayssince = soup.find('div', attrs={'id':'nbcs_blotter-3'}).find('strong').find('a').text
        
        table = soup.find('div', attrs={'class':'post-body clearfix'})
        rows = table.findAll('div')[0:5]

        append_list = []
        
        for row in rows:
            text = row.text.split(':')
            date = text[0].strip()
            arrest = text[1].strip().replace('is arrested',' arrested')
            append_list.append(ircutils.bold(date) + " :: " + arrest)

        irc.reply("%s days since the last arrest." % ircutils.mircColor(dayssince, 'red'))
        
        for each in append_list:
            irc.reply(each)        

    nflarrests = wrap(nflarrests)


    def nflrumors(self, irc, msg, args):
        """
        Display the latest NFL rumors.
        """

        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL3J1bW9ycz93amI9')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Something broke trying to read: %s" % url)
            return

        html = html.replace('<div class="ind alt">', '<div class="ind">')

        soup = BeautifulSoup(html)
        t1 = soup.findAll('div', attrs={'class': 'ind'})

        if len(t1) < 1:
            irc.reply("No NFL rumors found. Check formatting?")
            return

        for t1rumor in t1[0:5]:
            item = t1rumor.find('div', attrs={'class': 'noborder bold tL'}).renderContents()
            item = re.sub('<[^<]+?>', '', item)
            rumor = t1rumor.find('div', attrs={'class': 'inline rumorContent'}).renderContents().replace('\r','')
            irc.reply(ircutils.bold(item) + " :: " + rumor)

    nflrumors = wrap(nflrumors)
    
    
    def nfltotalqbr(self, irc, msg, args, optlist):
        """<--postseason>
        Display the top10 NFL QBs, ranked by Total QBR. Use --postseason to display for postseason. 
        """
        
        postseason = False
        for (option, arg) in optlist:
            if option == 'postseason':
                postseason = True
        
        if postseason:
            url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9xYnIvXy9zZWFzb250eXBlLzM=')
        else:
            url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9xYnI=')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        html = html.replace('tr class="evenrow','tr class="oddrow')

        soup = BeautifulSoup(html)

        title = soup.find('div', attrs={'class':'mod-header stathead'}).find('h4')
        table = soup.find('table', attrs={'class':'tablehead'})
        rows = table.findAll('tr', attrs={'class': re.compile('^oddrow')})[0:10]

        append_list = []

        for row in rows:
            rank = row.find('td', attrs={'align':'left'})
            name = rank.findNext('td').find('a')
            qbr = name.findNext('td', attrs={'class':'sortcell'})
            append_list.append(rank.text + ". " + ircutils.bold(name.text) + " " + qbr.text)

        output = string.join([item for item in append_list], " | ")
        irc.reply(ircutils.mircColor(title.text, 'red') + ": " + output)
        
    nfltotalqbr = wrap(nfltotalqbr, [(getopts({'postseason':''}))])


    def nflcoach(self, irc, msg, args, optteam):
        """[team]
        Display the manager for team. Ex: NYJ
        """

        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return

        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9jb2FjaGVz')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Cannot fetch URL: %s" % url)
            return

        html = html.replace('class="evenrow', 'class="oddrow')

        soup = BeautifulSoup(html)
        rows = soup.findAll('tr', attrs={'class':'oddrow'})

        object_list = []

        for row in rows:
            manager = row.find('td').find('a')
            exp = manager.findNext('td')
            record = exp.findNext('td')
            team = record.findNext('td').find('a')

            d = collections.OrderedDict()
            d['manager'] = manager.renderContents().strip().replace("  "," ") # some of these coach strings are double spaced, for whatever reason.
            d['exp'] = exp.renderContents().strip()
            d['record'] = record.renderContents().strip()
            d['team'] = self._translateTeam('team', 'full', team.renderContents().strip())
            object_list.append(d)

        for each in object_list:
            if each['team'] == optteam:
                output = "The coach of {0} is {1}({2}) with {3} years experience.".format( \
                    ircutils.bold(each['team']), ircutils.bold(each['manager']), each['record'], each['exp'])
                irc.reply(output)

    nflcoach = wrap(nflcoach, [('somethingWithoutSpaces')])
    
    
    def nfldotcomnews(self, irc, msg, args):
        """
        Display the latest headlines from nfl.com
        """
        
        url = self._b64decode('aHR0cDovL3MzLmFtYXpvbmF3cy5jb20vbmZsZ2MvYWxsX25ld3NMaXN0Lmpz')
                    
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to fetch: %s" % url)
            return
        
        try:
            jsondata = json.loads(html)['content']
        except:
            irc.reply("Failed to parse article json from: %s" % url)
            return
        
        for article in jsondata[0:6]:
            title = article.get('title', None)
            desc = article.get('description', None)
            link = article.get('linkURL', None)
            date = article.get('date_ago', None)
            
            output = "{0} - {1}".format(ircutils.bold(title), self._shortenUrl(link))
            irc.reply(output)
    
    nfldotcomnews = wrap(nfldotcomnews)


    # improve matching here?
    def nflplayers(self, irc, msg, args, optplayer):
        """[player]
        Look up NFL players in database.
        """
        
        db_filename = self.registryValue('nflPlayersDb')
        
        if not os.path.exists(db_filename):
            self.log.error("ERROR: I could not find: %s" % db_filename)
            return
            
        db = sqlite3.connect(db_filename)
        cursor = db.cursor()
        
        optplayer = optplayer.lower().strip()

        #cursor.execute("select id from players where name='?'", ([optplayer]))
        
        query = "select id, name from players WHERE name LIKE '%%%s%%'" % optplayer
        cursor.execute(query)
        
        rows = cursor.fetchall()
        
        if len(rows) < 1:
            irc.reply("I did not find anything matching: %s" % optplayer)
            return
        else:
            results = string.join([str(item[1]) + " (" + str(item[0]) + ")" for item in rows], " | ")
            output = "I found {0} results for: {1} :: {2}".format(len(rows), optplayer, results)
            irc.reply(output)
            
    nflplayers = wrap(nflplayers, [('text')])
    
    
    def _playerLookup(self, table, optstring):
        """Return the specific id number[table] for playerstring"""
        
        db_filename = self.registryValue('nflPlayersDb')
        
        if not os.path.exists(db_filename):
            self.log.error("ERROR: I could not find: %s" % db_filename)
            return
            
        db = sqlite3.connect(db_filename)
        cursor = db.cursor()
        query = "select %s from players WHERE id in (select id from aliases WHERE name LIKE ? )" % (table)
        cursor.execute(query, ('%'+optstring+'%',))
        aliasrow = cursor.fetchone()
        self.log.info(str(aliasrow))
        
        if aliasrow is None:
            cursor = db.cursor()
            query = "select %s from players WHERE name LIKE ?" % (table)
            cursor.execute(query, ('%'+optstring+'%',))
            row = cursor.fetchone()
            self.log.info(str(row))
        
            if row is None:
                db.close()
                return "0"
            else:
                db.close()
                return (str(row[0]))
        else:
            db.close()
            return (str(aliasrow[0]))


    def nflgame(self, irc, msg, args, optplayer):
        """[player]
        Display NFL player's game log for current/active game. Ex: Eli Manning
        """
        
        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('eid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wbGF5ZXIvXy9pZA==') + '/%s/' % lookupid
        
        #self.log.info(url)

        try:        
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        if "No statistics available." in html:
            irc.reply("Sorry, no statistics found on the page for: %s" % optplayer.title())
            return
        
        soup = BeautifulSoup(html)
        
        currentGame, previousGame = True, True # booleans for below. 
        h4 = soup.find('h4', text="CURRENT GAME")
        if not h4:
            h4 = soup.find('h4', text="PREVIOUS GAME")
            if not h4: 
                irc.reply("I could not find game statistics for: %s. Player not playing? Also try nflgamelog command." % optplayer.title())
                return
            else:
                previousGame = True
        else:
            currentGame = True

        div = h4.findParent('div').findParent('div')
        gameTime = False
        # <div class="game-details"><div class="venue">Lambeau Field</div><div class="time">Sun, Sept 30<br>Final</div><div class="overview" style="padding-left:90px;"><div class="team team-away"><a href="http://espn.go.com/nfl/team/_/name/no/new-orleans-saints"><div class="logo logo-medium logo-nfl-medium nfl-medium-18"></div></a><div class="record"><h6 style="padding-left:25px;font-size:16px;">27</h6></div></div><div class="symbol">@</div><div class="team team-home"><a href="http://espn.go.com/nfl/team/_/name/gb/green-bay-packers"><div class="logo logo-medium logo-nfl-medium nfl-medium-9"></div></a><div class="record"><h6 style="padding-right:25px;font-size:16px;">28</h6></div></div></div><p class="links"><a href="/nfl/recap?gameId=320930009">Recap »</a><a href="/nfl/boxscore?gameId=320930009">Box&nbsp;Score »</a></p></div>
        #gameTime = div.find('li', attrs={'class':'game-clock'})
        #gameTimeSpan = gameTime.find('span')
        #if gameTimeSpan:
        #    gameTimeSpan.extract()

        table = div.find('table', attrs={'class':'tablehead'})
        header = table.find('tr', attrs={'class':'colhead'}).findAll('th')[1:]
        row = table.findAll('tr')[1].findAll('td')[1:]

        output = string.join([ircutils.bold(each.getText()) + ": " + row[i].getText() for i,each in enumerate(header)], " | ")
        if gameTime:
            irc.reply("{0} :: {1} ({2} ({3}))".format(ircutils.mircColor(optplayer.title(), 'red'), output, gameTime.getText(), gameTimeSpan.getText()))
        else:
            irc.reply("{0} :: {1}".format(ircutils.mircColor(optplayer.title(), 'red'), output))
            
    nflgame = wrap(nflgame, [('text')])


    def nflrotonews(self, irc, msg, args, optplayer):
        """[player]
        Display latest Rotowire news for NFL player.
        """
        
        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('rid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
        
        url = self._b64decode('aHR0cDovL3d3dy5yb3Rvd29ybGQuY29tL3BsYXllci9uZmw=') + '/%s/' % lookupid

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)

        if soup.find('div', attrs={'class':'playerdetails'}):
            playerName = soup.find('div', attrs={'class':'playerdetails'}).find('h1')

        if soup.find('div', attrs={'class':'playerdetails'}):
            playerNews = soup.find('div', attrs={'class':'playernews'})
            playerNews = ' '.join(str(playerNews.getText().replace('&quot;','"')).split()) 
        else:
            playerNews = "No news for player found."
        
        output = "{0} :: {1}".format(ircutils.mircColor(playerName.getText(), 'red'), playerNews)
        
        irc.reply(output)
        
    nflrotonews = wrap(nflrotonews, [('text')])    


    def nflplayernews(self, irc, msg, args, optplayer):
        """[player]
        Display latest news for NFL player.
        """
        
        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('eid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return    
    
        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL3BsYXllcnVwZGF0ZQ==') + '?playerId=%s&wjb=' % lookupid

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        playerName = soup.find('div', attrs={'class':'sub bold'})
        if not playerName:
            irc.reply("I could not find any news. Did formatting change?")
            return

        if soup.find('div', attrs={'class':'ind line'}):
            playerNews = soup.find('div', attrs={'class':'ind line'})
            extraPlayerNews = playerNews.find('div', attrs={'style':'font-style:italic;'})
            if extraPlayerNews: # clean it up.
                extraPlayerNews.extract()
                playerNews = ' '.join(str(self._remove_accents(playerNews.getText())).split()) # for some reason, rotowire has many spaces in its reports.
            else:
                playerNews = "No news found for player"
    
        output = "{0} :: {1}".format(ircutils.mircColor(playerName.getText(), 'red'), playerNews)
        
        irc.reply(output)
    
    nflplayernews = wrap(nflplayernews, [('text')])
   
    
    def nflinfo(self, irc, msg, args, optlist, optplayer):
        """Display basic information on NFL player."""
        
        mobile = False
        for (option, arg) in optlist:
            if option == 'mobile':
                mobile = True
        
        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('eid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
        
        if not mobile: # mobile method, which is an alternative.
        
            url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL3BsYXllcmluZm8=') + '?playerId=%s&wjb=' % lookupid

            try:
                req = urllib2.Request(url)
                html = (urllib2.urlopen(req)).read()
            except:
                irc.reply("Failed to open: %s" % url)
                return

            soup = BeautifulSoup(html)
            team = soup.find('td', attrs={'class':'teamHeader'}).find('b')
            playerName = soup.find('div', attrs={'class':'sub bold'})
            divs = soup.findAll('div', attrs={'class':re.compile('^ind tL$|^ind alt$|^ind$')})

            append_list = []

            for div in divs:
                bold = div.find('b')
                if bold:
                    key = bold        
                    bold.extract()
                    value = div
                    append_list.append(str(key.getText() + ": " + value.getText()))

            descstring = string.join([item for item in append_list], " | ")
            output = "{0} :: {1} :: {2}".format(ircutils.mircColor(playerName.getText(), 'red'),ircutils.bold(team.getText()), descstring)
            
            irc.reply(output)           
                    
        else:
        
            url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wbGF5ZXIvXy9pZA==') + '/%s/' % lookupid
            
            try:        
                req = urllib2.Request(url)
                html = (urllib2.urlopen(req)).read()
            except:
                irc.reply("Failed to open: %s" % url)
                return
            
            html = html.replace('&nbsp;','')

            soup = BeautifulSoup(html)
            playername = soup.find('a', attrs={'class':'btn-split-btn'}).renderContents().strip()
            ul = soup.find('ul', attrs={'class':'general-info'})
            numpos = ul.find('li', attrs={'class':'first'})
            heightw = numpos.findNext('li')
            team = ul.find('li', attrs={'class':'last'}).find('a')
            ul2 = soup.find('ul', attrs={'class':'player-metadata floatleft'})       
            
            bd = ul2.find('li') # and remove span below
            span = bd.find('span') 
            if span:
                span.extract()
            
            bp = bd.findNext('li')
        
            exp = bp.findNext('li') # remove span
            span = exp.find('span') 
            if span:
                span.extract()
                    
            col = exp.findNext('li') # remove span.
            span = col.find('span') 
            if span:
                span.extract()
        
            output = "{0} :: {1} {2}  Bio: {3} {4}  College: {5}".format(ircutils.bold(playername), numpos.text, team.text, bd.text, exp.text, col.text)
            irc.reply(output)
        
    nflinfo = wrap(nflinfo, [(getopts({'mobile':''})), ('text')])
    
    
    def nflcontract(self, irc, msg, args, optplayer):
        """[player]
        Display NFL contract for Player Name. Ex: Ray Lewis
        """

        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('rid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
            
        url = self._b64decode('aHR0cDovL3d3dy5yb3Rvd29ybGQuY29tL3BsYXllci9uZmwv') + '/%s/' % lookupid

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return

        soup = BeautifulSoup(html)
        pn = soup.find('div', attrs={'class':'playercard',  'style':'display:none;', 'id': re.compile('^cont_.*')})

        if not pn:
            irc.reply("No contract found for: %s" % player)
            return

        p1 = pn.find('div', attrs={'class': 'report'}).renderContents().strip()
        h1 = soup.find('h1').renderContents().strip()
        contract = re.sub('<[^<]+?>', '', p1).strip()

        irc.reply(ircutils.mircColor(h1, 'red') + ": " + contract)

    nflcontract = wrap(nflcontract, [('text')])
    
    
    def nflcareerstats(self, irc, msg, args, optplayer):
        """[player]
        Look up NFL career stats for a player. Ex: nflcareerstats tom brady
        """
        
        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('eid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wbGF5ZXIvXy9pZA==') + '/%s/' % lookupid
        
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return

        if "No stats available." in html:
            irc.reply("No stats available for: %s" % optplayer)
            return
    
        soup = BeautifulSoup(html)
        
        if not soup.find('a', attrs={'class':'btn-split-btn'}): # check if player is active.
            irc.reply("Cannot find any career stats for an inactive/unsigned player: %s" % optplayer)
            return
        
        playername = soup.find('a', attrs={'class':'btn-split-btn'}).renderContents().strip()
        div = soup.find('h4', text="STATS").findNext('table', attrs={'class':'tablehead'})
        header = div.find('tr', attrs={'class':'colhead'}).findAll('th')
        row = div.find('td', text="Career").findParent('tr')
        tds = row.findAll('td')

        del header[0],tds[0] # junk parts of career we can delete.

        output = string.join([ircutils.bold(header[i].text) + ": " + td.text for i,td in enumerate(tds)], " | ")        
        irc.reply(ircutils.mircColor(playername, 'red') + " (career) :: " + output)
            
    nflcareerstats = wrap(nflcareerstats, [('text')])
    

    def nflseasonstats(self, irc, msg, args, optyear, optplayer):
        """[year] [player]
        Look up NFL Season stats for a player. Ex: nflplayer 2010 tom brady
        """
        
        if optyear: # check our year. validate below.
            testdate = self._validate(optyear, '%Y')
            if not testdate:
                irc.reply("Invalid year. Must be YYYY.")
                return

        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('eid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wbGF5ZXIvc3RhdHMvXy9pZA==') + '/%s/' % lookupid
        
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        html = html.replace('tr class="evenrow','tr class="oddrow')

        if "No stats available." in html:
            irc.reply("No stats available for: %s" % optplayer)
            return
    
        soup = BeautifulSoup(html)
        
        if not soup.find('a', attrs={'class':'btn-split-btn'}): # check if player is active.
            irc.reply("Cannot find any season stats for an inactive/unsigned player: %s" % optplayer)
            return
        
        playername = soup.find('a', attrs={'class':'btn-split-btn'}).renderContents().strip()
        table = soup.find('table', attrs={'class':'tablehead'}) # first table.
        headings = table.findAll('tr', attrs={'class':'colhead'})
        rows = table.findAll('tr', attrs={'class': re.compile('^oddrow')})

        seasonlist = [str(i.find('td').string) for i in rows] # cheap list to find the index for a year.

        if optyear in seasonlist:
            yearindex = seasonlist.index(optyear)
        else:
            irc.reply("No season stats found for: %s in %s" % (optplayer, optyear))
            return
            
        heading = headings[0].findAll('td') # first table, first row is the heading.
        row = rows[yearindex].findAll('td') # the year comes with the index number, which we find above.

        output = string.join([ircutils.bold(each.text) + ": " + row[i].text for i,each in enumerate(heading)], " | ")
        irc.reply(ircutils.mircColor(playername, 'red') + " :: " + output)
            
    nflseasonstats = wrap(nflseasonstats, [('somethingWithoutSpaces'), ('text')])
    
    
    def nfltrans(self, irc, msg, args, optdate):
        """[YYYYmmDD]
        Display all NFL transactions. Will only display today's. Use date in format: 20120912
        """

        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL3RyYW5zYWN0aW9ucz93amI9')

        if optdate:
            try:
                #time.strptime(optdate, '%Y%m%d') # test for valid date
                datetime.datetime.strptime(optdate, '%Y%m%d')
            except:
                irc.reply("ERROR: Date format must be in YYYYMMDD. Ex: 20120714")
                return
        else:
            now = datetime.datetime.now()
            optdate = now.strftime("%Y%m%d")

        url += '&date=%s' % optdate

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Something broke trying to read: %s" % url)
            return
            
        if "No transactions today." in html:
            irc.reply("No transactions for: %s" % optdate)
            return

        soup = BeautifulSoup(html)
        t1 = soup.findAll('div', attrs={'class': 'ind alt'})
        t1 += soup.findAll('div', attrs={'class': 'ind'})

        out_array = []

        for trans in t1:
            if "<a href=" not in trans: # no links
                match1 = re.search(r'<b>(.*?)</b><br />(.*?)</div>', str(trans), re.I|re.S) #strip out team and transaction
                if match1:
                    team = match1.group(1) 
                    transaction = match1.group(2) 
                    team = self._translateTeam('team', 'full', str(team)) # use team ABBR.
                    output = ircutils.mircColor(team, 'red') + " - " + transaction
                    out_array.append(output)

        if len(out_array) > 0:
            for output in out_array:
                irc.reply(output)
        else:
            irc.reply("Did something break?")
            return
    
    nfltrans = wrap(nfltrans, [optional('somethingWithoutSpaces')])

Class = NFL


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
