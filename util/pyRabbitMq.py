import pika
import json

from django.conf import settings

rabbitMq_conf = settings.RABBITMQ_CONFIG


class MyRabbitMq:
    connection = None
    channel = None
    exchange = None

    def __del__(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __init__(self, username=rabbitMq_conf.get('username'), password=rabbitMq_conf.get('password')):
        parameters = pika.ConnectionParameters(credentials=pika.PlainCredentials(username=username, password=password),
                                               host=rabbitMq_conf.get('host'), port=rabbitMq_conf.get('port'),
                                               heartbeat=None)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.exchange = 'default'
        self.channel.exchange_declare(exchange_type=rabbitMq_conf.get('exchange').get('default'),
                                      exchange='default', durable=True)


class RabbitMqPublisher(MyRabbitMq):
    queue_name = None

    def __init__(self, queue_name=rabbitMq_conf.get('queue').get('task')):
        super().__init__()
        self.queue_name = queue_name
        self.channel.queue_declare(queue_name, durable=True)
        self.channel.queue_bind(exchange=self.exchange, queue=self.queue_name)

    def basic_publish(self, message):
        # print(message, self.exchange)
        self.channel.basic_publish(exchange=self.exchange, routing_key=self.queue_name, body=message)


class RabbitMqConsumer(MyRabbitMq):
    queue_name = None

    def __init__(self, queue_name=rabbitMq_conf.get('queue').get('task')):
        super().__init__()
        self.queue_name = queue_name
        self.channel.queue_declare(queue_name, durable=True)
        self.channel.queue_bind(exchange=self.exchange, queue=self.queue_name)
        self.channel.basic_qos(prefetch_count=1)

    def test_callback(self, ch, method, properties, body: bytes):
        # print(type(body), body)
        res = json.loads(body)
        print(type(res), res)

        ch.basic_ack(method.delivery_tag)

    def basic_consume(self, callback=None):
        if callback is None:
            self.channel.basic_consume(on_message_callback=self.test_callback, queue=self.queue_name)
        else:
            self.channel.basic_consume(on_message_callback=callback, queue=self.queue_name)

    def start_consuming(self):
        self.channel.start_consuming()


class RabbitMqHttpApi:
    api = {
        'overview', 'exchanges'
    }
    prefix = "http://%s:%s@%s:%s/api/" % (
        rabbitMq_conf.get('username'), rabbitMq_conf.get('password'), rabbitMq_conf.get('host'),
        rabbitMq_conf.get('http_port'))

    @classmethod
    def get(cls, _url: str):
        url = "%s%s" % (cls.prefix, _url)
