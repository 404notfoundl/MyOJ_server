<!--
 * @Author: 
 * @Date: 2022-10-23 20:52:28
 * @LastEditors: Please set LastEditors
 * @LastEditTime: 2023-03-01 14:23:24
 * @Description: 请填写简介
-->
# MyOJ_server
项目的后端，基于 `django` 开发,实现了一些基本功能
于容器位置 `/home/online_judge` 
[前端](https://github.com/404notfoundl/MyOJ_web)
[评测机](https://github.com/404notfoundl/MyOJ_judger)

## 项目结构
```shell
.
├── oj_tasks # 处理提交部分
├── online_judge # 相关设置
├── problem_lib # 题库
├── site_config # 设置
├── site_users # 用户
├── solutions # 题解
├── util # 常用工具
```
## 配置
* `deploy/docker-compose.yml`
  请根据需要修改 `environment` 相关选项，如密码等
  * 需要修改 email 相关配置 smtp
  * 需要修改 `FRONT_END_HOST` 前端的地址
  * 需要修改 `DJANGO_SECRET_KEY` 
    ~~~python
    # 可通过以下命令生成
    from django.core.management.utils import get_random_secret_key
    get_random_secret_key()
    ~~~
## 部署 
1. 打包前端
   见前端部分
   在修改后端地址后将打包的文件置于 `deploy/nginx/html` 中
2. 启动
    ```shell
    cd ./deploy/
    docker-compose up -d
    ```
  * 访问 `[host]:8080` 可进入前端
  * 访问 `[host]:8008` 显示如下
    ```html
    <h1>Not Found</h1>
    <p>The requested resource was not found on this server.</p>
    ```
    表示后端成功启动
  * 访问 `[host]:15672` 可进入 rabbitmq 管理界面，在该界面下：
    * 访问 queues -> queue_task 看到相应连接则评测机连接成功
    * 访问 queues 看到有 celery 相关队列及其有相应连接则 celery 启动成功
    * 访问 queues -> queue_result 看到相应连接则处理评测结果(consumer)的进程连接成功
### 注意
* 由于需要部分权限，目前创建容器需要附加参数 `privileged`。
待查明所需具体权限后进行进一步限制
* 如果 `celery` 或 `consumer` 没启动成功，可能是对应.pid文件中的pid已存在，可清空该文件再启动

## 配置文件位置
* uwsgi
  `uwsgi.ini`
* django
  `online_judge/settings.py`
* celery
  `online_judge/celeryconfig.py`

## 添加管理员
于 `server` 容器，项目根目录，虚拟环境内
```shell
source venv/bin/activate # 进入虚拟环境
python manage.py createsuperuser # 创建管理员
```
