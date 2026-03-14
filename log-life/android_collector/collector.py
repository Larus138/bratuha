import time
import datetime

while True:
    now = datetime.datetime.now()
    entry = f"{now} - device active\n"

    with open("life_log.txt", "a") as f:
        f.write(entry)

    print(entry)

    time.sleep(60)
