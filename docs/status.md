---
layout: default
title:  Status
---

#### Project Summary
Our project makes use of Deep Q-Learning with Neural Network to let the agent find the shortest path between the source/starting block (unknown to the agent initially) and the destination block (unknown to the agent initially) in a pre-build 2D maze. The agent will be led to play in a set of pre-built Minecraft 2D mazes. The agent is able to see the voxels in front of its sight, which is similar to what a normal player can see in Minecraft (however, we might also change this to be a small range of voxels around the agent). The agent is given the full map of a maze, but it does not know source/starting block (the agent needs to locate itself on the map first) and the destination block (the agent needs to find its way out of the maze). The agent's goal is trying to get out of the maze as fast as possible using the limited resources we have given to the agent. The output (for each maze) is the starting block of the agent and a set of positions of blocks ordered by the path sequence found by the agent (if optimal, should be the shortest path between agent's starting block and the destination block).

#### Approach

#### Evaluation
For quantitative evaluation, we plan to use two features as metrics. The first metric is the time taken for the agent to get out of a maze (measured in fixed timestep). Thid metric will indicate how efficient a particular algorithm is implemented. The second metric is the number of voxels that the agent has visited (repeated visits will be counted separately as we are measuring how far the agent has travelled to reach the goal).
For qualitative evaluation, we plan to run the agent with each implemented algorithm within a controlled set of mazes (ranges from the simplest to the most complicated). There are also edge cases in which a maze might not have any exit , which becomes a dead block for the agent from the very beginning. On the other hand, a maze could have mutiple exits, and a smart agent should be able to find the most optimal exit for the shortest travelled path. If an algorithm can pass all these tests, then it is proven to be working. For moonshot cases, we plan to add monsters and traps to the mazes, which significantly increases the complexity of the world for the agent to perceive. The agent carries a weapon that is a type of consumable, which can be used to fight against monsters. In the best scenario,the agent will reach the goal.

#### Remaining Goals and Challenges

#### Resources Used