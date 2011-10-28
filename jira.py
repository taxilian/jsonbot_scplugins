#!/usr/bin/env python
"""
jira.py - jsonbot module for performing lookups on a jira server
Copyright 2011, Richard Bateman

Special thanks to Sean B. Palmer for his phenny module; many of the ideas for
this were adapted from that plugin

http://inamidst.com/phenny/
"""

from jsb.lib.callbacks import callbacks
from jsb.lib.commands import cmnds
from jsb.lib.persist import PlugPersist
from jsb.lib.examples import examples
from jsb.plugs.common.tinyurl import get_tinyurl
import logging
import xmlrpclib
import re
import time
#import modules.activecollab

recent_tickets = {}
min_age = 60 * 5
rpc_clients = {}
cfg = PlugPersist('jira', {})

def getServerInfo(server, auth):
    try:
        server_statuses = server.jira1.getStatuses(auth)
        statusMap = {}
        for status in server_statuses:
            statusMap[status['id']] = status['name']

        server_priorities = server.jira1.getPriorities(auth)

        priorityMap = {}
        for priority in server_priorities:
            priorityMap[priority['id']] = priority['name']

        info = server.jira1.getServerInfo(auth)
        jira_baseurl = info['baseUrl']

        return {
            "statusMap": statusMap,
            "priorityMap": priorityMap,
            "baseUrl": jira_baseurl
        }
    except xmlrpclib.Error, v:
        print "XMLRPC ERROR: ",


def getRpcClient(sInfo):
    if sInfo["name"] not in rpc_clients:
        base_url = "%s/rpc/xmlrpc" % sInfo["url"]
        server = xmlrpclib.ServerProxy(base_url)

        username, password = sInfo["username"], sInfo["password"]
        auth = server.jira1.login(username, password)

        rpc_clients[sInfo["name"]] = (server, auth)

        sInfo["serverInfo"] = getServerInfo(server, auth)
        logging.info("Server info: %s" % sInfo)

    return rpc_clients[sInfo["name"]]

def getJiraIssue(s, ticket):
    server, auth = getRpcClient(s)
    try:
        info = server.jira1.getIssue(auth, ticket)
        return info
    except xmlrpclib.Error, v:
        print "XMLRPC ERROR:", v
    return None

def getJiraIssueMessage(s, ticket):
    """docstring for ticket_lookup"""
    info = getJiraIssue(s, ticket)
    logging.info("jira ticket: %s is %s" % (ticket, info))
    if info:
        outInfo = []
        outInfo.append("%s: Summary:     %s" % (info['key'], info['summary']))
        if info.has_key('assignee'):
            outInfo.append( "%s: Assigned To: %s" % (info['key'], info['assignee']))
        else:
            outInfo.append( "%s: Assigned To: Unassigned" % (info['key']))
        data = (info["key"], s["serverInfo"]["priorityMap"][info['priority']], s["serverInfo"]["statusMap"][info['status']], s["serverInfo"]["baseUrl"], info["key"])
        outInfo.append( "%s: Priority: %s, Status: %s, %s/browse/%s" % data)

        logging.info("Jira ticket text: %s" % outInfo)
        return outInfo

def getMatchRegEx(prefixList):
    prefixLookup = "(%s)" % "|".join(prefixList)

    test = re.compile(".*(%s-[0-9]+).*" % prefixLookup)
    return test


def containsJiraTag(bot, ievent):
    if ievent.how == "backgound": return 0

    prefixList = set()
    for server, serverData in cfg.data["servers"].iteritems():
        if ievent.channel in serverData["channels"]:
            prefixList.update(serverData["channels"][ievent.channel])

    test = getMatchRegEx(prefixList)
    fnd = test.match(ievent.txt)

    if fnd:
        return 1

    return 0

def doLookup(bot, ievent):
    prefixList = set()
    serversForPrefix = {}
    for server, serverData in cfg.data["servers"].iteritems():
        if ievent.channel in serverData["channels"]:
            for prefix in serverData["channels"][ievent.channel]:
                serversForPrefix[prefix] = server
                prefixList.add(prefix)

    test = getMatchRegEx(prefixList)
    fnd = test.match(ievent.txt)
    if fnd:
        ticket = fnd.group(1)
        prefix = fnd.group(2)
        logging.info("Found: %s %s" % (ticket, prefix))
        logging.info("servers: %s" % cfg.data["servers"])
        server = serversForPrefix[prefix]

        msg = getJiraIssueMessage(cfg.data["servers"][server], ticket)
        for line in msg:
            bot.say(ievent.channel, line)


callbacks.add('PRIVMSG', doLookup, containsJiraTag, threaded=True)
callbacks.add('CONSOLE', doLookup, containsJiraTag, threaded=True)
callbacks.add('MESSAGE', doLookup, containsJiraTag, threaded=True)
callbacks.add('DISPATCH', doLookup, containsJiraTag, threaded=True)
callbacks.add('TORNADO', doLookup, containsJiraTag, threaded=True)

def handle_add_jira_server(bot, ievent):
    """ configure a new jira server; syntax: add_jira_server [server name] [url] [username] [password] """
    if len(ievent.args) != 4:
        ievent.reply("syntax: add_jira_server [server name] [url] [username] [password]")
        return

    server = {
        "name": ievent.args[0],
        "url": ievent.args[1].strip("/"),
        "username": ievent.args[2],
        "password": ievent.args[3],
        "channels": {},
        "serverInfo": {},
    }

    if not cfg.data.has_key("servers"):
        cfg.data["servers"] = {}
    cfg.data["servers"][server["name"]] = server
    cfg.save()

    ievent.reply("Added jira server %s" % server["name"])
cmnds.add("add_jira_server", handle_add_jira_server, ["OPER"])
examples.add("add_jira_server", "add a jira server", "add_jira_server FireBreath http://jira.firebreath.org myuser mypassword")

def handle_del_jira_server(bot, ievent):
    """ remove a jira server; syntax: del_jira_server """
    if len(ievent.args) != 1:
        ievent.reply("syntax: del_jira_server [server name]")
        return

    serverName = ievent.args[0]
    if not cfg.data.has_key("servers"):
        cfg.data["servers"] = {}
    if serverName in cfg.data["servers"]:
        del cfg.data["servers"][serverName]
        cfg.save()
        ievent.reply("Deleted jira server %s" % serverName)
    else:
        ievent.reply("Unknown jira server %s" % serverName)
cmnds.add("del_jira_server", handle_del_jira_server, ["OPER"])
examples.add("del_jira_server", "del a jira server", "del_jira_server FireBreath http://jira.firebreath.org myuser mypassword")

def handle_jira_issue_lookup_enable(bot, ievent):
    """ enable lookups for jira issues in the current channel; syntax: jira_issue_lookup_enable [server] [prefix] """
    if len(ievent.args) != 2:
        ievent.reply("syntax: jira_issue_lookup_enable [server] [prefix]")
        return

    serverName, prefix = ievent.args
    if not "servers" in cfg.data or not serverName in cfg.data["servers"]:
        ievent.reply("Unknown server %s" % serverName)
        return

    prefixSet = set(cfg.data["prefixes"]) if "prefixes" in cfg.data else set()
    server = cfg.data["servers"][serverName]
    if ievent.channel not in server["channels"]:
        server["channels"][ievent.channel] = []

    if not prefix in server["channels"][ievent.channel]:
        server["channels"][ievent.channel].append(prefix)

    prefixSet.add(prefix)

    cfg.data["prefixes"] = list(prefixSet)
    cfg.save()
    ievent.reply("enabled lookups of %s-* jira tickets in this channel on server %s" % (prefix, serverName))
cmnds.add("jira_issue_lookup_enable", handle_jira_issue_lookup_enable, ["OPER"])
examples.add("jira_issue_lookup_enable", "enable lookups of jira tickets in the channel", "jira_issue_lookup_enable jiraserver FIREBREATH")

def handle_jira_issue_lookup_disable(bot, ievent):
    """ enable lookups for jira issues in the current channel for a given server; syntax: jira_issue_lookup_disable [server] """
    if len(ievent.args) != 1:
        ievent.reply("syntax: jira_issue_lookup_disable [server]")
        return

    serverName = ievent.args[0]
    if not "servers" in cfg.data or not serverName in cfg.data["servers"]:
        ievent.reply("Unknown server %s" % serverName)
        return

    server = cfg.data["servers"][serverName]
    if ievent.channel in server["channels"]:
        server["channels"].remove(ievent.channel)
        ievent.reply("disabled lookups of jira tickets on server %s from this server" % serverName)

