import numpy as np



def small_instance():
    # time horizon for the deployment
    T = 25

    # Description of nodes
    # Format: node_id, node_type_id, coord_x, coord_y, E (if relevant)
    #	* each row corresponds to 1 site
    #	* node_id = index of the node
    #   * node_type_id {0: capture site, 1: transfer site, 2: storage site}
    #	* (coord_x, coord_y) = geographical coordinates of the site
    #	* E = yearly emissions of this site (without any carbon capture technology)

    # Array of nodes
    nodes = np.array([
        [0, 2, 0, 10], 
        [1, 0, 9, 10, 200],
        [2, 0, 5, 7, 250],
        [3, 0, 10, 4, 400],
        [4, 0, 5, 2, 200],
        [5, 0, 0, 0, 350]
    ])

    N = [int(node[0]) for node in nodes]

    Nc_nodes = [node for node in nodes if int(node[1]) == 0]
    Nt_nodes = [node for node in nodes if int(node[1]) == 1]
    Ns_nodes = [node for node in nodes if int(node[1]) == 2]

    Nc = [int(node[0]) for node in Nc_nodes]
    Nt = [int(node[0]) for node in Nt_nodes]
    Ns = [int(node[0]) for node in Ns_nodes]

    Lij = np.zeros(len(nodes), len(nodes))
    M1 = 0
    E = {}
    b = {}
    for node_i in nodes:
        if node_i[1] == 0:
            M1 += node_i[4]  # The big M is used to allow the flow of emissions so taking the sum of all the emissions is a reasonable big M variable
            E[node_i[0]] = node_i[4]
        if node_i[1] == 2:
            b[node_i[0]] = node_i[4]
        for node_j in nodes:
            Lij[node_i[0], node_j[0]] = np.sqrt((node_i[2] - node_j[2])**2 + (node_i[3] - node_j[3])**2)


    M2 = M1 # The sum is also reasonable for the second big M constraint

    T = np.array([t for t in range(T)])

    # -- array (of size N*N) where element w_ij indicates whether or not a rail connection exists between two nodes
    #	* w_ij = 1 if a rail connection exists between node i (row index) and j (column index), w_ij = 0 otherwise

    # Existing rail connections
    w_rail = np.array([
        [0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [1, 0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ], dtype=int)

    # beta[mode][0]: cost per unit transported per unit distance
    # beta[mode][1]: additional cost per unit transported
    beta = {
        "truck": np.array([1_000_000, 0]),
        "rail": np.array([1, 0.5]),
        "pipe": np.array([0.05, 0]),
    }

    gamma = {"truck": 0, "rail": 0.003, "pipe": 0}
    alpha = np.array([0.3, 27])

    # Assumed capture efficiency: replace with your actual value
    emission_coefficient = 0.90

    total_emissions = sum(E.values())
    max_captured = emission_coefficient * total_emissions

    # Flow bounds; sufficient for routing captured carbon without cycles
    M1 = max_captured
    M2 = max_captured

    # Bounds on transport emissions MINUS captured emissions.
    # Assumption: progress from no required reduction to a 90% reduction.
    Q_init = 0.0
    Qt = -0.90 * total_emissions

    params = {
        "T": T,
        "N": N,
        "nodes": nodes,
        "w_rail": w_rail,
        "beta": beta,
        "gamma": gamma,
        "alpha": alpha,
        "Nc_nodes": Nc_nodes,
        "Nt_nodes": Nt_nodes,
        "Ns_nodes": Ns_nodes,
        "Nc": Nc,
        "Nt": Nt,
        "Ns": Ns,
        "Lij": Lij,
        "M1": M1,
        "M2": M2,
        "E": E,
        "b": b,
        "emission_coefficient": emission_coefficient,
        "Q_init": Q_init,
        "Qt": Qt,
    }

    return params


