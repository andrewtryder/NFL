###
# see LICENSE.txt for information.
###

from supybot.test import *

class NFLTestCase(PluginTestCase):
    plugins = ('NFL',)

    def testNFL(self):
        self.assertNotError('nflcap NE')

