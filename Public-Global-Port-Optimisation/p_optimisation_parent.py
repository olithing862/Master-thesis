"""This code contains the optimisation class, which sets up the abstract problem
(i.e. parameters, variables, constraints), and then creates a concrete instance of the problem
using the input data provided in the create_instance method of this class
Input data is loaded using main.py, and then sent to the create_instance class via p_driver.py
Copyright N Salmon 2022

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>."""

import p_constraints as cons

import pyomo.environ as pm
# noinspection PyUnresolvedReferences
import gurobipy
import numpy as np


class Optimiser:
    """Class designed for optimising the ammonia network to various shipping destinations"""

    def __init__(self):
        """Initialises the optimiser class"""
        self.model = pm.AbstractModel()
        self.opt = pm.SolverFactory('gurobi')
        self.opt.options["NumericFocus"] = 1
        self.opt.options["Presolve"] = 2
        self.opt.options["NodeMethod"] = 1
        self.opt.options["PreSparsify"] = 1
        self.opt.options["NodefileStart"] = 0.5
        self.opt.options["MIPGap"] = 0.015
        self.opt.options["Threads"] = 10
        self.model_set_up()
        self.converged = False

    def model_set_up(self):
        """Calls the functions which create the model"""
        self.model_sets()
        self.general_model_features()
        self.model_parameters()
        self.model_variables()
        self.model_constraints()

    def model_sets(self):
        """Defines the key operating sets in the model"""
        self.model.suppliers = pm.Set()
        self.model.ports = pm.Set()

    # noinspection PyAttributeOutsideInit
    def general_model_features(self):
        """Sets up the model features that are common to all locations
            Input data to the model also stored here.
            This information is hard-coded because it should not change between runs."""
        # Financial Parameters
        self.G_discount_rate_general = 0.07
        self.G_operating_years = 25
        self.G_crf = self.G_discount_rate_general * (1 + self.G_discount_rate_general) ** self.G_operating_years / (
                (1 + self.G_discount_rate_general) ** self.G_operating_years - 1)
        self.G_O_and_M_frac = 0.02  # Estimated - can be updated

        # Physical Properties
        self.G_rho_NH3_l = 680  # kg/m^3, from NIST at 1 bar, -33*C
        self.G_LHV_NH3 = 18.6  # in GJ/t
        self.G_HHV_NH3 = 22.5  # in GJ/t
        self.G_h_fg_NH3_1_atm_240_K = (1564.5 - 195.82) / 1000  # in GJ/t, from NIST Webbook

        # Pipeline costs
        pipe_costs = {0.01: 1.6859E-2,
                      0.02: 1.8200E-2,
                      0.03: 1.9596E-2,
                      0.04: 2.1033E-2,
                      0.05: 2.2501E-2,
                      0.06: 2.4027E-2,
                      0.07: 2.5612E-2}  # Costs in Cost/t/km at nominated discount rates
        # Calcs not included here for efficiency; see detail in iScience (Salmon & Bañares-Alcántara 2021)
        # More commentary in Schoots (2011)
        self.G_onshore_specific_cost = pipe_costs[np.round(self.G_discount_rate_general, 2)]  # In USD/annual t/km

        # Storage Costs
        # Tank CAPEX and Maintenance
        max_mass_tank = 60000  # in tons
        max_volume_tank = max_mass_tank / (self.G_rho_NH3_l / 1000)  # m3
        tank_cost = 28.5E6  # Estimate from Leighty 2008

        # Boil off
        specific_boil_off_rate = 0.05 / 100  # From Breiki et al., measured as fraction / day
        average_tank_fill = 0.5  # Assumed average level
        refrigeration_COP = 2  # Conservative Assumption
        port_power = 80  # USD / MWh
        mass_boil_off_rate = average_tank_fill * specific_boil_off_rate * 365 * self.G_rho_NH3_l / 1000  # in t/year
        boil_off_energy = mass_boil_off_rate * self.G_h_fg_NH3_1_atm_240_K / refrigeration_COP / 3.6  # in MWh/year
        boil_off_cost = boil_off_energy * port_power  # in USD/year

        # Overall storage costs
        self.G_storage_costs = tank_cost / max_volume_tank * (self.G_crf + self.G_O_and_M_frac) + boil_off_cost


    def model_parameters(self):
        """Defines the key model parameters"""
        # Array parameters
        self.model.LCOAs = pm.Param(self.model.suppliers, within=pm.NonNegativeReals, mutable=True, initialize=0)
        self.model.capacities = pm.Param(self.model.suppliers, within=pm.NonNegativeReals, mutable=True, initialize=0)
        self.model.onshore_distances = pm.Param(self.model.suppliers * self.model.ports, initialize=1)
        self.model.offshore_costs = pm.Param(self.model.ports * self.model.ports, initialize=0)
        self.model.demands = pm.Param(self.model.ports, initialize=0, mutable=True)

        # Single value parameters
        self.model.O_and_M_frac = pm.Param(initialize=self.G_O_and_M_frac)
        self.model.onshore_specific_cost = pm.Param(initialize=self.G_onshore_specific_cost)
        self.model.storage_cost = pm.Param(initialize=self.G_storage_costs)
        self.model.total_demand = pm.Param(within=pm.NonNegativeReals, mutable=True)  # needed for scaling binaries

    def model_variables(self):
        """Defines the key model variables"""
        self.model.supplier_production = pm.Var(self.model.suppliers, bounds=(0, 10E6))
        self.model.onshore_transport = pm.Var(self.model.suppliers, self.model.ports, bounds=(0, 10E7), initialize=0)
        self.model.offshore_transport = pm.Var(self.model.ports, self.model.ports, bounds=(0, 10E7), initialize=0)
        self.model.supplier_storage = pm.Var(self.model.suppliers, initialize=0)
        self.model.port_storage = pm.Var(self.model.ports, initialize=0)
        self.model.supplier_active = pm.Var(self.model.suppliers, within=pm.Binary, initialize=0)
        self.model.port_active = pm.Var(self.model.ports, within=pm.Binary, initialize=0)

    # noinspection PyProtectedMember
    def model_constraints(self):
        """Calls the main constraints"""
        self.model.supplier_capacity = pm.Constraint(self.model.suppliers, rule=cons._supplier_capacity)
        self.model.force_production_2 = pm.Constraint(self.model.suppliers, rule=cons._force_production_2)
        self.model.supplier_balance = pm.Constraint(self.model.suppliers, rule=cons._supplier_balance)
        self.model.port_demand = pm.Constraint(self.model.ports, rule=cons._port_demand)
        self.model.port_active_cons = pm.Constraint(self.model.ports, rule=cons._port_active)
        self.model.supply_storage = pm.Constraint(self.model.suppliers, rule=cons._supply_storage)
        self.model.port_storage_1 = pm.Constraint(self.model.ports, rule=cons._port_storage_1)
        self.model.port_storage_2 = pm.Constraint(self.model.ports, rule=cons._port_storage_2)
        self.model.pipeline_build_constraint1 = pm.Constraint(self.model.suppliers, self.model.ports,
                                                              rule=cons._pipeline_build_constraint1)
        self.model.obj = pm.Objective(rule=cons._calculate_NPV)

    def create_instance(self, supplier_data, port_data, onshore_distances_xarray, offshore_costs_xarray, demand_data):
        """Creates the instance holding the model data for all the parameters that aren't already initialised"""
        data_dct = dict()
        # Sets:
        data_dct['suppliers'] = {None: supplier_data.Index}
        data_dct['ports'] = {None: port_data.name}

        # Parameters:
        # LCOA and capacity
        print('Loading in LCOAs, capacities and minimum distances...')
        LCOAs = dict()
        capacities = dict()
        for _, supplier in supplier_data.iterrows():
            LCOAs[supplier.Index] = supplier.LCOA
            capacities[supplier.Index] = supplier.Max_capacity
        data_dct['LCOAs'] = LCOAs
        data_dct['capacities'] = capacities

        print('Loading in onshore distances...')
        try:
            subset_onshore = onshore_distances_xarray.sel(suppliers=supplier_data.Index.to_list(),
                                                          ports=port_data.name.to_list())
        except KeyError:
            raise KeyError("You have ports in the port list that aren't in the land distance dataset!")
        data_dct['onshore_distances'] = subset_onshore.to_dataframe().to_dict()['distances']

        # Offshore costs
        print('Loading in offshore costs...')
        subset_offshore = offshore_costs_xarray.sel(supply_ports=port_data.name.to_list(),
                                    demand_ports=port_data.name.to_list())
        data_dct['offshore_costs'] = subset_offshore.to_dataframe().to_dict()['shipping_costs']

        # Demands
        print('Loading in demand data...')
        total_demand = np.sum(demand_data.Fuel_consumption)
        demands = dict()
        consuming_ports = demand_data.name.to_list()
        for port in port_data.name:
            if port in consuming_ports:
                demands[port] = demand_data.loc[demand_data.name == port].iloc[0].Fuel_consumption
            else:
                demands[port] = 0
        data_dct['demands'] = demands
        data_dct['total_demand'] = {None: total_demand}

        # Create overall data dictionary:
        data = {None: data_dct}
        print('\nThe total demand is {a}'.format(a=total_demand))

        print('Creating the instance...')
        # Return the instance using that data
        instance = self.model.create_instance(data)
        return instance


    def solve_model(self, instance, warmstart=False, tee=False):
        """Solves the model, and checks that it reached an optimal solution"""
        sol = self.opt.solve(instance, tee=tee, warmstart=warmstart)
        # instance.display("Results.csv")  # Only used if you want to check the results
        if sol.solver.termination_condition != pm.TerminationCondition.optimal:
            print('\nThe instance did not converge properly')
            self.converged = False
        else:
            self.converged = True
