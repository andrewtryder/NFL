#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib2
import time
import json
import fuzzy

def dm(string):
    dmeta = fuzzy.DMetaphone()
    return dmeta(string)

def sanitizeName(string):
    string = string.lower()
    string = string.replace('-','')
    string = string.replace("'",'')
    string = string.replace('.','')
    return string

offset = 0

f = open('nfl_players.sql', 'w')

while offset < 3306:
    time.sleep(1)
    url = 'http://api.espn.com/v1/sports/football/nfl/athletes/?offset=%s&apikey=dha4fmjhb6q36zffzkech2zn' % offset
    print url
    req = urllib2.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
    r = urllib2.urlopen(req)
    data = json.loads(r.read())
    players = data['sports'][0]['leagues'][0]['athletes']
    offset += 50

    for player in players:
        eid = player['id']
        rid = ""
        first = sanitizeName(player['firstName'])
        last = sanitizeName(player['lastName'])
        full = sanitizeName(player['fullName'])
        (firstdm1, firstdm2) = dm(first)
        (lastdm1, lastdm2) = dm(last)
        output = "INSERT INTO players (eid,rid,full,first,last,firstdm1,firstdm2,lastdm1,lastdm2) values ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}');\n"\
                 .format(eid, rid, full, first, last, firstdm1, firstdm2, lastdm1, lastdm2)
        print output
        f.write(output)

f.close()
