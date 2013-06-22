#!/usr/bin/env python
# -*- coding: utf-8 -*-
# libs
import argparse
import sqlite3
from base64 import b64decode
import json
import urllib
import urllib2
from BeautifulSoup import BeautifulSoup
import re
from metaphone import doublemetaphone
# WHERE IS THE DB?
DB="../nfl_players.db"

# INTERNALS
def _sanitizeName(name):
    """ Sanitize name. """

    name = name.lower()  # lower.
    name = name.replace('.','')  # remove periods.
    name = name.replace('-','')  # remove dashes.
    name = name.replace("'",'')  # remove apostrophies.
    # possibly strip jr/sr/III suffixes in here?
    return name

def _eidlookup(eid):
    """Returns a playername for a specific EID."""

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT fullname FROM players WHERE eid=?", (eid,))
        row = cursor.fetchone()
        if row:
            return (str(row[0]))
        else:
            return None

def _addalias(optid, optalias):
    """<eid> <alias> Add a player alias. Ex: 2330 gisele"""

    optplayer = _eidlookup(optid)  # lookup player name.
    if not optplayer:
        return "Sorry, {0} is an invalid playerid.".format(optid)

    optalias = optalias.lower()  # sanitize name so it conforms.
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute("INSERT INTO aliases VALUES (?, ?)", (optid, optalias,))
            db.commit()
            return ("I have successfully added '{0}' as an alias to '{1} ({2})'.".format(optalias, _eidlookup(optid), optid))
        except sqlite3.Error, e:  # more descriptive error messages? (column name is not unique, foreign key constraint failed)
            return("ERROR: I cannot insert alias {0} to {1}: {0}".format(optalias, optid, e)) #(e.args[0]))

def _delalias(optalias):
    """<player alias> Delete a player alias. Ex: gisele."""

    optalias = optalias.lower()  # sanitize name.
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM aliases WHERE name=?", (optalias,))
        rowid = cursor.fetchone()
        if not rowid:
            return("ERROR: I do not have any aliases under '{0}'.".format(optalias))
        else:
            cursor.execute("DELETE FROM aliases WHERE name=?", (optalias,))
            db.commit()
            return("I have successfully deleted the player alias '{0}' from: {1} ({2}).".format(optalias, _eidlookup(rowid[0]), rowid[0]))

def _listalias(lookupid):
    """<player|eid> Fetches aliases for player. Specify the player name or their eid. Ex: Tom Brady or 2330."""

    optplayer = _eidlookup(lookupid)  # lookup player name.
    if not optplayer:
        return "Sorry, {0} is an invalid playerid.".format(lookupid)

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT name FROM aliases WHERE id=?", (lookupid,))
        rows = cursor.fetchall()
        if len(rows) > 0:
            return("{0}({1}) aliases: {2}".format(optplayer, lookupid, " | ".join([item[0] for item in rows])))
        else:
            return("I did not find any aliases for: {0}({1}".format(optplayer, lookupid))

def _eidnamelookup(eid):
    """Looks up player name + team using EID."""

    url = b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL3BsYXllcmluZm8/cGxheWVySWQ9') + eid + '&wjb='
    req = urllib2.Request(url)
    r = urllib2.urlopen(req)
    html = r.read()

    soup = BeautifulSoup(html)
    team = soup.find('td', attrs={'class':'teamHeader'}).find('b')
    name = soup.find('div', attrs={'class':'sub bold'})
    return "{0} {1}".format(team.getText(), name.getText())

def _rotofind(searchname, ridsonly=False):
    """Find a roto id."""

    pnsplit = searchname.split(' ')
    pn = "{0}, {1}".format(pnsplit[1], pnsplit[0])
    pn = urllib.quote(pn)
    url = b64decode('aHR0cDovL3d3dy5yb3Rvd29ybGQuY29tL2NvbnRlbnQvcGxheWVyc2VhcmNoLmFzcHg/') + "searchname=" + pn + "&sport=nfl"
    req = urllib2.Request(url)
    r = urllib2.urlopen(req)
    html = r.read()
    # output.
    output = []
    # process.
    if 'Search Results for:' in html:  # usually not a good sign.
        soup = BeautifulSoup(html)
        table = soup.find('table', attrs={'id':'cp1_tblSearchResults'})
        if table:  # this means we found more than one person.
            rows = table.findAll('tr')[2:]
            for row in rows:
                tds = row.findAll('td')
                pname = tds[0].getText()
                pid = tds[0].find('a')['href'].split('/')[3]
                ppos = tds[1].getText()
                pteam = tds[2].getText()
                if ridsonly:
                    output.append(pid)
                else:
                    output.append("{0} {1} {2} {3}".format(pname, pid, ppos, pteam))
        else:  # didn't find anything.
            print "I did not find any results for {0}".format(searchname)
    else:  # this means we found a person.
        soup = BeautifulSoup(html)
        playername = soup.find('div', attrs={'class':'playername'})
        playerid = soup.find('div', attrs={'class':'fb-like'})['data-href']
        playerid = playerid.split('/')[5]
        playertable = soup.find('table', attrs={'id':'cp1_ctl00_tblPlayerDetails'}).findAll('td')[1]
        if ridsonly:
            output.append(playerid)
        else:
            output.append("{0} {1} {2}".format(playername.getText(), playerid, playertable.getText()))
    # now return.
    return output

def _activerosters():
    """Fetch a set of EIDs from activerosters."""

    output = set()

    teams = [ 'dal', 'nyg', 'phi', 'wsh', 'ari', 'sf', 'sea', 'stl', 'chi', 'det', 'gb',
          'min', 'atl', 'car', 'no', 'tb', 'buf', 'mia', 'ne', 'nyj', 'den', 'kc',
          'oak', 'sd', 'bal', 'cin', 'cle', 'pit', 'hou', 'ind', 'jac', 'ten']

    for team in teams:
        url = b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC90ZWFtL3Jvc3Rlcg==') + '/_/name/' + team + '/'
        # url = 'http://espn.go.com/nfl/team/roster/_/name/' + team + '/'
        req = urllib2.Request(url)
        req.add_header("User-Agent","Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
        r = urllib2.urlopen(req)
        soup = BeautifulSoup(r.read())
        div = soup.find('div', attrs={'class':'col-main', 'id':'my-players-table'})
        table = div.find('table', attrs={'class':'tablehead', 'cellpadding':'3', 'cellspacing':'1'})
        rows = table.findAll('tr', attrs={'class':re.compile(r'(odd|even)row')})

        for row in rows:
            tds = row.findAll('td')
            #plr = tds[1]
            pid = tds[1].find('a')['href'].split('/')[7]
            output.add(int(pid))
        # return the set of ids.
    return output

def _eidnamefetch(eid):
    """Uses API to fetch player's name."""

    url = 'http://api.espn.com/v1/sports/football/nfl/athletes/%s?apikey=dha4fmjhb6q36zffzkech2zn' % str(eid)
    req = urllib2.Request(url)
    req.add_header("User-Agent","Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
    r = urllib2.urlopen(req)
    data = json.loads(r.read())
    data = data['sports'][0]['leagues'][0]['athletes'][0]
    fn = data['fullName']
    return fn

def _eidset():
    """Return a set with all EIDs in database."""

    dbrosters = set()
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT eid FROM players")
        rows = cursor.fetchall()
        for row in rows:
            dbrosters.add(int(row[0]))
    # return set.
    return dbrosters

def _addplayer(opteid, optrid, optplayer):
    """<eid> <rid> <player name> adds a new player into the database."""

    # everything looks good so lets prep to add.  # 2330|1163|tom brady|tom|brady|TM||PRT|
    optplayer = _sanitizeName(optplayer)  # sanitize.
    namesplit = optplayer.split()  # now we have to split the optplayer into first, last.
    fndm = doublemetaphone(namesplit[0])  # dm first.
    lndm = doublemetaphone(namesplit[1])  # dm last.
    # connect to the db and finally add.
    with sqlite3.connect(DB) as db:
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (opteid, optrid, optplayer, namesplit[0], namesplit[1], fndm[0], fndm[1], lndm[0], lndm[1]))
            db.commit()
            return("I have successfully added player {0}({1}).".format(optplayer, opteid))
        except sqlite3.Error, e:
            return("ERROR: I cannot add {0}. Error: '{1}'".format(optplayer, e))

def _deleteplayer(eid):
    """Deletes a player from the DB and aliases via eid."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM players where eid=?", (eid,))
            cursor.execute("DELETE FROM aliases where id=?", (eid,))
            db.commit()
            return("I have successfully deleted EID {0}.".format(eid))
        except sqlite3.Error, e:
            return("ERROR: I cannot delete EID {0}: '{1}'".format(eid, e))

# MAIN COMMANDS
def dbstats():
    """Stats on the DB."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT Count() FROM players")
        numofplayers = cursor.fetchone()[0]
        cursor.execute("SELECT Count() FROM aliases")
        numofaliases = cursor.fetchone()[0]

    return("NFLDB: I know about {0} players and {1} aliases.".format(numofplayers, numofaliases))

def finddupes():
    """Uses internal sql to find if there are dupes in the playernames."""

    with sqlite3.connect(DB) as db:
        #db.row_factory = sqlite3.Row
        cursor = db.cursor()
        cursor.execute("SELECT eid, fullname FROM players WHERE fullname IN (SELECT fullname FROM players GROUP BY fullname HAVING (COUNT(fullname) > 1))")
        rows = cursor.fetchall()

        if len(rows) == 0:  # no dupes.
            return None  # special return value due to specific handling.
        else:  # we have dupes.
            dupes = {}
            for row in rows:  # key is playername. value = list of eids.
                dupes.setdefault(row[1], []).append(row[0])
            return dupes  # return the dict.

def missingrids():
    """Find all players missing RIDs."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT eid, fullname FROM players WHERE rid=''")
        rows = cursor.fetchall()

        if len(rows) == 0:  # no dupes.
            return None  # special return value due to specific handling.
        else:  # we have missing rotoids.
            missing = []
            for row in rows:  # key is playername. value = list of eids.
                missing.append("{0} - {1}".format(row[0], row[1]))
            return missing  # return the dict.

def updatename(eid, pn):
    """Update's a players name."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE players SET fullname=? WHERE eid=?", (pn, eid,))
            db.commit()
            return("I have successfully updated EID {0} with name {1}.".format(eid, pn))
        except sqlite3.Error, e:
            return("ERROR: I cannot update EID {0}: '{1}'".format(eid, e))

def updaterid(opteid, optrid):
    """Update a player's rotoid using their eid."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE players SET rid=? WHERE eid=?", (optrid, opteid,))
            db.commit()
            return("I have successfully updated EID {0} with RID {1}.".format(opteid, optrid))
        except sqlite3.Error, e:
            return("ERROR: I cannot update EID {0}: '{1}'".format(opteid, e))

def missingplayers():
    """Scrape rosters and find players missing in our player database."""

    rosters = _activerosters()
    dbrosters = _eidset()  # players in rosters scrape but not in db.
    missingids = rosters.difference(dbrosters)
    return missingids

def inactiveplayers():
    """Scrape DB to find players who are not on active rosters."""

    rosters = _activerosters()
    dbrosters = _eidset()  # players not in rosters scrape but in db.
    notactive = dbrosters.difference(rosters)
    return notactive

def _badnames():
    """Find badnames in the database."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT eid, fullname from players ORDER BY eid")
        rows = cursor.fetchall()
    # list to put all entries in.
    outlist = []
    # now check each name.
    for row in rows:  # fullname = row[1]
        splitname = row[1].split()  # splits on the space.
        if len(splitname) != 2:  # if the name is not 2. append to list.
            outlist.append("{0} - {1}".format(row[0], row[1]))
    # return what we have.
    return outlist

def _baddm():
    """Find badnames in the database."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT eid, fullname, fndm1, lndm1 from players ORDER BY eid")
        rows = cursor.fetchall()
    # list to put all entries in.
    outlist = []
    # now check each name.
    for row in rows:  # eid = row[0], fullname = row[1], fndm1 = row[2], lndm1 = row[3]
        if row[2] == '':
            outlist.append("{0} - {1} - FNDM1: {2}".format(row[0], row[1], row[2]))
        if row[3] == '':
            outlist.append("{0} - {1} - LNDM1: {2}".format(row[0], row[1], row[3]))
    # return what we have.
    return outlist

def _rehashdm(eid):
    """."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT firstname, lastname FROM players WHERE eid=?", (eid,))
        row = cursor.fetchone()

    if not row:
        print "I did not find any player in the db with EID '{0}'".format(eid)
        return None
    else:
        firstname = doublemetaphone(row[0])
        lastname = doublemetaphone(row[1])
        print "DM :: FIRSTNAME {0} LASTNAME {1}".format(firstname, lastname)
        return dm

parser = argparse.ArgumentParser(description='playerdb management script')
parser.add_argument("--finddupes", action='store_true', help="find duplicate player names in the database.")
parser.add_argument("--missingrids", action='store_true', help="find players with missing rids.")
parser.add_argument("--updaterid", action='store', nargs=2, metavar=('EID', 'RID'), help="update a players rid.")
parser.add_argument('--rotofind', action='store', nargs=2, metavar=('EID', 'RID'), help="Find a players roto id.")
parser.add_argument("--fixmissingroto", action='store_true', help="Attempt to fix missing roto ids automatic.")
parser.add_argument("--missingplayers", action='store_true', help="find players missing from the database.")
parser.add_argument("--inactiveplayers", action='store_true', help="find inactive players in db but not on roster.")
parser.add_argument("--dbstats", action='store_true', help="show statistics about the database.")
parser.add_argument('--deleteinactive', action='store_true', help="delete the inactive players in the db")
parser.add_argument("--updatename", action='store', nargs=3, metavar=('EID', '', ''), help="update a player's name.")
parser.add_argument("--eidlookup", action='store', nargs=1, metavar=('EID'), help="print a player's name and team from eid lookup.")
parser.add_argument("--badnames", action='store_true', help="check the database for bad/broken playernames.")
parser.add_argument("--baddm", action='store_true', help="check the database for broken primary DM information.")
parser.add_argument("--rehashdm", action='store', nargs=1, metavar=('EID'), help="recalculate a player's doublemetaphone and store it.")
parser.add_argument("--addplayer", action='store', nargs=4, metavar=('EID', 'ALIAS', '', ''), help="add a player into the database.")
parser.add_argument("--addalias", action='store', nargs=2, metavar=('EID', 'ALIAS'), help="add an alias to a player in the db.")
parser.add_argument("--delalias", action='store', nargs=1, metavar=('ALIAS'), help="Delete an alias for a player.")
parser.add_argument("--listalias", action='store', nargs=1, metavar=('EID'), help="list player aliases")
args = parser.parse_args()

if args.finddupes:
    dupes = finddupes()
    if not dupes:
        print "I did not find any dupes"
    else:
        print "I found {0} duplicates in the database.".format(len(dupes))
        for (k, v) in  dupes.items():
            print k, v
elif args.missingrids:
    missing = missingrids()
    if not missing:
        print "I did not find any players with missing rids."
    else:
        print "I found {0} players with missing rids.".format(len(missing))
        for plyr in missing:
            print plyr
elif args.updaterid:
    opteid = args.updaterid[0]
    optrid = args.updaterid[1]
    update = updaterid(opteid, optrid)
    print update
elif args.missingplayers:
    missing = missingplayers()
    if len(missing) == 0:  # no missing.
        print "No players in db missing from active rosters."
    else:
        print "I found {0} players missing in the db that are on active rosters.".format(len(missing))
        print missing
elif args.inactiveplayers:
    inactive = inactiveplayers()
    if len(inactive) == 0:
        print "No players in db are not on active rosters."
    else:
        print "I found {0} players who are in the database but not on an active NFL roster.".format(len(inactive))
        print inactive
elif args.dbstats:
    dbstats = dbstats()
    print dbstats
elif args.deleteinactive:
    inactive = inactiveplayers()
    if len(inactive) == 0:
        print "Sorry, no in-active players."
    else:
        for inactive in inactive:  # iterate over all.
            resp = _deleteplayer(inactive)
            print resp
elif args.rotofind:
    pn = "{0} {1}".format(args.rotofind[0], args.rotofind[1])
    rf = _rotofind(pn, ridsonly=False)
    rflen = len(rf)
    if rflen == 0:
        print "Sorry, I did not find any rotoworld matches for {0}".format(pn)
    elif rflen == 1:
        print "I found 1 match for {0} :: {1}".format(pn, "".join(rf))
    else:
        print "I found {0} matches for {1}".format(rflen, pn)
        for i in rf:
            print i
elif args.fixmissingroto:
    missing = missingrids()
    if not missing:  # no missing ids.
        print "I did not find any players with missing rids."
    else:  # missing ids.
        for plyr in missing:  # iterate over each.
            plyrsplit = plyr.split(' - ')  # output is eid - name.
            eid, plyrname = plyrsplit[0], plyrsplit[1]  # assign strings.
            rf = _rotofind(plyrname, ridsonly=True)  # only return rids.
            rids = len(rf)  # test length.
            if rids == 1:  # we only found one.
                update = updaterid(eid, rf[0])  # lets update.
                print "Updated {0} :: {1}".format(plyrname, update)
            else:  # less than one.
                print "I could not update {0}.".format(plyrname)
elif args.updatename:
    eid = args.updatename[0]
    pn = "{0} {1}".format(args.updatename[1], args.updatename[2])
    update = updatename(eid, pn)
    print update
elif args.eidlookup:
    eidlookup = _eidnamelookup(args.eidlookup[0])
    print eidlookup
elif args.badnames:
    badnames = _badnames()  # returns a list.
    badnameslength = len(badnames)
    if badnameslength == 0:  # no badnames.
        print "I did not find any badnames in the database."
    else:
        print "I found {0} badnames in the database.".format(badnameslength)
        for badname in badnames:
            print badname
elif args.baddm:
    baddms = _baddm()
    baddmlength = len(baddms)
    if baddmlength == 0:
        print "I did not find any bad DM information in the database."
    else:
        print "I Found {0} bad DM in the db".format(baddmlength)
        for baddm in baddms:
            print baddm
elif args.rehashdm:  # needs fix.
    eid = args.rehashdm[0]
    dm = _rehashdm(eid)
    print dm
elif args.addplayer:
    opteid = args.addplayer[0]
    optrid = args.addplayer[1]
    optplayer = " ".join(args.addplayer[2:])
    # perform trans.
    addplayer= _addplayer(opteid, optrid, optplayer)
    print addplayer
elif args.addalias:  # add alias.
    opteid = args.addalias[0]
    optalias = args.addalias[1]
    addalias = _addalias(opteid, optalias)
    print addalias
elif args.delalias:  # delete alias.
    optalias = args.delalias[0]
    delalias = _delalias(optalias)
    print delalias
elif args.listalias:  # list a player's alias.
    opteid = args.listalias[0]
    listalias = _listalias(opteid)
    print listalias

#if __name__ == '__main__':
