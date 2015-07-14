<?php

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

class ansibleLogger {
	private $con;

	function ansibleLogger() {
		global $config;
		$this->con = new mysqli($config["db"]["server"], $config["db"]["user"], $config["db"]["password"], $config["db"]["db"]);
		if($this->con->connect_errno) {
			die("Sadly, the database as passed away.\n");
		}
	}

	function validateDate($date, $format = 'Y-m-d H:i:s') {
		$d = DateTime::createFromFormat($format, $date);
		return $d && $d->format($format) == $date;
	}
	
	function prettyTime($seconds) {
		$ret = "";

		$days = intval(intval($seconds) / (3600*24));
		if($days> 0) {
			$ret .= $days . "d ";
		}

		$hours = (intval($seconds) / 3600) % 24;
		if($hours > 0) {
			$ret .= $hours . "h ";
		}

		$minutes = (intval($seconds) / 60) % 60;
		if($minutes > 0) {
			$ret .= $minutes. "m ";
		}

		$seconds = intval($seconds) % 60;
		if ($seconds > 0) {
			$ret .= $seconds . "s";
		}

		return $ret;	
	}

	function getPlaybookHostCount($pId) {
		$hC = $this->con->prepare("SELECT
							COUNT(DISTINCT hosts.id)
						FROM
							hosts,
							runner_log,
							task_log
						WHERE
							task_log.playbook_id = ? AND
							task_log.id = runner_log.task_id AND
							hosts.id = runner_log.host_id");
		$hC->bind_param("s",$pId);
		$hC->execute();
		$hC->bind_result($hostCount);
		$hC->fetch();
		return $hostCount;
	}

	function getPlaybook($pId) {
		$play = $this->con->prepare("SELECT
                                                        playbook_log.start,
                                                        playbook_log.host_pattern,
							playbook_log.end,
							TIMESTAMPDIFF(SECOND, playbook_log.start, playbook_log.end),
							playbook_log.running
                                                FROM
                                                        playbook_log LEFT JOIN
                                                        task_log ON task_log.playbook_id = playbook_log.id LEFT JOIN
                                                        runner_log ON runner_log.task_id = task_log.id
                                                WHERE
                                                        playbook_log.id = ?");
		$play->bind_param("s",$pId);
		$play->execute();
		$play->bind_result($playStart, $playPattern, $playEnd, $playTime, $playRunningState);
		$play->fetch();
		$playbook = array("pId" => $pId, "playStart" => $playStart, "playPattern" => $playPattern, "playTime" => $playTime, "playTimePretty" => $this->prettyTime($playTime));
		$playbook["isRunning"] = ($playRunningState > 0 ? true : false);
		$play->close();
		$playbook["hostCount"] = $this->getPlaybookHostCount($pId);
		$tasks = $this->con->prepare("SELECT
							COUNT(DISTINCT task_log.id),
							MAX(runner_log.changed),
							MIN(runner_log.ok),
							MAX(runner_log.unreachable)
						FROM
							task_log,
							runner_log
						WHERE
							task_log.playbook_id=? AND
							task_log.id = runner_log.task_id");
		$tasks->bind_param("s",$pId);
		$tasks->bind_result($taskCount,$hasChanged,$hasFailed,$unreachable);
		$tasks->execute();
		$tasks->fetch();
		if(!empty($taskCount)) {
			$playbook["taskCount"] = $taskCount;
			$playbook["hasChanged"] = ($hasChanged > 0 ? true : false);
			$playbook["hasFailed"] = (($hasFailed == 0 || $unreachable == 1) ? true : false);
		}
		else {
			$playbook["taskCount"] = 0;
			$playbook["hasChanged"] = false;
			$playbook["hasFailed"] = false;
		}
		$tasks->close();
		return $playbook;
	}

	function getPlaybookTasks($pId) {
		$tasks = array();
		$play = $this->con->prepare("SELECT
							task_log.id,
							task_log.name,
							hosts.host,
							runner_log.id,
							runner_log.ok,
							runner_log.changed,
							runner_log.unreachable,
							runner_log.skipped,
							task_log.start,
							runner_log.fail_msg,
							runner_log.delegate_host,
							runner_log.module,
							runner_log.extra_info
						FROM
							task_log,
							runner_log,
							hosts
						WHERE
							task_log.playbook_id = ? AND
							runner_log.task_id = task_log.id AND
							runner_log.host_id = hosts.id
						ORDER BY
							task_log.id, hosts.id");
		$play->bind_param("s",$pId);
		$play->execute();
		$play->bind_result($taskId, $taskName, $hostName, $runId, $runOk, $runChanged, $runUnreach, $runSkipped, $taskStart, $runFailMsg, $runDelegateHost, $runModule, $runExtraInfo);
		while($play->fetch()) {
			$run = array( "hostName" => $hostName, "failMsg" => $runFailMsg, "runId" => $runId);
			$run["changed"] = ($runChanged > 0 ? true : false);
			$run["failed"] = ($runOk < 1 ? true : false);
			$run["unreachable"] = ($runUnreach > 0 ? true : false);
			$run["skipped"] = ($runSkipped > 0 ? true : false);
			if(!empty($runDelegateHost)) {
				$run["delegated"] = true;
				$run["delegatedHost"] = $runDelegateHost;
			}
			else {
				$run["delegated"] = false;
			}
			if(!empty($runExtraInfo) && $runExtraInfo != "{}") {
				$run["extraInfo"] = print_r(json_decode($runExtraInfo,true),true);
			}
			else {
				$run["extraInfo"] = false;
			}

			$tasks[$taskId]["name"] = $taskName;
			$tasks[$taskId]["start"] = $taskStart;
			$tasks[$taskId]["module"] = $runModule;
			$tasks[$taskId]["runs"][] = $run;
		}
		$play->close();
		return $tasks;
	}

	function getPlayBookWithTasks($pId) {
		$p = $this->getPlaybook($pId);
		$p["tasks"] = $this->getPlaybookTasks($pId);
		return $p;
	}

	function getPlaybooksBetween($end = "", $start = "") {
		$pIds = array();
		$p = array();

		if(empty($end)) $end = date("Y-m-d H:i:s", time() - 10800);
		if(empty($start)) $start = date("Y-m-d H:i:s", time());
		if(!$this->validateDate($end) || !$this->validateDate($start)) return $p;
		$hosts = $this->con->prepare("SELECT DISTINCT
							id
						FROM
							playbook_log
						WHERE
							playbook_log.start BETWEEN ? AND ?
							ORDER BY start DESC;");
		$hosts->bind_param("ss", $end, $start);
		$hosts->execute();
		$hosts->bind_result($pId);
		while($hosts->fetch()) {
			$pIds[] = $pId;
		}
		$hosts->close();
		foreach($pIds AS $pId) {
			$p[] = $this->getPlaybook($pId);
		}
		return $p;
	}

	function getPlaybooksForHost($hId) {
		$p = array();
		$playbooks = array();
		$plays = $this->con->prepare("SELECT DISTINCT
							playbook_log.id
						FROM
							hosts,
							runner_log,
							task_log,
							playbook_log
						WHERE
							hosts.id = ? AND
							hosts.id = runner_log.host_id AND
							runner_log.task_id = task_log.id AND
							task_log.playbook_id = playbook_log.id
						ORDER BY
							playbook_log.start DESC");
		$plays->bind_param("s",$hId);
		$plays->execute();
		$plays->bind_result($pId);
		while($plays->fetch()) {
			$p[] = $pId;
		}
		foreach($p AS $pId) {
			$playbooks[] = $this->getPlaybook($pId);
		}
		return $playbooks;
	}

	function getFactsForHost($hId) {
		$f = array();
		$facts = $this->con->prepare("SELECT
							facts.id,
							facts.fact,
							fact_data.value
						FROM
							facts,
							fact_data
						WHERE
							fact_data.host_id = ? AND
							fact_data.fact_id = facts.id
						ORDER BY
							facts.fact");
		$facts->bind_param("s",$hId);
		$facts->execute();
		$facts->bind_result($fId, $factName, $factData);
		while($facts->fetch()) {
			$f[] = array("fId" => $fId, "factName" => $factName, "factData" => $factData);
		}
		return $f;
	}

	function getHosts() {
		$hosts = $this->con->prepare("SELECT
							id,
							host,
							last_seen
						FROM
							hosts
						ORDER BY
							host");
		$hosts->execute();
		$hosts->bind_result($hId, $hostName, $lastSeen);
		while($hosts->fetch()) {
			$h[] = array("hId" => $hId, "hostName" => $hostName, "lastSeen" => $lastSeen);
		}
		return $h;
	}

	function getHostName($hId) {
		$host = $this->con->prepare("SELECT
							host
						FROM
							hosts
						WHERE
							id = ?");
		$host->bind_param("s",$hId);
		$host->execute();
		$host->bind_result($hostName);
		$host->fetch();
		return $hostName;
	}

	function getHostCount() {
		$host = $this->con->prepare("SELECT
							COUNT(*)
						FROM
							hosts");
		$host->execute();
		$host->bind_result($hostCount);
		$host->fetch();
		return $hostCount;
	}

	function getFactNames() {
		$f = array();
		$facts = $this->con->prepare("SELECT
							facts.id,
							facts.fact,
							(SELECT COUNT(*) FROM fact_data WHERE fact_data.fact_id = facts.id)
						FROM
							facts
						ORDER BY facts.fact");
		$facts->execute();
		$facts->bind_result($fId, $factName, $useCount);
		while($facts->fetch()) {
			$f[] = array("fId" => $fId, "factName" => $factName, "useCount" => $useCount);
		}
		return $f;
	}

	function getFactName($fId) {
		$f = array();
		$facts = $this->con->prepare("SELECT
							facts.fact
						FROM
							facts
						WHERE
							facts.id = ?");
		$facts->bind_param("s",$fId);
		$facts->execute();
		$facts->bind_result($factName);
		$facts->fetch();
		return $factName;
	}

	function getFactId($factName) {
		$f = array();
		$facts = $this->con->prepare("SELECT
							facts.id
						FROM
							facts
						WHERE
							facts.fact = ?");
		$facts->bind_param("s",$factName);
		$facts->execute();
		$facts->bind_result($factId);
		$facts->fetch();
		return $factId;
	}

	function getFactData($fId) {
		$f = array();
		$facts = $this->con->prepare("SELECT
							fact_data.value,
							hosts.host
						FROM
							fact_data,
							hosts
						WHERE
							fact_data.host_id = hosts.id AND
							fact_data.fact_id = ?
						ORDER BY hosts.host");
		$facts->bind_param("s",$fId);
		$facts->execute();
		$facts->bind_result($factData, $hostName);
		while($facts->fetch()) {
			$f[] = array("factData" => $factData, "hostName" => $hostName);
		}
		return $f;
	}

	function getGroupedFactData($fId) {
		$f = array();
		$facts = $this->con->prepare("SELECT
							COUNT(fact_data.value),
							fact_data.value
						FROM
							fact_data
						WHERE
							fact_data.fact_id = ?
						GROUP BY fact_data.value");
		$facts->bind_param("s",$fId);
		$facts->execute();
		$facts->bind_result($factCount, $factData);
		$countSum = 0;
		while($facts->fetch()) {
			$f[] = array("factData" => $factData, "factCount" => $factCount);
			$countSum += $factCount;
		}
		$factName = $this->getFactName($fId);
		$data = array ("resultCount" => $countSum, "factName" => $factName, "results" => $f);
		return $data;
	}

	function getDashboardGraphs() {
		global $config;
		$g = array();
		foreach($config["graphs"] AS $graph) {
			$g[] = $this->getGroupedFactData($this->getFactId($graph));
		}
		return $g;
	}

}
?>
