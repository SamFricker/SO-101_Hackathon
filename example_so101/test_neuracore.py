import time
import neuracore as nc

print("Logging into Neuracore...")
nc.login()

print("Connecting robot...")

robot = nc.connect_robot(
    robot_name="SO101-Hackathon",
    overwrite=False,
)

print("Robot connected.")

print("Creating dataset...")

dataset = nc.create_dataset(
    name="so101_pick_place",
    description="SO101 pick and place training dataset",
)

print("Dataset created.")

nc.start_recording()

print("Recording started...")

for i in range(50):

    joints = {
        "base": 0.0,
        "shoulder": 0.1,
        "elbow": 0.2,
        "wrist_pitch": 0.3,
        "wrist_roll": 0.4,
        "gripper": 0.0,
    }

    nc.log_joint_positions(joints)

    print(f"Logged frame {i}")

    time.sleep(0.1)

print("Stopping recording...")

nc.stop_recording()

print("Done.")