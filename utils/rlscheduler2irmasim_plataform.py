#!/usr/bin/env python3
import json
  
# Opening JSON file
f = open('cluster_x4_64procs.json')
  
# returns JSON object as 
# a dictionary
data = json.load(f)
  
# Iterating through the json
# list
node_list = []
node_number_list = []
node_num_proc_list = []
node_freq_list = []
for i in data['clusters']:
    for n in range(len(i['nodes'])):
        node_list.append(i['nodes'][n]['id'])
        node_number_list.append(i['nodes'][n]['number'])
        node_num_proc_list.append(i['nodes'][n]['num_procs'])
        node_freq_list.append(i['nodes'][n]['frec'])

node_dict = {}
node_dict["id"] = node_list
node_dict["number"] = node_number_list
node_dict["num_procs"] = node_num_proc_list
node_dict["frec"] = node_freq_list

#print(node_dict)

file = ""

plataform_info = """{
    "platform": {
       "the_platform": {
          "id": "the_platform",
          "clusters": [
             { "id": "cluster0",
                "nodes": [ \n"""

local_links = """
                ],
             "local_links":{
                 "type":"InfiniBand QDR",
                "latency":"0us"
             }
             }
          ],
          "global_links":{
             "type":"InfiniBand QDR",
             "latency":"0us"
          }
          , "model_name" : "modelV1"
       }
    },
    "node": {\n"""

"file += local_links"


node_id = '''": {
          "id": "n1112",
          "processors": [
             {"type": "proc_'''
node_memory = """ }
          ],
          "memory": {"type": "DDR3-1600", "capacity": 32}
       },\n"""

proccessor_intro = '''    "processor": {
'''
processor_name = '''       "proc_'''
processor_feature_1 = '''": {
          "uarch": "basic_arch", "id": "'''
processor_feature_2 = '''", "type": "CPU",
          "cores": '''
processor_feature_3 = ''',
          "llc_size": 8, "power": 100, "dpflops_per_cycle": 1, "min_power" : 0.05,
          "dc": 50000, "dynamic_power": 5.59316, "da": 1.75, "static_power": 6.14211, "dd": 6000, "c": 32000, "db": 2000, "b": -1.85e-05 },\n'''


#print(file)

def parse_plataform_data(self, file_name : str):
    ######################### Take data from json #############
    f = open(file_name)
    
    data = json.load(f)

    node_list = []
    node_number_list = []
    node_num_proc_list = []
    node_freq_list = []
    for i in data['clusters']:
        for n in range(len(i['nodes'])):
            node_list.append(i['nodes'][n]['id'])
            node_number_list.append(i['nodes'][n]['number'])
            node_num_proc_list.append(i['nodes'][n]['num_procs'])
            node_freq_list.append(i['nodes'][n]['frec'])

    node_dict = {}
    node_dict["id"] = node_list
    node_dict["number"] = node_number_list
    node_dict["num_procs"] = node_num_proc_list
    node_dict["frec"] = node_freq_list

    ######################## Funcionality ###################3
    file = "" #Final variable that will contain the test to write on the new file

    #Automaticaly generate text for cluster/nodes block
    cluster_nodes = ""
    for i in range(len(node_dict["id"])):
        aux = '                     { "type": "' + node_dict["id"][i] + '", "number": ' + str(node_dict["number"][i]) + '},'
        cluster_nodes += aux + "\n"
    
    cluster_nodes = cluster_nodes[:-2]
        
    #Automaticaly generate text for Node block
    node_info_block = ""
    for i in range(len(node_dict["id"])):
        aux = '       "'+ node_dict["id"][i] + node_id + node_dict["id"][i]+ '", "number": ' + str(node_dict["number"][i]) + node_memory
        node_info_block += aux

    node_info_block = node_info_block[:-2] + "\n    },\n"


    #Automaticaly generate testx for Processors block
    processor_info_block = proccessor_intro
    for i in range(len(node_dict["id"])):
        aux = processor_name + node_dict["id"][i] + processor_feature_1 + node_dict["id"][i] + processor_feature_2 + str(node_dict["num_procs"][i]) + \
            ', "clock_rate": ' + str(node_dict["frec"][i]) + processor_feature_3
        processor_info_block += aux

    processor_info_block = processor_info_block[:-2] + "\n    }\n }"

    file += plataform_info + cluster_nodes + local_links + node_info_block + processor_info_block
    
    print (file)
    f.close()
    return file


text = parse_plataform_data(None, file_name='cluster_x4_64procs.json') 
# Writing to sample.json

exit_file_name = "Jaime_cluster.json"
with open(exit_file_name, "w") as outfile:
    outfile.write(text)
  
# Closing file
f.close()

