# -*- coding: utf-8 -*-
###
# Copyright (c) 2012, spline
# All rights reserved.
#
#
###

# my libs.
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
    
    def _red(self, string):
        """Returns a red string."""
        return ircutils.mircColor(string, 'red')
    
    def _green(self, string):
        """Returns a green string."""
        return ircutils.mircColor(string, 'green')

    def _blue(self, string):
        """Returns a blue string."""
        return ircutils.mircColor(string, 'blue')
        
    def _bold(self, string):
        """Returns a bold string."""
        return ircutils.bold(string)
            
    def _batch(self, iterable, size):
        """http://code.activestate.com/recipes/303279/#c7"""
        c = count()
        for k, g in groupby(iterable, lambda x:c.next()//size):
            yield g
            
    def _validate(self, date, format):
        """Return true or false for valid date based on format."""
        try:
            datetime.datetime.strptime(str(date), format) # format = "%m/%d/%Y"
            return True
        except ValueError:
            return False

    def _remove_accents(self, data):
        """
        Unicode normalize for news.
        """

        nkfd_form = unicodedata.normalize('NFKD', unicode(data))
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

    def _b64decode(self, string):
        """
        Returns base64 encoded string.
        """
        
        import base64
        return base64.b64decode(string)

    def _int_to_roman(self, i):
        """
        Returns a string containing the roman numeral from a number.
        """
        
        numeral_map = zip((1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
            ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I'))
        result = []
        for integer, numeral in numeral_map:
            count = int(i / integer)
            result.append(numeral * count)
            i -= integer * count
        return ''.join(result)

    def _smart_truncate(self, text, length, suffix='...'):
        """
        Truncates `text`, on a word boundary, as close to the target length it can come.
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
        """
        Turns a number like 1,000,000 into 1M.
        """
        
        for x in ['','k','M','B','T']:
            if num < 1000.0:
                return "%3.3f%s" % (num, x)
            num /= 1000.0

    def _shortenUrl(self, url):
        """
        Tiny's a url using google's API (goo.gl).
        """
        
        posturi = "https://www.googleapis.com/urlshortener/v1/url"
        headers = {'Content-Type' : 'application/json'}
        data = {'longUrl' : url}

        data = json.dumps(data)
        request = urllib2.Request(posturi,data,headers)
        response = urllib2.urlopen(request)
        response_data = response.read()
        shorturi = json.loads(response_data)['id']
        return shorturi

    ######################
    # DATABASE FUNCTIONS #
    ######################

    def _validteams(self, conf=None, div=None):
        """
        Returns a list of valid teams for input verification.
        """
        
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
        """
        Returns a list of valid teams for input verification.
        """
        
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
        """<year>
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
        if not soup.find('h2', text="Award Winners"):
            irc.reply("Could not find NFL Awards for the %s season. Perhaps formatting changed or you are asking for the current season in-progress." % optyear)
            return
        
        table = soup.find('h2', text="Award Winners").findParent('div', attrs={'id':'awards'}).find('table')            
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
        """<number>
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
        """<team>
        Display most recent practice report for team. Ex: NE.
        """
        
        optteam = optteam.upper()

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
        """<team>
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

    
    def nflgamelog(self, irc, msg, args, optlist, optplayer):
        """[--game #] <player>
        Display gamelogs from previous # of games. Ex: Tom Brady
        """

        lookupid = self._playerLookup('eid', optplayer.lower())
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wbGF5ZXIvZ2FtZWxvZy9fL2lk') + '/%s/' % lookupid
        
        # handle getopts
        optgames = "1"
        if optlist:
            for (key, value) in optlist:
                if key == 'year': # year, test, optdate if true
                    testdate = self._validate(value, '%Y')
                    if not testdate:
                        irc.reply("Invalid year. Must be YYYY.")
                        return
                    else:
                        url += 'year/%s' % value
                if key == 'games': # how many games?
                    optgames = value

        # now do the http fetching.
        #self.log.info(url)                    
        try:
            request = urllib2.Request(url)
            html = (urllib2.urlopen(request)).read()
        except:
            irc.reply("Failed to load: %s" % url)
            return
        
        # process html, with some error checking.
        soup = BeautifulSoup(html)
        div = soup.find('div', attrs={'class':'mod-container mod-table mod-player-stats'})
        if not div:
            irc.reply("Something broke loading the gamelog. Player might have no stats or gamelog due to position.")
            return
        table = div.find('table', attrs={'class':'tablehead'})
        if not table:
            irc.reply("Something broke loading the gamelog. Player might have no stats or gamelog due to position.")
            return
        stathead = table.find('tr', attrs={'class':'stathead'}).findAll('td')
        header = table.find('tr', attrs={'class':'colhead'}).findAll('td')
        rows = table.findAll('tr', attrs={'class': re.compile('^oddrow.*?|^evenrow.*?')})        
        selectedyear = soup.find('select', attrs={'class':'tablesm'}).find('option', attrs={'selected':'selected'})
        # last check before we process the data.
        if len(rows) < 1 or len(header) < 1 or len(stathead) < 1:
            irc.reply("ERROR: I did not find any gamelog data for: %s (Check formatting on gamelog page)." % optplayer)
            return
                
        # now, lets get to processing the data      
        # this is messy but the only way I thought to handle the colspan situation.
        # below, we make a list and iterate in order over stathead tds.
        # statheadlist uses enum to insert, in order found (since the dict gets reordered if you don't)
        # each entry in statheadlist is a dict of colspan:heading, like:
        # {0: {'3': '2012 REGULAR SEASON GAME LOG'}, 1: {'10': 'PASSING'}, 2: {'5': 'RUSHING'}}
        statheaddict = {}
        for e,blah in enumerate(stathead):
            tmpdict = {}
            tmpdict[str(blah['colspan'])] = str(blah.text)
            statheaddict[int(e)] = tmpdict
        # now, we have the statheadlist, create statheadlist to be the list of
        # each header[i] colspan element, where you can use its index value to ref.
        # so, if header[i] = QBR, the "parent" td colspan is PASSING.
        # ex: ['2012 REGULAR SEASON GAME LOG', '2012 REGULAR SEASON GAME LOG', 
        # '2012 REGULAR SEASON GAME LOG', 'PASSING', 'PASSING', ... 'RUSHING'
        statheadlist = []
        for q,x in sorted(statheaddict.items()): # sorted dict, x is the "dict" inside.
            for k,v in x.items(): # key = colspan, v = the td parent header
                for each in range(int(k)): # range the number to insert.
                    # do some replacement (truncating) because we use this in output.
                    v = v.replace('PASSING','PASS').replace('RUSHING','RUSH').replace('PUNTING','PUNT')
                    v = v.replace('RECEIVING','REC').replace('FUMBLES','FUM').replace('TACKLES','TACK')
                    v = v.replace('INTERCEPTIONS','INT').replace('FIELD GOALS','FG').replace('PATS','XP')
                    v = v.replace('PUNTING','PUNT-')
                    statheadlist.append(v)

        # now, we put all of the data into a data structure
        gamelist = {} # gamelist dict. one game per entry. 
        for i,row in enumerate(rows): # go through each row and extract, mate with header.
            d = collections.OrderedDict() # everything in an OD for calc/sort later.
            tds = row.findAll('td') # all td in each row.
            d['WEEK'] = str(i+1) # add in the week but +1 for human reference later.
            for f,td in enumerate(tds): # within each round, there are tds w/data.
                if f > 2: # the first three will be game log parts, so append statheadlist from above.
                    if str(statheadlist[f]) == str(header[f].getText()): # check if key is there like INT so we don't double include
                        d[str(header[f].getText())] = str(td.getText()) # this will just look normal like XPM or INT
                    else: # regular "addtiion" where it is something like FUM-FF
                        d[str(statheadlist[f] + "-" + header[f].getText())] = str(td.getText())
                else: # td entries 2 and under like DATE, OPP, RESULT
                    d[str(header[f].getText())] = str(td.getText()) # inject all into the OD.
            gamelist[int(i)] = d # finally, each game and its data in OD now injected into object_list.
                
        # now, finally, output what we have.
        outputgame = gamelist.get(int(optgames), 'None')
        
        # handle finding the game or not for output.
        if not outputgame:
            irc.reply("ERROR: I did not find game number {0} in {1}. I did find:".format(optgames, selectedyear.getText()))
            return
        else: # we did find an outputgame, so go out.
            output = ""
            for k, v in outputgame.items():
                output += "{0}: {1} | ".format(ircutils.bold(k), v)
        
            irc.reply(output)
                     
    nflgamelog = wrap(nflgamelog, [getopts({'year':('somethingWithoutSpaces'),
                                            'games':('somethingWithoutSpaces')}), ('text')])


    def nflprobowl(self, irc, msg, args, optyear):
        """<year>
        Display NFL Pro Bowlers for a year. Ex: 2011. 
        """
        
        # must test the date.
        testdate = self._validate(str(optyear), '%Y')
        if not testdate:
            irc.reply("Invalid year. Must be YYYY.")
            return
        if int(optyear) < 1950:
            irc.reply("Year must be 1950 or after.")
            return
        
        url = self._b64decode('aHR0cDovL3d3dy5wcm8tZm9vdGJhbGwtcmVmZXJlbmNlLmNvbS95ZWFycw==') + '/%s/probowl.htm' % optyear
        
        # url time.
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        # process html    
        soup = BeautifulSoup(html)
        h1 = soup.find('h1')
        if not soup.find('table', attrs={'id':'pro_bowl'}): # one last sanity check
            irc.reply("Something broke trying to read probowl data page. Did you try and check the current year before the roster is out?")
            return
        table = soup.find('table', attrs={'id':'pro_bowl'}).find('tbody')
        rows = table.findAll('tr', attrs={'class':''})
        
        # setup containers
        teams = {}
        positions = {}
        players = []

        # process each player.
        for row in rows:
            tds = row.findAll('td')
            pos = str(tds[0].getText())
            player = str(tds[1].getText())
            tm = str(tds[2].getText())
            teams[tm] = teams.get(tm, 0) + 1 # to count teams
            positions[pos] = positions.get(pos, 0) + 1 # to count positions
            players.append("{0}, {1} ({2})".format(ircutils.bold(player), tm, pos)) # append player to list

        # now output.
        # we display the heading, total teams (len) and use teams, sorted in rev, top10.
        irc.reply("{0} :: Total Players: {1} - Total Teams: {2} - Top Teams: {3}".format(\
            self._red(h1.getText()), ircutils.underline(len(players)), ircutils.underline(len(teams)),\
                [k + ": " + str(v) for (k,v) in sorted(teams.items(),\
                    key=lambda x: x[1], reverse=True)[0:10]]))
        
        irc.reply("{0}".format(" | ".join(players)))
           
    nflprobowl = wrap(nflprobowl, [('int')])

    
    def nflfines(self, irc, msg, args, optlist):
        """[--num #]
        Display latest NFL fines. Use --num # to display more than 3. Ex: --num 5
        """

        # handle optlist/optnumber
        optnumber = '5'
        if optlist:
            for (key, value) in optlist:
                if key == 'num': # between 1 and 10, go to 5 
                    if value < 1 or value > 10:
                        optnumber = '5'
                    else:
                        optnumber = value

        url = self._b64decode('aHR0cDovL3d3dy5qdXN0ZmluZXMuY29t')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        # process html. little error checking.
        soup = BeautifulSoup(html)        
        heading = soup.find('div', attrs={'class':'title1'})
        div = soup.find('div', attrs={'class':'standing'})
        table = div.find('table')
        rows = table.findAll('tr', attrs={'class':'data'})
        totalfines = len(rows)

        append_list = []

        for row in rows:
            tds = row.findAll('td')
            date = tds[0]
            # team = tds[2] # team is broken due to html comments
            player = tds[3]
            fine = tds[4]
            reason = tds[5]
            append_list.append("{0} {1} {2} :: {3}".format(date.getText(),\
                ircutils.bold(player.getText()), fine.getText(), reason.getText()))   
        
        for i,each in enumerate(append_list[0:int(optnumber)]):
            if i is 0: # only for header row.
                irc.reply("Latest {0} :: Total {1} Fines.".format(heading.getText(), totalfines))
                irc.reply(each)
            else:
                irc.reply(each)
                
    nflfines = wrap(nflfines, [getopts({'num':('int')})])
    
    
    def nflweeklyleaders(self, irc, msg, args):
        """
        Display weekly NFL Leaders in various categories.
        """
    
        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL2xlYWRlcnM/d2pi')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        # parse html
        html = html.replace('&nbsp;','')
        soup = BeautifulSoup(html)
        tables = soup.findAll('table', attrs={'class':'table'})
        subheading = soup.find('div', attrs={'class':'sub dark'})
        subheadingextract = subheading.a.extract() # remove the junk - might be buggy. 

        # one small sanity check.
        if len(tables) < 1:
            irc.reply("Something broke parsing weekly leaders.")
            return

        weeklyleaders = collections.defaultdict(list)

        # parse each table, which is a stat category.
        for table in tables:
            rows = table.findAll('tr') # all rows, first one, below, is the heading
            heading = rows[0].find('td', attrs={'class':'sec row', 'width':'65%'})
            append_list = [] # container per list
            for i,row in enumerate(rows[1:]): # rest of the rows, who are leaders.
                tds = row.findAll('td')
                rnk = tds[0]
                player = tds[1]
                stat = tds[2] # +1 the count so it looks normal, bold player/team and append.
                append_list.append("{0}. {1} ({2})".format(i+1, ircutils.bold(player.getText()), stat.getText()))
            # one we have everything in the string, append, so we can move into the next category.
            weeklyleaders[str(heading.getText())] = append_list

        # output time.
        for i,x in weeklyleaders.items():
            irc.reply("{0} {1} :: {2}".format(self._red(i), self._red(subheading.getText())," ".join(x)))
    
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

        positions = ['center','guard','tackle','tight-end','wide-receiver','fullback',\
            'running-back', 'quarterback', 'defensive-end', 'defensive-tackle', 'linebacker',\
             'cornerback', 'safety', 'kicker', 'punter', 'kick-returner', 'long-snapper']

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
        
        try:
            request = urllib2.Request(url, params, headers)
            html = (urllib2.urlopen(request)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
        
        # process html.
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
        
        # now output
        irc.reply("{0}: {1}".format(title, descstring))
            
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
    
    
    def nflteamdraftpicks(self, irc, msg, args, optteam):
        """<team>
        Display total NFL draft picks for a team and what round.
        """
        
        optteam = optteam.upper()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
        
        url = self._b64decode('aHR0cDovL3d3dy5mZnRvb2xib3guY29tL25mbF9kcmFmdA==') + '/' + str(datetime.datetime.now().year) + '/nfl_draft_order_full.cfm'
        
        try:
            request = urllib2.Request(url)
            html = (urllib2.urlopen(request)).read()
        except:
            irc.reply("Failed to open url: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        if not soup.find('div', attrs={'id':'content_nosky'}):
            irc.reply("Something broke on formatting.")
            return
            
        div = soup.find('div', attrs={'id':'content_nosky'})
        h1 = div.find('h1', attrs={'class':'newpagetitle'}).getText()
        table = div.find('table', attrs={'class':'fulldraftorder'})
        rows = table.findAll('tr')[1:] # skip the first row.

        nflteampicks = collections.defaultdict(list)

        for row in rows:
            tds = row.findAll('td')
            team = tds[0].getText().strip().replace('WAS','WSH') # again a hack for people using WAS instead of WSH.
            numofpicks = tds[1].getText().strip()
            pickrounds = tds[2].getText().strip()
            appendString = "{0} {1} {1} {2}".format(ircutils.bold("Total:"),numofpicks,ircutils.bold("Picks:"),pickrounds)
            nflteampicks[str(team)].append(appendString)

        # get the team
        output = nflteampicks.get(optteam, None)
        
        # finally output
        if not output:
            irc.reply("Team not found. Something break?")
            return
        else:
            irc.reply("{0} :: {1} :: {2}".format(ircutils.mircColor(h1, 'red'), ircutils.bold(optteam), "".join(output)))

        
    nflteamdraftpicks = wrap(nflteamdraftpicks, [('somethingWithoutSpaces')])
    
    
    def nfldraftorder(self, irc, msg, args, optlist):
        """[--round #]
        Display current NFL Draft order for next year's draft.
        Will default to display the first round. Use --round # to display another (1-7)
        """
        
        optround = "1" # by default, show round 1.
        
        # handle getopts.
        if optlist:
            for key, value in optlist:
                if key == 'round':
                    if value > 7 or value < 1:
                        irc.reply("ERROR: Round must be between 1-7")
                        return
                    else:
                        optround = value
        
        url = self._b64decode('aHR0cDovL3d3dy5mZnRvb2xib3guY29tL25mbF9kcmFmdA==') + '/' + str(datetime.datetime.now().year) + '/nfl_draft_order.cfm'
        
        try:
            request = urllib2.Request(url)
            html = (urllib2.urlopen(request)).read()
        except:
            irc.reply("Failed to open url: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        
        # minor error checking
        if not soup.find('div', attrs={'id':'content'}):
            irc.reply("Something broke in formatting on the NFL Draft order page.")
            return  
        
        # now process html
        div = soup.find('div', attrs={'id':'content'})
        h1 = div.find('h1', attrs={'class':'newpagetitle'}).getText() 
        optround = "Round %s" % (optround) # create "optround" total hack but works.
        round = div.find('h2', text=optround).findNext('ol') # ol container, found by text.
        rows = round.findAll('li') # each li has an a w/the team.
        
        append_list = []

        # go through each and append to list. This is ugly but it works. 
        for i,row in enumerate(rows):
            rowtext = row.find('a')
            if rowtext:
                rowtext.extract()
                rowtext = rowtext.getText().strip().replace('New York','NY') # ugly spaces + wrong NY.
                rowtext = self._translateTeam('team', 'draft', rowtext) # shorten teams.
            
            # now, handle appending differently depending on what's left in row after extract()
            if len(row.getText().strip()) > 0: # handle if row has more after (for a trade)
                append_list.append("{0}. {1} {2}".format(i+1,rowtext, row.getText().strip())) # +1 since it starts at 0.
            else: # most of the time, it'll be empty.
                append_list.append("{0}. {1}".format(i+1,rowtext))
                
        # now output
        irc.reply("{0} :: {1} :: {2}".format(ircutils.mircColor(h1, 'red'),optround," ".join(append_list)))
        
    nfldraftorder = wrap(nfldraftorder, [getopts({'round': ('int')})])


    def nflplayoffs(self, irc, msg, args):
        """
        Display the current NFL playoff match-ups if the season ended today.
        """

        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9zdGFuZGluZ3MvXy90eXBlL3BsYXlvZmZzL3NvcnQvY29uZmVyZW5jZVJhbmsvb3JkZXIvZmFsc2U=')

        try:
            request = urllib2.Request(url)
            html = (urllib2.urlopen(request)).read()
        except:
            irc.reply("Failed to open url: %s" % url)
            return
            
        soup = BeautifulSoup(html)
        
        if not soup.find('table', attrs={'class':'tablehead', 'cellpadding':'3'}):
            irc.reply("Failed to find table for parsing.")
            return

        table = soup.find('table', attrs={'class':'tablehead', 'cellpadding':'3'})
        rows = table.findAll('tr', attrs={'class': re.compile('^oddrow.*?|^evenrow.*?')}) 

        nflplayoffs = collections.defaultdict(list)

        for row in rows: # now build the list. table has rows with the order. we work with 1-6 below when outputting.
            conf = row.findPrevious('tr', attrs={'class':'stathead'}).find('td', attrs={'colspan':'13'})
            conf = str(conf.getText().replace('National Football Conference','NFC').replace('American Football Conference','AFC'))
            
            tds = row.findAll('td') # now get td in each row for making into the list
            rank = tds[0].getText()
            team = tds[1].getText().replace('z -', '').replace('y -', '').replace('x -', '').replace('* -','') # short.
            #self.log.info(str(team))
            #team = self._translateTeam('team', 'short', team)
            reason = tds[10].getText()
            appendString = "{0}".format(self._bold(team.strip()))
            nflplayoffs[conf].append(appendString)

        for i,x in nflplayoffs.iteritems():
            matchups = "{6} :: BYES: {4} and {5} | WC: {3} @ {0} & {2} @ {1} | In the Hunt: {7} & {8}".format(\
                x[2], x[3], x[4], x[5], x[0], x[1], self._red(i), x[6], x[7])
            irc.reply(matchups)

    nflplayoffs = wrap(nflplayoffs)


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

    def nflpowerrankings(self, irc, msg, args, optteam):
        """[team]
        Display this week's NFL Power Rankings.
        Optional: use [team] to display specific commentary. Ex: ATL
        """
        
        if optteam: # if we have a team, check if its valid.
                optteam = optteam.upper()
                if optteam not in self._validteams():
                    irc.reply("Team not found. Must be one of: %s" % self._validteams())
                    return
            
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wb3dlcnJhbmtpbmdz')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to fetch: %s" % url)
            return

        # process HTML
        soup = BeautifulSoup(html)
        if not soup.find('table', attrs={'class':'tablehead'}):
            irc.reply("Something broke heavily formatting on powerrankings page.")
            return
        
        # go about regular html business.
        datehead = soup.find('div', attrs={'class':'date floatleft'})
        table = soup.find('table', attrs={'class':'tablehead'})
        headline = table.find('tr', attrs={'class':'stathead'}) 
        rows = table.findAll('tr', attrs={'class':re.compile('^oddrow|^evenrow')})

        powerrankings = [] # list to hold each one.
        prtable = {}

        for row in rows: # one row per team.
            teamdict = {} # teamdict to put into powerrankings list
            tds = row.findAll('td') # findall tds.
            rank = tds[0].getText() # rank #
            team = tds[1].find('div', attrs={'style':'padding:10px 0;'}).find('a').getText() # finds short.
            shortteam = self._translateTeam('team', 'short', str(team)) # small abbreviation via the db.
            lastweek = tds[2].find('span', attrs={'class':'pr-last'}).getText().replace('Last Week:','').strip() # rank #
            comment = tds[3].getText() # comment.
            # check if we're up or down and insert a symbol.
            if int(rank) < int(lastweek):
                symbol = self._green('▲')
            elif int(rank) > int(lastweek):
                symbol = self._red('▼')
            else: # - if the same.
                symbol = "-"

            # now add the rows to our data structures.
            powerrankings.append("{0}. {1} (prev: {2} {3})".format(rank,shortteam,symbol,lastweek))
            prtable[str(shortteam)] = "{0}. {1} (prev: {2} {3}) {4}".format(rank,team,symbol,lastweek,comment)
        
        # now output. conditional if we have the team or not.
        if not optteam: # no team so output the list.
            irc.reply("{0} :: {1}".format(self._blue(headline.getText()), datehead.getText()))            
            for N in self._batch(powerrankings, 12): # iterate through each team. 12 per line
                irc.reply("{0}".format(string.join([item for item in N], " | ")))
        else: # find the team and only output that team.
            output = prtable.get(str(optteam), None)
            if not output:
                irc.reply("I could not find: %s - Something must have gone wrong." % optteam)
                return
            else:
                irc.reply("{0} :: {1}".format(self._blue(headline.getText()), datehead.getText()))
                irc.reply("{0}".format(output))
                
    nflpowerrankings = wrap(nflpowerrankings, [optional('somethingWithoutSpaces')])


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
        
        optplayer = optplayer.lower()

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

        optplayer = optplayer.lower()
        
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
            irc.reply("No contract found for: %s" % optplayer)
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
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wbGF5ZXIvc3RhdHMvXy9pZA==') + '/%s/' % lookupid
        
        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return

        if "No stats available." in html:
            irc.reply("No stats available for: %s" % optplayer)
            return
    
        soup = BeautifulSoup(html,convertEntities=BeautifulSoup.HTML_ENTITIES)
        if not soup.find('a', attrs={'class':'btn-split-btn'}): # check if player is active.
            irc.reply("Cannot find any career stats for an inactive/unsigned player: %s" % optplayer)
            return
        # experience.
        exp = soup.find('span', text="Experience")
        if exp: 
            exp = exp.findParent('li')
            exp.span.extract()
        # position
        pos = soup.find('ul', attrs={'class':'general-info'}).find('li',attrs={'class':'first'}).getText().upper()
        pos = ''.join([eachLetter for eachLetter in pos if eachLetter.isalpha()])
        # basics.
        playername = soup.find('a', attrs={'class':'btn-split-btn'}).getText().strip()
        article = soup.find('div', attrs={'class':'article'})
        divs = article.findAll('table', attrs={'class':'tablehead'}) # each one.

        # what to look for with each position
        postostats = {
            'QB':['passing','rushing'],
            'RB':['rushing','receiving'],
            'FB':['rushing','receiving'],
            'WR':['receiving','rushing'],
            'TE':['receiving','rushing'],
            'DE':['defensive'],
            'DT':['defensive'],
            'LB':['defensive'],
            'CB':['defensive'],
            'S':['defensive'],
            'PK':['kicking'],
            'P':['punting']
        }

        # prepare dicts for output
        stats = {} # holds the actual stats
        statcategories = {} # holds the categories.

        # expanded careerstats. 
        for f,div in enumerate(divs):
            if div.find('tr', attrs={'class':'colhead'}):
                if not div.find('tr', attrs={'class':'total'}, text="There are no stats available."):
                    stathead = div.find('tr', attrs={'class':'stathead'})
                    colhead = div.find('tr', attrs={'class':'colhead'}).findAll('td')[1:]     
                    totals = div.find('tr', attrs={'class':'total'}).findAll('td')[1:]
                    tmplist = []
                    for i,total in enumerate(totals):
                        tmplist.append(ircutils.bold(colhead[i+1].getText())+": "+total.getText())
                    stats[int(f)] = tmplist
                    statcategories[str(stathead.getText().replace('Stats','').strip().lower())] = f
        
        # now output.
        output = []
        if postostats.has_key(pos): # if we want specific stats.
            for each in postostats[pos]:
                if statcategories.has_key(each):
                    output.append("{0}: {1}".format(ircutils.underline(each.title()), " | ".join(stats.get(statcategories[each]))))
        else:
            output.append("No stats for the {0} position.".format(pos))
        
        irc.reply("{0}({1} exp) career stats :: {2}".format(self._red(playername),exp.getText()," || ".join(output)))
            
    nflcareerstats = wrap(nflcareerstats, [('text')])
    
    
    def nflseason(self, irc, msg, args, optlist, optplayer):
        """<--year DDDD> [player]
        Look up NFL Season stats for a player. Ex: nflseason tom brady.
        To look up a different year, use --year YYYY. Ex: nflseason --year 2010 tom brady
        """
        
        season = False
        
        if optlist:
            for (key,value) in optlist:
                if key == 'year': # check our year. validate below.
                    season = self._validate(str(value), '%Y')
                    if not season:
                        irc.reply("%s is an invalid year. Must be YYYY." % value)
                        return
                    else:
                        season = str(value)
        
        if not season:
            # Season stats do not appear until after the first week of games, which is always going to be first weekend in September
            # So, we account for this using September 9 of each year as the time to use the current year, otherwise, subtract 1 year.
            if datetime.datetime.now().month < 9 and datetime.datetime.now().day < 9:
                season = str(datetime.datetime.now().year - 1)
            else:
                season = str(datetime.datetime.now().year)            

        # now, handle the rest.
        optplayer = optplayer.lower()
        
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

        if season in seasonlist:
            yearindex = seasonlist.index(season)
        else:
            irc.reply("No season stats found for: %s in %s" % (optplayer, season))
            return
            
        heading = headings[0].findAll('td') # first table, first row is the heading.
        row = rows[yearindex].findAll('td') # the year comes with the index number, which we find above.

        output = string.join([ircutils.bold(each.text) + ": " + row[i].text for i,each in enumerate(heading)], " | ")
        irc.reply(ircutils.mircColor(playername, 'red') + " :: " + output)

    nflseason = wrap(nflseason, [(getopts({'year': ('int')})), ('text')])
    
    
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
