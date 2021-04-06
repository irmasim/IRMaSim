import subprocess
import shutil
import sys
import json

def test_nb_runs():
    file = __file__[:-3] + "/"

    platform_name = "example"
    platorma_file = "platform.json"
    job_file = "jobs.json"
    outpul_dir = "delme"
    agent_file = "agent_examples/actor_critic.py"
    option_file = "options.json"
    nb_runs = 3

    subprocess.call(["irmasim", "-n" , platform_name, "-p", file+platorma_file, "-w", file+job_file,
                    "-o", file+outpul_dir, "-a", agent_file, "-nr", str(nb_runs), file+option_file ])

    with open(file+outpul_dir+"/"+"statistics.json") as stats:
        data = json.load(stats)
        assert float(data["Makespan (seconds)"]) == 3.8
        assert float(data["Energy_Consumed (Julios)"]) == 355

    with open(file+outpul_dir+"/"+"rewards.log") as rew:
        for i, l in enumerate(rew):
            print(i)
            pass
        assert nb_runs == i+1

    shutil.rmtree(file+outpul_dir)
