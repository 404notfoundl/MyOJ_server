#!/bin/bash
pid_file=consumer.pid
log_file=consumer.log
# source venv/bin/activate
while true
do
if [ -f $log_file ]; then
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
source venv/bin/activate && python manage.py result_consumer >> $log_file 
fi

sleep 300
done
