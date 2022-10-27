import subprocess
import shutil
import sys
import json

def test_one_core_one_job():
    file = __file__[:-3] + "/"

    sys.stdout = open("/dev/null", "w")

    platform_name = "example"
    platorma_file = "platform.json"
    job_file = "jobs.json"
    outpul_dir = "delme"
    agent_file = "agent_examples/ActorCritic.py"
    option_file = "options.json"

    subprocess.call(["irmasim", "-n" , platform_name, "-p", file+platorma_file, "-w", file+job_file,
                    "-o", file+outpul_dir, "-a", agent_file, file+option_file,"-v"])

    with open(file+outpul_dir+"/"+"statistics.json") as stats:
        data = json.load(stats)
        assert float(data["Makespan (seconds)"]) == 3
        assert float(data["Energy_Consumed (J)"]) == 155


    shutil.rmtree(file+outpul_dir)