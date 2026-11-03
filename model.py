import gurobipy as gb
from constraints import CarbonCaptureConstraints
from problem_instances import small_instance, medium_instance, large_instance

import csv
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


class OptiModel:
    def __init__(self, model_name, TIME_LIMIT, model_instance):
        self.model_name = model_name
        self.TIME_LIMIT = TIME_LIMIT
        # self.params = small_instance()
        self.params = model_instance()
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


def run_optimisation_model(model_instance):

    model_builder = OptiModel(
        model_name="small_instance",
        TIME_LIMIT=200,
        model_instance=model_instance
    )

    m, vars_ = model_builder.build()

    m.optimize()
    export_flows_csv(m, vars_)
    export_pipeline_and_emissions_csv(m, vars_, model_builder.params)
    export_costs_and_emissions_csv(m, vars_, model_builder.params, filename="costs_and_emissions.csv")


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
    

def run_optimisation_model_2():
    """fonction run pour calcul du pareto front"""
    

    model_builder = OptiModel(
        model_name="small_instance",
        TIME_LIMIT=300
    )

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


def export_costs_and_emissions_csv(
    model, vars_, params, filename="costs_and_emissions.csv"
):
    if model.SolCount == 0:
        print("No feasible solution to export.")
        return

    modes = ("truck", "rail", "pipe")
    N = params["N"]

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Period",
            "Truck_operating_cost", "Rail_operating_cost",
            "Pipeline_operating_cost", "Total_operating_cost",
            "Truck_emissions", "Rail_emissions",
            "Pipeline_emissions", "Total_transport_emissions",
            "Captured_CO2", "Net_emissions",
        ])

        for t in sorted(params["T"]):
            costs = {}
            emissions = {}

            for mode in modes:
                costs[mode] = sum(
                    (
                        params["beta"][mode][0] * params["Lij"][i, j]
                        + params["beta"][mode][1]
                    ) * vars_[f"F_{mode}"][i, j, t].X
                    for i in N for j in N
                )

                emissions[mode] = sum(
                    params["gamma"][mode]
                    * params["Lij"][i, j]
                    * vars_[f"F_{mode}"][i, j, t].X
                    for i in N for j in N
                )

            captured = sum(
                params["emission_coefficient"]
                * params["E"][i]
                * vars_["c_site"][i, t].X
                for i in params["Nc"]
            )

            total_emissions = sum(emissions.values())

            writer.writerow([
                t,
                *[costs[mode] for mode in modes],
                sum(costs.values()),
                *[emissions[mode] for mode in modes],
                total_emissions,
                captured,
                total_emissions - captured,
            ])

    print(f"Exported to {filename}")



def export_solution_csvs(model, vars_, params, instance, experiment):
    if model.SolCount == 0:
        print("No feasible solution to export.")
        return

    folder = Path(__file__).resolve().parent / "solution_folder"
    folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Hh%M")
    suffix = f"{instance}_{experiment}_{timestamp}.csv"

    export_flows_csv(
        model, vars_,
        filename=folder / f"solution_flows_{suffix}",
    )

    export_pipeline_and_emissions_csv(
        model, vars_, params,
        pipeline_filename=folder / f"solution_pipelines_{suffix}",
        emissions_filename=folder / f"emissions_compliance_{suffix}",
    )

    export_costs_and_emissions_csv(
        model, vars_, params,
        filename=folder / f"costs_and_emissions_{suffix}",
    )


# def run_optimisation_model(instance="medium_instance", alpha_k=1):
#     model_builder = create_model_builder(
#         instance,
#         model_name=instance,
#     )

#     m, vars_ = model_builder.build()
#     try:
#         m.optimize()
#         export_solution_csvs(
#             m, vars_, model_builder.params, instance, alpha_k
#         )
#     finally:
#         m.dispose()



def run_experiment(
    experiment,
    instance="medium_instance",
    time_limit=200,
    alpha=None,
    beta_mode=None,
    beta_factor=None,
    reduction=None,
):
    loaders = {
        "small_instance": small_instance,
        "medium_instance": medium_instance,
        "large_instance": large_instance,
    }

    model_builder = OptiModel(
        model_name=f"{instance}_{experiment}",
        TIME_LIMIT=time_limit,
        model_instance=medium_instance
    )
    params = loaders[instance]()
    model_builder.params = params

    metadata = {}

    if alpha is not None:
        params["alpha"] = list(alpha)
        metadata["alpha"] = list(alpha)

    if beta_mode is not None:
        beta = [
            beta_factor * float(value)
            for value in params["beta"][beta_mode]
        ]
        params["beta"][beta_mode] = beta
        metadata.update({
            "transport": beta_mode,
            "factor": beta_factor,
            "beta": beta,
        })

    if reduction is not None:
        params["Q_init"] = 0.0
        params["Qt"] = -reduction * sum(params["E"].values())
        metadata.update({
            "reduction": reduction,
            "Qt": params["Qt"],
        })

    m, vars_ = model_builder.build()

    try:
        m.optimize()

        export_solution_csvs(
            m, vars_, params,
            instance=instance,
            experiment=experiment,
        )

        return {
            "experiment": experiment,
            "instance": instance,
            **metadata,
            "status": m.Status,
            "objective": m.ObjVal if m.SolCount > 0 else None,
            "runtime": m.Runtime,
            "gap": m.MIPGap if m.SolCount > 0 else None,
            "nodes": m.NodeCount,
        }
    finally:
        m.dispose()


def run_multiple_optimisation_runs_for_multiple_beta(
    factors=(0.5, 1.0, 1.5),
    time_limit=200,
    instance="medium_instance",
):
    results = []

    for mode in ("truck", "rail", "pipe"):
        for k, factor in enumerate(factors, start=1):
            results.append(
                run_experiment(
                    experiment=f"beta_{mode}_{k}",
                    instance=instance,
                    time_limit=time_limit,
                    beta_mode=mode,
                    beta_factor=factor,
                )
            )

    return results


def run_multiple_optimisation_runs_for_multiple_Qt(
    reductions=(0.90, 0.80, 0.70, 0.60, 0.50),
    time_limit=300,
    instance="medium_instance",
):
    return [
        run_experiment(
            experiment=f"Qt_{k}",
            instance=instance,
            time_limit=time_limit,
            reduction=reduction,
        )
        for k, reduction in enumerate(reductions, start=1)
    ]


def run_multiple_optimisation_runs_for_multiple_alpha(
    alpha_list,
    instance="medium_instance",
    time_limit=200,
):
    return [
        run_experiment(
            experiment=f"alpha_{k}",
            instance=instance,
            time_limit=time_limit,
            alpha=alpha,
        )
        for k, alpha in enumerate(alpha_list, start=1)
    ]



def plot_solution_csvs(
    costs_csv,
    flows_csv,
    pipelines_csv,
    tolerance=1e-3,
):
    def read_csv(path):
        with open(path, newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))

    costs = read_csv(costs_csv)
    flows = read_csv(flows_csv)
    pipelines = read_csv(pipelines_csv)

    periods = sorted(int(row["Period"]) for row in costs)
    modes = ("truck", "rail", "pipe")
    colors = {
        "truck": "darkorange",
        "rail": "royalblue",
        "pipe": "seagreen",
    }
    labels = {
        "truck": "Truck",
        "rail": "Rail",
        "pipe": "Pipeline",
    }

    # Total flow carried on arcs, grouped by mode and period.
    flow_totals = {
        mode: {t: 0.0 for t in periods}
        for mode in modes
    }

    for row in flows:
        t = int(row["Period"])
        mode = row["Transport"]
        flow_totals[mode][t] += float(row["Flow"])

    cost_rows = {int(row["Period"]): row for row in costs}

    cost_columns = {
        "truck": "Truck_operating_cost",
        "rail": "Rail_operating_cost",
        "pipe": "Pipeline_operating_cost",
    }

    emissions_columns = {
        "truck": "Truck_emissions",
        "rail": "Rail_emissions",
        "pipe": "Pipeline_emissions",
    }

    # Sets avoid counting a physical pipeline more than once.
    installed = {t: set() for t in periods}
    used = {t: set() for t in periods}
    installation_dates = {}

    for row in pipelines:
        t = int(row["Period"])
        edge = tuple(sorted((
            int(row["Node_1"]),
            int(row["Node_2"]),
        )))

        installed[t].add(edge)
        installation_dates[edge] = int(row["Installation_period"])

        if float(row["Total_flow"]) > tolerance:
            used[t].add(edge)

    newly_built = {
        t: sum(date == t for date in installation_dates.values())
        for t in periods
    }

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    for mode in modes:
        style = {
            "label": labels[mode],
            "color": colors[mode],
            "linewidth": 2,
        }

        axes[0, 0].plot(
            periods,
            [flow_totals[mode][t] for t in periods],
            **style,
        )

        axes[0, 1].plot(
            periods,
            [
                float(cost_rows[t][cost_columns[mode]])
                for t in periods
            ],
            **style,
        )

        axes[1, 0].plot(
            periods,
            [
                float(cost_rows[t][emissions_columns[mode]])
                for t in periods
            ],
            **style,
        )

    axes[0, 0].set_title("Flow by transport mode")
    axes[0, 0].set_ylabel("Total arc flow")

    axes[0, 1].set_title("Operating cost by transport mode")
    axes[0, 1].set_ylabel("Operating cost")

    axes[1, 0].set_title("Transport emissions by mode")
    axes[1, 0].set_ylabel("CO₂ emissions")

    ax = axes[1, 1]
    ax.bar(
        periods,
        [newly_built[t] for t in periods],
        label="Newly built",
        color="lightsteelblue",
    )
    ax.step(
        periods,
        [len(installed[t]) for t in periods],
        where="mid",
        label="Installed",
        color="black",
        linewidth=2,
    )
    ax.step(
        periods,
        [len(used[t]) for t in periods],
        where="mid",
        label="Used",
        color="seagreen",
        linewidth=2,
        linestyle="--",
    )
    ax.set_title("Pipeline deployment and use")
    ax.set_ylabel("Number of pipelines")

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    for ax in axes.flat:
        ax.set_xlabel("Period")
        ax.grid(alpha=0.3)
        ax.legend()

    fig.tight_layout()
    plt.show()
    return fig


def plot_all_experiments(folder="solution_folder"):
    folder = Path(folder)
    figures = []

    for costs_csv in sorted(
        folder.glob("costs_and_emissions_medium_instance_*.csv")
    ):
        suffix = costs_csv.name.removeprefix("costs_and_emissions_")

        flows_csv = folder / f"solution_flows_{suffix}"
        pipelines_csv = folder / f"solution_pipelines_{suffix}"

        if not flows_csv.exists() or not pipelines_csv.exists():
            print(f"Skipped {suffix}: missing flows or pipelines CSV.")
            continue

        fig = plot_solution_csvs(
            costs_csv=costs_csv,
            flows_csv=flows_csv,
            pipelines_csv=pipelines_csv,
        )

        title = Path(suffix).stem
        fig.suptitle(title)
        fig.canvas.manager.set_window_title(title)
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        figures.append(fig)

    if figures:
        plt.show()  # Opens all experiment windows together.
    else:
        print(f"No complete experiment results found in {folder.resolve()}.")

    return figures


    m, vars_ = model_builder.build()

    m.optimize()
    
    params = model_builder.params
    
    return m, vars_, params

if __name__ == "__main__":
    # run_optimisation_model(small_instance)
    # run_optimisation_model(medium_instance)
    # run_optimisation_model(large_instance)

    # alpha_list = [
    #     [0.00025, 1500],
    #     [0.0005, 3000],
    #     [0.00075, 4500],
    #     [0.001, 6000],
    # ]

    # results = []
    # results.extend(
    #     run_multiple_optimisation_runs_for_multiple_alpha(alpha_list)
    # )
    # results.extend(
    #     run_multiple_optimisation_runs_for_multiple_beta()
    # )
    # results.extend(
    #     run_multiple_optimisation_runs_for_multiple_Qt()
    # )

    # for result in results:
    #     print(result)

    # plot_all_experiments(folder="solution_folder")
    
    # Large instance
    plot_solution_csvs(
        costs_csv=Path("solution_folder/costs_and_emissions_large.csv"),
        flows_csv=Path("solution_folder/solution_flows_large.csv"),
        pipelines_csv=Path("solution_folder/solution_pipelines_large.csv"),
        tolerance=1e-3,
    )

    # Medium instance
    plot_solution_csvs(
        costs_csv=Path("solution_folder/costs_and_emissions_medium.csv"),
        flows_csv=Path("solution_folder/solution_flows_medium.csv"),
        pipelines_csv=Path("solution_folder/solution_pipelines_medium.csv"),
        tolerance=1e-3,
    )

    # Small instance
    plot_solution_csvs(
        costs_csv=Path("solution_folder/costs_and_emissions_small.csv"),
        flows_csv=Path("solution_folder/solution_flows_small.csv"),
        pipelines_csv=Path("solution_folder/solution_pipelines_small.csv"),
        tolerance=1e-3,
    )