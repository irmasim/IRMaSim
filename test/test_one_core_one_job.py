import subprocess
import shutil
import sys

def test_one_core_one_job():
    file = __file__[:-3] + "/"

    sys.stdout = open("/dev/null", "w")

    platform_name = "example"
    platorma_file = "platform.json"
    job_file = "jobs.json"
    outpul_dir = "delme"
    agent_file = "agent_examples/actor_critic.py"
    option_file = "options.json"

    subprocess.call(["irmasim", "-n" , platform_name, "-p", file+platorma_file, "-w", file+job_file,
                    "-o", file+outpul_dir, "-a", agent_file, file+option_file,"-v"])

    with open(file+outpul_dir+"/"+"makespans.log") as makespan:
        makespan_calculated = makespan.readline()
        assert float(makespan_calculated) == 3

    with open(file + outpul_dir + "/" + "rewards.log") as energy:
        energy_calculated = energy.readline()
        assert float(energy_calculated) == -150

    shutil.rmtree(file+outpul_dir)