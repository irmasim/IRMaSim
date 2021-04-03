import subprocess
import shutil
import json
import sys

def test_one_core_two_job():
    file = __file__[:-3] + "/"

    platform_name = "example"
    platorma_file = "platform.json"
    job_file = "jobs.json"
    outpul_dir = "delme"
    agent_file = "agent_examples/actor_critic.py"
    option_file = "options.json"

    subprocess.call(["irmasim", "-n" , platform_name, "-p", file+platorma_file, "-w", file+job_file,
                    "-o", file+outpul_dir, "-a", agent_file, file+option_file])

    with open(file+outpul_dir+"/"+"statistics.json") as stats:
        data = json.load(stats)
        assert float(data["Makespan (seconds)"]) == 4
        assert float(data["Energy_Consumed (Julios)"]) == 305

    shutil.rmtree(file+outpul_dir)