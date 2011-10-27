#!/usr/bin/env python
"""
irccat.py - jsonbot "irccat" Module
Copyright 2011, Richard Bateman
Licensed under the New BSD License.

Written to be used in the #firebreath IRC channel: http://www.firebreath.org

To test, set up the host and port, then use something like:

echo "@taxilian I am awesome" | netcat -g0 localhost 54321

echo "#channel I am awesome" | netcat -g0 localhost 54321

you can specify multiple users (with @) and channels (with #) by seperating them
with commas.  Not that with jabber, channels tend to be treated as users
unless you set up an alias in your channel:

!irccat_add_alias #channel

"""

## jsb imports

from jsb.lib.threads import start_new_thread
from jsb.lib.persistconfig import PersistConfig
from jsb.lib.fleet import getfleet
from jsb.lib.commands import cmnds
from jsb.lib.examples import examples

## basic imports

import logging

## defines

cfg = PersistConfig()
cfg.define("botnames", ["default-sxmpp",])
cfg.define("channels", [])
cfg.define("host", "localhost")
cfg.define("port", 54321)
cfg.define("aliases", {})

import SocketServer
from SocketServer import ThreadingMixIn, StreamRequestHandler

shared_data = {}

server = None

class IrcCatListener(ThreadingMixIn, StreamRequestHandler):
    def handle(self):
        fleet = getfleet()
        msg = self.rfile.readline().strip()
        logging.warn("received %s" % msg)
        dest, msg = self.splitMsg(msg)
        for chan in dest:
            logging.info("sending to %s" % chan)
            for botname in cfg.botnames:
                bot = fleet.byname(botname)
                if bot:
                    if chan[0] == "#" and chan not in bot.state['joinedchannels']:
                        logging.warn("someone tried to make me say something in a channel i'm not in!")
                    else:
                        bot.say(chan, msg)
                else: logging.error("can't find %s bot in fleet" % botname)

    def splitMsg(self, message):
        if message[0] not in ('#', '@'): return [], message
        dest, message = message.split(" ", 1)
        dest = [x.strip().strip("@") for x in dest.split(",")]
        finalDest = []
        for d in dest:
            finalDest.append(d)
            if d in cfg.aliases.keys():
                for alias in cfg.aliases[d]:
                    finalDest.append(alias)
        return finalDest, message

def init():
    global server
    server = SocketServer.TCPServer((cfg.host, cfg.port), IrcCatListener)
    logging.warn("starting irccat server on %s:%s" % (cfg.host, cfg.port))
    start_new_thread(server.serve_forever, ())

def shutdown():
    if server:
        logging.warn("shutting down the irccat server")
        server.shutdown()

def handle_irccat_add_alias(bot, ievent):
    if len(ievent.args) != 1:
        ievent.reply("syntax: irccat_add_alias <alias> (where <alias> is the channel you want notifications for)")
        return
    dest = ievent.args[0]
    if dest not in cfg.aliases:
        cfg.aliases[dest] = []
    if ievent.channel not in cfg.aliases[dest]:
        cfg.aliases[dest].append(ievent.channel)
    cfg.save()
    ievent.reply("%s will now receive irccat messages directed at %s" % (ievent.channel, dest))
cmnds.add("irccat_add_alias", handle_irccat_add_alias, ['OPER'])
examples.add("irccat_add_alias", "add an alias to the current channel from the specified one", "irccat_add_alias #firebreath")

def handle_irccat_list_aliases(bot, ievent):
    """ List all aliases defined for the current channel """
    if len(ievent.args) != 1:
        ievent.reply("syntax: irccat_list_aliases ")
        return

    aliases = [dest for dest, chanlist in cfg.aliases.iteritems() if ievent.channel in chanlist]

    ievent.reply("%s is receiving irccat messages directed at: %s" % (ievent.channel, ", ".join(aliases)))
cmnds.add("irccat_list_aliases", handle_irccat_add_alias, ['OPER'])
examples.add("irccat_list_aliases", "lists the aliases for the current channel", "irccat_list_aliases")

def handle_irccat_del_alias(bot, ievent):
    if len(ievent.args) != 1:
        ievent.reply("syntax: irccat_del_alias <alias> (where <alias> is the channel you no longer want notifications for)")
        return
    dest = ievent.args[0]
    if dest not in cfg.aliases or ievent.channel not in cfg.aliases[dest]:
        ievent.reply("%s is not an alias for %s" % (ievent.channel, dest))
        return

    cfg.aliases[dest].remove(ievent.channel)
    ievent.reply("%s will no longer receive irccat messages directed at %s" % (ievent.channel, dest))
    cfg.save()
cmnds.add("irccat_del_alias", handle_irccat_add_alias, ['OPER'])
examples.add("irccat_del_alias", "add an alias to the current channel from the specified one", "irccat_del_alias #firebreath")

