# ansible-logger
ansible-logger archives the results and gathered facts of your ansible runs in a MySQL database (using ansible callbacks). It comes with an easy to use and responsive web interface. It works as a 'drop-in' logging solution - you do not have to modify your existing playbooks in any way to make use of it!

# Requirements
* Ansbile (tested with 1.5.4 and 1.8)
* Python 2.7
* Python MySQLdb
* Webserver (tested with apache) + PHP5 (tested with 5.4)
* MySQL DB (tested with 5.6, but 5.5 and 5.1 should also work)

# Setup
To use the logger, add the following to your /etc/ansible/ansible.cfg or ~/.ansible.cfg:
```
[defaults]
callback_plugins  = /path/to/repo/ansible-logger/ansible-callbacks 
bin_ansible_callbacks = true
```
* Rename ```ansible-callbacks/ansible-logger.conf.dist``` to ```ansible-logger.conf```
* Edit this file to hold your database credentials
* Configure your weberserver to serve the contents of the folder ```ansible-logger-web/public``` as its DocumentRoot
* Enable ```mod_rewrite``` and set ```AllowOverride FileInfo```, otherwise you will run into errors with the included ```.htaccess``` file
* Rename the file ```ansible-logger-web/config/config.inc.php.dist``` to ```config/config.inc.php```
* Edit this file to hold your database credentials
* Create a new database and import the included schema: ```mysql <your_db_name> < sql/schema.sql```
* If you want authentication, please configure Apache with your favorite authentication method - currently, there is no authentication at all built into ansible-logger-web!

# Versioning
ansible-logger is currently in a very very early state. Things may change and break quickly (e.g. database layout, URLs, internal structure etc.). However, since it is easy to re-create data with some quick ansible runs and there is no configuration or inventory data stored in the database yet, this should not be a large issue.

# Todo
* add Graphs (Dashboard, Fact Browser etc.)
* Paginate Results (maybe with https://datatables.net/ ?)
* Export Hosts, Facts etc.
* REST-API interface for use as inventory source to ansible (+ corresponding inventory script for ansible)
* Store host list (or query external source like LDAP) for inventory queries
* Store inventory variables and tie them to fact values (e.g. deliver a certain value for all Debian squeeze machines), like hiera for puppet

# Third Party Software
ansible logger ships with and/or makes use of the following third party software/libraries:
* Bootstrap (http://getbootstrap.com/)
* Slim Framework (http://www.slimframework.com/)
* Twig (http://twig.sensiolabs.org/)
* jQuery (https://jquery.com/)
* bootstrap3-typeahead (https://github.com/bassjobsen/Bootstrap-3-Typeahead)
* Google Charts API (https://google-developers.appspot.com/chart/)

# LICENSE
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

