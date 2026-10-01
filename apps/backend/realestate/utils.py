import logging
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="server")



def get_headshot_image(image):
    """returns the image displayed in admin inlines overview"""
    if image:
        return format_html(
            f'<a href="{image.url}" target="_blank">'
            f'<img src="{image.url}" style="max-height:500px;"/>'  # noqa
            f"</a>"
        )
    else:
        return _("No Image Found")


def get_image_format(image):
    """returns the image displayed in admin model overview"""
    if image:
        return format_html(f'<img src="{image.url}" style="max-width:100px;" />')
    else:
        return _("No Image Found")


def get_coordinates(address, user_agent="realestate-tornode"):
    """Returns the coordinates of a given address.

    Args:
        address (str): The address to geocode.
        user_agent (str, optional): The user agent string to use when making
            geocoding requests. Defaults to "realestate-tornode".

    Returns:
        dict: A dictionary containing the following keys:
            "address": The geocoded address.
            "latitude": The latitude of the address.
            "longitude": The longitude of the address.
            "point": The latitude and longitude as a (latitude, longitude) tuple.
            "raw": The raw geocoding data.
            "altitude": The altitude of the address.
    """
    geolocator = Nominatim(user_agent=user_agent)
    try:
        location = geolocator.geocode(address)
        return {
            "address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "point": (location.latitude, location.longitude),
            "raw": location.raw,
            "altitude": location.altitude,
        }
    except (GeocoderTimedOut, GeocoderUnavailable):
        return None


def find_nearest_property(user_location):
    # Assuming Property model has a 'location' field of type PointField
    properties = Property.objects.all()
    nearest_property = None
    min_distance = float("inf")
    for prop in properties:
        prop_location = prop.location  # Get property location
        distance = geodesic(user_location, prop_location).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_property = prop
    return nearest_property


def find_nearest_agent(client_location):
    # Assuming Agent model has a 'location' field of type PointField
    agents = Agent.objects.all()
    nearest_agent = None
    min_distance = float("inf")
    for agent in agents:
        agent_location = agent.location
        client_location = client.location  # Get agent location
        distance = geodesic(client_location, agent_location).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_agent = agent
    return nearest_agent


def locate_nearest(client_location):
    nearest_property = find_nearest_property(client_location)
    nearest_agent = find_nearest_agent(client_location)
    return nearest_property, nearest_agent


# Example usage:
# client_location = (latitude, longitude)  # User's location
# nearest_property, nearest_agent = locate_nearest(user_location)
