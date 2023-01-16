#!/usr/bin/env python3
import re
import sys
import fileinput
import argparse as ap

head = '''{
   "jobs": ['''

tail = '''\n   ]\n}'''


def parse_workload_data(args):
    print(head)
    sep = ""
    for line in fileinput.input(args.swf_filename, openhook=fileinput.hook_compressed):
        if line[0] != ";":
            row = re.split(r'\s+',line)
            if len(row) < 4:
               continue
            ntasks = int(row[4])
            if args.max_ntasks != None and ntasks > args.max_ntasks:
                ntasks = args.max_ntasks
            id=1
            while ntasks > 0:
                if args.split_ntasks != None:
                    n = min(ntasks, args.split_ntasks)
                else:
                    n = ntasks
                ntasks -= n
                output = f'      {{"id": "job{row[0]}.{id}", "subtime": {row[1]}, "ntasks": {n}, ' + \
                         f'"nodes": 1, "req_ops": {int(int(row[3])*args.freq)}, "ipc": 1, ' + \
                         f'"req_time": {row[3]}, "mem": 0, "mem_vol": 0 }}'
                print(sep + output, end="")
                sep = ",\n"
                id += 1
    
    print(tail)


def main():
    parser = ap.ArgumentParser(description='Converts SWF traces to IRMaSim workload format')
    parser.add_argument('swf_filename', help='File containing the SWF trace')
    parser.add_argument('-f', '--freq', type=float, default=1e9, help='Frequency of the reference processor in Hz')
    parser.add_argument('--max-ntasks', type=int, help='Number of tasks to limit the jobs to')
    parser.add_argument('--split-ntasks', type=int, help='Number of tasks to limit the jobs to')

    args = parser.parse_args()

    if args.swf_filename:
        parse_workload_data(args) 

if __name__ == "__main__":
    # calling the main function
    main()
