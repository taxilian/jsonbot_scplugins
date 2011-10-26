#!/usr/bin/env python
"""
jira.py - jsonbot module; adapted from a phenny module by Sean B. Palmer
Copyright 2008, Sean B. Palmer, inamidst.com
Licensed under the Eiffel Forum License 2.

Modifications Copyright 2011, Richard Bateman

http://inamidst.com/phenny/
"""

from jsb.utils.exception import handle_exception
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

def getRpcClient(server):
    if project["name"] not in rpc_clients:
        base_url = "%s/api/xmlrpc" % project["url"]
        server = xmlrpclib.ServerProxy(base_url)
        auth = server.login(project["username"], project["password"])
        logging.info("Created new RPC client for %s with auth token: %s" % (project["name"], auth))
        rpc_clients[project["name"]] = (server, auth)

    return rpc_clients[project["name"]]

def get_status(self):
    server = xmlrpclib.ServerProxy(self.config.jira_baseurl)
    print self.config.jira_baseurl
    try:
        # self.jira = {}
        auth = server.jira1.login(self.config.jira_username, self.config.jira_password)
        server_statuses = server.jira1.getStatuses(auth)
        print server_statuses
        jira_statuses = {}
        for status in server_statuses:
            if self.config.jira_mappings['status'].has_key(status['name']):
                jira_statuses[status['id']] = self.config.jira_mappings['status'][status['name']]
            else:
                jira_statuses[status['id']] = status['name']
        self.jira_statuses = jira_statuses
        server_priorities = server.jira1.getPriorities(auth)
        jira_priorities = {}
        for priority in server_priorities:
            if self.config.jira_mappings['priority'].has_key(priority['name']):
                jira_priorities[priority['id']] = self.config.jira_mappings['priority'][priority['name']]
            else:
                jira_priorities[priority['id']] = priority['name']
        self.jira_priorities = jira_priorities

        info = server.jira1.getServerInfo(auth)
        self.jira_baseurl = info['baseUrl']
    except xmlrpclib.Error, v:
        print "XMLRPC ERROR: ", v

def _ticket_lookup(self, ticket):
    server = xmlrpclib.ServerProxy(self.config.jira_baseurl)
    print self.config.jira_baseurl
    try:
        auth = server.jira1.login(self.config.jira_username, self.config.jira_password)
        info = server.jira1.getIssue(auth, ticket)
        print info
        return info
    except xmlrpclib.Error, v:
        print "XMLRPC ERROR:", v
    return None

def ticket_lookup(self, ticket):
    """docstring for ticket_lookup"""
    info = _ticket_lookup(self, ticket)
    if info:
        self.say( "%s: Summary:     %s" % (info['key'], info['summary']))
        if info.has_key('assignee'):
            self.say( "%s: Assigned To: %s" % (info['key'], info['assignee']))
        else:
            self.say( "%s: Assigned To: Unassigned" % (info['key']))
        data = (info["key"], self.jira_priorities[info['priority']], self.jira_statuses[info['status']], self.jira_baseurl, info["key"])
        self.say( "%s: Priority: %s, Status: %s, %s/browse/%s" % data)

def f_jira(phenny, input):
    """JIRA stuff"""
    if not input.sender in phenny.config.jira_channels and not input.owner:
        return
    for ticket in phenny.jira_re.findall(input.bytes):
        if ticket not in recent_tickets or recent_tickets[ticket] < time.time() - min_age:
            recent_tickets[ticket] = time.time()
            ticket_lookup(phenny, ticket)
f_jira.priority = 'low'

def f_jiratoac(phenny, input):
    """docstring for f_jiratoac"""
    ticket = input.group(2)
    info = _ticket_lookup(phenny, ticket)
    #if info:
    #    project = modules.activecollab.current_project(phenny, input.sender)
    #    if project:
    #        summary = '(%s) %s' % (ticket, info['summary'])
    #        js = modules.activecollab.create_ticket(phenny, project, summary)
    #        phenny.say('Created ticket %s-%s: %s' % (project, js['id'], js['permalink']))
f_jiratoac.commands = [ 'jiratoac' ]
f_jiratoac.priority = 'medium'

def f_search_confluence(self, input):
    print "Wiki search", input
    query = input.group(1)
    if not input.sender in self.config.jira_channels and not input.owner:
        return
    server = xmlrpclib.ServerProxy(self.config.confluence_baseurl)
    rpc = server.confluence1
    auth = rpc.login(self.config.confluence_username, self.config.confluence_password)
    results = rpc.search(auth, query, self.config.confluence_searchresults)

    self.say ("%s results found. Note: Results limited to %s" % (len(results), self.config.confluence_searchresults))
    for page in results[:self.config.confluence_searchresults]:
        self.say ('"%s": %s' % (page["title"], shorten(page["url"])))

f_search_confluence.rule = r'^\!wiki (.*)'
f_search_confluence.priority = "medium"
f_search_confluence.thread = True

def setup(self):
    get_status(self)
    re_str = r'((?:' + '|'.join(self.config.jira_projects) + ')-(?:\d+))'
    self.jira_re = re.compile(re_str)
    f_jira.rule = r'.*' + re_str

