##### Imports #####
import gurobipy as gb



class CarbonCaptureConstraints:
    def __init__(self, m, params):
        self.m = m
        self.params_ = params

    def define_variables(self):
        T, N= (
            self.params_["T"],
            self.params_["N"],
        )

        F_rail = self.m.addVars(N, N, T, vtype=gb.GRB.CONTINUOUS, lb=0)

        w_pipe = self.m.addVars(N, N, T, vtype=gb.GRB.BINARY, name="w_ij_pipe")
        S_pipe = self.m.addVars(N, N, T,  vtype=gb.GRB.CONTINUOUS, lb=0)
        F_pipe = self.m.addVars(N, N, T, vtype=gb.GRB.CONTINUOUS, lb=0)

        F_truck = self.m.addVars(N, N, T, vtype=gb.GRB.CONTINUOUS, lb=0)

        c_site = self.m.addVars(N, T, vtype=gb.GRB.BINARY)

        self.vars_ = {"F_rail": F_rail, "w_pipe": w_pipe, "S_pipe": S_pipe, "F_pipe": F_pipe, "F_truck": F_truck, "c_site": c_site}

        return self.vars_

    def function_objective(self):
        T, N, nodes, w_rail, beta, gamma, alpha, Nc_nodes, Nt_nodes, Ns_nodes, Nc, Nt, Ns, Lij = (
            self.params_["T"],
            self.params_["N"],
            self.params_["nodes"],
            self.params_["w_rail"],
            self.params_["beta"],
            self.params_["gamma"],
            self.params_["alpha"],
            self.params_["Nc_nodes"],
            self.params_["Nt_nodes"],
            self.params_["Ns_nodes"],
            self.params_["Nc"],
            self.params_["Nt"],
            self.params_["Ns"],
            self.params_["Lij"]
        )

        S_pipe, w_pipe = self.vars_["S_pipe"], self.vars_["w_pipe"]
        F_pipe = self.vars_["F_pipe"]
        F_rail = self.vars_["F_rail"]
        F_truck = self.vars_["F_truck"]
        c_site = self.vars_["c_site"]

        f1 = gb.quicksum(
            beta["truck"][0] * F_truck[i,j,t] * Lij[i,j] + beta["truck"][1] * F_truck[i,j,t] for i in N for j in N for t in T
        )

        f2 = gb.quicksum(
            beta["rail"][0] * F_rail[i,j,t] * Lij[i,j] + beta["rail"][1] * F_rail[i,j,t] for i in N for j in N for t in T
        )

        f3 = gb.quicksum(
            beta["pipe"][0] * F_pipe[i,j,t] * Lij[i,j] + beta["pipe"][1] * F_pipe[i,j,t] for i in N for j in N for t in T
        )

        f4 = gb.quicksum(
            alpha[0] * S_pipe[i,j,t] + alpha[1] * Lij[i,j] * w_pipe[i,j,t] for i in N for j in N for t in T
        )

        self.m.setObjective(f1 + f2 + f3 + f4, gb.GRB.MINIMIZE)
        

    def pipeline_constraints(self):
        S_pipe = self.vars_["S_pipe"]
        w_pipe = self.vars_["w_pipe"]
        F_pipe = self.vars_["F_pipe"]
        
        T, N, M1 = (
            self.params_["T"],
            self.params_["N"],
            self.params_["M1"]
        )

        for i in N:
            for j in N:
                for t in T:
                    self.m.addConstr(
                        S_pipe[i,j,t] - S_pipe[j,i,t] == 0, name=f"Pipeline Capacity constraint S_{i},{j},{t} = S_{j},{i},{t}"
                    )

        for i in N:
            for j in N:
                for t in T:
                    if t < max(T):
                        self.m.addConstr(
                            S_pipe[i,j,t+1] - S_pipe[i,j,t] >= 0, name="Non-decreasing pipeline capacity over time"
                        )

        for i in N:
            for j in N:
                for t in T:
                    if t < max(T):
                        self.m.addConstr(
                            w_pipe[i,j,t+1] - w_pipe[i,j,t] >= 0, name="Pipeline doesn't disappear after being created"
                        )

        for i in N:
            for j in N:
                self.m.addConstr(
                    gb.quicksum(S_pipe[i,j,t+1] - S_pipe[i,j,t] for t in T if t < max(T)) == gb.quicksum((S_pipe[i,j,t+1] - S_pipe[i,j,t])*(w_pipe[i,j,t+1] - w_pipe[i,j,t]) for t in T if t < max(T)), name="Pipeline capacity increases onmy once"
                )

        for i in N:
            for j in N:
                if i<j:
                    for t in T:
                        self.m.addConstr(
                            F_pipe[i,j,t] + F_pipe[j,i,t] <= S_pipe[i,j,t], name="The total flux in a pipeline cannot be larger than it's capacity"
                        )

        for i in N:
            for j in N:
                if i<j:
                    for t in T:
                        self.m.addConstr(
                            w_pipe[i,j,t] - w_pipe[j,i,t] == 0, name="A pipeline is bidirectional"
                        )

        for i in N:
            for t in T:
                self.m.addConstr(
                    w_pipe[i,i,t] == 0, name="A pipeline doesn't loop around to the same node"
                )
                self.m.addConstr(
                    F_pipe[i,i,t] == 0, name="A pipeline flow doesn't loop around to the same node"
                )

        for i in N:
            for j in N:
                for t in T:
                    self.m.addConstr(
                        S_pipe[i,j,t] <= M1 * w_pipe[i,j,t]
                    )

    def rail_constraints(self):
        F_rail = self.vars_["F_rail"]

        T, N, w_rail, M1= (
            self.params_["T"],
            self.params_["N"],
            self.params_["w_rail"],
            self.params_["M1"]
        )

        for i in N:
            for j in N:
                for t in T:
                    self.m.addConstr(
                        F_rail[i,j,t] <= w_rail[i,j] * M1, name="There is only emissions sent through rail if a line exists"
                    )


        for i in N:
            for t in T:
                self.m.addConstr(self.vars_["F_truck"][i, i, t] == 0, name="No truck self loops")
                self.m.addConstr(self.vars_["F_rail"][i, i, t] == 0, name="No rail self loops")

    def flow_constraints(self):
        F_pipe = self.vars_["F_pipe"]
        F_rail = self.vars_["F_rail"]
        F_truck = self.vars_["F_truck"]
        c_site = self.vars_["c_site"]

        T, N, Nc, Nt, Ns, emission_coefficient, E, M2, b = (
            self.params_["T"],
            self.params_["N"],
            self.params_["Nc"],
            self.params_["Nt"],
            self.params_["Ns"], 
            self.params_["emission_coefficient"],
            self.params_["E"], 
            self.params_["M2"],
            self.params_["b"]
        )
    
        for i in Nc:
            for t in T:
                self.m.addConstr(
                    gb.quicksum(F_truck[j,i,t] + F_rail[j,i,t] + F_pipe[j,i,t] for j in N) - 
                    gb.quicksum(F_truck[i,j,t] + F_rail[i,j,t] + F_pipe[i,j,t] for j in N) ==
                    - emission_coefficient * E[i] * c_site[i,t],
                    name="The flow out of a capture site is equal to the amount of carbon captured at this site"
                )

        for i in Nt:
            for t in T:
                self.m.addConstr(
                    gb.quicksum(F_truck[j,i,t] + F_rail[j,i,t] + F_pipe[j,i,t] for j in N) - 
                    gb.quicksum(F_truck[i,j,t] + F_rail[i,j,t] + F_pipe[i,j,t] for j in N) == 0 ,
                    name="The flow of a transfer site is equal to zero"
                )

        for i in Ns:
            for t in T:
                active_site = int(t >= b[i, t])
                self.m.addConstr(
                    gb.quicksum(F_truck[j,i,t] + F_rail[j,i,t] + F_pipe[j,i,t] for j in N) <= M2 * active_site ,
                    name=f"Storage site {i} is available or not"
                )

        for i in Ns:
            for t in T:
                self.m.addConstr(
                    gb.quicksum(F_truck[i,j,t] + F_rail[i,j,t] + F_pipe[i,j,t] for j in N) == 0 ,
                    name=f"The flow out of storage site {i} is equal to zero"
                )

    def emission_management_constraints(self):
        T, N, gamma, Nc, emission_coefficient, E, Qt, Q_init, Lij = (
            self.params_["T"],
            self.params_["N"],
            self.params_["gamma"],
            self.params_["Nc"],
            self.params_["emission_coefficient"],
            self.params_["E"],
            self.params_["Qt"],
            self.params_["Q_init"],
            self.params_["Lij"]
        )
        
        F_pipe = self.vars_["F_pipe"]
        F_rail = self.vars_["F_rail"]
        F_truck = self.vars_["F_truck"]
        c_site = self.vars_["c_site"]
    
        for t in T:
            self.m.addConstr(
                gb.quicksum(
                    gamma["truck"] * F_truck[i,j,t] * Lij[i,j] + 
                    gamma["rail"] * F_rail[i,j,t] * Lij[i,j] + 
                    gamma["pipe"] * F_pipe[i,j,t] * Lij[i,j]
                    for i in N for j in N
                ) - gb.quicksum(emission_coefficient * E[i] * c_site[i,t] for i in Nc) 
                <= Q_init + (Qt - Q_init) * (t/max(T)),
                name="Emissions are reduced in a linear fashion in order to reach the emissions goal"
            )






