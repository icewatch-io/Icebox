import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from modules.logger import Logger


class SMTP:
    def __init__(self, smtp_config):
        self.smtp_config = smtp_config
        self.logger = Logger.get_logger('SMTP')

    def send_email(self, subject, body, timeout=10):
        self.logger.info(f"Sending email: {subject}, {body}")

        msg = MIMEMultipart()
        msg['From'] = self.smtp_config['from']
        msg['To'] = self.smtp_config['to']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if not self.smtp_config['sending_enabled']:
            self.logger.warning("Not sending email as sending is disabled")
            return

        try:
            socket.setdefaulttimeout(timeout)
            server = smtplib.SMTP(
                host=self.smtp_config['smtp_server'],
                port=self.smtp_config['smtp_port'],
                timeout=timeout
            )
            if self.smtp_config['tls']:
                server.starttls()
            server.login(
                self.smtp_config['smtp_user'],
                self.smtp_config['smtp_password']
            )
            server.sendmail(
                self.smtp_config['from'],
                self.smtp_config['to'],
                msg.as_string()
            )
            server.quit()
            self.logger.info("Email sent successfully")
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
        finally:
            socket.setdefaulttimeout(None)
