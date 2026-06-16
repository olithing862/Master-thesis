"""Selects locations for use in optimisation.
Top locations above a certain level of production are selected.
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


def select_locations(df, number_of_locations=1000, min_production=1):
    # Remove locations which didn't converge, and locations with a negligible maximum capacity
    df = df.drop(df.loc[df['Max_capacity'] < min_production].index).sort_values('LCOA')
    return df[:number_of_locations]



