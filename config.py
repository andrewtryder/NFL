###
# Copyright (c) 2012, spline
# All rights reserved.
#
#
###

import os
import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('NFL')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NFL', True)


NFL = conf.registerPlugin('NFL')
conf.registerGlobalValue(NFL, 'dbLocation', registry.String(os.path.abspath(os.path.dirname(__file__)) + '/nfl.db', """Absolute path for nfl.db sqlite3 database file location."""))
conf.registerGlobalValue(NFL, 'nflPlayersDb', registry.String(os.path.abspath(os.path.dirname(__file__)) + '/nfl_players.db', """Absolute path for nflplayers.db sqlite3 database file location."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=250:
