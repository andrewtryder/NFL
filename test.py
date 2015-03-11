###
# see LICENSE.txt for information.
###

from supybot.test import *

class NFLTestCase(PluginTestCase):
    plugins = ('NFL',)

    def testNFL(self):
        self.assertNotError('nflarrests')
        self.assertNotError('nflawards 2012')
        self.assertNotError('nflcap NE')
        self.assertNotError('nflcareerstats Tom Brady')
        self.assertNotError('nflcoach NE')
        self.assertNotError('nflcoachingstaff NE')
        self.assertNotError('nflcountdown')
        self.assertNotError('nfldraft 2013 1')
        self.assertNotError('nfldraftorder')
        self.assertNotError('nflgame Tom Brady')
        self.assertNotError('nflgamelog Tom Brady')
        self.assertNotError('nflgamestats NE')
        self.assertNotError('nflhead2head NE NYJ')
        self.assertNotError('nflhof 2013')
        self.assertNotError('nflinfo Tom Brady')
        self.assertNotError('nflinjury NE')
        self.assertNotError('nflleagueleaders Passing td')
        self.assertNotError('nflplayercareer Tom Brady')
        self.assertNotError('nflplayerfines Tom Brady')
        self.assertNotError('nflplayernews Tom Brady')
        self.assertNotError('nflplayertransactions Tom Brady')
        self.assertNotError('nflplayoffs')
        self.assertNotError('nflpowerrankings')
        self.assertNotError('nflpracticereport NE')
        self.assertNotError('nflprobowl 2013')
        self.assertNotError('nflroster NE QB')
        self.assertNotError('nflrotocontract Tom Brady')
        self.assertNotError('nflschedule NE')
        self.assertNotError('nflseason Tom Brady')
        self.assertNotError('nflseasonsummary NE 2014')
        self.assertNotError('nflspotcontract Tom Brady')
        self.assertNotError('nflstandings afc east')
        self.assertNotError('nflsuperbowl 2014')
        self.assertNotError('nflteamdraft NE 2011')
        self.assertNotError('nflteamrankings NE')
        self.assertNotError('nflteams')
        self.assertNotError('nflteamtrans NE')
        self.assertNotError('nfltotalqbr')
        self.assertNotError('nfltrades')
        self.assertNotError('nfltrans')
        self.assertNotError('nflweather')
        self.assertNotError('nflweeklyleaders')
        self.assertNotError('nflcap NE')

