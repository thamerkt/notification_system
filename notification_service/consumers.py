import pika
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import os
import django

# Initialize Django (adjust the settings module name if needed)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notificationsystem.settings')
django.setup()

from django.conf import settings
from .models import Notification
from django.db import transaction, connection

# RabbitMQ CloudAMQP URL
CLOUDAMQP_URL = 'amqps://dxapqekt:BbFWQ0gUl1O8u8gHIUV3a4KLZacyrzWt@possum.lmq.cloudamqp.com/dxapqekt'

# Email (Brevo SMTP) Config
SMTP_SERVER = 'smtp-relay.brevo.com'
SMTP_PORT = 587
SMTP_USERNAME = '7e8bcf002@smtp-brevo.com'
SMTP_PASSWORD = 'tGMsIDKfLYh0vbWS'
FROM_EMAIL = 'kthirithamer2@gmail.com'

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def callback(ch, method, properties, body):
    print("Received message:", body)
    try:
        message = json.loads(body)
        event = message.get('event')
        payload = message.get('payload', {})
        email = payload.get('email')
        user = payload.get('user')
        rental_request_id = payload.get('rental_request_id')
        status = payload.get('status')

        subject = ""
        body_content = ""

        if event == 'rental.confirmed':
            subject = "Votre réservation a été confirmée"
            body_content = f"Bonjour,\n\nVotre demande de location (ID: {rental_request_id}) a été confirmée. Statut : {status}.\n\nMerci."
        elif event == 'rental.canceled':
            subject = "Votre réservation a été annulée"
            body_content = f"Bonjour,\n\nVotre demande de location (ID: {rental_request_id}) a été annulée. Statut : {status}.\n\nMerci."
        else:
            print(f"Unhandled event type: {event}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        send_email(email, subject, body_content)

        with transaction.atomic():
            notif = Notification(user=user, title=subject)
            notif.save()
            print(f"Notification saved: {notif.id} - {notif.title}")

    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_notification_service():
    print("Notification service module loaded.", flush=True)
    while True:
        try:
            print("Connecting to RabbitMQ via CloudAMQP...")
            parameters = pika.URLParameters(CLOUDAMQP_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            queue_name = 'generate_contract'
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=callback)
            print("Waiting for messages. Service is running...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Auto-start the consumer thread when the app is ready
threading.Thread(target=start_notification_service, daemon=True).start()
