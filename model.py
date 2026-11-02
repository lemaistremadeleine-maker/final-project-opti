import gurobipy as gb
from constraints import CarbonCaptureConstraints
from problem_instances import small_instance, medium_instance, large_instance

import csv
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.widgets import Slider

class OptiModel:
    def __init__(self, model_name, TIME_LIMIT):
        self.model_name = model_name
        self.TIME_LIMIT = TIME_LIMIT
        # self.params = small_instance()
        self.params = medium_instance()
        # self.params = large_instance()
        self.vars = None
        self.model = None

    def build(self):
        m = gb.Model(self.model_name)
        m.setParam("TimeLimit", self.TIME_LIMIT)

        constraint_builder = CarbonCaptureConstraints(m=m, params=self.params)

        vars_ = constraint_builder.define_variables()

        constraint_builder.function_objective()

        constraint_builder.pipeline_constraints()
        constraint_builder.rail_constraints()
        constraint_builder.flow_constraints()
        constraint_builder.emission_management_constraints()

        m.update()
        self.model, self.vars = m, vars_
        return self.model, self.vars


def run_optimisation_model():

    model_builder = OptiModel(
        model_name="small_instance",
        TIME_LIMIT=300
    )

    m, vars_ = model_builder.build()

    m.optimize()
    export_flows_csv(m, vars_)
    export_pipeline_and_emissions_csv(m, vars_, model_builder.params)
    # export_constraints_txt(m, filename="model_constraints.txt")


def export_flows_csv(model, vars_, filename="solution_flows.csv", tolerance=1e-6):
    if model.SolCount == 0:
        print("No feasible solution to export.")
        return

    rows = []
    for mode in ("truck", "rail", "pipe"):
        for (i, j, t), variable in vars_[f"F_{mode}"].items():
            if variable.X > tolerance:
                rows.append((t, i, j, mode, variable.X))

    rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Period", "From", "To", "Transport", "Flow"])
        writer.writerows(rows)

    print(f"Exported {len(rows)} active flows to {filename}")


def export_pipeline_and_emissions_csv(
    model, vars_, params,
    pipeline_filename="solution_pipelines.csv",
    emissions_filename="emissions_compliance.csv",
    tolerance=1e-6,
):
    if model.SolCount == 0:
        print("No feasible solution to export.")
        return

    T = sorted(params["T"])
    N = sorted(params["N"])

    # One row per existing physical pipeline and period.
    # Installation period = first period where w_pipe > 0.5.
    pipeline_rows = []

    for i in N:
        for j in N:
            if i >= j:
                continue

            installation_period = next(
                (t for t in T if vars_["w_pipe"][i, j, t].X > 0.5),
                None,
            )

            if installation_period is None:
                continue

            for t in T:
                if vars_["w_pipe"][i, j, t].X > 0.5:
                    capacity = vars_["S_pipe"][i, j, t].X
                    flow = (
                        vars_["F_pipe"][i, j, t].X
                        + vars_["F_pipe"][j, i, t].X
                    )

                    pipeline_rows.append((
                        t, i, j, installation_period,
                        capacity, flow,
                        100 * flow / capacity if capacity > tolerance else "",
                    ))

    pipeline_rows.sort(key=lambda row: (row[0], row[1], row[2]))

    with open(pipeline_filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Period", "Node_1", "Node_2", "Installation_period",
            "Capacity", "Total_flow", "Utilisation_percent",
        ])
        writer.writerows(pipeline_rows)

    # Same emissions expression and target as your model.
    emissions_rows = []

    for t in T:
        captured = sum(
            params["emission_coefficient"]
            * params["E"][i]
            * vars_["c_site"][i, t].X
            for i in params["Nc"]
        )

        transport_emissions = sum(
            params["gamma"][mode]
            * params["Lij"][i, j]
            * vars_[f"F_{mode}"][i, j, t].X
            for mode in ("truck", "rail", "pipe")
            for i in N
            for j in N
        )

        net_emissions = transport_emissions - captured
        target = (
            params["Q_init"]
            + (params["Qt"] - params["Q_init"]) * t / max(T)
        )
        slack = target - net_emissions

        emissions_rows.append((
            t, captured, transport_emissions,
            net_emissions, target, slack,
            slack >= -tolerance,
        ))

    with open(emissions_filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Period", "Captured", "Transport_emissions",
            "Net_emissions", "Target", "Slack", "Compliant",
        ])
        writer.writerows(emissions_rows)

    print(f"Exported: {pipeline_filename} and {emissions_filename}")


def export_constraints_txt(model, filename="model_constraints.txt"):
    model.update()

    txt_path = Path(filename)
    lp_path = txt_path.with_suffix(".lp")

    model.write(str(lp_path))
    lp_path.replace(txt_path)

    print(f"Model exported to {txt_path.resolve()}")


def run_multiple_optimisation_runs_for_multiple_alpha(alpha_list):
    results = []

    for alpha in alpha_list:
        model_builder = OptiModel(
            model_name=f"alpha_{alpha[0]}_{alpha[1]}",
            TIME_LIMIT=300,
        )

        model_builder.params["alpha"] = list(alpha)

        m, vars_ = model_builder.build()
        m.optimize()
        export_flows_csv(m, vars_)
        export_pipeline_and_emissions_csv(m, vars_, model_builder.params)

        results.append({
            "alpha": list(alpha),
            "status": m.Status,
            "objective": m.ObjVal if m.SolCount > 0 else None,
            "runtime": m.Runtime,
            "gap": m.MIPGap if m.SolCount > 0 else None,
            "nodes": m.NodeCount,
        })

        m.dispose()

    return results




if __name__ == "__main__":
    run_optimisation_model()

    # alpha_list = [
    #     [0.00025, 1500],
    #     [0.0005, 3000],
    #     [0.00075, 4500],
    #     [0.001, 6000],
    # ]

    # results = run_multiple_optimisation_runs_for_multiple_alpha(alpha_list)

    # for result in results:
    #     print(result)