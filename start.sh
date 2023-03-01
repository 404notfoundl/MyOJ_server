#!/bin/bash

is_proc_exist(){
	printf "check \033[36m %-20s  \033[0m:" $1
	exist=$(ps -e | grep -w $1 | grep -v "grep" | wc -l)
	if [ $exist -eq 0 ]; then
		printf "not exist\nrun   \033[36m %s \033[0m\n" $1	
		$2 &
	else
		printf "exist\n"
	fi
	return $exist
}
source venv/bin/activate
is_proc_exist "uwsgi" "uwsgi /home/online_judge/uwsgi.ini"
is_proc_exist "sshd" "/sshd.sh &"
is_proc_exist "start_celeryd" "/home/online_judge/start_celeryd.sh > /dev/null &"
is_proc_exist "start_consumerd" "/home/online_judge/start_consumerd.sh &"
echo -n "set cgroup limits"
/root/projects/resource_limit/resource_limit
echo "     ok"
