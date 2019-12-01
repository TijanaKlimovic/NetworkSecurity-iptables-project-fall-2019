import argparse
import os
import json
import networkx as nx
import shutil

def parseArgs():

    parser = argparse.ArgumentParser(description='Process some args.')
    parser.add_argument('-i', default='inputs/')
    parser.add_argument('-o', default='outputs/')
    args = vars(parser.parse_args()) #create dictionary with argument names as keys and their values
    for k in args.keys():
        print(k, args.get(k))
    return args

def createRules(G, testcase, OUTPUT_DIR, file):
    communications = testcase['communications']
    nodeDict = dict(G.nodes.data()) #dict of nodes and attribute dict pairs
    #edgeDict = dict(G.edges.data())
    #print(G.edges.data())
    #print(G['s0']['r0'])

    #print('type is: ' , type(file) ,' of ' , file )
    filename, file_extension = os.path.splitext(file)
    #print(filename)

    if not os.path.exists(OUTPUT_DIR + filename):
        os.mkdir(OUTPUT_DIR + filename)

    #if it's the first time its opening an existing file maybe we should delete it's current conent?

    #fill in each router iptable with empty nat table and initial part of filter tbl
    for node in G.nodes:
        if nodeDict[node]['type'] == 'router':
            f = open(OUTPUT_DIR + filename + '/' + nodeDict[node]['id'], "a+")
            f.write('* nat\n')
            f.write(':OUTPUT ACCEPT [0:0]\n')
            f.write(':PREROUTING ACCEPT [0:0]\n')
            f.write(':POSTROUTING ACCEPT [0:0]\n')
            f.write('\n')
            f.write('COMMIT\n')
            f.write('\n')
            f.write('* filter\n')
            f.write(':INPUT DROP [0:0]\n')
            f.write(':OUTPUT DROP [0:0]\n')
            f.write(':FORWARD DROP [0:0]\n')

    for c in communications:

        #create all rules associated with c for all routers
        s = 's' + str(c['sourceSubnetId'])
        t = 's' + str(c['targetSubnetId'])
        #get unique path of all nodes traversed and extract the router nodes to set rules for
        path = nx.shortest_path(G, source=s, target=t) #returns a list

        print('source node', s + ' target node ' + t, ' with path:')
        print(path)


        i = 0
        while i < len(path)-2:

            i_edge_attr = G[path[i]][path[i+1]]         #dicts of edge incoming and outgoing edge attrs
            o_edge_attr = G[path[i+1]][path[i+2]]       #i+1 is the router node always
            f = open(OUTPUT_DIR + filename + '/' + nodeDict[path[i+1]]['id'], "a+")

            #write rules based on c
            f.write('-A FORWARD -p ' + c['protocol'] + \
                    ' --sport ' + str(c['sourcePortStart']) + ':' + str(c['sourcePortEnd']) + \
                    ' --dport ' + str(c['targetPortStart']) + ':' + str(c['targetPortEnd']) + \
                    ' -s ' + nodeDict[s]['subnet'] + ' -d ' + nodeDict[t]['subnet'] + \
                    ' -i ' + i_edge_attr['interface'] + ' -o ' + o_edge_attr['interface'] + \
                    ' -m state --state NEW,ESTABLISHED -j ACCEPT\n')

            if c['direction'] == 'bidirectional':
                # case of udp and tcp
                if c['protocol'] == 'udp' or c['protocol'] == 'tcp':
                    f.write('-A FORWARD -p ' + c['protocol'] + \
                            ' --sport ' + str(c['targetPortStart']) + ':' + str(c['targetPortEnd']) + \
                            ' --dport ' + str(c['sourcePortStart']) + ':' + str(c['sourcePortEnd']) + \
                            ' -s ' + nodeDict[t]['subnet'] + ' -d ' + nodeDict[s]['subnet'] + \
                            ' -i ' + o_edge_attr['interface'] + ' -o ' + i_edge_attr['interface'] + \
                            ' -m state --state ESTABLISHED -j ACCEPT\n')
                # case of icmp
                else:
                    f.write('-A FORWARD -p ' + c['protocol'] + \
                            ' --sport ' + str(c['targetPortStart']) + ':' + str(c['targetPortEnd']) + \
                            ' --dport ' + str(c['sourcePortStart']) + ':' + str(c['sourcePortEnd']) + \
                            ' -s ' + nodeDict[t]['subnet'] + ' -d ' + nodeDict[s]['subnet'] + \
                            ' -i ' + o_edge_attr['interface'] + ' -o ' + i_edge_attr['interface'] + \
                            ' -m state --state NEW,ESTABLISHED -j ACCEPT\n')
            i = i+2
     
    for node in G.nodes:
        if nodeDict[node]['type'] == 'router':
            f = open(OUTPUT_DIR + filename + '/' + nodeDict[node]['id'], "a+")
            f.write('\n')
            f.write('COMMIT')
            f.write('\n')


def createGraph(testcase):
    G = nx.Graph()
    netdir = testcase['network'] #extract the netdir
    #lists of routers, subnets and links
    routerIDs = netdir['routers']
    subnets = netdir['subnets']
    links = netdir['links']

    #create router and subnet nodes
    for r in routerIDs:
        name = 'r' + str(r['id'])
        G.add_node(name, id=str(r['id']), type='router')

    for s in subnets:
        name = 's' + str(s['id'])
        address = s['address'] + "/" + str(s['prefix']) #address/prefix
        G.add_node(name, id=str(s['id']), subnet=address, type='subnet')

    #add edges to graph
    #attributes of edge are the interface name of the router_node on the edge and it's ip
    for l in links:
        router_node = 'r' + str(l['routerId'])
        subnet_node = 's' + str(l['subnetId'])
        G.add_edge(router_node, subnet_node, interface=l['interfaceId'], ip=l['ip'])

    print('the nodes are: \n', G.nodes)
    print('attribtues of each of the nodes: ', G.nodes.data())
    print('the edges are: \n', G.edges)
    print('attribtues of each of the edges: ', G.edges.data())

    return G

if __name__ == '__main__':
    args = parseArgs()
    INPUT_DIR = args.get('i')
    OUTPUT_DIR = args.get('o')
    #if directory specified by OUTPUT_DIR doesn't exist create it
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    else:
        shutil.rmtree(OUTPUT_DIR)   #if it delete it recursively
        os.mkdir(OUTPUT_DIR) # create a new empty one

    #print(INPUT_DIR, " ", OUTPUT_DIR)
    directory = os.fsencode(INPUT_DIR)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".json"):
            # get filename of each .json file
            #print(filename)
            with open(INPUT_DIR + filename, 'r') as f:
                testcase = json.load(f)
                G = createGraph(testcase)
                createRules(G, testcase, OUTPUT_DIR, filename)
                print(type(testcase))
        else:
            continue
    '''

    #testing  set
    with open('inputs/0.json') as f:
        testcase = json.load(f)
        G = createGraph(testcase)
        createRules(G, testcase, OUTPUT_DIR, '0.json')

    '''