#!/bin/bash
log_file=celery.log
pid_file=celery.pid
# source venv/bin/activate
while true
do
if [ -f "$pid_file" ]; then
pid="$(cat $pid_file)"
else
pid="123asd"
fi
res="$(ps -e | grep -w $pid | grep -v "grep" | wc -l)"
if [ $res -eq 1 ]; then
# proc exist
echo pid exist > /dev/null # 占位用
else
# restart proc
source venv/bin/activate && celery multi start w1 -A online_judge worker  -l info  --logfile=$log_file --pidfile=$pid_file
fi
sleep 300
done
