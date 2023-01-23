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
            #print(f'{row[1]} < {args.from_time}')
            if args.include_abort == None and row[3] == "0":
                continue
            if args.from_time != None and float(row[1]) < args.from_time:
                continue
            if args.to_time != None and float(row[1]) > args.to_time:
                continue
            ntasks = int(row[4])
            if ntasks <= 0:
                continue
            if args.max_ntasks != None and ntasks > args.max_ntasks:
                ntasks = args.max_ntasks
            if args.speed != None:
                row[1] = float(row[1]) * args.speed
            postfix = ""
            if args.split_ntasks != None and ntasks > args.split_ntasks:
                postfix = ".x"
            id=1
            while ntasks > 0:
                if args.split_ntasks != None:
                    n = min(ntasks, args.split_ntasks)
                    if postfix != "":
                        postfix = "."+str(id)
                else:
                    n = ntasks
                ntasks -= n
                output = f'      {{"id": "job{row[0]}{postfix}", "subtime": {row[1]}, "ntasks": {n}, ' + \
                        f'"nodes": 1, "req_ops": {int(int(row[3])*args.freq)}, "ipc": 1, ' + \
                        f'"req_time": {row[3]}, "mem": 0, "mem_vol": 0 }}'
                print(sep + output, end="")
                sep = ",\n"
                id += 1

    print(tail)

def process_time_suffix(value: str):
    m = re.match( r'^([.0-9]+)([hdwmy])$', value)
    if m:
        time = float(m.group(1))
        if m.group(2) == 'h':
            return time*3600
        if m.group(2) == 'd':
            return time*3600*24
        if m.group(2) == 'w':
            return time*3600*24*7
        if m.group(2) == 'm':
            return time*3600*24*30
        if m.group(2) == 'y':
            return time*3600*24*365
    raise Exception("Invalid format of time specification.")


def main():
    parser = ap.ArgumentParser(description='Converts SWF traces to IRMaSim workload format')
    parser.add_argument('swf_filename', help='File containing the SWF trace')
    parser.add_argument('-f', '--freq', type=float, default=1e9, help='Frequency of the reference processor in Hz')
    parser.add_argument('--max-ntasks', type=int, help='Number of tasks to limit large jobs to')
    parser.add_argument('--split-ntasks', type=int, help='Number of tasks to split large jobs to')
    parser.add_argument('--from-time', type=str, help='Submission time of the first job')
    parser.add_argument('--to-time', type=str, help='Submission time of the last job')
    parser.add_argument('--speed', type=float, help='Apply factor to submission times (> 1 speed up, <1 slow down)')
    parser.add_argument('--include-abort', type=bool, help='Include jobs with zero execution time.')

    args = parser.parse_args()
    if args.from_time != None:
       args.from_time = process_time_suffix(args.from_time)
    if args.to_time != None:
       args.to_time = process_time_suffix(args.to_time)

    if args.swf_filename:
        parse_workload_data(args) 

if __name__ == "__main__":
    # calling the main function
    main()
