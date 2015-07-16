# dbprep

You can use this script to prepare your database with random data. It will only work on your database if no hosts are found in the ```hosts``` table!
You need to have the database credentials in your config file (currently ```../../ansible-callbacks/ansible-logger.conf```).

# Usage
```
./dbprep.py
```

# Data Source
The script uses several textfiles to generate random data (Hosts, Facts, Playbook Runs etc.). If you want to add new tasks: please seperate Task-Name and command with a semicolon. The same applies for facts and their values.
