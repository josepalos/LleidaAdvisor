#!/usr/bin/env python3
import typing

import utils
import sys

BASE_URL = "https://www.tripadvisor.es"
RESTAURANT_PAGINATION_URL = BASE_URL + "/RestaurantSearch?" \
                                       "&geo={geo}" \
                                       "&sortOrder=relevance" \
                                       "&o=a{offset}"
RESTAURANT_PAGE_SIZE = 30

GEO_LLEIDA = 187500
RESTAURANT_DIV_CLASS = "restaurants-list-ListCell__cellContainer--2mpJS"
RESTAURANT_NAME_CLASS = "restaurants-list-ListCell__restaurantName--2aSdo"


class Restaurant:
    def __init__(self,
                 name: str,
                 direction: str,
                 phone: str,
                 score: float,
                 score_food: float,
                 score_service: float,
                 score_price: float,
                 score_ambient: float,
                 opening_hours: str,  # TODO review
                 cuisine_details: str,
                 excellency_certificate: bool):
        self.name = name,
        self.direction = direction
        self.phone = phone
        self.score = score
        self.score_food = score_food
        self.score_service = score_service
        self.score_price = score_price
        self.score_ambient = score_ambient
        self.opening_hours = opening_hours
        self.cuisine_details = cuisine_details
        self.excellency_certificate = excellency_certificate

    @staticmethod
    def get_csv_headers() -> typing.List:
        raise NotImplemented

    def to_csv_row(self) -> typing.List:
        raise NotImplemented


def get_restaurants_list(geolocation, offset):
    bs = utils.get_bs(generate_page_url(geolocation, offset))
    return bs.find_all(class_=RESTAURANT_DIV_CLASS)


def generate_page_url(geolocation, offset):
    return RESTAURANT_PAGINATION_URL.format(geo=geolocation, offset=offset)


def parse_div(restaurant_div):
    name_div = restaurant_div.find(class_=RESTAURANT_NAME_CLASS)
    name = name_div.text
    url = name_div.attrs["href"]
    return name, url


def fetch_restaurant_info(name: str, restaurant_url: str) -> Restaurant:
    raise NotImplemented


if __name__ == "__main__":
    offset = sys.argv[1]
    restaurants_divs = get_restaurants_list(GEO_LLEIDA, sys.argv[1])
    restaurants_urls = (parse_div(restaurant)
                        for restaurant in restaurants_divs)

    restaurants = [fetch_restaurant_info(name, restaurant)
                   for name, restaurant in restaurants_urls]
