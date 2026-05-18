README

for asus ZenBook 14: 
Leader arm  = COM4
Follower arm = COM6

lerobot-find-port

Pathway: 
conda activate so101-teleop
cd "C:\Users\samfr\OneDrive\Desktop\Projects\SO-101_Hackathon\example_so101"

cd example_so101/examples
python 1_leader_arm_teleop_so101.py --leader-port COM4 --leader-id my_leader

Data collection:
python 2_collect_teleop_data_with_neuracore.py --leader-port COM4 --leader-id my_leader --follower-port COM6 --follower-id my_follower_arm --dataset-name so101-demo


test: 
cd examples
python 1_leader_arm_teleop_so101.py --real-robot --leader-port COM4 --leader-id my_leader --follower-port COM6 --follower-id my_follower_arm

Calibrate: 
cd ..
lerobot-calibrate --robot.type=so101_follower --robot.port=COM6 --robot.id=my_follower_arm
lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=my_leader


process:
1. getting the robot to run following arm, reinstalling python etc and the GitHub repositories, initialising ports, calibrating to maximum values.
2. we've got movements and GUI is working properly, experienced some hardware issues with the motors jittering and not working but this was replaced, use case is autonomous laundry sorting, wet and dry clothes, at the moments however this can be changed as sensors are modular so can be replaced whenever.
3. now thinking about implementing the camera system, humidity sensor circuitry, mounting both to robot and environment, chosen to do a birds eye view of the operation area to train data. 
4. were thinking of implementing cursor, and neuracore next.
5. trying to get the camera working, python script keeps opening and running my laptop webcam.
6. to fix the Atech module, implementing lovable collaboration.
7. Camera wasn't registering on the laptop USB, replacement camera was used and we now have live video feed.
8. How do we wire humidity test into the demo movement?
9. we are trying to implement neuracore now, using cursor to help understand how this can work
10. Neuracore GUI was working but uploads have frozen due to temporary issues with the website. The project must change course.
New plan:
Camera detects cloth (image colour segmentation)
Robot moves to cloth (inverse kinematics)
Robot moves cloth over humidity sensor (saved position)
Sensor classifies wet/dry (Atech sensor module)
Robot places into correct bin (simple threshold decision algorithm, into saved position outcomes)
11.

