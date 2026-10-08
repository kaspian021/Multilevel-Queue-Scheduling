import subprocess
import time

queue1 = []
queue2 = []
queue3 = []

try:
    number_programm = int(input("please number program: "))
except ValueError:
    print("please enter number(int): ")
    number_programm = int(input("please number program: "))

for i in range(number_programm):
    command = input(f"\ncommand program {i + 1}: ")
    queue = int(input("queue (1-3): "))

    job = {
        "name": f"Job:{i + 1}",
        "command": command
    }

    if queue == 1:
        queue1.append(job)
    elif queue == 2:
        queue2.append(job)
    elif queue == 3:
        queue3.append(job)
    else:
        print("invalid queue")
        continue


jobs = queue1 + queue2 + queue3

for job in jobs:
    print("\n" + "-" * 20)
    print("Running...", job["name"])
    print("Command:", job["command"])

    start = time.perf_counter()

    try:
        subprocess.run(job["command"], shell=True)

        end = time.perf_counter()

        run_time = end - start

        print("Runtime:", round(run_time, 2), "second")

    except FileNotFoundError:
        print("ERROR: Program not found!")
        print("Please enter the full path of the .exe file.")

