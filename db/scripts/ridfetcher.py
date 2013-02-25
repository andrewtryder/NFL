#!/usr/bin/env python

# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup
import urllib2

def sanitizeName(name):
    name = name.lower()
    name = name.replace('.','')
    name = name.replace('-','')
    name = name.replace("'",'')
    return name

f = open('rid_players.sql', 'w')

teams = ['sf','chi','cin','buf','den','cle','tb','arz','sd','kc','ind','dal','mia','phi','atl','nyg','jac','nyj','det','gb','car','ne','oak','stl','bal','was','no','sea','pit','hou','ten','min']

for url in teams:
    url = 'http://www.rotoworld.com/teams/contracts/nfl/' + url + '/'
    req = urllib2.Request(url)
    html = (urllib2.urlopen(req)).read()

    soup = BeautifulSoup(html)
    table = soup.find('table', attrs={'id':'cp1_tblContracts'})
    rows = table.findAll('tr')[1:]

    for row in rows:
        tds = row.findAll('td')
        id = tds[0].find('a')['href']
        id = id.split('/', 3)[3].split('/')[0]
        name = tds[0].getText()
        name = sanitizeName(name)
        #output = "{0},{1}\n".format(id,name)
        output = "UPDATE players SET rid='{0}' where fullname='{1}'\n".format(id,name)
        f.write(output)

f.close()
