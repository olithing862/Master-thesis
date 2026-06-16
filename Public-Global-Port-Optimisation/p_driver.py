"""This code takes given scenario information from the main file, and then creates an instance of the optimisation class
It then plots the results.
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

import p_toolbox as toolbox
import pandas as pd


def driver(optimiser, instance, demand_data, scenario, case, output_file_name, electricity_consumption_data,
           reset_demand=False, overwrite_lb=False,  demand_factor=1):
    """The driver function. Inputs are:
    optimiser - The abstract class for the model
    instance - A concrete instance of the optimiser
    demand_data - a string describing a csv file that contains the necessary demand information.
                    Fuel demand expressed as HFO consumption
    scenario - A string identifying the climate/economic growth that determines how much shipping will occur and where
    case - A string determining where refuelling is happening (i.e. as ships arrive, or as they leave)
    output_file_name - A string (without file extension) for where the output should be saved
    electricity consumption data- A list of the amount of cost at each production site associated with electricity
    reset_demand - A boolean that determines if the demands in instance will be overwritten
    overwrite_lb - A boolean that determines if demand in subsequent cases must depend on that in previuos cases
    factor - A float applied as a factor to the demand data when it converts HFO consumption to ammonia.
        Could express efficiency changes, or only a fraction of demand being covered by ammonia (or both)."""

    if reset_demand:
        print('\nOverwriting demand...')
        # If you want to overwrite the demand with something else, then make this variable true
        new_demand_df = toolbox.extract_demand_data(demand_data, scenario, case, factor=demand_factor)
        new_demand_df = new_demand_df.rename(columns={'name': 'port_name'})
        instance = optimiser.overwrite_demand(instance, new_demand_df)

    if overwrite_lb:
        print('Overwriting lbs on existing installations...')
        instance = optimiser.fix_instance_lbs(instance)

    # Get an output file name that will work
    try:
        output_file_name = toolbox.generate_output_file_name(output_file_name, '.xlsx')
    except NameError:
        output_file_name = toolbox.generate_output_file_name('Fail_name', '.xlsx')

    # Solve the instance
    optimiser.solve_model(instance, tee=True, warmstart=reset_demand)  # If you're resolving with a reset_demand,
    # then you can use a warmstart.

    # Store the results
    print('Storing results...')
    results = toolbox.store_results(instance, elec_consumption=electricity_consumption_data)

    print('Sending the results to excel...')
    with pd.ExcelWriter(output_file_name, engine='xlsxwriter') as writer:
        for key in results.keys():
            df = pd.DataFrame.from_dict(results[key], orient="index")
            df.to_excel(writer, sheet_name=key, index=False)

