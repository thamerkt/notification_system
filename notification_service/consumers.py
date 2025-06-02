import pika
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
from django.conf import settings
from .models import Notification
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notificationsystem.settings')  # replace with your settings module



from django.conf import settings
from .models import Notification 
# Configuration RabbitMQ
RABBITMQ_HOST = getattr(settings, 'RABBITMQ_HOST', 'https://rabbitmq-hj5y.onrender.com')
RABBITMQ_PORT = getattr(settings, 'RABBITMQ_PORT', 5672)
RABBITMQ_QUEUE = getattr(settings, 'RABBITMQ_QUEUE', 'generate_contract')

# Configuration Email (Brevo SMTP)
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
        user=payload.get('user')
        rental_request_id = payload.get('rental_request_id')
        status = payload.get('status')
        print("user",user)

        subject = ""
        body = ""

        if event == 'rental.confirmed':
            subject = "Votre réservation a été confirmée"
            body = f"Bonjour,\n\nVotre demande de location (ID: {rental_request_id}) a été confirmée. Statut : {status}.\n\nMerci."
        elif event == 'rental.canceled':
            subject = "Votre réservation a été annulée"
            body = f"Bonjour,\n\nVotre demande de location (ID: {rental_request_id}) a été annulée. Statut : {status}.\n\nMerci."
        else:
            print(f"Unhandled event type: {event}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        send_email(email, subject, body)
        from django.db import transaction, connection
        from django.db import connection
        print(f"DB connection alias: {connection.alias}")
        print(f"DB connection settings: {connection.settings_dict}")
        print(f"Is connection closed? {connection.is_usable()}")

        try:
            print(f"DB connection alias: {connection.alias}")
            print(f"DB connection settings: {connection.settings_dict}")
            print(f"Is connection closed? {connection.is_usable()}")
            with transaction.atomic():
                notif = Notification(user=user, title=subject)
                notif.save()
                print(f"Notification saved: {notif.id} - {notif.title}")

            transaction.commit()
           

            all_notifications = Notification.objects.all()
            print("All notifications in DB:")
            for n in all_notifications:
                print(f"{n.id} - {n.user} - {n.title}")

        except Exception as e:
            print(f"Failed to create notification: {e}")


    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_notification_service():
    print("Notification service module loaded.", flush=True)
    while True:
        try:
            print("Connecting to RabbitMQ...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.environ.get('RABBITMQ_HOST', 'host.docker.internal'),
                    port=int(os.environ.get('RABBITMQ_PORT', 5672)),
                    heartbeat=int(os.environ.get('RABBITMQ_HEARTBEAT', 600)),
                    blocked_connection_timeout=int(os.environ.get('RABBITMQ_TIMEOUT', 300))
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)
            print("Waiting for messages. Service is running...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Auto-start the consumer thread when app is ready
threading.Thread(target=start_notification_service, daemon=True).start()
