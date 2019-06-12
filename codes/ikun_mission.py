from __future__ import generators

try:
    from malmo import MalmoPython
except:
    import MalmoPython

import os
import sys
import time
import json
import re
import copy
import numpy as np

# parameters (fixed)
AGENT_OBSERVATION_LENGTH = 61

# size of the maze
size_of_maze = 21

# original matrix in 2D
matrix2dOriginal = []

# maze_map
maze_map =[]

# 0 means front; 1 means right; 2 means back; 3 means left (in default direction: 0)
agent_current_direction = 0

# position variables
agent_current_position_xy_in_maze = [-1, -1]
agent_current_position_index_in_grid = -1

# Record the maze map position in the actual map
first_block_index_in_actual_map = -1
last_block_index_in_actual_map = -1

#malmo agent
agent_host = None

#actionFile counter
actionHistCounter = 0

# Helpful Classes or functions not related to the core of the project

# Priority dictionary using binary heaps
# David Eppstein, UC Irvine, 8 Mar 2002

class priorityDictionary(dict):
    def __init__(self):
        '''Initialize priorityDictionary by creating binary heap
of pairs (value,key).  Note that changing or removing a dict entry will
not remove the old pair from the heap until it is found by smallest() or
until the heap is rebuilt.'''
        self.__heap = []
        dict.__init__(self)

    def smallest(self):
        '''Find smallest item after removing deleted items from heap.'''
        if len(self) == 0:
            raise IndexError("smallest of empty priorityDictionary")
        heap = self.__heap
        while heap[0][1] not in self or self[heap[0][1]] != heap[0][0]:
            lastItem = heap.pop()
            insertionPoint = 0
            while 1:
                smallChild = 2 * insertionPoint + 1
                if smallChild + 1 < len(heap) and \
                                heap[smallChild] > heap[smallChild + 1]:
                    smallChild += 1
                if smallChild >= len(heap) or lastItem <= heap[smallChild]:
                    heap[insertionPoint] = lastItem
                    break
                heap[insertionPoint] = heap[smallChild]
                insertionPoint = smallChild
        return heap[0][1]

    def __iter__(self):
        '''Create destructive sorted iterator of priorityDictionary.'''

        def iterfn():
            while len(self) > 0:
                x = self.smallest()
                yield x
                del self[x]

        return iterfn()

    def __setitem__(self, key, val):
        '''Change value stored in dictionary and add corresponding
pair to heap.  Rebuilds the heap if the number of deleted items grows
too large, to avoid memory leakage.'''
        dict.__setitem__(self, key, val)
        heap = self.__heap
        if len(heap) > 2 * len(self):
            self.__heap = [(v, k) for k, v in self.items()]
            self.__heap.sort()  # builtin sort likely faster than O(n) heapify
        else:
            newPair = (val, key)
            insertionPoint = len(heap)
            heap.append(None)
            while insertionPoint > 0 and \
                            newPair < heap[(insertionPoint - 1) // 2]:
                heap[insertionPoint] = heap[(insertionPoint - 1) // 2]
                insertionPoint = (insertionPoint - 1) // 2
            heap[insertionPoint] = newPair

    def setdefault(self, key, val):
        '''Reimplement setdefault to call our customized __setitem__.'''
        if key not in self:
            self[key] = val
        return self[key]

def dijkstra_shortest_path(grid_obs, source, dest):
    """
    Finds the shortest path from source to destination on the map. It used the grid observation as the graph.
    See example on the Tutorial.pdf file for knowing which index should be north, south, west and east.

    Args
        grid_obs:   <list>  list of block types string representing the blocks on the map.
        source:     <int>   source block index.
        dest:       <int>   destination block index.

    Returns
        path_list:  <list>  block indexes representing a path from source (first element) to destination (last)
    """
    #------------------------------------
    #
    #   Fill and submit this code
    #

    # Assistant functions
    square_side_length = AGENT_OBSERVATION_LENGTH

    def is_reachable(block):
        return block in ["emerald_block", "redstone_block", "diamond_block"]

    def get_all_visable_positions(index):
        result = []
        # check left
        result.append((index - 1)) if ((index - 1) in reachable_blocks) else None
        # check right
        result.append((index + 1)) if ((index + 1) in reachable_blocks) else None
        # check above
        result.append((index - square_side_length)) if ((index - square_side_length) in reachable_blocks) else None
        # check below
        result.append((index + square_side_length)) if ((index + square_side_length) in reachable_blocks) else None
        return result

    reachable_blocks = []

    for index, block in enumerate(grid_obs):
        if is_reachable(block):
            reachable_blocks.append(index)

    pq = priorityDictionary()

    for index in reachable_blocks:
        pq[index] = sys.maxsize

    pq[source] = 0

    shortest_paths = {source: [None, 0]}
    current_position = source
    visited_positions = []
    visited_positions.append(source)

    while current_position != dest:
        destinations = get_all_visable_positions(current_position)
        cost_of_current_position = pq[current_position]

        for position in destinations:
            if position not in visited_positions:
                current_cost_to_position = pq[position]
                new_cost_to_position = cost_of_current_position + 1
                if new_cost_to_position < current_cost_to_position:
                    pq[position] = new_cost_to_position
                    shortest_paths[position] = [current_position, current_cost_to_position]
        
        visited_positions.append(current_position)
        del pq[current_position]
        current_position = pq.smallest()
    
    previous_position = dest
    path_to_dest = [dest]
    while previous_position != source:
        previous_position = shortest_paths[previous_position][0]
        path_to_dest.append(previous_position)

    path_to_dest.reverse()

    return path_to_dest
    #-------------------------------------

def extract_action_list_from_path(path_list):
    """
    Converts a block idx path to action list.

    Args
        path_list:  <list>  list of block idx from source block to dest block.

    Returns
        action_list: <list> list of string discrete action commands (e.g. ['movesouth 1', 'movewest 1', ...]
    """
    action_trans = {-AGENT_OBSERVATION_LENGTH: 'movenorth 1', AGENT_OBSERVATION_LENGTH: 'movesouth 1', -1: 'movewest 1', 1: 'moveeast 1'}
    alist = []
    for i in range(len(path_list) - 1):
        curr_block, next_block = path_list[i:(i + 2)]
        alist.append(action_trans[next_block - curr_block])

    return alist

# End of helpful classes or functions not related to the core of the project

def load_grid(world_state, agent_host):
    """
    Used the agent observation API to get a 21 X 21 grid box around the agent (the agent is in the middle).

    Args
        world_state:    <object>    current agent world state

    Returns
        grid:   <list>  the world grid blocks represented as a list of blocks (see Tutorial.pdf)
    """
    while world_state.is_mission_running:
        #sys.stdout.write(".")
        time.sleep(0.1)
        world_state = agent_host.getWorldState()
        if len(world_state.errors) > 0:
            raise AssertionError('Could not load grid.')

        if world_state.number_of_observations_since_last_state > 0:
            msg = world_state.observations[-1].text
            observations = json.loads(msg)
            grid = observations.get(u'floorAll', 0)
            break
    return grid

# Not used since we need to do set some parameters programmatically
# def get_mission_xml():
#     xml_file = open("./ikun_mission.xml", "r")
#     return xml_file.read()

def get_mission_xml(seed, gp, size=10, yaw=0):
    # yaw: only accept 0, 90, 180, 270 and 360
    if yaw not in [0, 90, 180, 270, 360]:
        raise Exception("IllegalYawPararmeter: yaw only accept 0, 90, 180, 270, 360, where", yaw, "is given!")
    return '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

              <About>
                <Summary>Adventure of Aiku</Summary>
              </About>

            <ServerSection>
              <ServerInitialConditions>
                <Time>
                    <StartTime>1000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                </Time>
                <Weather>clear</Weather>
              </ServerInitialConditions>
              <ServerHandlers>
                  <FlatWorldGenerator generatorString="3;1*minecraft:bedrock,7*minecraft:dirt,1*minecraft:grass;1;village,mineshaft(chance=0.01),stronghold(chance=32 count=3 spread=3),biome_1(distance=32),dungeon,decoration,lake,lava_lake"/>
                  <DrawingDecorator>
                    <DrawSphere x="-27" y="70" z="0" radius="30" type="air"/>
                    <DrawCuboid x1="-35" y1="19" z1="-7" x2="''' + str(-31+size) + '''" y2="21" z2="''' + str(-3+size) + '''" type="structure_block" />
                  </DrawingDecorator>
                  <MazeDecorator>
                    <Seed>'''+str(seed)+'''</Seed>
                    <SizeAndPosition width="''' + str(size) + '''" length="''' + str(size) + '''" height="10" xOrigin="-32" yOrigin="20" zOrigin="-5"/>
                    <StartBlock type="emerald_block" fixedToEdge="false"/>
                    <EndBlock type="redstone_block" fixedToEdge="true"/>
                    <PathBlock type="diamond_block"/>
                    <FloorBlock type="air"/>
                    <GapBlock type="lava"/>
                    <GapProbability>'''+str(gp)+'''</GapProbability>
                    <AllowDiagonalMovement>false</AllowDiagonalMovement>
                  </MazeDecorator>
                  <ServerQuitWhenAnyAgentFinishes/>
                </ServerHandlers>
              </ServerSection>

              <AgentSection mode="Survival">
                <Name>Aiku</Name>
                <AgentStart>
                    <Placement x="0.5" y="56.0" z="0.5" pitch="30" yaw="''' + str(yaw) + '''"/>
                </AgentStart>
                <AgentHandlers>
                    <DiscreteMovementCommands/>
                    <AgentQuitFromTouchingBlockType>
                        <Block type="redstone_block"/>
                    </AgentQuitFromTouchingBlockType>
                    <ObservationFromGrid>
                      <Grid name="floorAll">
                        <min x="-30" y="-1" z="-30"/>
                        <max x="30" y="-1" z="30"/>
                      </Grid>
                  </ObservationFromGrid>
                </AgentHandlers>
              </AgentSection>
            </Mission>'''

def is_reachable(block):
    # Return true is the block is walkable; otherwise, return false.
    return block in ["emerald_block", "redstone_block", "diamond_block"]

def is_in_map(block):
    # Return true is the block is inside the map; otherwise, return false.
    return block in ["diamond_block", "redstone_block", "emerald_block", "flowing_lava", "lava"]

def get_maze_map(original_grid):
    # get the actual map of maze in the word
    # return a list
    # original_grid: the original map in list (Observed by agent; defined in XML as ObservationFromGrid)
    temp_grid = []
    for index, block in enumerate(original_grid):
        if is_in_map(block):
            temp_grid.append(block)
            global first_block_index_in_actual_map, last_block_index_in_actual_map
            if first_block_index_in_actual_map == -1:
                first_block_index_in_actual_map = index
            last_block_index_in_actual_map = index
            #print("Next one after:", block, "is", original_grid[index+1])
    return temp_grid

def find_start_end(grid):
    """
    Finds the source and destination block indexes from the list.

    Args
        grid:   <list>  the world grid blocks represented as a list of blocks (see Tutorial.pdf)

    Returns
        start: <int>   source block index in the list
        end:   <int>   destination block index in the list
    """
    #------------------------------------
    #
    #   Fill and submit this code
    #
    return (grid.index("emerald_block"), grid.index("redstone_block"))
    #-------------------------------------

def agent_turn_left():
    # make agent turn left (Not actually turn left)
    global agent_current_direction
    agent_current_direction -= 1
    if agent_current_direction == -1:
        agent_current_direction = 3
    #print("After turn left:", agent_current_direction)

def agent_turn_right():
    # make agent turn right (Not actually turn right)
    global agent_current_direction
    agent_current_direction += 1
    if agent_current_direction == 4:
        agent_current_direction = 0
    #print("After turn right:", agent_current_direction)

def move_forward(agent_host, grid):
    # move 1 to the agent's current direction(fake)
    # Also deal with the agent position variables (both)
    global agent_current_position_xy_in_maze, agent_current_position_index_in_grid, matrix2dOriginal, maze_map
    
    
    backup_xy_in_maze = copy.deepcopy(agent_current_position_xy_in_maze)
    backup_agent_current_posisition_index_in_grid = agent_current_position_index_in_grid 
    """
    if agent_current_direction == 0:
        agent_host.sendCommand("movesouth 1")
        agent_current_position_xy_in_maze[1] += 1
        agent_current_position_index_in_grid += AGENT_OBSERVATION_LENGTH
    elif agent_current_direction == 1:
        agent_host.sendCommand("movewest 1")
        agent_current_position_xy_in_maze[0] -= 1
        agent_current_position_index_in_grid -= 1
    elif agent_current_direction == 2:
        agent_host.sendCommand("movenorth 1")
        agent_current_position_xy_in_maze[1] -= 1
        agent_current_position_index_in_grid -= AGENT_OBSERVATION_LENGTH
    elif agent_current_direction == 3:
        agent_host.sendCommand("moveeast 1")
        agent_current_position_xy_in_maze[0] += 1
        agent_current_position_index_in_grid += 1
    """
    print("agent_current_direction: ",agent_current_direction)

    print("In move_forward:", agent_current_position_xy_in_maze)

    #JUST FOR TEST
    if agent_current_direction == 0:
        
        agent_current_position_xy_in_maze[1] += 1
        agent_current_position_index_in_grid += AGENT_OBSERVATION_LENGTH
        #x,y = agent_current_position_xy_in_maze[0], agent_current_position_xy_in_maze[1]
        #We use formula caclulating maze map index to check the next step

        print("In move_foreward, direction is", agent_current_direction, "; and next position:", agent_current_position_xy_in_maze)
        index = get_position_of_actual_map_by_xy_position_of_maze_map(agent_current_position_xy_in_maze, grid)
        if is_reachable(grid[index]):
            agent_host.sendCommand("movesouth 1")
        else:
            print('Encountered Obstacle')
            agent_current_position_xy_in_maze = backup_xy_in_maze
            agent_current_position_index_in_grid = backup_agent_current_posisition_index_in_grid
            
    elif agent_current_direction == 1:
       
        agent_current_position_xy_in_maze[0] -= 1
        agent_current_position_index_in_grid -= 1
        x,y = agent_current_position_xy_in_maze[0], agent_current_position_xy_in_maze[1]

        print("In move_foreward, direction is", agent_current_direction, "; and next position:", agent_current_position_xy_in_maze)
        index = get_position_of_actual_map_by_xy_position_of_maze_map(agent_current_position_xy_in_maze, grid)
        if is_reachable(grid[index]):
            agent_host.sendCommand("movewest 1")
        else:
            print('Encountered Obstacle')
            agent_current_position_xy_in_maze = backup_xy_in_maze
            agent_current_position_index_in_grid = backup_agent_current_posisition_index_in_grid
        
    elif agent_current_direction == 2:
        
        agent_current_position_xy_in_maze[1] -= 1
        agent_current_position_index_in_grid -= AGENT_OBSERVATION_LENGTH
        x,y = agent_current_position_xy_in_maze[0], agent_current_position_xy_in_maze[1]

        print("In move_foreward, direction is", agent_current_direction, "; and next position:", agent_current_position_xy_in_maze)
        index = get_position_of_actual_map_by_xy_position_of_maze_map(agent_current_position_xy_in_maze, grid)
        if is_reachable(grid[index]):
            agent_host.sendCommand("movenorth 1")
        else:
            print('Encountered Obstacle')
            agent_current_position_xy_in_maze = backup_xy_in_maze
            agent_current_position_index_in_grid = backup_agent_current_posisition_index_in_grid
        
    elif agent_current_direction == 3:
        
        agent_current_position_xy_in_maze[0] += 1
        agent_current_position_index_in_grid += 1
        #x,y = agent_current_position_xy_in_maze[0], agent_current_position_xy_in_maze[1]

        print("In move_foreward, direction is", agent_current_direction, "; and next position:", agent_current_position_xy_in_maze)
        
        index = get_position_of_actual_map_by_xy_position_of_maze_map(agent_current_position_xy_in_maze, grid)
        if is_reachable(grid[index]):
            agent_host.sendCommand("moveeast 1")
        else:
            print('Encountered Obstacle')
            agent_current_position_xy_in_maze = backup_xy_in_maze
            agent_current_position_index_in_grid = backup_agent_current_posisition_index_in_grid
        

def get_xy_position_of_maze_map_by_position_of_actual_map(\
    position_in_actual_map, grid):
    # position_in_actual_map: index in grid
    # Assuming grid is 61 * 61 (defined in XML as ObservationFromGrid)
    # returning (x, y) (Started from (0, 0) as bottom right)
    size_of_grid = len(grid)
    y_position = position_in_actual_map // AGENT_OBSERVATION_LENGTH - \
        first_block_index_in_actual_map // AGENT_OBSERVATION_LENGTH
    x_position = position_in_actual_map % AGENT_OBSERVATION_LENGTH - \
        first_block_index_in_actual_map % AGENT_OBSERVATION_LENGTH
    return [x_position, y_position]

def get_position_of_actual_map_by_xy_position_of_maze_map(\
    xy_position_in_maze_map, grid):
    # xy_position_in_maze_map: (x, y) (Started from (0, 0) as bottom right)
    # Assuming grid is 61 * 61 (defined in XML as ObservationFromGrid)
    # returning index in grid
    return xy_position_in_maze_map[1] * AGENT_OBSERVATION_LENGTH + first_block_index_in_actual_map \
        + xy_position_in_maze_map[0]

def test_moving(agent_host, directions, grid):
    # this function is used for testing agent to move
    # directions should be a list
    # e.g. giving directions as [0, 1, 2, 0]
    # direction here is absolute to the agent's current direction
    # p.s. this function will restore the agent's direction back to the original one when it finishes moving
    print("Before moving, the agent is at xy_maze:", agent_current_position_xy_in_maze, \
        "and it is at index_of_grid:", agent_current_position_index_in_grid)
    global agent_current_direction
    original_direction = agent_current_direction
    for direction in directions:
        #print('The agent curent direction: ', agent_current_direction)
        print("The direction: ", direction)
        if direction == 1:
            print('The agent turn right')
            agent_turn_right()
        elif direction == 2:
            agent_turn_left()
            agent_turn_left()
            print('The agnet truns back')
        elif direction == 3:
            agent_turn_left()
            print('The agent turn left')
        elif direction == 0:    
            move_forward(agent_host, grid)
            print('The agent move forward')
        print("After making a move of [" + str(direction) + "], the agent is at xy_maze:", \
            agent_current_position_xy_in_maze , "and it is at index_of_grid:", agent_current_position_index_in_grid)
        #agent_current_direction = original_direction
        time.sleep(2)
        print("Sleep finish, going to next...")

def execute_action_list(agent_host, directions):
    # same as test_moving function, but without printing log
    global agent_current_direction
    original_direction = agent_current_direction
    for direction in directions:
        if direction == 1:
            agent_turn_right()
        elif direction == 2:
            agent_turn_left()
            agent_turn_left()
        elif direction == 3:
            agent_turn_left()
        move_forward(agent_host)
        agent_current_direction = original_direction
        time.sleep(2)

def sync_agent_direction_with_yaw(yaw):
    global agent_current_direction
    if yaw in [0, 360]:
        agent_current_direction = 0
    elif yaw == 90:
        agent_current_direction = 1
    elif yaw == 180:
        agent_current_direction = 2
    elif yaw == 270:
        agent_current_direction = 3
    else:
        print("Illegal yaw is given:", yaw)

def go_to_goal_and_finish_mission(grid, agent_current_position_index_in_grid,\
     goal_position_index_in_grid, world_state, agent_host, mission_number):
    shortest_path_to_goal = dijkstra_shortest_path(grid, agent_current_position_index_in_grid, goal_position_index_in_grid)
    actions_of_shortest_path_to_goal = extract_action_list_from_path(shortest_path_to_goal)
    
    print("Output (start,end)", (mission_number+1), ":", (agent_current_position_index_in_grid,\
        goal_position_index_in_grid))
    print("Output (path length)", (mission_number+1), ":", len(shortest_path_to_goal))
    print("Output (actions)", (mission_number+1), ":", actions_of_shortest_path_to_goal)
    
    # Loop until mission ends:
    action_index = 0
    while world_state.is_mission_running:
        #sys.stdout.write(".")
        time.sleep(0.1)

        # Sending the next commend from the action list -- found using the Dijkstra algo.
        if action_index >= len(actions_of_shortest_path_to_goal):
            print("Error:", "out of actions, but mission has not ended!")
            time.sleep(2)
        else:
            agent_host.sendCommand(actions_of_shortest_path_to_goal[action_index])
        action_index += 1
        if len(actions_of_shortest_path_to_goal) == action_index:
            # Need to wait few seconds to let the world state realise I'm in end block.
            # Another option could be just to add no move actions -- I thought sleep is more elegant.
            time.sleep(2)
        world_state = agent_host.getWorldState()
        for error in world_state.errors:
            print("Error:",error.text)

    print()
    print("Mission", (mission_number+1), "ended")

def get_num_of_walkable_blocks_in_front_of_agent(agent_current_position_xy_in_maze, size_of_maze, grid):
    # will return 0 if the block in front of agent's current direction is not walkable
    result = 0
    agent_current_direction_xy_in_maze_temp_copy = copy.deepcopy(agent_current_position_xy_in_maze)
    while True:
        if agent_current_direction == 0:
            agent_current_direction_xy_in_maze_temp_copy[1] += 1
        elif agent_current_direction == 1:
            agent_current_direction_xy_in_maze_temp_copy[0] -= 1
        elif agent_current_direction == 2:
            agent_current_direction_xy_in_maze_temp_copy[1] -= 1
        elif agent_current_direction == 3:
            agent_current_direction_xy_in_maze_temp_copy[0] += 1
        else:
            raise Exception("NoLegalDirection: get_num_of_walkable_blocks_in_front_of_agent, where direction is:", \
                agent_current_direction)
        # print("Going to check: ", agent_current_direction_xy_in_maze_temp_copy, "with direction:", agent_current_direction)
        if agent_current_direction_xy_in_maze_temp_copy[0] < 0 or \
            agent_current_direction_xy_in_maze_temp_copy[0] >= size_of_maze or \
                agent_current_direction_xy_in_maze_temp_copy[1] < 0 or \
                    agent_current_direction_xy_in_maze_temp_copy[1] >= size_of_maze or \
                        not is_reachable(grid[get_position_of_actual_map_by_xy_position_of_maze_map(agent_current_direction_xy_in_maze_temp_copy, \
                            grid)]):
                            break
        result += 1
    return result

def maze_to_2dMatrix(maze_map, size_of_maze):
    matrix2d = []
    i = 0
    #print("This is maze_map: ",len(maze_map))
    while i < len(maze_map):
        subList = []
        innerI = 0
        while innerI < size_of_maze:
            #print('There is the BUG: ',maze_map[i+innerI])
            if is_reachable(maze_map[i+innerI]):
                subList.append(0)
            else:
                subList.append(1)
            innerI += 1
        matrix2d.append(subList)
        i += size_of_maze
    return matrix2d

def maze_to_2dMatrix_reversed(maze_map, size_of_maze):
    matrix2d = []
    #print("size of maze:", size_of_maze)
    """for i in range(0, len(maze_map), size_of_maze):
        subList = []
        for innerI in range(0, size_of_maze):
            print(i, innerI)
            print(i+innerI)
            if is_reachable(maze_map[i+innerI]):
                subList.append(1)
            else:
                subList.append(0)
        matrix2d.append(subList)
    """
    i = 0
    #print("This is maze_map: ",len(maze_map))
    while i < len(maze_map):
        subList = []
        innerI = 0
        while innerI < size_of_maze:
            #print('There is the BUG: ',maze_map[i+innerI])
            if is_reachable(maze_map[i+innerI]):
                subList.append(0)
            else:
                subList.append(1)
            innerI += 1
        matrix2d.append(subList)
        i += size_of_maze

    reversedMatrix = []
    
    i = len(matrix2d) - 1
    while i >= 0:
        #print('the i is : ', i)
        subList = []
        innerI = len(matrix2d[i])-1
        while innerI >= 0:
            subList.append(matrix2d[i][innerI])
            innerI -= 1
        reversedMatrix.append(subList)
        print('THE SUBLIST: ', subList)
        i -= 1

    matrix2d = np.array(reversedMatrix)
    return matrix2d.astype(np.float64)

def is_finish(block):
    # return true if the agent is standing in the goal block
    return block == "redstone_block"

def positionTransition(grid, matrixArray, orientation, size_of_maze):
    start_and_end_positions_in_actual_map = find_start_end(grid)
    startPosition = get_xy_position_of_maze_map_by_position_of_actual_map(\
    start_and_end_positions_in_actual_map[0], \
        grid)
    
    newOrientation = orientation
    if orientation == 0:
        newOrientation = 1
    elif orientation == 1:
        newOrientation = 0
    elif orientation == 2:
        newOrientation = 3
    elif orientation == 3:
        newOrientation = 2

    newStartPosition = [size_of_maze - startPosition[1]-1, \
        size_of_maze - startPosition[0]-1, newOrientation]
    newStartPosition = np.array(newStartPosition)
    print("The matrix: ",matrixArray)
    concatMatrix = np.concatenate((matrixArray, newStartPosition), axis = None)
    concatMatrix = np.reshape(concatMatrix,(1,-1))

    print(concatMatrix)

    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '../Neural-Localization/test_data/hello.npy')
    print(file_path)
    np.save(file_path, concatMatrix)

def directionConvert(direction):
    converted = direction
    if direction == 1:
        converted = 1
    elif direction == 2:
        converted = 0
    elif direction == 0:
        converted = 3
    return converted

def main():
    # Start mission
    # Create default Malmo objects:
    global agent_host
    global matrix2dOriginal
    global maze_map
    global actionHistCounter
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

    # The following one line is for setting how many times you want the agent to repeat
    num_repeats = 10

    esFile = open("Eval_Stats.txt", "w+")
    esFile.write("\n")
    esFile.close()

    esFile = open("Eval_Stats.txt", "a")

    for i in range(num_repeats):
        esFile.write("Run #"+str(i+1)+"\n")
        actionHistCounter = i+1
        # size = int(6 + 0.5*i)
        print("Size of maze:", size_of_maze)
        #my_mission = MalmoPython.MissionSpec(get_mission_xml("0", 0.4 + float(i/20.0), size_of_maze, 0), True)
        print("Parameters of the mission:", str(i), "next:", 0.4 + float(i/20.0), "size:", size_of_maze)
        my_mission = MalmoPython.MissionSpec(get_mission_xml(str(i), 0.4 + float(i/20.0), size_of_maze, 0), True)
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

        grid = load_grid(world_state, agent_host)
        # print("World State Grid:", grid)
        print("Size of actual map:", len(grid))
        
        maze_map = get_maze_map(grid)
        print("maze map:", len(maze_map))
        #print(maze_map[244])
        #The maze construction
        matrix2dOriginal = maze_to_2dMatrix(maze_map, size_of_maze)
        matrix2d = maze_to_2dMatrix_reversed(maze_map, size_of_maze)
        print("the matrix 2d: ", matrix2d)
        matrixArray = matrix2d.flatten()

        start_and_end_positions_in_actual_map = find_start_end(grid)
        
        print("size of maze map:", len(maze_map))
        print("first position in actual map:", first_block_index_in_actual_map)
        print("last position in actual map:", last_block_index_in_actual_map)

        global agent_current_position_xy_in_maze, agent_current_position_index_in_grid

        agent_current_position_xy_in_maze = get_xy_position_of_maze_map_by_position_of_actual_map(\
            start_and_end_positions_in_actual_map[0], \
                grid)
        
        print("Started: agent current position(xy in maze):", agent_current_position_xy_in_maze)
        
        agent_current_position_index_in_grid = get_position_of_actual_map_by_xy_position_of_maze_map(\
            agent_current_position_xy_in_maze, grid)

        print("Started: agent current position(index in grid):", agent_current_position_index_in_grid \
            , "compared with real position:", start_and_end_positions_in_actual_map[0])
        
        index_of_yaw = my_mission.getAsXML(True).index("yaw")
        yaw_of_agent = int(re.compile("(\d+)").match(my_mission.getAsXML(True)[index_of_yaw+5 : index_of_yaw+8]).group(1))
        sync_agent_direction_with_yaw(yaw_of_agent)

        print("Started: agent current yaw(face to where):", yaw_of_agent)

        # go_to_goal_and_finish_mission(grid, start_and_end_positions_in_actual_map[0], \
        #     start_and_end_positions_in_actual_map[1], world_state, agent_host, i)

        print("Started: How many walkable blocks in front of agent's direction:", agent_current_direction, "is walk able? Answer:", \
            get_num_of_walkable_blocks_in_front_of_agent(agent_current_position_xy_in_maze, size_of_maze, grid))

        # test_moving(agent_host, [3, 3, 0, 3, 3, 0, 3])

        positionTransition(grid, matrixArray, yaw_of_agent, size_of_maze)

        trainingStart = time.time()
        os.system("python ../Neural-Localization/a3c_main.py --num-processes 0 --evaluate 1 --map-size 21 --max-episode-length 60 --load ../Neural-Localization/pretrained_models/m21_l60 --test-data ../Neural-Localization/test_data/hello.npy --counter " + str(actionHistCounter))

        stringList = []
        
        while True:
            actionHistFile = open("action_history_"+str(actionHistCounter)+"_.txt", "r")
            stringList = actionHistFile.readlines()
            if (stringList[len(stringList)-1] == "END"):
                break
        trainingEnd = time.time()
        trainingElapsed = trainingEnd - trainingStart
        esFile.write("Training Time: " + str(trainingElapsed) + " ")

        actionHistFile.close()
        
        #actionList = []

        print(stringList)
        actionCollection = []
        positionCollection = []
        for n in range(0, len(stringList)-1):
            tmp = stringList[n].split(' ')
            for m in range(0,len(tmp)-1):
                L = tmp[m].split(',')
                actionCollection.append(L[0])
                positionCollection.append([L[1],L[2]])

        print('The original: ',actionCollection)
        print(positionCollection)
        """
        del stringList[-1]
        for string in stringList:
            actionCollection = string.split(' ')
            del actionCollection[-1]
            for aindex in range(len(actionCollection)):
                converted = directionConvert(int(actionCollection[aindex]))
                actionCollection[aindex] = converted
            actionList.append(actionCollection)
        """
        """
        for testingset in actionList:
            #check if it's reachable

            test_moving(agent_host, testingset)
        """
        actionList = []
        
        for index in range(len(actionCollection)):
            row,col = positionCollection[index][0], positionCollection[index][1]
            action = actionCollection[index]
            print(matrix2d[int(row)][int(col)])
            if matrix2d[int(row)][int(col)] == 0:
                convertAction = directionConvert(int(action))
                actionList.append(convertAction)
        #print('THIS IS THE ACTION: ',len(actionList), actionList)
        
        print('The list:', actionList)
        #raise('STOP HERE')
        test_moving(agent_host, actionList, grid)
        
        print("Training complete. Training result can be found in training_result.txt.")

        travelStart = time.time()
        go_to_goal_and_finish_mission(grid, agent_current_position_index_in_grid, \
             start_and_end_positions_in_actual_map[1], world_state, agent_host, i)
        travelEnd = time.time()
        travelElapsed = travelEnd - travelStart
        esFile.write("Agent Travel Time: "+str(travelElapsed) + "\n\n")

        print("Aiku did it!")
    
    esFile.close()

if __name__ == "__main__":
    main()