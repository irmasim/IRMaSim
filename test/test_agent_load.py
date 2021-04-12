import subprocess
import shutil
import sys
import json

def test_agent_load():
    file = __file__[:-3] + "/"

    platform_name = "example"
    platorma_file = "platform.json"
    job_file = "jobs.json"
    outpul_dir = "delme"
    agent_file = "agent_examples/actor_critic.py"
    option_file = "options.json"
    model = "model"


    subprocess.call(["irmasim", "-n" , platform_name, "-p", file+platorma_file, "-w", file+job_file,
                    "-o", file+outpul_dir, "-a", agent_file, "-im", file+outpul_dir+"/"+model, "-om", file+outpul_dir+"/"+model,
                    file+option_file ])

    with open(file+outpul_dir+"/"+"statistics.json") as stats:
        data = json.load(stats)
        assert float(data["Makespan (seconds)"]) == 3.8
        assert float(data["Energy_Consumed (J)"]) == 355

    try:
        f = open(file+outpul_dir+"/"+model)
        assert True
    except:
        assert False

    shutil.rmtree(file+outpul_dir)
