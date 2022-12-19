#!/usr/bin/env python3
import re
import sys

head = '''{
   "nb_res": 60,
   "num_instructions": "TRUE",
   "jobs": ['''

tail = '''\n   ]\n}'''


def parse_workload_data(self, file_name : str, freq : float):
    file = open(file_name)
    
    #data = [ x for x in file.readlines() if x[0] != ";"] 
    
    
    print(head)
    sep = ""
    for line in file:
        #print(line)
        if line[0] != ";":
            row = re.split(r'\s+',line)
            output = f'      {{"id": "job{row[0]}", "subtime": {row[1]}, "res": {row[4]}, "req_ops": {int(int(row[3])*freq)}, "ipc": 1, "req_time": {row[3]}, "mem": 0, "mem_vol": 0 }}'       
            
            print(sep + output, end="")
            sep = ",\n"
    
    print(tail)



if len(sys.argv) < 3:
    print ("Usage: \n\n   swf2irmasim_workload.py <swf-filename> <processor-frequensy>\n")
else :
    text = parse_workload_data(None, file_name=str(sys.argv[1]), freq=float(sys.argv[2])) 

