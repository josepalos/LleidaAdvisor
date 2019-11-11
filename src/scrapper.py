#!/usr/bin/env python3
import typing

from bs4 import Tag

import utils
import sys

BASE_URL = "https://www.tripadvisor.com"
RESTAURANT_PAGINATION_URL = BASE_URL + "/RestaurantSearch?" \
                                       "&geo={geo}" \
                                       "&sortOrder=relevance" \
                                       "&o=a{offset}"
RESTAURANT_PAGE_SIZE = 30

GEO_LLEIDA = 187500
RESTAURANT_DIV_CLASS = "restaurants-list-ListCell__cellContainer--2mpJS"
RESTAURANT_NAME_CLASS = "restaurants-list-ListCell__restaurantName--2aSdo"

RESTAURANT_DETAILS_NAME_CLASS_TOP = "restaurants-detail-overview-cards-DetailsSectionOverviewCard__categoryTitle--2RJP_"
RESTAURANT_DETAILS_CONTENT_CLASS_TOP = "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h"

RESTAURANT_DETAILS_NAME_CLASS_BOTTOM = "restaurants-details-card-TagCategories__categoryTitle--28rB6"
RESTAURANT_DETAILS_CONTENT_CLASS_BOTTOM = "restaurants-details-card-TagCategories__tagText--Yt3iG"


class Restaurant:
    def __init__(self,
                 name: str,
                 direction: str,
                 phone: str,
                 score: float,
                 score_food: float,
                 score_service: float,
                 score_price: float,
                 prices: str,
                 score_ambient: float,
                 cuisine_details: str,
                 excellency_certificate: bool):
        self.name = name
        self.direction = direction
        self.phone = phone
        self.score = score
        self.score_food = score_food
        self.score_service = score_service
        self.score_price = score_price
        self.score_ambient = score_ambient
        self.prices = prices
        self.cuisine_details = cuisine_details
        self.excellency_certificate = excellency_certificate

    @staticmethod
    def get_csv_headers() -> typing.List:
        return ["name", "direction", "phone", "score", "score_food",
                "score_service", "score_price", "score_ambient",
                "prices", "cuisine_details", "excellency_certificate"]

    def to_csv_row(self) -> typing.List:
        return [self.name, self.direction, self.phone, self.score,
                self.score_food, self.score_service, self.score_price,
                self.score_ambient, self.prices, self.cuisine_details,
                self.excellency_certificate]


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

    bs = utils.get_bs(BASE_URL + restaurant_url)

    # Get address and phone
    direction = utils.get_text_elem(bs, "span", "class", "restaurants-detail-overview-cards-LocationOverviewCard__detailLinkText--co3ei").text
    phone = utils.get_text_elem(bs, "div", "data-blcontact", "PHONE").text

    score_food = None
    score_service = None
    score_price = None
    score_ambient = None
    prices = None
    cuisine_details = None

    excellency_certificate = False

    # Get score
    score = float(utils.get_text_elem(bs, "span", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__overallRating--nohTl").text.replace(',', '.'))

    all_scores = utils.get_text_all_elems(bs, "div", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__ratingQuestionRow--5nPGK")
    all_scores_len = len(all_scores)

    # Get all scores

    if all_scores_len != 0:
        score_food = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[0], "span", "class", "ui_bubble_rating"))))/10
        score_service = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[1], "span", "class", "ui_bubble_rating"))))/10
        score_price = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[2], "span", "class", "ui_bubble_rating"))))/10

        if all_scores_len == 4:
            score_ambient = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[3], "span", "class", "ui_bubble_rating"))))/10
        else:
            score_ambient = None

    # Get restaurant details and prices

    restaurant_details_top = utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-DetailsSectionOverviewCard__detailsSummary--evhlS")
    restaurant_details_bottom = utils.get_text_elem(bs, "div", "data-tab", "TABS_DETAILS")

    if not restaurant_details_top and restaurant_details_bottom:

        cols = utils.get_text_all_elems(restaurant_details_bottom, "div", "class", "ui_column")
        list_cols = []
        cuisine_details = ""

        for col in cols:
            list_cols.append(parse_restaurant_details(col, "BOTTOM"))

        col1 = list_cols[0]
        col2 = list_cols[1]
        col3 = list_cols[2]

        dict = {**col1, **col2, **col3}


        prices = dict.get("PRICE RANGE", None)


        if "CUISINES" in dict:
            cuisine_details += dict["CUISINES"] + ", "

        if "Special Diets" in dict:
            cuisine_details += dict["Special Diets"]


    elif not restaurant_details_bottom and restaurant_details_top:

        details = parse_restaurant_details(restaurant_details_top, "TOP")
        cuisine_details = ""

        prices = details.get("PRICE RANGE", None)

        if "CUISINES" in details:
            cuisine_details += details["CUISINES"] + ", "

        if "Special Diets" in details:
            cuisine_details += details["Special Diets"]

    # Get excellency certificate

    if utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__award--31yzt"):
        excellency_certificate = True

    print(
        name,
        direction,
        phone,
        score,
        score_food,
        score_service,
        score_price,
        prices,
        score_ambient,
        cuisine_details,
        excellency_certificate
    )

    return Restaurant(
        name,
        direction,
        phone,
        score,
        score_food,
        score_service,
        score_price,
        prices,
        score_ambient,
        cuisine_details,
        excellency_certificate
    )


def parse_restaurant_details(categories_element: Tag, pos) -> dict:
    categories = dict()
    name = ""
    content = ""
    categories_divs = categories_element.children
    for category in categories_divs:

        if pos == "TOP":
            name = category.find(class_=RESTAURANT_DETAILS_NAME_CLASS_TOP).text
            content = category.find(class_=RESTAURANT_DETAILS_CONTENT_CLASS_TOP).text
        elif pos == "BOTTOM":
            name = category.find(class_=RESTAURANT_DETAILS_NAME_CLASS_BOTTOM).text
            content = category.find(class_=RESTAURANT_DETAILS_CONTENT_CLASS_BOTTOM).text

        categories[name] = content

    return categories


if __name__ == "__main__":
    restaurant_offset = sys.argv[1]
    restaurants_divs = get_restaurants_list(GEO_LLEIDA, restaurant_offset)
    restaurants_urls = (parse_div(restaurant)
                        for restaurant in restaurants_divs)

    restaurants = [fetch_restaurant_info(name, restaurant)
                   for name, restaurant in restaurants_urls]
