###
# see LICENSE.txt for information.
###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NFL', True)


NFL = conf.registerPlugin('NFL')
conf.registerGlobalValue(NFL, 'logURLs', registry.Boolean(True, """Should we log all URL calls?"""))
conf.registerChannelValue(NFL, 'requireVoiceForCalls', registry.Boolean(False, """Require voice for commands?"""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=250:
