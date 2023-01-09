IRMaSim
=======

Framework for evaluating *workload management* policies based on
*deep reinforcement learning* for *heterogeneous* clusters.

.. include-overview-start

Overview
--------

IRMaSim was designed to simulate a computer cluster with great speed. Because of this, it models the execution of jobs in the cluster in a very efficient way. It considers that applications have a number of instructions and the processor will execute them at a given rate. This eliminates the overhead of modeling complex structures of the architecture of the cluster, like speculative execution or cache memory.

IRMaSim can simulate classic workload managers based on simple policies, like FIFO or Shortest Job First. But more interstingly it can simulate workload manager based on machine learning. 

To simualte IRMaSim takes the description of the cluster, which we call generically the *platform*, and a list of jobs that are submitted to the cluster,      called the *workload*, in addition to some global settings.

.. include-overview-end

Installation
------------

The installation procedure is straightforward. Clone the repository, or download and unpack the source code into a folder called IRMaSim. Then with the help   of PIP the instllation is performed with a simple command. If you do not have PIP installed consult https://pypi.org/project/pip/ or use your operating        system's package manager. For instance in Ubuntu, the following commands would install IRMaSim::

   $ git clone https://github.com/irmasim/IRMaSim.git
   $ apt install python3-pip
   $ pip install IRMaSim

After taking these steps, you should be able to execute IRMaSim from the command line.

Dev-Instalation
---------------

ToDo::

   $ git clone https://github.com/irmasim/IRMaSim.git
   $ apt install python3-pip
   $ cd IRMaSim
   $ pip install -e .
   $ export PATH=$HOME/.local/bin:$PATH

After taking these steps, you should be able to execute IRMaSim from the command line and develop the code at the same time.

Usage
-----

Executing IRMaSim with no parameters brings a help message::

   $ irmasim

   usage: irmasim [-h] [-n PLATFORM_NAME] ...

   [...]

   Need to specify a platform to simulate. Either with -n or in an options_file.

A simple example
~~~~~~~~~~~~~~~~

To actually perform a simulation IRMaSim requires a platform, a workload and some global options. There are several examples clusters in the examples folder.  For instance, this simualtes a dual core machine executing two jobs::

   $ cd IRMaSim/examples/dual_core
   $ irmasim options.json
   Loading options from options.json
   Setting the random seed to 0
   Loaded 2 jobs from jobs.json. Using 2 jobs starting with #0
   Loading definitions from /home/esteban/projects/2021/IRMaSim_/irmasim/data/network_types.json
   Loading definitions from /home/esteban/projects/2021/IRMaSim_/irmasim/data/node_types.json
   Loading definitions from /home/esteban/projects/2021/IRMaSim_/irmasim/data/processor_types.json
   Loading definitions from platform.json
   Using platform example
   Using workload manager irmasim.workload_manager.Minimal
   Starting simulation run: 0
   Simulation time: total: 3.8
   Energy consumption: total: 350.0
   Jobs: future: 0, queue: 0, running: 0, finished: 2
   Slowdown:  total: 2.0, avg: 1.0, max: 1.0, min: 1.0
   Bounded Slowdown:  total: 2.0, avg: 1.0, max: 1.0, min: 1.0
   Waiting Time:  total: 0.0, avg: 0.0, max: 0.0, min: 0.0
   Execution time 0.005236148834228516 seconds

The options.json file defines several simulation parameters, of which the most relevant are the platform_file that indicates where is the cluster defined, the platform_name that tells which platform to simulate (The platform_file can define more than one platform), and the workload_file that specifies where are the jobs to feed to the cluster. The output of the simulator tells that it is indeed using the files defined in the options.json file, as well as some defaults. For instance, it uses the Minimal workload manager, which is a simple FCFS scheduler.

There are more experiments and more complex setups in the examples folder. These are usually acompanied by some documentation that explains them.
