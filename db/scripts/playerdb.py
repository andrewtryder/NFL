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
    """
    Sanitize name. Remove . - ' and lowercases.
    """

    name = name.lower()  # lower.
    name = name.replace('.','')  # remove periods.
    name = name.replace('-','')  # remove dashes.
    name = name.replace("'",'')  # remove apostrophies.
    # return it.
    return name

def _eidlookup(eid, splitname=False):
    """
    Returns a playername for a specific EID.
    """

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        if splitname:
            cursor.execute("SELECT lastname, firstname FROM players WHERE eid=?", (eid,))
        else:  # grab fullname.
            cursor.execute("SELECT fullname FROM players WHERE eid=?", (eid,))
        row = cursor.fetchone()
        if row:
            if splitname:
                return ("{0}, {1}".format(str(row[0]), str(row[1])))
            else:
                return (str(row[0]))
        else:
            return None

def _addalias(optid, optalias):
    """<eid> <alias>
    Add a player alias.
    Ex: 2330 gisele
    """

    optalias = _sanitizeName(optalias) # sanitize name so it conforms.
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute("INSERT INTO aliases VALUES (?, ?)", (optid, optalias,))
            db.commit()
            return True
        except sqlite3.Error, e:  # more descriptive error messages? (column name is not unique, foreign key constraint failed)
            print ("ERROR: I cannot insert alias {0} to {1}: {0}".format(optalias, optid, e))
            return None

def _delalias(optalias):
    """<player alias>
    Delete a player alias.
    Ex: gisele.
    """

    optalias = _sanitizeName(optalias) # sanitize name so it conforms.
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM aliases WHERE name=?", (optalias,))
        db.commit()
        return True
        # return("I have successfully deleted the player alias '{0}' from: {1} ({2}).".format(optalias, _eidlookup(rowid[0]), rowid[0]))

def _listalias(lookupid):
    """<eid>
    Fetches aliases for player by their EID.
    Ex: 2330
    """

    #optplayer = _eidlookup(lookupid)  # lookup player name.
    #if not optplayer:
    #    return "Sorry, {0} is an invalid playerid.".format(lookupid)
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT name FROM aliases WHERE id=?", (lookupid,))
        rows = cursor.fetchall()
        if len(rows) > 0:
            return("{0}({1}) aliases: {2}".format(optplayer, lookupid, " | ".join([item[0] for item in rows])))
        else:
            return None

def _eidnamelookup(eid):
    """<eid>
    Looks up player name + team using EID.
    Ex: 2330
    """

    url = b64decode('aHR0cDovL20uZXNwbi5nby5jb20vbmZsL3BsYXllcmluZm8/cGxheWVySWQ9') + eid + '&wjb='
    req = urllib2.Request(url)
    r = urllib2.urlopen(req)
    html = r.read()
    try:
        soup = BeautifulSoup(html)
        team = soup.find('td', attrs={'class':'teamHeader'}).find('b')
        name = soup.find('div', attrs={'class':'sub bold'})
        return "{0} {1}".format(team.getText(), name.getText())
    except Exception, e:
        print "ERROR: _eidnamelookup :: {0}".format(e)
        return None

def _rotofind(searchname, ridsonly=False):
    """<searchname>
    Find a roto id.
    Ex: Tom Brady
    """

    pn = urllib.quote(searchname)  # quote the name.
    url = b64decode('aHR0cDovL3d3dy5yb3Rvd29ybGQuY29tL2NvbnRlbnQvcGxheWVyc2VhcmNoLmFzcHg/') + "searchname=" + pn + "&sport=nfl"
    # do our request.
    try:
        req = urllib2.Request(url)
        r = urllib2.urlopen(req)
        html = r.read()
    except Exception, e:
        print "ERROR: _rotofind: in HTTP request: {0}".format(e)
        return None
    # output container.
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
            return None
            #print "I did not find any results for {0}".format(searchname)
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

def _activerosters(pnames=False):
    """
    Fetch a set of EIDs from activerosters.
    Call with pnames=True to return a dict vs. set (dict k=pid, v=fullname)
    """

    # determine our output container based on pnames.
    if pnames:
        output = {}
    else:
        output = set()
    # list of all teams.
    teams = [
            'dal', 'nyg', 'phi', 'wsh', 'ari', 'sf', 'sea', 'stl', 'chi', 'det', 'gb',
            'min', 'atl', 'car', 'no', 'tb', 'buf', 'mia', 'ne', 'nyj', 'den', 'kc',
            'oak', 'sd', 'bal', 'cin', 'cle', 'pit', 'hou', 'ind', 'jac', 'ten'
            ]
    # wrap in a big try/except block. dirty but works.
    try:
        for team in teams:
            url = b64decode('aHR0cDovL2VzcG4uZ28uY29tL25mbC90ZWFtL3Jvc3Rlcg==') + '/_/name/' + team + '/'
            req = urllib2.Request(url)
            req.add_header("User-Agent","Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
            r = urllib2.urlopen(req)
            soup = BeautifulSoup(r.read())
            div = soup.find('div', attrs={'class':'col-main', 'id':'my-players-table'})
            table = div.find('table', attrs={'class':'tablehead', 'cellpadding':'3', 'cellspacing':'1'})
            rows = table.findAll('tr', attrs={'class':re.compile(r'(odd|even)row')})

            for row in rows:
                tds = row.findAll('td')
                pname = tds[1].getText()
                pid = tds[1].find('a')['href'].split('/')[7]
                if pnames:  # add dict.
                    output[pid] = pname
                else:  # add to set.
                    output.add(int(pid))
        # return our container.
        return output
    except Exception, e:
        print "ERROR: _activerosters: {0}".format(e)
        return None

def _eidnamefetch(eid):
    """<eid>
    Uses API to fetch player's name.
    Ex: 2330
    """

    try:
        url = 'http://api.espn.com/v1/sports/football/nfl/athletes/%s?apikey=dha4fmjhb6q36zffzkech2zn' % str(eid)
        req = urllib2.Request(url)
        req.add_header("User-Agent","Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
        r = urllib2.urlopen(req)
        data = json.loads(r.read())
        data = data['sports'][0]['leagues'][0]['athletes'][0]
        fn = data['fullName']
        return fn
    except Exception, e:
        print "ERROR: _eidnamefetch :: {0}".format(e)
        return None

def _eidset():
    """
    Return a set with all EIDs in database.
    """

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
    """<eid> <rid> <player name>
    Adds a new player into the database.
    Needs a unique EID, RID, and playername (sanitized and parsed). DM will be calculated upon insertion.
    Ex: 2330 <RID> tom brady
    """

    # everything looks good so lets prep to add.  # 2330|1163|tom brady|tom|brady|TM||PRT|
    optplayer = _sanitizeName(optplayer)  # sanitize.
    namesplit = optplayer.split()  # now we have to split the optplayer into first, last. (name needs to be parsed before)
    fndm = doublemetaphone(namesplit[0])  # dm first.
    lndm = doublemetaphone(namesplit[1])  # dm last.
    # connect to the db and finally add.
    with sqlite3.connect(DB) as db:
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (opteid, optrid, optplayer, namesplit[0], namesplit[1], fndm[0], fndm[1], lndm[0], lndm[1]))
            db.commit()
            #return("I have successfully added player {0}({1}).".format(optplayer, opteid))
            return True
        except sqlite3.Error, e:
            print("ERROR: I cannot add {0}. Error: '{1}'".format(optplayer, e))
            return None

def _deleteplayer(eid):
    """<eid>
    Deletes a player from the DB and aliases via eid.
    Ex: 2330
    """

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM players where eid=?", (eid,))
            cursor.execute("DELETE FROM aliases where id=?", (eid,))
            db.commit()
            #return("I have successfully deleted EID {0}.".format(eid))
            return True
        except sqlite3.Error, e:
            print("ERROR: I cannot delete EID {0}: '{1}'".format(eid, e))
            return None

def _missingrids():
    """Find all players missing RIDs."""

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT eid FROM players WHERE rid=''")
        rows = cursor.fetchall()

        if len(rows) == 0:  # no dupes.
            return None  # special return value due to specific handling.
        else:  # we have missing rotoids.
            missing = []
            for row in rows:  # key is playername. value = list of eids.
                #missing.append("{0} - {1}".format(row[0], row[1]))
                missing.append(row[0])  # add the missing EID.
            return missing  # return the dict.

def _updatename(eid, pn):
    """<eid> <player name>
    Update's a players name.
    Ex: 2330 tom brady
    """

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE players SET fullname=? WHERE eid=?", (pn, eid,))
            db.commit()
            #return("I have successfully updated EID {0} with name {1}.".format(eid, pn))
            print True
        except sqlite3.Error, e:
            print("ERROR: I cannot update EID {0}: '{1}'".format(eid, e))
            print None

def _updaterid(opteid, optrid):
    """<eid> <rid>
    Update a player's rotoid using their eid.
    Ex: 2330 <RID>
    """

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE players SET rid=? WHERE eid=?", (optrid, opteid,))
            db.commit()
            return True
        except sqlite3.Error, e:
            print("ERROR: I cannot update EID {0}: '{1}'".format(opteid, e))
            return None

def _inactiveplayers():
    """
    Scrape DB to find players who are not on active rosters.
    """

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
    if len(rows) == 0:
        return None
    else:
        for row in rows:  # fullname = row[1]
            splitname = row[1].split()  # splits on the space.
            if len(splitname) != 2:  # if the name is not 2. append to list.
                outlist.append("{0} - {1}".format(row[0], row[1]))
        # return what we have.
        return outlist

def _rehashdm(eid):
    """<eid>
    Recalculate the doublemetaphone for a player (eid)
    Ex: 2330
    """

    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT firstname, lastname FROM players WHERE eid=?", (eid,))
        row = cursor.fetchone()
    # calculate the dm on first,l ast
    fndm = doublemetaphone(row[0])
    lndm = doublemetaphone(row[1])
    # firstname and lastname are tuples.
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE players SET fndm1=?, fndm2=?, lndm1=?, lndm2=? WHERE eid=?", (fndm[0], fndm[1], lndm[0], lndm[1], eid,))
            db.commit()
            #return("I have successfully updated EID {0}'s doublemetaphone ({1}, {2})".format(eid, fndm, lndm))
            return True
        except sqlite3.Error, e:
            print("ERROR: _rehashdm: I cannot update EID {0}'s doublemetaphone: '{1}'".format(eid, e))
            return None

def _pnameparse(inp):
    inputlen = len(inp)
    if inputlen != 0:  # more than one.
        inp = _sanitizeName(inp)  # clean up name.
        splitinput = inp.split()  # split on a space.
        splitlen = len(splitinput)
        if splitlen == 1:  # only "last" name.
            return None
        elif splitlen == 2:  # return a tuple of first, last
            return (splitinput[0], splitinput[1])
        elif splitlen == 3:  # 3..
            if splitinput[2] in ['jr', 'sr', 'iii']:  # common suffixes.
               return (splitinput[0], splitinput[1])
            else:  # make it first and last element.
                return (splitinput[0], "".join(splitinput[1:]))
        else:  # make it first element and last.
            return (splitinput[0], splitinput[-1])
    else:
        return None

# main part of ArgumentParser
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
parser.add_argument("--missingdm", action='store_true', help="check the database for missing primary DM information.")
parser.add_argument("--rehashdm", action='store', nargs=1, metavar=('EID'), help="recalculate a player's doublemetaphone and store it.")
parser.add_argument("--addplayer", action='store', nargs=4, metavar=('EID', 'ALIAS', '', ''), help="add a player into the database.")
parser.add_argument("--addalias", action='store', nargs=2, metavar=('EID', 'ALIAS'), help="add an alias to a player in the db.")
parser.add_argument("--delalias", action='store', nargs=1, metavar=('ALIAS'), help="Delete an alias for a player.")
parser.add_argument("--listalias", action='store', nargs=1, metavar=('EID'), help="list player aliases")
parser.add_argument("--fixmissingplayers", action='store_true', help="attempt to add in missing players (EID and RID) from active rosters")
parser.add_argument("--cleanup", action='store_true', help="clean up player database (vacuum, etc)")
# parse args
args = parser.parse_args()
# individual functions per argument.
if args.finddupes:
    with sqlite3.connect(DB) as db:
        #db.row_factory = sqlite3.Row
        cursor = db.cursor()
        cursor.execute("SELECT eid, fullname FROM players WHERE fullname IN (SELECT fullname FROM players GROUP BY fullname HAVING (COUNT(fullname) > 1))")
        rows = cursor.fetchall()
    # now check what we got back.
    if len(rows) == 0:  # no dupes.
        print "I did not find any dupes"
    else:  # we have dupes.
        print "I found {0} duplicates in the database.".format(len(rows))
        dupes = {}
        for row in rows:  # key is playername. value = list of eids.
            dupes.setdefault(row[1], []).append(row[0])
        # now output.
        for (k, v) in dupes.items():
            print "{0} :: {1}".format(k, v)
elif args.missingrids:
    missing = _missingrids()
    if not missing:
        print "I did not find any players with missing rids."
    else:
        print "I found {0} players with missing rids.".format(len(missing))
        for eid in missing:
            plyrname = _eidlookup(eid, splitname=True)
            print "{0} :: EID: {1} :: MISSING RID".format(plyrname, eid)
elif args.updaterid:
    opteid = args.updaterid[0]
    optrid = args.updaterid[1]
    update = _updaterid(opteid, optrid)
    if not update:
        print "ERROR: updating EID: {0} with RID: {1}".format(opteid, optrid)
    else:
        print "I have successfully updated EID: {0} with RID: {1}".format(opteid, optrid)
elif args.fixmissingroto:
    missing = _missingrids()
    if not missing:  # no missing ids.
        print "I did not find any players with missing rids."
    else:  # missing ids.
        for eid in missing:  # iterate over each.
            plyrname = _eidlookup(eid, splitname=True)
            rf = _rotofind(plyrname, ridsonly=True)  # only return rids.
            # now we have to check what comes back.
            if not rf:
                print "ERROR: I could not find an RID for {0} (EID: {1})".format(plyrname, eid)
            # we did get something back. make sure we only get one back.
            if len(rf) == 1:  # we only found one.
                update = _updaterid(eid, rf[0])  # lets update.
                print "Updated {0} :: EID: {1} RID: {2}".format(plyrname, eid, rf)
            # NEED CASE HERE IF WE FIND MORE THAN ONE.
            else:  # either more than one or less than one.
                print "I could not update {0} EID: {1} RIDS: {2}".format(plyrname, eid, rf)
elif args.missingplayers:
    rosters = _activerosters()  # this will be a dict of missing players. key=eid, value=name.
    dbrosters = _eidset()  # players in rosters scrape but not in db.
    missing = rosters.difference(dbrosters)
    if len(missing) == 0:  # no missing.
        print "No players in db missing from active rosters."
    else:
        print "I found {0} players missing in the db that are on active rosters.".format(len(missing))
        print missing
elif args.fixmissingplayers:
    rosters = _activerosters(pnames=True)   # find our missing players but also return with name (dict).
    rosterkeys = set([int(i) for i in rosters.keys()])  # rosters is a k, v dict. key are the ids. lets make a set of these keys.
    #print rosterkeys
    dbrosters = _eidset()  # players in rosters scrape but not in db.
    missingids = rosterkeys.difference(dbrosters)  # this will be a set of missing player ids (if any)
    # make sure players are missing..
    if len(missingids) == 0:  # no missing.
        print "No players in db missing from active rosters."
    else:  # we have players missing.
        #print "{0} missing ids. {1}".format(len(missingids), " | ".join([str(i) for i in missingids]))
        for mpid in missingids:
            # with each mpid (missing id of player), grab the corresponding name in  rosters.
            mpname = rosters[str(mpid)]
            # now we should clean up the name.
            mpnameparse = _pnameparse(mpname)
            if not mpnameparse:  # make sure something comes back.
                print "_pnameparse broke parsing: {0} EID: {1}".format(mpname, mpid)
            else:  # valid. lets go.
                optplayer = "{0} {1}".format(mpnameparse[0], mpnameparse[1])
                #print "mpid: {0} mpname: {1} mpnameparse: {2} optplayer: {3}".format(mpid, mpname, mpnameparse, optplayer)
                apreturn = _addplayer(mpid, '', optplayer)  # we add w/o rotoid. run --fixmissingroto to fix this later.
                if apreturn:
                    print "I have successfully added {0} EID: {1}".format(optplayer, mpid)
                else:
                    print "ERROR trying to add {0}".format(optplayer)
elif args.inactiveplayers:
    inactive = _inactiveplayers()
    if len(inactive) == 0:
        print "No players in db are not on active rosters."
    else:
        print "I found {0} players who are in the database but not on an active NFL roster.".format(len(inactive))
        print inactive
elif args.deleteinactive:
    inactives = _inactiveplayers()
    if len(inactives) == 0:
        print "Sorry, no in-active players."
    else:
        for inactive in inactives:  # iterate over all.
            resp = _deleteplayer(inactive)
            if not resp:
                print "ERROR trying to delete player: {0}".format(inactive)
elif args.dbstats:
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("SELECT Count() FROM players")
        numofplayers = cursor.fetchone()[0]
        cursor.execute("SELECT Count() FROM aliases")
        numofaliases = cursor.fetchone()[0]
    print ("NFLDB: I know about {0} players and {1} aliases.".format(numofplayers, numofaliases))
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
elif args.updatename:
    eid = args.updatename[0]
    pn = "{0} {1}".format(args.updatename[1], args.updatename[2])
    update = _updatename(eid, pn)
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
elif args.cleanup:
    with sqlite3.connect(DB) as db:
        cursor = db.cursor()
        cursor.execute("VACUUM")
elif args.missingdm:
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
    if outlist == 0:
        print "I did not find any bad DM information in the database."
    else:
        print "I Found {0} bad DM in the db".format(len(outlist))
        for baddm in outlist:
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
    # first, make sure we have a valid EID.
    optplayer = _eidlookup(opteid)
    if not optplayer:
        print "Sorry, {0} is an invalid playerid.".format(opteid)
    else:  # valid EID.
        addalias = _addalias(opteid, optalias)
        if addalias:
            print "We have added alias '{0}' to {1} ({2})".format(optalias, opteid, optplayer)
        else:
            print "Something went wrong trying to add '{0}' as an alias to {1} ({2})".format(optalias, opteid, optplayer)
elif args.delalias:  # delete alias.
    optalias = args.delalias[0]
    delalias = _delalias(optalias)
    print delalias
elif args.listalias:  # list a player's alias.
    opteid = args.listalias[0]
    listalias = _listalias(opteid)
    print listalias

#if __name__ == '__main__':
