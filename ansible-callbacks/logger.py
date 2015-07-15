
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
import MySQLdb as mdb
import pprint
import json
import re
import ConfigParser
import logging
import time

configDefaults = {
	'host': 'localhost',
	'user': 'root',
	'password': '',
	'db': 'ansible',
	'logging': False,
	'logpath': '/tmp/',
	'loglevel': 'warn'}
Config = ConfigParser.ConfigParser(configDefaults)
basePath = os.path.dirname(os.path.realpath(__file__))
configFile = basePath + "/ansible-logger.conf"
Config.read(configFile)

# config
try:
	mysqlHost = Config.get("database","host")
	mysqlUser = Config.get("database","user")
	mysqlPassword = Config.get("database","password")
	mysqlDb = Config.get("database","db")
	logEnabled = Config.getboolean("log-settings","logging")
	logPath = Config.get("log-settings","logpath")
	logLevel = Config.get("log-settings","loglevel")
except:
	print("Could not read config from %s" % (configFile))

if logEnabled:
	logFile = logPath + "ansible-logger." + str(time.time()) + ".log"
	if logLevel == "warn":
		configuredLogLevel = logging.WARNING
	elif logLevel == "crit":
		configuredLogLevel = logging.CRITICAL
	elif logLevel == "info":
		configuredLogLevel = logging.INFO
	elif logLevel == "debug":
		configuredLogLevel = logging.DEBUG
	else:
		configuredLogLevel = logging.INFO

	logging.basicConfig(filename=logFile,level = configuredLogLevel)
	logging.info("Loglevel set to %s" % (configuredLogLevel))

# initialise some variables
playbookId = -1
taskId = -1

def playbookLog(hostPattern):

	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb)
	cur = con.cursor()
	id = -1
	try:
		cur.execute("INSERT INTO playbook_log (host_pattern, running) VALUES (%s,'1')", (hostPattern))
		id = cur.lastrowid
	except mdb.Error as e:
		if logEnabled:
			logging.critical("playbookLog() - This query failed to execute: %s" %(cur._last_executed))
			logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
	finally:
		cur.close()
		con.commit()
		con.close()
	return id

def playbookFinished():

	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb)
	cur = con.cursor()
	try:
		cur.execute("UPDATE playbook_log SET end = NOW(), running='0' WHERE id = %s", (playbookId))
	except mdb.Error as e:
		if logEnabled:
			logging.critical("playbookFinished() - This query failed to execute: %s" %(cur._last_executed))
			logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
	finally:
		cur.close()
		con.commit()
		con.close()


def taskLog(name):

	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb)
	cur = con.cursor()
	id = -1
	try:
		cur.execute("INSERT INTO task_log (playbook_id, name) VALUES (%s,%s)", (playbookId, name))
		id = cur.lastrowid
	except mdb.Error as e:
		if logEnabled:
			logging.critical("taskLog() - This query failed to execute: %s" %(cur._last_executed))
			logging.critial("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
	finally:
		cur.close()
		con.commit()
		con.close()

	return id


def isDelegatedHostname(hostName):
	pattern = re.compile("^[a-zA-Z0-9\.-]+ -> [a-zA-Z0-9\.-]+$")
	if pattern.match(hostName):
		return True;
	else:
		return False;

def insertOrUpdateHostName(hostName):

	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb)
	cur = con.cursor()
	# get ID of given host
	try:
		try:
			cur.execute("SELECT id FROM hosts WHERE host=%s",(hostName))
			rows = cur.rowcount
		except mdb.Error as e:
			if logEnabled:
				logging.critical("insertOrUpdateHostName() - This query failed to execute: %s" %(cur._last_executed))
				logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
			pass

		# check number of results - it might be a new host
		if rows > 0:
			try:
				hostId = cur.fetchone()[0]
				cur.execute("UPDATE hosts SET last_seen = NOW() WHERE id=%s", (hostId))
			except mdb.Error as e:
				if logEnabled:
					logging.critical("insertOrUpdateHostName() - This query failed to execute: %s" %(cur._last_executed))
					logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
				pass

		else:
			# add a new host to the table
			try:
				cur.execute("INSERT INTO hosts (host, last_seen) VALUES (%s,NOW())", (hostName))
				hostId = cur.lastrowid
			except mdb.Error as e:
				if logEnabled:
					logging.critical("insertOrUpdateHostName() - This query failed to execute: %s" %(cur._last_executed))
					logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
				pass
	finally:
		cur.close()
		con.commit()
		con.close()
	return hostId

def insertOrUpdateFactName(factName):

	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb) 
	cur = con.cursor()
	factId = -1
	# get ID of given fact
	try:
		try:
			cur.execute("SELECT id FROM facts WHERE fact=%s",(factName))
			rows = cur.rowcount
		except mdb.Error as e:
			if logEnabled:
				logging.critical("insertOrUpdateFactName() - This query failed to execute: %s" %(cur._last_executed))
				logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
			pass

		# check number of results - it might be a new fact
		if rows > 0:
			factId = cur.fetchone()[0]
		else:
			# add a new fact to the table
			try:
				cur.execute("INSERT INTO facts (fact) VALUES (%s)", (factName))
				factId = cur.lastrowid
			except mdb.Error as e:
				if logEnabled:
					logging.critical("insertOrUpdateFactName() - This query failed to execute: %s" %(cur._last_executed))
					logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
				pass
	finally:
		cur.close()
		con.commit()
		con.close()
	return factId

def storeFactData(hostId, factId, factData):
	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb)
	cur = con.cursor()
	# get ID of given fact
	try:
		try:
			cur.execute("SELECT fact_id FROM fact_data WHERE fact_id=%s AND host_id=%s",(factId, hostId))
			rows = cur.rowcount
		except mdb.Error as e:
			if logEnabled:
				logging.critical("insertOrUpdateFactName() - This query failed to execute: %s" %(cur._last_executed))
				logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
			pass

		# check number of results - it might be a new fact
		if rows > 0:
			try:
				cur.execute("UPDATE fact_data SET value=%s WHERE fact_id=%s AND host_id=%s",(factData, factId, hostId))
			except mdb.Error as e:
				if logEnabled:
					logging.critical("storeFactData() - This query failed to execute: %s" %(cur._last_executed))
					logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
				pass
		else:
			# add new fact data to the table
			try:
				cur.execute("INSERT INTO fact_data (fact_id, host_id, value) VALUES (%s,%s,%s)", (factId, hostId, factData))
			except mdb.Error as e:
				if logEnabled:
					logging.critical("storeFactData() - This query failed to execute: %s" %(cur._last_executed))
					logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
				pass
	finally:
		cur.close()
		con.commit()
		con.close()

def storeFacts(hostId, facts, parentString = None):
	if parentString == None:
		parentString = ""
	else:
		parentString = parentString + "."

	if isinstance(facts, dict):
		for k,v in facts.items():
			if isinstance(v, dict):
				storeFacts(hostId, v, parentString + k)
			elif isinstance(v, list):
				storeFacts(hostId, v, parentString + k)
			else:
				factName = parentString + k
				factId = insertOrUpdateFactName(factName)
				storeFactData(hostId, factId, v)

	elif isinstance(facts, list):
		for k,v in enumerate(facts) :
			if isinstance(v, dict):
				storeFacts(hostId, v, parentString + str(k))
			elif isinstance(v, list):
				storeFacts(hostId, v, parentString + str(k))
			else:
				factName = parentString + str(k)
				factId = insertOrUpdateFactName(factName)
				storeFactData(hostId, factId, v)

def storeRunnerLog(hostId, delegateHost, module, details, ok):
	# evaluate changed flag (MySQL uses TINYINT(1) for bool values)
	if details.get("changed", False):
		changed = 1
	else:
		changed = 0

	if ok:
		statusInt = 1
	else:
		statusInt = 0

	# remove possible useless information before mis-interpreting them as facts
	try:
		del details["changed"]
	except:
		pass
	try:
		del details["module_setup"]
	except:
		pass

	# convert whatever remains to JSON (depending on the ansible module, there might be more or less extra information)
	extraInfo = json.dumps(details)

	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb)
	cur = con.cursor()
	try:
		cur.execute("INSERT INTO runner_log (`host_id`, `task_id`, `module`, `changed`, `extra_info`, `ok`, `delegate_host`) VALUES (%s,%s,%s,%s,%s,%s,%s)",
			(hostId,
			taskId,
			module,
			changed,
			extraInfo,
			statusInt,
			delegateHost))
	except mdb.Error as e:
		if logEnabled:
			logging.critical("storeRunnerLog() - This query failed to execute: %s" %(cur._last_executed))
			logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
		pass
	finally:
		cur.close()
		con.commit()
		con.close()

def storeRunnerLogMissed(hostId, delegateHost, reason, msg):
	# host was unreachable or skipped - not much to do here
	if reason == "unreachable":
		unreachInt = 1
		skipInt = 0
	elif reason == "skipped":
		unreachInt = 0
		skipInt = 1
	else:
		return

	if taskId == -1:
		# there is no notification about the "setup"/"gather_facts" tasks - so if the setup task fails, the following query would fail es well since the taskId is still at default (-1)
		return

	con = mdb.connect(mysqlHost,mysqlUser,mysqlPassword,mysqlDb) 
	cur = con.cursor()
	try:
		cur.execute("INSERT INTO runner_log (`host_id`, `task_id`, `module`, `changed`, `extra_info`, `ok`, `delegate_host`, `unreachable`, `skipped`, `fail_msg`) VALUES (%s,%s,NULL,'0',NULL,'1',%s,%s,%s,%s)",
			(hostId,
			taskId,
			delegateHost,
			unreachInt,
			skipInt,
			msg))
	except mdb.Error as e:
		if logEnabled:
			logging.critical("storeRunnerLogMissed() - This query failed to execute: %s" %(cur._last_executed))
			logging.critical("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
		pass
	finally:
		cur.close()
		con.commit()
		con.close()
	return

def runnerLog(hostName, data, ok = True, unreachable = False, skipped = False):
	if logEnabled:
		logging.debug("runnerLog(): Called for host=%s ok=%s unreachable=%s skipped=%s" % (hostName, ok, unreachable, skipped))

	# check if this is a delegate_to: situation (hostnameA -> hostnameB) and act accordingly.
	if isDelegatedHostname(hostName):
		delegateHost = hostName.split(' ')[2]
		hostName = hostName.split(' ')[0]
	else:
		delegateHost = None

	if type(data) == dict:
		# we might be removing some things from the dict before storing parts of it in
		# the database (see storeRunnerLog()). therefore we want a 'working copy' here 
		workData = data.copy()

		hostId = insertOrUpdateHostName(hostName)
		invocation = workData.pop('invocation', None)
		module = invocation.get('module_name', None)
		if module == 'setup':
			facts = workData.get('ansible_facts', None)
			storeFacts(hostId,facts)
		else:
			storeRunnerLog(hostId, delegateHost, module ,workData, ok)
	else:
		if unreachable:
			hostId = insertOrUpdateHostName(hostName)
			reason = "unreachable"
			msg = data
			storeRunnerLogMissed(hostId, delegateHost, reason, msg)
		elif skipped:
			hostId = insertOrUpdateHostName(hostName)
			reason = "skipped"
			msg = None
			storeRunnerLogMissed(hostId, delegateHost, reason, msg)


class CallbackModule(object):
	def on_any(self, *args, **kwargs):
		pass
	def runner_on_failed(self, host, res, ignore_errors=False):
		if logEnabled:
			logging.debug("Callback: runner_on_failed(): host=%s, ingore_errors=%s" % (host, ignore_errors))
		if ignore_errors:
			okStatus = True
		else:
			okStatus = False
		runnerLog(host, res, okStatus)
		pass
	def runner_on_ok(self, host, res):
		if logEnabled:
			logging.debug("Callback: runner_on_ok(): host=%s" % (host))
		okStatus = True;
		runnerLog(host, res,okStatus)
		pass
	def runner_on_skipped(self, host, item=None):
		if logEnabled:
			logging.debug("Callback: runner_on_skipped(): host=%s" % (host))
		okStatus = False
		unreachableStatus = False
		skippedStatus = True
		runnerLog(host, None, okStatus, unreachableStatus, skippedStatus)
		pass
	def runner_on_unreachable(self, host, res):
		if logEnabled:
			logging.debug("Callback: runner_on_unreachable(): host=%s" % (host))
		okStatus = False
		unreachableStatus = True
		runnerLog(host, res, okStatus, unreachableStatus)
		pass
	def runner_on_no_hosts(self):
		if logEnabled:
			logging.debug("Callback: runner_on_no_hosts(): no-op")
		pass
	def runner_on_async_poll(self, host, res, jid, clock):
		if logEnabled:
			logging.debug("Callback: runner_on_async_poll(): host=%s" % (host))
		runnerLog(host, res)
		pass
	def runner_on_async_ok(self, host, res, jid):
		if logEnabled:
			logging.debug("Callback: runner_on_async_ok(): host=%s" % (host))
		okStatus = True
		runnerLog(host, res, okStatus)
		pass
	def runner_on_async_failed(self, host, res, jid):
		if logEnabled:
			logging.debug("Callback: runner_on_async_failed(): host=%s" % (host))
		okStatus = False
		runnerLog(host, res, okStatus)
		pass
	def playbook_on_start(self):
		if logEnabled:
			logging.debug("Callback: playbook_on_start(): no-op")
		pass
	def playbook_on_notify(self, host, handler):
		if logEnabled:
			logging.debug("Callback: playbook_on_notify(): host=%s no-op" % (host))
		pass
	def playbook_on_no_hosts_matched(self):
		if logEnabled:
			logging.debug("Callback: playbook_on_no_hosts_matched(): no-op")
		pass
	def playbook_on_no_hosts_remaining(self):
		if logEnabled:
			logging.debug("Callback: playbook_on_no_hosts_remaining(): no-op")
		pass
	def playbook_on_task_start(self, name, is_conditional):
		global taskId
		if logEnabled:
			logging.debug("Callback: playbook_on_task_start(): task=%s" % (name))
		taskId = taskLog(name)
		pass
	def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
		if logEnabled:
			logging.debug("Callback: playbook_on_vars_prompt(): varname=%s no-op" % (varname))
		pass
	def playbook_on_setup(self):
		if logEnabled:
			logging.debug("Callback: playbook_on_setup(): no-op")
		pass
	def playbook_on_import_for_host(self, host, imported_file):
		if logEnabled:
			logging.debug("Callback: playbook_on_import_for_host(): host=%s no-op" % (host))
		pass
	def playbook_on_not_import_for_host(self, host, missing_file):
		if logEnabled:
			logging.debug("Callback: playbook_on_not_import_for_host(): host=%s no-op" % (host))
		pass
	def playbook_on_play_start(self, pattern):
		global playbookId
		if logEnabled:
			logging.debug("Callback: playbook_on_play_start(): pattern=%s" % (pattern))
		playbookId = playbookLog(pattern)
		pass
	def playbook_on_stats(self, stats):
		if logEnabled:
			logging.debug("Callback: playbook_on_stats():")
		playbookFinished()
		pass

