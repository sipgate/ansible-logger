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

require_once('../includes/Twig/Autoloader.php');
require_once('../includes/Slim/Slim.php');

require_once('../config/config.inc.php');
require_once('../includes/ansible-logger.php');

\Slim\Slim::registerAutoloader();

$app = new \Slim\Slim(array(
	'templates.path' => '../tpl'
));

$app->view(new \Slim\Views\Twig());
$app->view->parserExtensions = array(new \Slim\Views\TwigExtension());

$app->get('/', function() use ($app) {
	$al = new ansibleLogger();
	$ansiblePlays = $al->getPlaybooksBetween();
	$charts = $al->getDashboardGraphs();
	$hostCount = $al->getHostCount();
	$app->render('page_dashboard.html', array(
		"charts" => $charts,
		"hostCount" => $hostCount,
		"ansiblePlays" => $ansiblePlays));
});

$app->get('/playbookdetails/:pId', function($pId) use ($app) {
	$al = new ansibleLogger();
	$playbookDetails = $al->getPlaybookWithTasks($pId);
	$charts = $al->getDashboardGraphs();
	$hostCount = $al->getHostCount();
	$app->render('page_playbookdetails.html', array(
		"hostCount" => $hostCount,
		"playbookDetails" => $playbookDetails,
		"charts" => $charts));
});

$app->get('/hosts', function() use ($app) {
	$al = new ansibleLogger();
	$hosts = $al->getHosts();
	$hostCount = $al->getHostCount();
	$charts = $al->getDashboardGraphs();
	$app->render('page_hosts.html', array(
		"hostCount" => $hostCount,
		"hosts" => $hosts,
		"charts" => $charts));
});

$app->get('/hostfactview/:hId', function($hId) use ($app) {
	$al = new ansibleLogger();
	$currentHost = $al->getHostName($hId);
	$charts = $al->getDashboardGraphs();
	$hostFacts = $al->getFactsForHost($hId);
	$hostCount = $al->getHostCount();
	$app->render('page_hostfactview.html', array(
		"hostCount" => $hostCount,
		"hostFacts" => $hostFacts,
		"currentHost" => $currentHost));
});

$app->get('/hostplayhistory/:hId', function($hId) use ($app) {
	$al = new ansibleLogger();
	$currentHost = $al->getHostName($hId);
	$charts = $al->getDashboardGraphs();
	$ansiblePlays = $al->getPlaybooksForHost($hId);
	$hostCount = $al->getHostCount();
	$app->render('page_hostplayhistory.html', array(
		"hostCount" => $hostCount,
		"ansiblePlays" => $ansiblePlays,
		"currentHost" => $currentHost,
		"charts" => $charts));
});

$app->get('/factbrowser(/:fId)', function($fId = -1) use ($app) {
	$al = new ansibleLogger();
	$factNames = $al->getFactNames();
	$hostCount = $al->getHostCount();
	$charts = $al->getDashboardGraphs();
	if($fId == -1) {
		$app->render('page_factbrowser.html', array(
			"hostCount" => $hostCount,
			"factNames" => $factNames,
			"charts" => $charts));
	}
	else {
		$factData = $al->getFactData($fId);
		$app->render('page_factbrowser.html', array(
			"hostCount" => $hostCount,
			"factNames" => $factNames,
			"factData" => $factData,
			"charts" => $charts));
	}

});

$app->run();

?>
