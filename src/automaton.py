import pydot
import re

graph = pydot.Dot("automaton", graph_type="digraph")

with open("src/parser.out", "r") as f:
    lines = f.readlines()

state_lineno = {}
for i in range(len(lines)):
    match = re.findall(r"^state \d+", lines[i])
    if len(match) > 0:
        state_lineno[int(match[-1][6:])] = i

n_states = len(state_lineno.keys())

for i in range(n_states):
    graph.add_node(pydot.Node("I" + str(i), shape="circle"))

for i in range(n_states):
    start = state_lineno[i]
    if i == (n_states - 1):
        end = len(lines)
    else:
        end = state_lineno[i + 1]
    for j in range(start, end):
        state_match = re.findall(r"shift and go to state \d+", lines[j])
        if len(state_match) > 0:
            edge_match = re.findall(r"[\w_]+", lines[j])
            next_state = state_match[-1][22:]
            edge = edge_match[0]
            graph.add_edge(pydot.Edge("I" + str(i), "I" + str(next_state), label=edge))

graph.write_raw("dot/automaton.dot")
