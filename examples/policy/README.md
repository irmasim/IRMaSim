Policy Agent Experiments
========================

Overview
--------

The Policy agent is capable of choosing the best scheduling policy from a given set. A scheduling policy is in this case a combination of policies. One to choose the next job to schedule and the other to choose the resource in which to launch the job. For instance the first-high_gflops policy schedules the first job from the queue to an idle core with the highest processing speed.

In this folder there are two simple experiments to prove that the agent is capable of learing the best policy. The first experiment called 'save' considers two policies: 'first-high_gflops'  and 'first-low_power' and the objective to optimise is the energy consumption of the cluster, and therefore, the best policy is 'first-low_power'. The workload consists on eight identical jobs, and the platform is a two-node cluster. One node is faster and the other consumes less power. The agent should choose the 'first-low_power' policy to achieve less enery consumption.

In the second experiment, called 'spread', the agent must decide between the two policies 'first-high_gflops' and 'first-high_cores' to minimise the execution time of a set of jobs. In this case the platform has eight identical nodes with four cores each, and there are also eight jobs in the workload. However, since the jobs have a high memory usage, executing all the jobs in two nodes, causes a high memory access contention. This, in turn, slows down significantly the execution of the jobs. Then, if execution time must be reduced it is better to schedule one job to each node, eliminating memory access contention. The agent should become aware of this fact and choose the 'first-high_cores' policy that schedules jobs to the nodes with the highest amount of free cores.

Experiment Details
------------------

Both experiments have the same structure, so only the 'save' will be described. The files in the experiment folder are the following.

 - platform.json is the definition of the computing resources of the cluster
 - workload.json is the definition of the jobs submitted to the cluster.
 - options_high_gflops.json simulates the use of the first-high_gflops policy exclusively.
 - options_low_power.json simulates the use of the first-low_power policy exclusively.
 - options_agent.json simulates the agent that must choose between both policies.
 - execute_experiments.sh is a script that executes all the simulations in the experiment
 - high_gflops is a folder that holds the results of the options_high_gflops simulation.
 - low_power is a folder that holds the results of the options_low_power simulation.
 - agent is a folder that holds the results of the agent training.
 - agent.model is the agent file after training.


Save Experiment
---------------

After running the execute_experiments.sh script, the three folders high_gflops, low_power and agent are created and filled with simulation results and logs. These give different insights about the development of the experiment.


high_gflops/simulation.log
~~~~~~~~~~~~~~~~~~~~~~~~~~

run,time,energy,future_jobs,pending_jobs,running_jobs,finished_jobs
0,0,0,8,0,0,0
...
0,35.34243583528412,985.6822291088713,0,0,0,8

The total execution time, 35.34s, and energy consumption, 985.68J, can be seen on the last line of this file.

high_gflops/jobs.log
~~~~~~~~~~~~~~~~~~~~

This file shows that all jobs were scheduled to the same node: the_platform.cluster0.node0

low_power/simulation.log
~~~~~~~~~~~~~~~~~~~~~~~~

In the last line of this file, it can be seen that the 'first-low_power' takes longer to execute the jobs, 39.21s, but it requires less energy than 'first-high_gflops', 834.45J. 

low_power/jobs.log
~~~~~~~~~~~~~~~~~~

This file shows that the first four jobs are executed in the slower node the_platform.cluster0.node1, and the other four on the fast one the_platform.cluster0.node0.

agent/simulation.log
~~~~~~~~~~~~~~~~~~~~

This file shows the evolution of the 10 simulations performed to train the agent. It allows following the evolution of the optimisation metric, the energy consumption. In this case, the agent learns quickly that the 'first-low_power' policy is the best, so the metric stabilises to a minimal value in the first simulations.

agent/rewards.log
~~~~~~~~~~~~~~~~~

The reward is a value passed from the simulator to the agent, based on the selected objective. In this case is the negative energy consumption of the cluster. The agent tries to maximise is reward. This file shows the evolution of the rewards given after each execution.

agent/losses.log
~~~~~~~~~~~~~~~~

The agent is based on the Actor-Critic structure, where there are two networs, one is the actor that decides what to do, and the other is the critic that decides how well is the first doing. This file shows the losses value that indicates how intense must the training be in each execution.

agent/probs.log
~~~~~~~~~~~~~~~

Finally, this file shows the probabilities assigned to each policy with every execution. It shows that very quickly, the agent favours the 'first-low_power' over the other by assigning it a probability close to 1.

Spread Experiment
-----------------

After running the execute_experiments.sh script, the three folders high_gflops, high_core and agent are created and filled with simulation results and logs. These give different insights about the development of the experiment.

high_gflops/simulation.log
~~~~~~~~~~~~~~~~~~~~~~~~~~

The total execution time, 14.75s, and energy consumption, 837.53J, can be seen on the last line of this file.

high_gflops/jobs.log
~~~~~~~~~~~~~~~~~~~~

This file shows that all jobs were scheduled to the same two nodes: the_platform.cluster0.node0 and the_platform.cluster0.node1.

high_core/simulation.log
~~~~~~~~~~~~~~~~~~~~~~~~

In the last line of this file, it can be seen that the 'first-high_core' takes less time, 5.32, and energy, 492.97, to execute the eight jobs.

high_core/jobs.log
~~~~~~~~~~~~~~~~~~

This file shows that each job is scheduled to a different node.

agent/simulation.log
~~~~~~~~~~~~~~~~~~~~

This file shows the evolution of the 50 simulations performed to train the agent. It allows following the evolution of the optimisation metric, the execution time. 

agent/rewards.log
~~~~~~~~~~~~~~~~~

The reward in this case is the oposite of the execution time, which the agent tries to minimise. It can be seen that towards the en of the learing process the rewards are close to -5.3.

agent/losses.log
~~~~~~~~~~~~~~~~

The losses decrease toward the end of the training process indicating that the agent has converged to one prefered solution.

agent/probs.log
~~~~~~~~~~~~~~~

The probabilities given in this file show that toward the end of the training process the first policy, 'first-high_core', is chosen with a much higher probability than the 'high-high_gflops'.


