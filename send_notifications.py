#/usr/bin/python3

from datetime import datetime
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import traceback

import copy_order_logging

'''Sends email notifications when orders are ready to send

Includes log file as an attachment

'''

log = copy_order_logging.get_logger(__name__)

def setup_smtp(email_pw, email_address):
    try:
        smtp_object = smtplib.SMTP('smtp.gmail.com', 587)
        smtp_object.ehlo()
        smtp_object.starttls()
        smtp_object.login(email_address, email_pw)
        return smtp_object
    except Exception as e:
        log.error(e)

def prep_message(message_to_send, email_address, recipient, logfile):
    msg = MIMEMultipart()
    msg['Subject'] = f"Copy order fulfillment status {str(datetime.now()).split(' ')[0]}"
    msg['From'] = email_address
    msg['To'] = recipient
    text = MIMEText(message_to_send, 'plain')
    msg.attach(text)
    if logfile:
        log_data = MIMEText(logfile)
        log_data.add_header('Content-Disposition', 'attachment', filename='log.log')
        msg.attach(log_data)
    return msg

'''Make these messages more informative - i.e. include the number of orders ready to be sent'''

def success_message():
    return '''Copy order fulfillment complete. Orders ready to be sent.'''

def failure_message():
    return '''Copy order fulfillment failed. See attached logs for details.'''

def get_log():
    logfile = open('logs/log.log')
    return logfile.read()

def main(success=True):
    try:
        cfg = json.load(open('config/config.json'))
        email_pw = cfg.get('status_email_password')
        email_address = cfg.get('status_email_address')
        smtp_obj = setup_smtp(email_pw, email_address)
        recipients = tuple(cfg[key] for key, value in cfg.items() if 'recipient' in key)
        if success:
            message_to_send = success_message()
            logfile = None
        else:
            message_to_send = failure_message()
            logfile = get_log()
        for recipient in recipients:
            prepared_message = prep_message(message_to_send, email_address, recipient, logfile)
            smtp_obj.sendmail(email_address, recipient, prepared_message.as_string())
    except Exception as e:
        log.error(e)

if __name__ == "__main__":
    main(success=False)