

import gurobipy as gb
from constraints_pareto import CarbonCaptureConstraints_Pareto
from problem_instances import small_instance, medium_instance, large_instance


class OptiModel_pareto:
    def __init__(self, model_name, TIME_LIMIT,eps):
        self.model_name = model_name
        self.TIME_LIMIT = TIME_LIMIT
        self.eps = eps
        self.params = small_instance()
        self.vars = None
        self.model = None

    def build(self):
        m = gb.Model(self.model_name)
        m.setParam("TimeLimit", self.TIME_LIMIT)

        constraint_builder = CarbonCaptureConstraints_Pareto(m=m, params=self.params, eps=self.eps)

        vars_ = constraint_builder.define_variables()

        constraint_builder.function_objective()

        constraint_builder.pipeline_constraints()
        constraint_builder.rail_constraints()
        constraint_builder.flow_constraints()
        constraint_builder.emission_management_constraints()
        constraint_builder.epsilon_constraint()

        m.update()
        self.model, self.vars = m, vars_
        return self.model, self.vars


# def run_optimisation_model():

#     model_builder = OptiModel(
#         model_name="small_instance",
#         TIME_LIMIT=300
#     )

#     m, vars_ = model_builder.build()

#     m.optimize()
    

def run_optimisation_model_pareto(eps):
    """fonction run pour calcul du pareto front"""
    

    model_builder = OptiModel_pareto(
        model_name="small_instance",
        TIME_LIMIT=300,
        eps=eps
    )

    m, vars_ = model_builder.build()

    m.optimize()
    
    params = model_builder.params
    
    return m, vars_, params


# m,vars_,params = run_optimisation_model_pareto(eps=4464)
# print(params.keys())
# print(vars_.keys())
# print("F_rail =", vars_["F_rail"]  )
# print("F_pipe =", vars_["F_pipe"]  )
# print("F_truck =", vars_["F_truck"]  )

import plotly.graph_objects as go

import matplotlib.pyplot as plt

def plot_emissions_over_time(params, vars_):

    T = params["T"]
    N = params["N"]
    Nc = params["Nc"]
    gamma = params["gamma"]
    E = params["E"]
    Lij = params["Lij"]
    emission_coefficient = params["emission_coefficient"]

    F_truck = vars_["F_truck"]
    F_rail = vars_["F_rail"]
    F_pipe = vars_["F_pipe"]
    c_site = vars_["c_site"]

    emissions_without_system = []
    emissions_with_system = []

    for t in T:

        # Emissions initiales pendant la période t
        initial = sum(E.values())

        # Emissions de transport pendant la période t
        transport = sum(
            gamma["truck"] * F_truck[i, j, t].X * Lij[i, j]
            + gamma["rail"] * F_rail[i, j, t].X * Lij[i, j]
            + gamma["pipe"] * F_pipe[i, j, t].X * Lij[i, j]
            for i in N for j in N
        )

        # Emissions évitées par le captage
        captured = sum(
            emission_coefficient * E[i] * c_site[i, t].X
            for i in Nc
        )

        emissions_without_system.append(initial)
        emissions_with_system.append(initial + transport - captured)

    plt.figure(figsize=(10, 6))
    plt.plot(T, emissions_without_system, marker="o", label="Without system")
    plt.plot(T, emissions_with_system, marker="o", label="With system")

    plt.xlabel("Time period")
    plt.ylabel("CO2 emissions")
    plt.title("CO2 emissions over time")
    plt.legend()
    plt.grid(True)
    plt.show()
    
# plot_emissions_over_time(params, vars_)

def plot_cumulative_emissions(params, vars_):

    T = params["T"]
    N = params["N"]
    Nc = params["Nc"]
    gamma = params["gamma"]
    E = params["E"]
    Lij = params["Lij"]
    emission_coefficient = params["emission_coefficient"]

    F_truck = vars_["F_truck"]
    F_rail = vars_["F_rail"]
    F_pipe = vars_["F_pipe"]
    c_site = vars_["c_site"]

    emissions_without_system = []
    emissions_with_system = []

    cumulative_without = 0
    cumulative_with = 0

    for t in T:

        initial = sum(E.values())

        transport = sum(
            gamma["truck"] * F_truck[i, j, t].X * Lij[i, j]
            + gamma["rail"] * F_rail[i, j, t].X * Lij[i, j]
            + gamma["pipe"] * F_pipe[i, j, t].X * Lij[i, j]
            for i in N for j in N
        )

        captured = sum(
            emission_coefficient * E[i] * c_site[i, t].X
            for i in Nc
        )

        cumulative_without += initial
        cumulative_with += initial + transport - captured

        emissions_without_system.append(cumulative_without)
        emissions_with_system.append(cumulative_with)

    plt.figure(figsize=(10, 6))

    plt.plot(T, emissions_without_system, marker="o",
             label="Without system")

    plt.plot(T, emissions_with_system, marker="o",
             label="With capture and transport system")

    plt.xlabel("Time period")
    plt.ylabel("Cumulative CO2 emissions")
    plt.title("Cumulative CO2 emissions over time")
    plt.legend()
    plt.grid(True)
    plt.show()
    
# plot_cumulative_emissions(params, vars_)

def analysis(params, vars_):
    T = params["T"]
    N = params["N"]
    Nc = params["Nc"]
    gamma = params["gamma"]
    emission_coefficient = params["emission_coefficient"]
    E = params["E"]
    Lij = params["Lij"]
    F_truck = vars_["F_truck"]
    F_rail = vars_["F_rail"]
    F_pipe = vars_["F_pipe"]
    c_site = vars_["c_site"]


    # du site i par période.
    emissions_without_system = sum(E.values())*len(T)
    
    emissions_with_system = sum(E.values())*len(T)+sum(
        (
            sum(
                gamma["truck"] * F_truck[i, j, t].X * Lij[i, j]
                + gamma["rail"] * F_rail[i, j, t].X * Lij[i, j]
                + gamma["pipe"] * F_pipe[i, j, t].X * Lij[i, j]
                for i in N for j in N
            )
            - sum(
                emission_coefficient * E[i] * c_site[i, t].X
                for i in Nc
            )
        )
        for t in T
    )

    total_cost = m.ObjVal
    print(emissions_without_system-emissions_with_system)
    #print(total_cost)
    return (total_cost,emissions_with_system,total_cost/(emissions_without_system-emissions_with_system))

m,vars_,params = run_optimisation_model_pareto(5000)

def analysis(params, vars_):
    T = params["T"]
    N = params["N"]
    Nc = params["Nc"]
    gamma = params["gamma"]
    emission_coefficient = params["emission_coefficient"]
    E = params["E"]
    Lij = params["Lij"]
    F_truck = vars_["F_truck"]
    F_rail = vars_["F_rail"]
    F_pipe = vars_["F_pipe"]
    c_site = vars_["c_site"]


    # du site i par période.
    emissions_without_system = sum(E.values())*len(T)
    
    emissions_with_system = sum(E.values())*len(T)+sum(
        (
            sum(
                gamma["truck"] * F_truck[i, j, t].X * Lij[i, j]
                + gamma["rail"] * F_rail[i, j, t].X * Lij[i, j]
                + gamma["pipe"] * F_pipe[i, j, t].X * Lij[i, j]
                for i in N for j in N
            )
            - sum(
                emission_coefficient * E[i] * c_site[i, t].X
                for i in Nc
            )
        )
        for t in T
    )

    total_cost = m.ObjVal
    print(emissions_without_system-emissions_with_system)
    #print(total_cost)
    return (total_cost,emissions_with_system,total_cost/(emissions_without_system-emissions_with_system))

print (analysis(params, vars_))
# print (analysis(params, vars_))






