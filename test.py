###
# see LICENSE.txt for information.
###

from supybot.test import *

class NFLTestCase(PluginTestCase):
    plugins = ('NFL',)

    def testnflarrests(self):
        self.assertNotError('nflarrests')

    def testnflawards(self):
        self.assertNotError('nflawards 2012')

    def testnflcap(self):
        self.assertNotError('nflcap NE')

    def testnflcareerstats(self):
        self.assertNotError('nflcareerstats Tom Brady')

    def testnflcoach(self):
        self.assertNotError('nflcoach NE')

    def testnflcoachingstaff(self):
        self.assertNotError('nflcoachingstaff NE')

    def testnflcountdown(self):
        self.assertNotError('nflcountdown')

    def testnfldraft(self):
        self.assertNotError('nfldraft 2013 1')

    def testnfldraftorder(self):
        self.assertNotError('nfldraftorder')

    def testnflgame(self):
        self.assertNotError('nflgame Tom Brady')

    def testnflgamelog(self):
        self.assertNotError('nflgamelog Tom Brady')

    def testnflgamestats(self):
        self.assertNotError('nflgamestats NE')

    def testnflhead2head(self):
        self.assertNotError('nflhead2head NE NYJ')

    def testnflhof(self):
        self.assertNotError('nflhof 2013')

    def testnflinfo(self):
        self.assertNotError('nflinfo Tom Brady')

    def testnflinjury(self):
        self.assertNotError('nflinjury NE')

    def testnflleagueleaders(self):
        self.assertNotError('nflleagueleaders Passing td')

    def testnflplayercareer(self):
        self.assertNotError('nflplayercareer Tom Brady')

    def testnflplayerfines(self):
        self.assertNotError('nflplayerfines Tom Brady')

    def testnflplayernews(self):
        self.assertNotError('nflplayernews Tom Brady')

    def testnflplayertransactions(self):
        self.assertNotError('nflplayertransactions Tom Brady')

    def testnflplayoffs(self):
        self.assertNotError('nflplayoffs')

    def testnflpowerrankings(self):
        self.assertNotError('nflpowerrankings')

    def testnflpracticereport(self):
        self.assertNotError('nflpracticereport NE')

    def testnflprobowl(self):
        self.assertNotError('nflprobowl 2013')

    def testnflroster(self):
        self.assertNotError('nflroster NE QB')

    def testnflrotocontract(self):
        self.assertNotError('nflrotocontract Tom Brady')

    def testnflschedule(self):
        self.assertNotError('nflschedule NE')

    def testnflseason(self):
        self.assertNotError('nflseason Tom Brady')

    def testnflseasonsummary(self):
        self.assertNotError('nflseasonsummary NE 2014')

    def testnflspotcontract(self):
        self.assertNotError('nflspotcontract Tom Brady')

    def testnflstandings(self):
        self.assertNotError('nflstandings afc east')

    def testnflsuperbowl(self):
        self.assertNotError('nflsuperbowl 2014')

    def nflteamdraft(self):
        self.assertNotError('nflteamdraft NE 2011')

    def testnflteamrankings(self):
        self.assertNotError('nflteamrankings NE')

    def testnflteams(self):
        self.assertNotError('nflteams')

    def testnflteamtrans(self):
        self.assertNotError('nflteamtrans NE')

    def testnfltotalqbr(self):
        self.assertNotError('nfltotalqbr')

    def testnflweeklyleaders(self):
        self.assertNotError('nflweeklyleaders')
