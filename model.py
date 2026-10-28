import gurobipy as gb
from constraints import CarbonCaptureConstraints
from problem_instances import small_instance


class OptiModel:
    def __init__(self, model_name, TIME_LIMIT):
        self.model_name = model_name
        self.TIME_LIMIT = TIME_LIMIT
        self.params = small_instance()
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

if __name__ == "__main__":
    run_optimisation_model()


