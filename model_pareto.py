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

if __name__ == "__main__":
    run_optimisation_model_pareto(eps=1000)


