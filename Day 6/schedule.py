import schedule
import time

def send_report():
    print("Sending daily report...")

schedule.every(10).seconds.do(send_report)

while True:
    schedule.run_pending()
    time.sleep(1)