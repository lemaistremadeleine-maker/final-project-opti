import gurobipy as gb
from constraints import CarbonCaptureConstraints
from problem_instances import small_instance, medium_instance, large_instance
from model import OptiModel, run_optimisation_model2

m,vars_,params = run_optimisation_model2()

print("N =", params["N"])
print("E =", params["E"])
print("Type de E =", type(params["E"]))


def calculate_total_emissions(params, vars_):
    T = params["T"]
    N = params["N"]
    Nc = params["Nc"]

    gamma = params["gamma"]
    emission_coefficient = params["emission_coefficient"]
    E = params["E"]
    Lij = params["Lij"]

    # 1. Emissions sans système de récupération
    # On suppose que E[i] représente les émissions initiales
    # du site i par période.
    emissions_without_system = sum(
        E[i] for i in N
    ) * len(T)

    # 2. Emissions avec le système de récupération
    total_transport_emissions = 0
    total_captured = 0

    for t in T:
        # Emissions liées au transport
        total_transport_emissions += sum(
            gamma["truck"] * vars_["F_truck"][i, j, t].X * Lij[i, j]
            + gamma["rail"] * vars_["F_rail"][i, j, t].X * Lij[i, j]
            + gamma["pipe"] * vars_["F_pipe"][i, j, t].X * Lij[i, j]
            for i in N for j in N
        )

        # Quantité de CO2 capturée
        total_captured += sum(
            emission_coefficient * E[i] * vars_["c_site"][i, t].X
            for i in Nc
        )

    emissions_with_system = (
        emissions_without_system
        - total_captured
        + total_transport_emissions
    )

    return emissions_without_system, emissions_with_system

print(calculate_total_emissions(params, vars_))