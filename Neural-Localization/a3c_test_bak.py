import time
import logging

from maze2d import *
from model import *
from collections import deque

import sys
sys.path.append("../codes")

def test(rank, args, shared_model, actual_counter_string):
    args.seed = args.seed + rank
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    env = Maze2D(args)
    action_hist_size = args.hist_size

    model = Localization_2D_A3C(args)
    if (args.load != "0"):
        print("Loading model {}".format(args.load))
        model.load_state_dict(torch.load(args.load))
    model.eval()

    reward_sum = 0
    episode_length = 0
    rewards_list = []
    accuracy_list = []
    best_reward = 0.0
    done = True

    if args.evaluate != 0:
        test_freq = env.test_mazes.shape[0]
    else:
        test_freq = 1000

    start_time = time.time()

    state, depth = env.reset()
    state = torch.from_numpy(state).float()

    #actionHistFile = open("action_history"+str(ikun_mission.actionHistCounter)+".txt", "w+")
    
    actionHistFile = open("action_history_" + actual_counter_string + "_.txt", "w+")

    while True:
        episode_length += 1
        if done:
            if (args.evaluate == 0):
                # Sync with the shared model
                model.load_state_dict(shared_model.state_dict())

            # filling action history with action 3 at the start of the episode
            action_hist = deque(
                [3] * action_hist_size,
                maxlen=action_hist_size)
            action_seq = []
        else:
            action_hist.append(action)
        '''
        ax = Variable(torch.from_numpy(np.array(action_hist)),
                      volatile=True)
        dx = Variable(torch.from_numpy(np.array([depth])).long(),
                      volatile=True)
        tx = Variable(torch.from_numpy(np.array([episode_length])).long(),
                      volatile=True)
        '''
        with torch.no_grad():
            ax = Variable(torch.from_numpy(np.array(action_hist)))
            dx = Variable(torch.from_numpy(np.array([depth])).long())
            tx = Variable(torch.from_numpy(np.array([episode_length])).long())
            
            """
            tempActionList = []
            for index in range(len(action_hist)):
                tempActionList.append(action_hist[index])
                actionHistFile.write("%d " %(action_hist[index]))
            actionHistFile.write("\n")
            #ikun_mission.test_moving(ikun_mission.agent_host, tempActionList)
            """
            value, logit = model((Variable(state.unsqueeze(0)), (ax, dx, tx)))
            
        prob = F.softmax(logit, dim=1)
        #print('The probability: ', prob)
        action = prob.max(1)[1].data.numpy()[0]
        
        state, reward, done, depth = env.step(action)
        #print('The action:', action)
        #print('The environment: ',  env.position)
        actionHistFile.write(str(int(action)) + "," + str(int(env.position[0])) + "," + str(int(env.position[1])) + " ")
        done = done or episode_length >= args.max_episode_length
        reward_sum += reward

        if done:
            actionHistFile.write("\nEND")
            actionHistFile.close()

            rewards_list.append(reward_sum)
            if reward >= 1:
                accuracy = 1
            else:
                accuracy = 0
            accuracy_list.append(accuracy)

            if(len(rewards_list) >= test_freq):
                trFile = open("training_result.txt", "a")
                esFile = open("Eval_Stats.txt", "a")
                time_elapsed = time.gmtime(time.time() - start_time)
                trFile.write(" ".join([
                    #"Time: {0:0=2d}d".format(time_elapsed.tm_mday-1),
                    #"{},".format(time.strftime("%Hh %Mm %Ss", time_elapsed)),
                    "Avg Reward: {0:.3f},".format(np.mean(rewards_list)),
                    "Avg Accuracy: {0:.3f},".format(np.mean(accuracy_list)),
                    "Best Reward: {0:.3f}".format(best_reward)]))
                trFile.write("\n")
                trFile.close()
                esFile.write(
                    "Avg Accuracy: {0:.3f} ".format(np.mean(accuracy_list))
                )
                esFile.write("\n")
                esFile.close()
                logging.info(" ".join([
                    "Time: {0:0=2d}d".format(time_elapsed.tm_mday-1),
                    "{},".format(time.strftime("%Hh %Mm %Ss", time_elapsed)),
                    "Avg Reward: {0:.3f},".format(np.mean(rewards_list)),
                    "Avg Accuracy: {0:.3f},".format(np.mean(accuracy_list)),
                    "Best Reward: {0:.3f}".format(best_reward)]))
                if args.evaluate != 0:
                    return
                elif (np.mean(rewards_list) >= best_reward):
                    torch.save(model.state_dict(),
                               args.dump_location + "model_best")
                    best_reward = np.mean(rewards_list)
                rewards_list = []
                accuracy_list = []


            reward_sum = 0
            episode_length = 0
            state, depth = env.reset()

        state = torch.from_numpy(state).float()
