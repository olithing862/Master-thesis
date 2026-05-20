"""This is the main code for the global optimisation of the port network
This code just iterates over the scenarios and cases of interest.
The work is done by p_driver, which creates an instance of the optimisation model (defined in optimisation_parent),
and then solves it.
The modules required to run the code are: xarray, pandas, pyomo, numpy, gurobipy, shapely, and bisect.
A gurobi license is also required. Solution time may be long depending on the number of input sites selected.
The purpose of the model is to optimise the distribution of ammonia given specific inputs relating to the supply chain.
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

import p_optimisation_parent as optimisation_class
import p_select_locations as sl
import p_toolbox as toolbox
import p_driver as dr

import xarray as xr
import pandas as pd


def main(scenario, demand_data, case, supplier_number, demand_factors):
    """Loads the data, and then runs the code for each of the instances of demand_factors. Inputs are:
    scenario - Either 2.6 (High-amb) or 4.5 (Mod-amb), relating to the RCP of the scenario you're interested in
    demand_data - csv file containing the demand at each port under the different scenarios
    case - the column in the demand_data file of interest for fuel demand prediction
    supplier_number - maximum number of allowed ammonia suppliers - mostly used for speeding convergence
    demand_factors - list of cases; each instance is the fraction of shipping fuel decarbonised by ammonia"""
    print('Importing the data...')

    # Create optimisation class
    optimiser = optimisation_class.Optimiser()

    # Load in the base case information
    supplier_data = pd.read_csv(r'/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/c_NH3_cost_{a}.csv'.format(a=scenario))  # Ammonia production
    supplier_data = sl.select_locations(supplier_data, number_of_locations=supplier_number, min_production=1)
    if len(supplier_data) < supplier_number:
        print('There are only {a} suppliers that meet that production requirement'.format(a=len(supplier_data)))

    # Keep a separate data frame with the needed info for saving outputs later
    location_elec_cost_frac = supplier_data.drop(columns=supplier_data.columns[1:-1]).set_index('Index')

    # Get the port data
    port_data = pd.read_csv(r'/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/c_port_data.csv')  # list of all ports

    # Get the onshore distance data
    onshore_distance_data = xr.open_dataset(r'/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/n_onshore_distances_{a}.nc'.format(a=scenario))

    # Load in offshore cost data
    offshore_cost_data = xr.open_dataset(r'/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/n_return_costs_{a}_Panamax.nc'.format(a=scenario))

    # Get the demand information for the first demand_factor
    # 'factor' is used to correct the data by any desirable property.
    demand_df = toolbox.extract_demand_data(demand_data, scenario, case, factor=demand_factors[0])

    # Create an initial instance of the class...
    instance = optimiser.create_instance(supplier_data, port_data, onshore_distance_data,
                                         offshore_cost_data, demand_df)

    # Free up some memory...
    onshore_distance_data.close()
    offshore_cost_data.close()

    # Simplify the instance to reduce the number of variables
    instance = toolbox.fix_variables(instance)

    # Iterate over all of the demand factors sent to the model
    for count, demand_factor in enumerate(demand_factors):
        file_name = '{a}_factor_{b}_reduced'.format(a=scenario, b=demand_factor)
        if count == 0:
            dr.driver(optimiser, instance, demand_data, scenario, case, file_name, location_elec_cost_frac)
        else:
            dr.driver(optimiser, instance, demand_data, scenario, case, file_name, location_elec_cost_frac,
                      reset_demand=True, overwrite_lb=True, demand_factor=demand_factor)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    print("Green ammonia distribution optimisation model for shipping decarbonisation. \n"
          "Copyright (C) 2022  N Salmon\n"
          "This program comes with ABSOLUTELY NO WARRANTY\n"
          "This is free software, and you are welcome to redistribute it under certain conditions; see COPYING.txt\n")

    scenario = '4.5'  # Mod-AMB; for High-AMB, use '2.6'
    demand_data = r'/Users/oliviathingvad/Master-thesis/Public-Global-Port-Optimisation/Input Data/c_fuel_demand_port_2050_1000km.csv'
    case = 'Fuel_tons_route_future'
    supplier_number = 100  # Max number of production sites in the model
    demand_factors = [0.01]  # Fraction of fuel demand met by ammonia; solution provided for each element in the list
    main('4.5', demand_data, case, supplier_number, demand_factors)
