"""Set of constraints required for global transport model
It is only called when an instance of the optimisation parent class is created.
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

def _supplier_capacity(model, supplier):
    """Checks that no site produces more ammonia than its max capacity"""
    return model.supplier_production[supplier] <= model.capacities[supplier] * 1E6


def _force_production(model, supplier):
    """If supplier is active, require there to be some production above a minimum rate of 100,000 tpa"""
    return model.suppler_production[supplier] >= model.supplier_active[supplier] * 1E3


def _force_production_2(model, supplier):
    """Make supplier active if it is producing anything"""
    return model.supplier_active[supplier] >= (model.supplier_production[supplier]-50) * 0.1E-6


def _supplier_balance(model, supplier):
    """Mass balance between production and onshore transport"""
    return model.supplier_production[supplier] == sum(model.onshore_transport[supplier, port] for port in model.ports)


def _port_demand(model, port):
    """Checks that each port receives its required demand"""
    return sum(model.onshore_transport[supplier, port] for supplier in model.suppliers) + \
           sum(model.offshore_transport[supply_port, port] for supply_port in model.ports) - \
           sum(model.offshore_transport[port, demand_port] for demand_port in model.ports) >= \
           model.demands[port]


def _port_active(model, port):
    """Turns the port on for transit if any ships stop at the port (i.e. to receive or drop off ammonia)"""
    flow_into_port = sum(model.offshore_transport[supply_port, port] for supply_port in model.ports) +\
                        sum(model.offshore_transport[port, demand_port] for demand_port in model.ports)
    return flow_into_port / model.total_demand <= model.port_active[port]


def _supply_storage(model, supplier):
    """Supplier must hold more than a week's worth of supply"""
    return model.supplier_storage[supplier] == model.supplier_production[supplier] / 52


def _port_storage_1(model, port):
    """Port must hold more than 1.5 times storage of a single ship (Yoo et al.)"""
    return model.port_storage[port] >= 1.5 * 82618 * model.port_active[port]  # 82618 for Panamax


def _port_storage_2(model, port):
    """Port must hold more than a week's worth of supply"""
    flow_into_port = sum(model.onshore_transport[supplier, port] for supplier in model.suppliers) + \
                     sum(model.offshore_transport[supply_port, port] for supply_port in model.ports)
    return model.port_storage[port] >= flow_into_port / 52


def _pipeline_build_constraint1(model, supplier, port):
    """Prevents the construction of pipelines that cross international borders and are too long"""
    return model.onshore_transport[supplier, port] * model.onshore_distances[supplier, port] >= 0
    # Note that model.onshore_distance = -1 if the route is banned


# noinspection PyPep8Naming
def _calculate_NPV(model):
    """Estimates the NPV - this is the value to be minimised; i.e. the objective function
    It's not the true NPV - it's the annual investment cost.
     Exactly what the NPV is depends on your WACC and plant lifetime"""
    production_cost = sum(model.supplier_production[supplier] * model.LCOAs[supplier] for supplier in model.suppliers)
    onshore_cost = sum(model.onshore_transport[supplier, port] * model.onshore_distances[supplier, port]
                       for supplier in model.suppliers for port in model.ports) * model.onshore_specific_cost

    storage_cost = (sum(model.port_storage[port] for port in model.ports) +
                    sum(model.supplier_storage[supplier] for supplier in model.suppliers)) * model.storage_cost
    offshore_cost = sum(model.offshore_transport[supply_port, demand_port] *
                        model.offshore_costs[supply_port, demand_port]
                        for supply_port in model.ports for demand_port in model.ports)

    NPV = production_cost + onshore_cost + storage_cost+ offshore_cost
    return NPV
