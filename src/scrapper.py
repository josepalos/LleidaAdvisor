#!/usr/bin/env python3
import utils
import sys

BASE_URL = "https://www.tripadvisor.es"
RESTAURANT_PAGINATION_URL = BASE_URL + "/RestaurantSearch?" \
                            "&geo={geo}" \
                            "&sortOrder=relevance" \
                            "&o=a{offset}"

GEO_LLEIDA = 187500
RESTAURANT_DIV_CLASS="restaurants-list-ListCell__cellContainer--2mpJS"
RESTAURANT_NAME_CLASS="restaurants-list-ListCell__restaurantName--2aSdo"


def generate_page_url(geolocation, offset):
    return RESTAURANT_PAGINATION_URL.format(geo=geolocation, offset=offset)


if __name__ == "__main__":
    offset = sys.argv[1]
    bs = utils.get_bs(generate_page_url(GEO_LLEIDA, sys.argv[1]))
    restaurants = bs.find_all(class_=RESTAURANT_DIV_CLASS)

    for restaurant in restaurants:
        name = restaurant.find(class_=RESTAURANT_NAME_CLASS)
        print(name.text, name.attrs["href"])

