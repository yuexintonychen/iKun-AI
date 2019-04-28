﻿---
layout: default
tile:   proposal
---

<center>Proposal</center>

## Summary of the Project
        We plan to make some mazes for our agent to play in (The mazes will be in 2D, but if we could make a good progress in the project, we might make the maze to be 3D). Our agent's input will be the voxels in front of its sight, which will be similar to what a normal player can see in Minecraft (However, we might also change this to be a small range of voxels around the agent). The agent's goal (output) will be trying to get out of the maze as fast as possible using the limited resources we have gived to the agent.

## AI/ML Algorithms
        We will be using reinforcement learning algorithm (Q-learning and Neural Network). We might be also using conventional shortest path algorithms like Dijkstra's algorithm for comparing the difference if possible.

## Evaluation Plan
        For quantitative evaluation, we plan to use two features as metrics. The first metric is the time taken for the agent to get out of a maze (measured in fixed timestep). Thid metric will indicate how efficient a particular algorithm is implemented. The second metric is the number of voxels that the agent has visited (repeated visits will be counted separately as we are measuring how far the agent has travelled to reach the goal).
        For qualitative evaluation, we plan to run the agent with each implemented algorithm within a controlled set of mazes (ranges from the simplest to the most complicated). There are also edge cases in which a maze might not have any exit , which becomes a dead block for the agent from the very beginning. On the other hand, a maze could have mutiple exits, and a smart agent should be able to find the most optimal exit for the shortest travelled path. If an algorithm can pass all these tests, then it is proven to be working. For moonshot cases, we plan to add monsters and traps to the mazes, which significantly increases the complexity of the world for the agent to perceive. The agent carries a weapon that is a type of consumable, which can be used to fight against monsters. In the best scenario,the agent will reach the goal.

## Appointment with the Instructor
        The meeting with instructor is scheduled at 9:30 - 9:45 a.m. on May 8th 2019.

























