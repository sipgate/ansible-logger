#!/usr/bin/env python
# ansible-logger
# Copyright (C) 2015  sipgate GmbH
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import MySQLdb as mdb
import ConfigParser
import random
import time
import datetime

configDefaults = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'db': 'ansible'}
Config = ConfigParser.ConfigParser(configDefaults)
basePath = os.path.dirname(os.path.realpath(__file__))
configFile = basePath + "/../../ansible-callbacks/ansible-logger.conf"
Config.read(configFile)

# config
try:
    mysqlHost = Config.get("database", "host")
    mysqlUser = Config.get("database", "user")
    mysqlPassword = Config.get("database", "password")
    mysqlDb = Config.get("database", "db")
except:
    print("Could not read config from %s" % (configFile))

try:
	con = mdb.connect(mysqlHost, mysqlUser, mysqlPassword, mysqlDb)
	cur = con.cursor()
except:
	print("Could not connect to Database %s on %s as user %s" % (mysqlDb, mysqlHost, mysqlUser))

try:
	cur.execute("SELECT COUNT(*) FROM hosts")
	hostCount = cur.fetchone()[0]
	if hostCount > 0:
		print "There seems to be data in your database. Please clean up first!"
		sys.exit(1)
except mdb.Error as e:
	print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])

hostnames = []
hostnameIds = []
hostpatterns = []
playbooks = []
tasks = []
facts = []

myPid = os.getpid()
myLogin = os.getlogin()
myPath = os.getcwd()
myTime = time.time()
seedStr = str(myPid) + str(myLogin) + str(myPath) + str(myTime)
random.seed(seedStr)

with open('hostnames') as inputfile:
	for line in inputfile:
		hostnames.append(line.strip())

with open('hostpatterns') as inputfile:
	for line in inputfile:
		hostpatterns.append(line.strip())
with open('playbooks') as inputfile:
	for line in inputfile:
		playbooks.append(line.strip())
with open('tasks') as inputfile:
	for line in inputfile:
		tasks.append(line.strip().split(';'))

for root, dirs, filenames in os.walk("facts"):
	for f in filenames:
		with open("facts/" + f) as inputfile:
			factCollection = []
			for line in inputfile:
				factCollection.append(line.strip().split(';'))
			facts.append(factCollection)


for k,v in enumerate(hostnames):
	try:
		cur.execute("INSERT INTO hosts (host, last_seen) VALUES (%s,NOW())", (v))
		hId = cur.lastrowid
		hostnameIds.append(hId)
		hostFacts = random.choice(facts)
		for k,v in enumerate(hostFacts):
			try:
				cur.execute("SELECT id FROM facts WHERE fact=%s", (v[0]))
				rows = cur.rowcount
			except mdb.Error as e:
				print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
			if rows > 0:
				fId = cur.fetchone()[0]
			else:
				cur.execute("INSERT INTO facts (fact) VALUES (%s)", (v[0]))
				fId = cur.lastrowid
			try:
				cur.execute("INSERT INTO fact_data (host_id, fact_id, value) VALUES (%s,%s,%s)", (
					hId,
					fId,
					v[1]))
			except mdb.Error as e:
				print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])

		con.commit()
	except mdb.Error as e:
		print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
	
now = time.time()
yesNo = [ 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ]
noYes = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1 ]
for run in range(0,200):
	playHosts = []
	for host in range(0,random.randrange(1,8)):
		playHosts.append(random.choice(hostnameIds))
	randomSub = random.randrange(60,6400)
	startTime = now - randomSub
	randomAdd = random.randrange(10,300)
	endTime = startTime + randomAdd
	sqlStartTime = datetime.datetime.fromtimestamp(startTime).strftime('%Y-%m-%d %H:%M:%S')
	sqlEndTime = datetime.datetime.fromtimestamp(endTime).strftime('%Y-%m-%d %H:%M:%S')
	try:
		cur.execute("INSERT INTO playbook_log (host_pattern,start,end,running) VALUES(%s,%s,%s,'0')", (
			random.choice(hostpatterns),
			sqlStartTime,
			sqlEndTime))
		pId = cur.lastrowid
	except mdb.Error as e:
		print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
	for task in range(3,random.randrange(4,15)):
		startTime = startTime + 5
		sqlStartTime = datetime.datetime.fromtimestamp(startTime).strftime('%Y-%m-%d %H:%M:%S')
		thisTask = random.choice(tasks)
		try:
			cur.execute("INSERT INTO task_log (playbook_id, name, start) VALUES (%s,%s,%s)", (
				pId,
				thisTask[0],
				sqlStartTime))
			tId = cur.lastrowid
		except mdb.Error as e:
			print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
		for key,hostId in enumerate(playHosts):
			ok = random.choice(yesNo)
			if ok == 0:
				unreachable = random.choice(noYes)
				skipped = 0
			else:
				unreachable = 0
				skipped = random.choice(noYes)
			changed = random.choice(noYes)
			try:
				cur.execute("INSERT INTO runner_log (host_id, task_id, module, changed, start, ok, unreachable, skipped) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (
					hostId,
					tId,
					thisTask[1],
					changed,
					sqlStartTime,
					ok,
					unreachable,
					skipped))
			except mdb.Error as e:
				print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
	con.commit()
	
		


con.close()

