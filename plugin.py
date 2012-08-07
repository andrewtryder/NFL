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

    def _b64decode(self, string):
        """Returns base64 encoded string."""
        import base64
        return base64.b64decode(string)

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
                return "%3.1f%s" % (num, x)
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
    
    def nflffdraftresults(self, irc, msg, args, opttype):
        """<QB | TQB | RB | WR | TE | DT | DE | LB | CB | S | D/ST | K | P | HC | ALL>
        Displays the average position players were selected by team owners in Fantasy Football online drafts.
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
            append_list.append(rank.getText() + ". " + player.getText() + " (" + avgpick.getText() + ")")

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
    
        
    def nflleagueleaders(self, irc, msg, args, optcategory, optyear):
        """[category] <YYYY>
        Display the NFL league leaders for a specific category. Use year, 2003-present, to
        display a season other than current.
        """
        
        category = {    'passingyards':'passingYards', 'passingtds':'passingTouchdowns', 'qbr':'quarterbackRating',
                        'rushingyards':'rushingYards', 'rushtd':'rushingTouchdowns', 'rec':'receptions',
                        'recyards':'receivingYards', 'rectds':'receivingTouchdowns', 'tackles':'totalTackles',
                        'sacks':'sacks', 'int':'interceptions', 'kickpoints':'totalPoints' }
        
        optcategory = optcategory.lower()
        
        if optcategory not in category:
            irc.reply("Category must be one of: %s" % category.keys())
            return
        
        url = self._b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL2xlYWd1ZWxlYWRlcnM=') + '?category=%s&groupId=9' % (category[optcategory])
        
        if optyear: 
            testdate = self._validate(optyear, '%Y')
            if not testdate:
                irc.reply("Invalid year. Must be YYYY.")
                return
            if int(optyear) < 2003:
                irc.reply("Year must be 2003 or after.")
                return
            
            url += '&season=%s&wjb=' % optyear
        else:
            url += '&wjb='    
        
        try:        
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to open: %s" % url)
            return
            
        html = html.replace('class="ind alt nw"', 'class="ind nw"')
        
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'class':'table'})
        rows = table.findAll('tr')

        append_list = []
        
        for row in rows[1:6]:
            rank = row.find('td', attrs={'class':'ind nw', 'nowrap':'nowrap', 'width':'10%'}).renderContents()
            team = row.find('td', attrs={'class':'ind nw', 'nowrap':'nowrap', 'width':'70%'}).find('a').text
            num = row.find('td', attrs={'class':'ind nw', 'nowrap':'nowrap', 'width':'20%'}).renderContents()
            append_list.append(rank + ". " + team + " " + num)

        thelist = string.join([item for item in append_list], " | ")
        
        irc.reply("Leaders in %s: %s" % (ircutils.bold(category[optcategory]), thelist))

    nflleagueleaders = wrap(nflleagueleaders, [('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])
    

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
    
    
    def nflweek(self, irc, msg, args, optweek):
        """<--pre|--post> <week>
        Display this week's schedule in the NFL. Use --pre or --post to display pre/post season games.
        """
        
        url = self._b64decode('aHR0cDovL3MzLmFtYXpvbmF3cy5jb20vbmZsZ2MvYWxsU2NoZWR1bGUuanM=')

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
            
        games = [item['games'] for item in games if item['weekName'] == currentWeekName]

        append_list = []

        for games in games:
            for t in games:
                awayTeam = self._translateTeam('team', 'nid', t['awayTeamId'])
                homeTeam = self._translateTeam('team', 'nid', t['homeTeamId'])
                append_list.append("[" + t['date']['num'] + "] " + awayTeam + "@" + homeTeam + " " + t['date']['time'])
        
        descstring = string.join([item for item in append_list], " | ")
        output = "{0} :: {1}".format(ircutils.bold(currentWeekName), descstring)
        
        irc.reply(output)
    
    nflweek = wrap(nflweek, [optional('somethingWithoutSpaces')])
    
    
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
            append_list.append(ircutils.underline(title) + ": " + self._millify(float(figure)))

        descstring = string.join([item for item in append_list], " | ")
        output = "{0} :: {1}  TOTAL: {2}".format(ircutils.bold(optteam), descstring, ircutils.mircColor(self._millify(float(caphit)), 'blue'))
        irc.reply(output)

    nflcap = wrap(nflcap, [('somethingWithoutSpaces')])        

    
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
    
    
    def nflroster(self, irc, msg, args, optteam, optposition):
        """[team] [position]
        Display roster for team by position. Ex: NE QB.
        Position must be one of: QB, RB, WR, TE, OL, DL, LB, SD, ST
        """

        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('yahoo', 'team', optteam)
        
        postable = { 'QB':'Quarterbacks', 'RB':'Running Backs' }
        
        if optposition not in postable:
            irc.reply("Position must be one of: %s" % optposition.keys())
            return
        
        url = self._b64decode('aHR0cDovL3Nwb3J0cy55YWhvby5jb20vbmZsL3RlYW1z') + '/%s/roster' % lookupteam

        try:        
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Could not fetch: %s" % url)
            return

        soup = BeautifulSoup(html)
        tbodys = soup.findAll('tbody')[1:] #skip search header.

        object_list = []

        for tbody in tbodys:
            rows = tbody.findAll('tr')
            for row in rows:
                number = row.find('td')
                playertype = row.findPrevious('h5')
                player = number.findNext('th', attrs={'class':'title'}).findNext('a')
                position = number.findNext('td')
        
                d = collections.OrderedDict()
                d['playertype'] = playertype.renderContents().strip()
                d['number'] = number.renderContents().strip()
                d['player'] = player.renderContents().strip()
                d['position'] = position.renderContents().strip()
                object_list.append(d)

        for each in object_list:
            if postable[optposition] == each['playertype']:
                irc.reply(each)
        
    nflroster = wrap(nflroster, [('somethingWithoutSpaces'), ('somethingWithoutSpaces')])


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
        """Display current NFL team valuations from Forbes."""
        
        url = self._b64decode('aHR0cDovL3d3dy5mb3JiZXMuY29tL2xpc3RzLzIwMTEvMzAvbmZsLXZhbHVhdGlvbnMtMTFfcmFuay5odG1s')

        try:
            req = urllib2.Request(url)
            html = (urllib2.urlopen(req)).read()
        except:
            irc.reply("Failed to load: %s" % url)
            return
 
        soup = BeautifulSoup(html)
        #tbody = soup.find('tbody', attrs={'id':'listbody'})
        tbody = soup.find('tbody')
        rows = tbody.findAll('tr')

        object_list = []

        for row in rows:
            rank = row.find('td', attrs={'class':'rank'})
            team = rank.findNext('td')
            value = team.findNext('td')
            yrchange = value.findNext('td')
            debtvalue = yrchange.findNext('td')
            revenue = debtvalue.findNext('td')
            operinc = revenue.findNext('td')
            d = collections.OrderedDict()
            d['rank'] = rank.renderContents().strip()
            d['team'] = team.find('h3').find('a').renderContents().strip()
            d['value'] = value.renderContents().strip()
            d['yrchange'] = yrchange.renderContents().strip()
            d['debtvalue'] = debtvalue.renderContents().strip()
            d['revenue'] = revenue.renderContents().strip()
            d['operinc'] = operinc.renderContents().strip()
            object_list.append(d)
        
        irc.reply(ircutils.mircColor("Current NFL Team Values", 'red'))
        
        for N in self._batch(object_list, 7):
            irc.reply(' '.join(str(str(n['rank']) + "." + " " + ircutils.bold(n['team'])) + " (" + n['value'] + "M)" for n in N))        
            
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

    def nflschedule(self, irc, msg, args, optteam):
        """[team]
        Display the last and next five upcoming games for team.
        """
        
        optteam = optteam.upper().strip()

        if optteam not in self._validteams():
            irc.reply("Team not found. Must be one of: %s" % self._validteams())
            return
            
        lookupteam = self._translateTeam('yahoo', 'team', optteam) # (db, column, optteam)
        
        url = self._b64decode('aHR0cDovL3Nwb3J0cy55YWhvby5jb20vbmZsL3RlYW1z') + '/%s/calendar/rss.xml' % lookupteam
        
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            html = response.read()
        except:
            irc.reply("Cannot open: %s" % url)
            return

        # clean this stuff up
        html = html.replace('<![CDATA[','') #remove cdata
        html = html.replace(']]>','') # end of cdata
        html = html.replace('EDT','') # tidy up times
        html = html.replace('\xc2\xa0',' ') # remove some stupid character.

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

    nflschedule = wrap(nflschedule, [('somethingWithoutSpaces')])


    def nfldraft(self, irc, msg, args, optyear, optround):
        """
        """
        
        if optyear: # if optyear is there, test for valid and if after 2003.
            testdate = self._validate(optyear, '%Y')
            if not testdate:
                irc.reply("Invalid year. Must be YYYY.")
                return
            if optyear < 2003:
                irc.reply("Year must be after 2003.")
                return
                
        if optround:
            if 1 <= optround <= 2:
                irc.reply("Draft round must be 1 or 2.")
                return
        
        url = self._b64decode('aHR0cDovL2luc2lkZXIuZXNwbi5nby5jb20vbmZsL2RyYWZ0L3JvdW5kcw==')

        if optyear: # add year if we have it.
            url += '?year=%s' % (optyear)

        if optround: # optional round.
            url += '&round=%s' % (optround)

        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            html = response.read()
        except:
            irc.reply("Failed to fetch: %s" % url)
            return

        html = html.replace('ind alt nw','ind nw tL') # fix up some html before parse.
        html = html.replace('evenrow', 'oddrow')
        
        soup = BeautifulSoup(html)

        # check and make sure we have a table, otherwise error.
        if not soup.find('table', attrs={'class':'tablehead draft-tracker'}): 
            irc.reply("error: could not find any draft information. Bad year or round?")
            return
        else:
            table = soup.find('table', attrs={'class':'tablehead draft-tracker'})
            
        h1 = soup.find('h2') 
        rows = table.findAll('tr', attrs={'class': re.compile('^oddrow team.*')})

        object_list = []
               
        for row in rows:
            picknumber = row.find('p', attrs={'class':'round-number'}).text.strip()
            team = row.find('p', attrs={'class':'team-name'}).find('a')
            pos = row.find('div', attrs={'class':'position-bubble'}).text.strip()
            player = row.find('p', attrs={'class':'player-name'}).text.strip()
            if row.find('p', attrs={'class':'notes'}): # some picks have notes.
                notes = row.find('p', attrs={'class':'notes'})
                team = self._translateTeam('team', 'draft', team.text.strip())
                team += " " + notes.text.strip()
            else:
                team = self._translateTeam('team', 'draft', team.text.strip())
                
            d = collections.OrderedDict()
            d['pick'] = picknumber
            d['team'] = team
            d['pos'] = pos
            d['player'] = player
            
        
        irc.reply(ircutils.mircColor(h1.text.strip(), 'red') + ": ") # print header.
        
        for N in self._batch(object_list, 6):
            irc.reply(' '.join(str(n['pick']) + "." + " " + ircutils.bold(n['player']) + "[" + n['pos'] + "]" + " (" + n['team'] + ")" for n in N)) 

    nfldraft = wrap(nfldraft, [optional('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])
    
    
    def nfltrades(self, irc, msg, args):
        """Display the last NFL 10 trades."""
    
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
            
    nflplayers = wrap(nflplayers, [('somethingWithoutSpaces')])
    
    def _playerLookup(self, table, optstring):
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
        """Display NFL player's game log from last game played'"""
        
        optplayer = optplayer.lower().strip()
        
        lookupid = self._playerLookup('eid', optplayer)
        
        if lookupid == "0":
            irc.reply("No player found for: %s" % optplayer)
            return
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC9wbGF5ZXIvZ2FtZWxvZy9fL2lk') + '/%s/' % lookupid

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
        playername = soup.find('a', attrs={'class':'btn-split-btn'}).renderContents().strip()
        table = soup.find('table', attrs={'class':'tablehead'})
        headings = table.findAll('tr', attrs={'class':'colhead'})
        rows = table.findAll('tr', attrs={'class': re.compile('^oddrow')})

        heading = headings[-1].findAll('td') # last, findall.
        row = rows[-1].findAll('td') # mate with what is coming out.
        
        output = string.join([ircutils.bold(each.text) + ": " + row[i].text for i,each in enumerate(heading)], " | ")
        irc.reply(ircutils.mircColor(playername, 'red') + " :: " + output)
    
    nflgame = wrap(nflgame, [('text')])
    
    
    def nflinfo(self, irc, msg, args, optplayer):
        """Display basic information on NFL player."""
        
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
        
    nflinfo = wrap(nflinfo, [('text')])
    
    
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
        playername = soup.find('a', attrs={'class':'btn-split-btn'}).renderContents().strip()
        table = soup.find('table', attrs={'class':'tablehead'})    
        heading = table.find('tr', attrs={'class':'colhead'}).findAll('td')
        row = table.find('tr', attrs={'class': 'total'}).findAll('td')

        del heading[0:2],row[0] # must delete one because career has colspan=2. We also remove the first element. Total 2. 

        output = string.join([ircutils.bold(each.text) + ": " + row[i].text for i,each in enumerate(heading)], " | ")
        irc.reply(ircutils.mircColor(playername, 'red') + " :: " + output)
            
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
        irc.reply(ircutils.mircColor(playername, 'red') + "(" + optyear + ") :: " + output)
            
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
                    output = ircutils.mircColor(team, 'red') + " - " + ircutils.bold(transaction)
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
