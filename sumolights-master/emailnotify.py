
import os
import smtplib
import imghdr
from email.message import EmailMessage

sender = 'litianxin920@gmail.com'
receiver  = 'ericleetx920@gmail.com'

EMAIL_ADDRESS = sender
EMAIL_PASSWORD = 'gmfdcucatvhvdrot'

with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()

    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

    subject='testing'
    body='done'
    msg='done'

    smtp.sendmail(EMAIL_ADDRESS, receiver, msg)