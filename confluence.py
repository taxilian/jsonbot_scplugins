from jsb.lib.callbacks import callbacks
from jsb.lib.commands import cmnds
from jsb.lib.persist import PlugPersist
from jsb.lib.examples import examples
from jsb.plugs.common.tinyurl import get_tinyurl
import logging
import xmlrpclib
import re
import time

def handle_add_fisheye_project(bot, ievent):
    """ configure a new fisheye project; syntax: add_fisheye_project [project name] [url] [username] [password] """
    if len(ievent.args) != 4:
        ievent.reply("syntax: add_fisheye_project [project name] [url] [username] [password]")
        return

    project = {
        "name": ievent.args[0],
        "url": ievent.args[1].strip("/"),
        "username": ievent.args[2],
        "password": ievent.args[3],
    }

    if not cfg.data.has_key("projects"):
        cfg.data["projects"] = {}
    cfg.data["projects"][project["name"]] = project
    cfg.save()

    ievent.reply("Added fisheye project %s" % project["name"])
cmnds.add("add_fisheye_project", handle_add_fisheye_project, ["OPER"])
examples.add("add_fisheye_project", "add a fisheye project", "add_fisheye_project FireBreath http://code.firebreath.org myuser mypassword")


