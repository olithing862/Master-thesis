import numpy as np


def great_circle_points(lat1, lon1, lat2, lon2, n_points=50):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    d = 2 * np.arcsin(np.sqrt(
        np.sin((lat2-lat1)/2)**2 +
        np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    ))

    if d == 0:
        return [np.degrees(lat1)], [np.degrees(lon1)]

    f = np.linspace(0, 1, n_points)

    A = np.sin((1-f)*d) / np.sin(d)
    B = np.sin(f*d) / np.sin(d)

    x = A*np.cos(lat1)*np.cos(lon1) + B*np.cos(lat2)*np.cos(lon2)
    y = A*np.cos(lat1)*np.sin(lon1) + B*np.cos(lat2)*np.sin(lon2)
    z = A*np.sin(lat1) + B*np.sin(lat2)

    lat = np.arctan2(z, np.sqrt(x**2 + y**2))
    lon = np.arctan2(y, x)

    return np.degrees(lat), np.degrees(lon)
