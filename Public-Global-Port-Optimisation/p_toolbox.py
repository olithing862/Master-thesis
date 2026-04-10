"""Some useful functions for the optimiser to use.
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

import pyomo.environ as pm
from shapely.geometry import Point
import sys
from bisect import bisect_left
import numpy as np
import glob
import pandas as pd


def take_closest(my_list, my_number):
    """Assumes myList is sorted. Returns the index in the list.
    If two numbers are equally close, return the smallest number."""
    pos = bisect_left(my_list, my_number)
    if pos == 0:
        return pos
    elif pos == len(my_list):
        return pos - 1
    before = my_list[pos - 1]
    after = my_list[pos]
    if after - my_number < my_number - before:
        return pos
    else:
        return pos - 1


def convert_HFO_to_NH3(HFO_fuel_consumption, factor=1):
    """Converts HFO into ammonia using LHVs. Default assumes equivalent combustion efficiencies.
    Factor can be adjusted as desired."""
    return HFO_fuel_consumption * 39 / 18.8 * factor


def generate_output_file_name(base_name, file_extension):
    """Checks that the proposed output file name doesn't already exist.
    If the file name does already exist, selects a new file name that is safe"""
    existing_files = glob.glob('*' + file_extension)
    start = -1
    file_name = base_name + file_extension
    while file_name in existing_files:
        start += 1
        file_name = base_name + str(start) + file_extension
    return file_name


def get_transfers(transfer_data, set1, set2, d=None):
    """Returns a dictionary containing all the transfers in a nominated set"""
    dct = dict()
    for supplier in set1:
        for demander in set2:
            transfer = pm.value(transfer_data[supplier, demander])
            if transfer > 1E-5:
                key = supplier + '_to_' + demander
                dct[key] = {"Supplier": supplier, "Recipient": demander, "Transfer": transfer}
                if d is not None:
                    dct[key][d.name] = pm.value(d[supplier, demander])
    return dct


def extract_demand_data(demand_file, scenario, case, limit_sites=None, factor=1):
    """
    Pulls out the shipping fuel information from the demand data in the relevant file, appropriate to the scenario.
    Both the 'reg' and 'multi' scenarios are included and averaged - these are different, equally likely trade scenarios
    """
    all_demands = pd.read_csv(demand_file)
    if scenario == '2.6':
        SSP = 1
    else:
        SSP = 2
    scenario1 = 'SSP{a}-RCP{b}-Multi'.format(a=SSP, b=scenario)
    scenario2 = 'SSP{a}-RCP{b}-Reg'.format(a=SSP, b=scenario)
    all_demands1 = all_demands.loc[all_demands['scenario'] == scenario1]
    all_demands2 = all_demands.loc[all_demands['scenario'] == scenario2]
    sites = [element for element in set(all_demands1.name)]
    demand_df = pd.Series(sites).to_frame('name')
    id = []
    fuel_consumption = []
    for site in sites:
        sub_df1 = all_demands1.loc[all_demands1.name == site]
        sub_df2 = all_demands2.loc[all_demands2.name == site]
        fuel_consumption.append(np.average([np.sum(sub_df1[case]), np.sum(sub_df2[case])]))
        id.append(sub_df1.iloc[0].id)
    demand_df['Fuel_consumption'] = fuel_consumption
    demand_df['id'] = id
    demand_df.sort_values('Fuel_consumption', axis=0, ascending=False, inplace=True)

    # When you need to reduce the number of demand sites for troubleshooting...
    if limit_sites is not None:
        if limit_sites < len(demand_df):
            fuel_frac = sum(demand_df[0:limit_sites].Fuel_consumption) / sum(demand_df.Fuel_consumption)
            print("\nBecause you've constrained the demand sites, you're using {a} % of the global fuel consumption".
                  format(a=round(fuel_frac, 2) * 100))
            demand_df = demand_df[0:limit_sites]

    # Convert HFO consumption to NH3 consumption...
    demand_df['Fuel_consumption'] = [convert_HFO_to_NH3(element['Fuel_consumption'], factor=factor)
                                     for _, element in demand_df.iterrows()]

    return demand_df


def get_storage(transfer_data, set):
    """Returns a dictionary containing the amount of ammonia storage required at given locations"""
    dct = dict()
    for location in set:
        storage = pm.value(transfer_data[location])
        if storage > 0:
            dct[location] = {'Location': location, 'Storage': storage}
    return dct


def get_electricity_cost_fraction(site_list, site):
    """Given a list of sites with the fraction of cost associated with electricity, returns the local cost. """
    if site_list is not None:
        production_site = site.split('.')[0]+'.0'
        try:
            return site_list.loc[production_site]['Electricity_Cost_Frac']
        except KeyError:
            return 0
    else:
        return 0


def store_results(instance, shipping_data=None, elec_consumption=None):
    """Sticks the results into a dictionary, ready to be sent to excel"""
    results = dict()
    if shipping_data is not None:
        for key1 in shipping_data.keys():
            dct = dict()
            for key2 in shipping_data[key1]:
                dct[key2] = {'Start port': key2[0], 'Finish_port': key2[1], key1: shipping_data[key1][key2]}
            results[key1] = dct

    print('Getting headline results...')
    results['headline_figures'] = get_headline_costs(instance)

    print('Getting transport information...')

    # Start with the easy data...
    results['supplier_storage'] = get_storage(instance.supplier_storage, instance.suppliers)
    results['port_storage'] = get_storage(instance.port_storage, instance.ports)
    results['offshore_transport'] = get_transfers(instance.offshore_transport, instance.ports, instance.ports, d=None)

    # This one is trickier - it is the onshore transport, and needs a bit of extra info
    dct = get_transfers(instance.onshore_transport, instance.suppliers, instance.ports,
                        d=instance.onshore_distances)
    port_df = pd.DataFrame(dct).transpose()
    for key, element in dct.items():
        transfer = element['Transfer']
        supplier_storage_allocation = results['supplier_storage'][element['Supplier']]['Storage'] * \
                                      transfer / pm.value(instance.supplier_production[element['Supplier']])
        total_port_onshore_supply = np.sum(port_df.loc[port_df.Recipient == element['Recipient']]['Transfer'])
        port_storage_allocation = results['port_storage'][element['Recipient']]['Storage'] * \
                                  transfer / total_port_onshore_supply
        # Delivered cost = LCOA + onshore cost + allocated storage costs
        elec_frac = get_electricity_cost_fraction(elec_consumption, key)
        total_production = pm.value(instance.LCOAs[element['Supplier']])
        pipeline = element['onshore_distances'] * instance.onshore_specific_cost
        storage = (supplier_storage_allocation + port_storage_allocation) * instance.storage_cost / transfer
        dct[key]['Production_cost'] = total_production * (1 - elec_frac)
        dct[key]['Electricity_cost'] = total_production * elec_frac
        dct[key]['Pipeline_cost'] = pipeline
        dct[key]['Storage_cost'] = storage
        dct[key]['Delivered_cost'] = total_production + pipeline + storage

    results['onshore_transport'] = dct
    supplier_df = pd.DataFrame(dct).transpose()  # Also store the dct as a convenient dataframe

    dct = get_transfers(instance.offshore_transport, instance.ports, instance.ports, d=instance.offshore_costs)
    for label, values in dct.items():
        reduced_df = supplier_df.loc[supplier_df.Recipient == values['Supplier']]
        production_port_cost = np.average(reduced_df.Production_cost.to_list(),
                                          weights=reduced_df.Transfer.to_list())
        electricity_port_cost = np.average(reduced_df.Electricity_cost.to_list(),
                                           weights=reduced_df.Transfer.to_list())
        pipeline_port_cost = np.average(reduced_df.Pipeline_cost.to_list(),
                                        weights=reduced_df.Transfer.to_list())
        storage_port_cost = np.average(reduced_df.Storage_cost.to_list(),
                                       weights=reduced_df.Transfer.to_list())

        dct[label]['Supplier_Production_cost'] = production_port_cost
        dct[label]['Supplier_Electricity_cost'] = electricity_port_cost
        dct[label]['Supplier_Pipeline_cost'] = pipeline_port_cost
        dct[label]['Supplier_Storage_cost'] = storage_port_cost
        dct[label]['Supplier_Total_cost'] = production_port_cost + electricity_port_cost + \
                                            pipeline_port_cost + storage_port_cost
        dct[label]['Delivered_Port_cost'] = production_port_cost + pipeline_port_cost + electricity_port_cost + \
                                            storage_port_cost + values['offshore_costs']
    results['offshore_transport'] = dct
    offshore_df = pd.DataFrame(dct).transpose()

    # Get data for hubs:
    print('Getting hub information...')
    dct = dict()
    for supplier in instance.suppliers:
        dct[supplier] = {'Location': supplier,
                         'local_production': pm.value(instance.supplier_production[supplier]),
                         'LCOA': pm.value(instance.LCOAs[supplier])}
        n = 0
        for demander in instance.ports:
            transfer = pm.value(instance.onshore_transport[supplier, demander])
            if transfer > 1E-5:
                n += 1
                key = 'Onshore transfer {n}'.format(n=n)
                dct[supplier][key] = demander
                dct[supplier][key + ' Transfer'] = transfer
                supplier_storage_allocation = results['supplier_storage'][supplier]['Storage'] * \
                                              transfer / dct[supplier]['local_production']
                total_port_onshore_supply = np.sum(port_df.loc[port_df.Recipient == demander]['Transfer'])
                port_storage_allocation = results['port_storage'][demander]['Storage'] * \
                                          transfer / total_port_onshore_supply
                dct[supplier][key + ' Port cost/t'] = pm.value(instance.onshore_distances[supplier, demander] *
                                                               instance.onshore_specific_cost +
                                                               pm.value(instance.LCOAs[supplier]) +
                                                               (supplier_storage_allocation + port_storage_allocation) *
                                                               instance.storage_cost / transfer)
        if dct[supplier]['local_production'] < 1:
            dct.pop(supplier)
        results['Suppliers'] = dct
    dct = dict()

    print('Getting data for ports...')
    for demander in instance.ports:
        if pm.value(instance.demands[demander]) > 1:
            dct[demander] = {'Port': demander, 'Demand (MMTPA)': pm.value(instance.demands[demander]) * 1E-6}
            delivered_costs, delivered_amounts = get_weighted_average_cost(supplier_df, demander)
            production_costs, _ = get_weighted_average_cost(supplier_df, demander, column='Production_cost')
            electricity_costs, _ = get_weighted_average_cost(supplier_df, demander, column='Electricity_cost')
            pipeline_costs, _ = get_weighted_average_cost(supplier_df, demander, column='Pipeline_cost')
            storage_costs, _ = get_weighted_average_cost(supplier_df, demander, column='Storage_cost')

            if delivered_amounts == 0:  # This will only occur if the site gets all its ammonia by sea;
                # If all ammonia by sea then storage costs also need to be accounted for
                stored_amount = results['port_storage'][demander]['Storage'] / (dct[demander]['Demand (MMTPA)'] * 1E6)
            else:
                stored_amount = 0
                # If any ammonia via land then it will have been accounted for earlier
            delivered_costs1, delivered_amounts1 = get_weighted_average_cost(offshore_df, demander,
                                                                             starting_costs=delivered_costs,
                                                                             starting_amounts=delivered_amounts,
                                                                             column='Delivered_Port_cost')
            production_costs1, _ = get_weighted_average_cost(offshore_df, demander,
                                                             starting_costs=production_costs,
                                                             column='Supplier_Production_cost')
            electricity_costs1, _ = get_weighted_average_cost(offshore_df, demander,
                                                              starting_costs=electricity_costs,
                                                              column='Supplier_Electricity_cost')
            pipeline_costs1, _ = get_weighted_average_cost(offshore_df, demander,
                                                           starting_costs=pipeline_costs,
                                                           column='Supplier_Pipeline_cost')
            storage_costs1, _ = get_weighted_average_cost(offshore_df, demander,
                                                          starting_costs=storage_costs,
                                                          column='Supplier_Storage_cost')
            ocean_transport = (delivered_costs1 - production_costs1 - electricity_costs1 -
                               pipeline_costs1 - storage_costs1) / delivered_amounts1
            if abs(ocean_transport) < 1E-4:
                ocean_transport = 0

            dct[demander]['Delivered Cost'] = delivered_costs1 / delivered_amounts1 + \
                                              stored_amount * instance.storage_cost
            dct[demander]['Production Cost'] = production_costs1 / delivered_amounts1
            dct[demander]['Electricity Cost'] = electricity_costs1 / delivered_amounts1
            dct[demander]['Pipeline Cost'] = pipeline_costs1 / delivered_amounts1
            dct[demander]['Supply Port Storage Cost'] = storage_costs1 / delivered_amounts1
            dct[demander]['Demand Port Storage Cost'] = stored_amount * instance.storage_cost
            dct[demander]['Ocean Transport Cost'] = ocean_transport
            dct[demander]['Total Storage Cost'] = storage_costs1 / delivered_amounts1 + \
                                                  stored_amount * instance.storage_cost
            dct[demander]['Land deliveries (MMTPA)'] = delivered_amounts * 1E-6
            dct[demander]['Ocean deliveries (MMTPA)'] = (delivered_amounts1 - delivered_amounts) * 1E-6

    results['Demand'] = dct
    return results


def overwrite_demand(instance, new_demand_data):
    """Overwrites the parameters in an existing instance to take on new values"""
    for _, row in new_demand_data.iterrows():
        instance.demands[row.port_name] = row.Fuel_consumption
    instance.total_demand = np.sum(new_demand_data.Fuel_consumption)
    return instance


def fix_instance_lbs(instance):
    """Fixes the values of each of the variables so that their value becomes their lower bound
    Only fixes the production and land transport - these are major physical assets.
    Ocean transport can be redirected."""
    for supplier in instance.suppliers.ordered_data():
        instance.supplier_production[supplier].lb = instance.supplier_production[supplier].value
        if instance.supplier_production[supplier].value > 0:
            for port in instance.ports.ordered_data():
                if instance.onshore_transport[supplier, port].value > 0:
                    instance.onshore_transport[supplier, port].lb = instance.onshore_transport[supplier, port].value
    return instance


def get_weighted_average_cost(df, port, starting_costs=0, starting_amounts=0, column='Delivered_cost'):
    """Gets the amount of ammonia delivered and how much it costs in the provided df at a given port.
        Can stack on top of another dataframe if the provided delivered_costs and delivered_amount are non 0.
        If you want a column other than 'Delivered_cost' for your weighted averages you can input them."""
    costs = starting_costs
    amounts = starting_amounts
    for _, row in df.iterrows():
        if row.Recipient == port:
            costs += row['Transfer'] * row[column]
            amounts += row['Transfer']
    return costs, amounts


def get_headline_costs(instance):
    """"Gets the most interesting information about the solution of an instance and puts it in a dictionary,
     ready to be sent to excel"""
    dct = dict()
    dct['Total Demand'] = {'Parameter': 'Total demand', 'Cost/year':
        pm.value(instance.total_demand)}
    dct['Production costs'] = {'Parameter': 'Production costs', 'Cost/year':
        sum(sum(pm.value(instance.onshore_transport[supplier, port]) for port in instance.ports)
            * pm.value(instance.LCOAs[supplier]) for supplier in instance.suppliers)}
    dct['Onshore costs'] = {'Parameter': 'Onshore costs', 'Cost/year':
        sum(pm.value(instance.onshore_transport[supplier, port]) *
            pm.value(instance.onshore_distances[supplier, port])
            for supplier in instance.suppliers for port in instance.ports)
        * pm.value(instance.onshore_specific_cost)}
    dct['Storage costs'] = {'Parameter': 'Storage costs', 'Cost/year':
        (sum(pm.value(instance.port_storage[port]) for port in instance.ports) +
         sum(pm.value(instance.supplier_storage[supplier]) for supplier in instance.suppliers)) *
        pm.value(instance.storage_cost)}
    dct['Offshore costs'] = {'Parameter': 'Offshore costs', 'Cost/year':
        sum(pm.value(instance.offshore_transport[supply_port, demand_port]) *
            pm.value(instance.offshore_costs[supply_port, demand_port])
            for supply_port in instance.ports for demand_port in instance.ports)}
    costs = ['Production costs', 'Onshore costs', 'Storage costs', 'Offshore costs']
    dct['Total'] = {'Parameter': 'Total', 'Cost/year': sum([dct[cost]['Cost/year'] for cost in costs])}
    for key in dct.keys():
        if key != 'Total Demand':
            dct[key]['Cost per ton'] = dct[key]['Cost/year'] / dct['Total Demand']['Cost/year']
        else:
            dct[key]['Cost per ton'] = ''
    return dct


def get_port_data(ports_list, port_name, element=None):
    """Finds the port and returns the latitude and longitude as a Shapely Point"""
    if element is None:
        port = ports_list.loc[ports_list.name == port_name]
    else:
        port = ports_list.loc[ports_list[element] == port_name]
    return Point(port.lon, port.lat)


def fix_variables(instance):
    """Fixes the variables which won't be used to 0"""
    print('Fixing variables that are banned. This might take a while...')
    for port in instance.ports:
        for supplier in instance.suppliers:
            if instance.onshore_distances[supplier, port] < 0:
                instance.onshore_transport[supplier, port].fix(0)
    return instance


def write_status_bar(percentage):
    sys.stdout.write('\r')
    sys.stdout.write("[%-20s] %d%% complete" % ('=' * int(float(percentage) // 5), percentage))
    sys.stdout.flush()
