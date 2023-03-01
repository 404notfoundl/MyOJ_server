import os

timezone = "Asia/Shanghai"
broker_url = os.getenv('CELERY_BROKER_URL')
result_backend = os.getenv('CELERY_RESULT_BACKEND')
result_serializer = 'json'
enable_utc = False
worker_max_tasks_per_child = 120
# 应答选项
task_acks_late = True
task_acks_on_failure_or_timeout = False
task_reject_on_worker_lost = True
# redis 配置
# redis_backend_health_check_interval = 60
# redis_max_connections = 60
# redis_retry_on_timeout = True
# redis_socket_keepalive = True
# rabbitMq
