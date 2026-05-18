import sensor_according_to_rate as sensor
import time

# wait for baseline to finish
while sensor.state == "baseline":
    time.sleep(0.1)

print('bring clothes')

sensor.start_measuring()

# wait for measurement to finish
while sensor.state == "measuring":
    time.sleep(0.1)

result = sensor.get_result()  # "Wet" or "Dry"

if result == "Wet":
    print("It's wet! ")
else:
    print("It's dry! ")
