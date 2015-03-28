import subprocess

class EmailSender:
    def sendEmail(self, toAddress, fromAddress, subject, body):
        message = '''To: %s
FromAddress: %s
Subject: %s
        
%s''' % (toAddress, fromAddress, subject, body)

        try:
            ssmtp = subprocess.Popen(('/usr/sbin/ssmtp', toAddress), stdin=subprocess.PIPE)
            ssmtp.communicate(message)
            ssmtp.wait()
        except OSError:
            return

