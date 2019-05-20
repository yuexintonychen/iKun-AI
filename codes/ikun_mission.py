try:
    from malmo import MalmoPython
except:
    import MalmoPython

import os
import sys
import time
import json

def get_mission_xml():
    xml_file = open("./ikun_mission.xml", "r")
    return xml_file.read()

def main():
    # Start mission
    # Create default Malmo objects:
    agent_host = MalmoPython.AgentHost()
    try:
        agent_host.parse( sys.argv )
    except RuntimeError as e:
        print('ERROR:',e)
        print(agent_host.getUsage())
        exit(1)
    if agent_host.receivedArgument("help"):
        print(agent_host.getUsage())
        exit(0)

    if agent_host.receivedArgument("test"):
        num_repeats = 1
    else:
        num_repeats = 1

    for i in range(num_repeats):
        size = int(6 + 0.5*i)
        print("Size of maze:", size)
        my_mission = MalmoPython.MissionSpec(get_mission_xml(), True)
        # my_mission = MalmoPython.MissionSpec(get_mission_xml(), True)
        my_mission_record = MalmoPython.MissionRecordSpec()
        my_mission.requestVideo(800, 500)
        my_mission.setViewpoint(1)
        # Attempt to start a mission:
        max_retries = 3
        my_clients = MalmoPython.ClientPool()
        my_clients.add(MalmoPython.ClientInfo('127.0.0.1', 10000)) # add Minecraft machines here as available

        for retry in range(max_retries):
            try:
                agent_host.startMission( my_mission, my_clients, my_mission_record, 0, "%s-%d" % ('Moshe', i) )
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print("Error starting mission", (i+1), ":",e)
                    exit(1)
                else:
                    time.sleep(2)

        # Loop until mission starts:
        print("Waiting for the mission", (i+1), "to start ",)
        world_state = agent_host.getWorldState()
        while not world_state.has_mission_begun:
            #sys.stdout.write(".")
            time.sleep(0.1)
            world_state = agent_host.getWorldState()
            for error in world_state.errors:
                print("Error:",error.text)

        print()
        print("Mission", (i+1), "running.")


if __name__ == "__main__":
    main()