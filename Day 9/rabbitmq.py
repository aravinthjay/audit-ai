# ============================================================

# EXTENSION A + EXTENSION B

# RabbitMQ (CloudAMQP) + Azure Service Bus

# ============================================================

import json
import aio_pika
from azure.servicebus import (
ServiceBusClient,
ServiceBusMessage
)

# ============================================================

# CONFIGURATION

# ============================================================

# Extension A — CloudAMQP RabbitMQ

RABBIT_URL = "amqps://<username>:<password>@<host>/<vhost>"

# Extension B — Azure Service Bus

SB_CONN_STR = "<AZURE_SERVICE_BUS_CONNECTION_STRING>"
QUEUE_NAME = "payments"

# ============================================================

# EXTENSION A — RABBITMQ (CLOUDAMQP)

# ============================================================

rabbit_connection = None
rabbit_channel = None
payments_queue = None

async def connect_rabbitmq():
    global rabbit_connection
    global rabbit_channel
    global payments_queue

    rabbit_connection = await aio_pika.connect_robust(
        RABBIT_URL
    )

    rabbit_channel = await rabbit_connection.channel()

    # Dead Letter Exchange
    dlx = await rabbit_channel.declare_exchange(
        "dlx",
        aio_pika.ExchangeType.DIRECT
    )

    # Dead Letter Queue
    dlq = await rabbit_channel.declare_queue(
        "payments.dlq",
        durable=True
    )

    await dlq.bind(
        dlx,
        routing_key="payments.failed"
    )

    # Main Queue
    payments_queue = await rabbit_channel.declare_queue(
        "payments",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": "payments.failed"
        }
    )

    print("RabbitMQ connected")


async def publish_rabbitmq(payment: dict):

    await rabbit_channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(payment).encode()
        ),
        routing_key="payments"
    )

    print("Message published to RabbitMQ")

async def consume_rabbitmq():

    async with payments_queue.iterator() as queue_iter:

        async for message in queue_iter:

            async with message.process():

                payload = json.loads(
                    message.body.decode()
                )

                print(
                    "RabbitMQ Processing:",
                    payload
                )


# ============================================================

# EXTENSION B — AZURE SERVICE BUS

# ============================================================

def publish_service_bus(payment: dict):

    with ServiceBusClient.from_connection_string(
        SB_CONN_STR
    ) as client:

        sender = client.get_queue_sender(
            queue_name=QUEUE_NAME
        )

        with sender:

            sender.send_messages(
                ServiceBusMessage(
                    json.dumps(payment)
                )
            )

    print("Message published to Azure Service Bus")


def consume_service_bus():

    with ServiceBusClient.from_connection_string(
        SB_CONN_STR
    ) as client:

        receiver = client.get_queue_receiver(
            queue_name=QUEUE_NAME
        )

        with receiver:

            messages = receiver.receive_messages(
                max_message_count=1,
                max_wait_time=5
            )

            for msg in messages:

                print(
                    "Azure Service Bus Processing:",
                    str(msg)
                )

                receiver.complete_message(
                    msg
                )


def dead_letter_message():

    with ServiceBusClient.from_connection_string(
        SB_CONN_STR
    ) as client:

        receiver = client.get_queue_receiver(
            queue_name=QUEUE_NAME
        )

        with receiver:

            messages = receiver.receive_messages(
                max_message_count=1,
                max_wait_time=5
            )

            for msg in messages:

                receiver.dead_letter_message(
                    msg,
                    reason="Payment Processing Failed"
                )

                print(
                    "Message moved to Azure DLQ"
                )


# ============================================================

# DEMO PAYMENT PAYLOAD

# ============================================================

sample_payment = {
"amount": 500,
"currency": "GBP",
"account_id": "ACC-001",
"reference": "Invoice-1001"
}

# ============================================================

# TEST FLOW

# ============================================================

# RabbitMQ

await connect_rabbitmq()

await publish_rabbitmq(sample_payment)

await consume_rabbitmq()

# Azure Service Bus

publish_service_bus(sample_payment)

consume_service_bus()

dead_letter_message()

print("Extension A: RabbitMQ CloudAMQP Enabled")
print("Extension B: Azure Service Bus Enabled")
