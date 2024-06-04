import serial.tools.list_ports
import serial
import time
import requests
from queue import Queue
import threading
import numpy as np

def call_script(invoked_sensor, direction, ongoing_actions):
    if ongoing_actions[direction, invoked_sensor-1] == 0:
        command = ""
        if invoked_sensor == 8 and direction == 2:
            command = "goto_start"
        
        elif invoked_sensor == 7 and direction == 2:
            command = "play_pause"

        elif invoked_sensor == 6 and direction == 1:
            command = "master_volume %2B0.1"

        elif invoked_sensor == 6 and direction == 0:
            command = "master_volume -0.1"

        elif invoked_sensor == 5:
            print("sensor: ",invoked_sensor)
            if direction == 1:
                print("action: ",direction)
                command = "effect_active 'loop roll'"
            elif direction == 2: 
                print("action: ",direction)
                command = "effect_active 'loop out'"

        elif invoked_sensor == 4:
            print("sensor: ",invoked_sensor)
            if direction == 1:
                print("action: ",direction)
                
                command = "effect_active 'echo'"
            elif direction == 0: 
                print("action: ",direction)
                command = "effect_active 'beat grid'"

        elif invoked_sensor == 3:
            print("sensor: ",invoked_sensor)
            if direction == 1:
                print("action: ",direction)
                command = "effect_active 'filter hp'"
            elif direction == 0: 
                print("action: ",direction)
                command = "effect_active 'filter lp'"

        elif invoked_sensor == 2:
            print("sensor: ",invoked_sensor)
            if direction == 1:
                print("action: ",direction)
                command = "stem_pad HiHat"
            elif direction == 0: 
                print("action: ",direction)
                command = "stem_pad Kick"

        elif invoked_sensor == 1:
            print("sensor: ",invoked_sensor)
            if direction == 1:
                print("action: ",direction)
                command = "stem_pad Vocal"
            elif direction == 0: 
                print("action: ",direction)
                command = "stem_pad Instru"
        

        # API CALLS ARE MADE HERE
        url = 'http://127.0.0.1:80/execute?script='+command
        obj = {'script': command}
        print("request: ",url)
        request = requests.get(url, json = obj)
        return request
        

def process_incoming(action_queue, serialInst, number_sensors, window_size):
    #INCOMING SIGNALS ARE READ HERE
    interval = np.ones((number_sensors,window_size))
    while True:
        incoming_readings = []
        for i in range(number_sensors):
            incoming_readings.append(int(serialInst.readline().decode("utf-8").strip('\r\n')))
        interval = np.hstack((interval[0:number_sensors,1:window_size],np.array(incoming_readings).reshape(number_sensors,1)))
        if sum(incoming_readings) < 8:
            invoked_sensor = incoming_readings.index(0,1)
            print("#######")
            print("invoked sensor: ",invoked_sensor)
            action_queue.put((interval[[invoked_sensor,-2,-1]],invoked_sensor))

def track_calls(ongoing_actions, direction, invoked_sensor):
    time.sleep(0.8)
    ongoing_actions[direction, invoked_sensor-1] = 0
    return None

def perform_actions(action_queue):
    ongoing_actions = np.zeros((3,8))
    while True:
        readings, invoked_sensor = action_queue.get()
        if invoked_sensor > 6: 
            if np.sum(readings[0]) == 0:
                direction = 2
                call_script(invoked_sensor, direction, ongoing_actions)
                ongoing_actions[direction,invoked_sensor-1] = 1
                closer_thread = threading.Thread(target=track_calls, args=(ongoing_actions,direction, invoked_sensor,))
                closer_thread.start()
            else: continue
        forward_reading = readings[1]
        upward_reading = readings[2]
        hold_reading = readings[0]
        direction = -1
        if np.sum(upward_reading[4:]) == 0 and np.sum(upward_reading[:2]) == 2:
            direction = 0
            call_script(invoked_sensor, direction, ongoing_actions)
            ongoing_actions[direction,invoked_sensor-1] = 1
            closer_thread = threading.Thread(target=track_calls, args=(ongoing_actions,direction, invoked_sensor,))
            closer_thread.start()
        elif np.sum(forward_reading[4:] == 0) and np.sum(forward_reading[:2]) == 2:
            direction = 1
            call_script(invoked_sensor, direction, ongoing_actions)
            ongoing_actions[direction,invoked_sensor-1] = 1
            closer_thread = threading.Thread(target=track_calls, args=(ongoing_actions,direction, invoked_sensor,))
            closer_thread.start()
        else:
            continue
        print("direction: ", direction)
    
if __name__ == "__main__":
    number_sensors = 9
    window_size = 6
    serialInst = serial.Serial("/dev/cu.usbmodem1101",4800)
    action_queue = Queue(maxsize = 128)
    sensor_queue = Queue(maxsize = 128)
    processor_thread = threading.Thread(target=process_incoming, args=(action_queue,serialInst, number_sensors, window_size,))
    actioner_thread = threading.Thread(target=perform_actions, args=(action_queue,))
    processor_thread.start()
    actioner_thread.start()