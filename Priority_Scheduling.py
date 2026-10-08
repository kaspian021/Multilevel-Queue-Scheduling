import subprocess
import time

jobs = []
try:
    number_programm = int(input("please number program: "))
except ValueError as e:
    print("please enter number(int): \n")
    number_programm = int(input("please number program: "))

for i in range(number_programm):
    command = input(f"\n command program {i + 1}: ")
    priority = int(input("priority: "))

    jobs.append({
        "name": f"Job:{i+1}",
        "command":command,
        "priority": priority
    })


jobs.sort(key=lambda job:job["priority"])


for job in jobs:
    print("\n"+"-"*20)
    print("Running...", job["name"])
    print("Command:", job["command"])
    print("Priority:", job["priority"])

    start = time.perf_counter()
    try:
        subprocess.run(job["command"],shell=True)

        end = time.perf_counter()

        run_time = end - start

        print("Runtime:", round(run_time,2), "second")
    except FileNotFoundError:
        end = time.perf_counter()
        print("ERROR: Program not found!")
        print("Please enter the full path of the .exe file.")