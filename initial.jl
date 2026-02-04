using HiGHS
using JuMP


model = Model(HiGHS.Optimizer)
@variable(model, x[1:3] >= 0)