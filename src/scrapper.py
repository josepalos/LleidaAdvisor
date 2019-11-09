#!/usr/bin/env python3
import datetime
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
                 prices: str,
                 score_ambient: float,
                 opening_hours: str,  # TODO review
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
        self.opening_hours = opening_hours
        self.cuisine_details = cuisine_details
        self.excellency_certificate = excellency_certificate

    @staticmethod
    def get_csv_headers() -> typing.List:
        return ["name", "direction", "phone", "score", "score_food",
                "score_service", "score_price", "score_ambient",
                "opening_hours", "cuisine_details", "excellency_certificate"]

    def to_csv_row(self) -> typing.List:
        return [self.name, self.direction, self.phone, self.score,
                self.score_food, self.score_service, self.score_price,
                self.score_ambient, self.opening_hours, self.cuisine_details,
                self.excellency_certificate]


class Review:
    def __init__(self,
                 restaurant_id: int,
                 user: str,
                 title: str,
                 text: str,
                 date: datetime.datetime,
                 score: int,
                 response: typing.Optional[str]):
        self.restaurant_id = restaurant_id,
        self.user = user
        self.title = title
        self.text = text
        self.date = date
        self.score = score
        self.response = response

    @staticmethod
    def get_csv_headers() -> typing.List:
        return ["restaurant_id", "user", "title", "text", "date", "score",
                "response"]

    def to_csv_row(self) -> typing.List:
        return [self.restaurant_id, self.user, self.title, self.text,
                self.date, self.score, self.response]


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
    print(restaurant_url)
    direction = utils.get_text_elem(bs, "span", "class", "restaurants-detail-overview-cards-LocationOverviewCard__detailLinkText--co3ei").text
    phone = utils.get_text_elem(bs, "div", "data-blcontact", "PHONE").text

    # Canviar a float
    score = utils.get_text_elem(bs, "span", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__overallRating--nohTl").text

    all_scores = utils.get_text_all_elems(bs, "div", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__ratingQuestionRow--5nPGK")

    if(len(all_scores)==0):
        score_food = None
        score_service = None
        score_price = None
    else:
        score_food = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[0], "span", "class", "ui_bubble_rating"))))/10
        score_service = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[1], "span", "class", "ui_bubble_rating"))))/10
        score_price = int(utils.get_bubble_score(str(utils.get_text_elem(all_scores[2], "span", "class", "ui_bubble_rating"))))/10

    restaurant_details = utils.get_text_all_elems(bs, "div", "class", "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h");
    print(len(restaurant_details))

    # prices = utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h").text

    # score_ambient: float,
    # opening_hours = utils.get_text_elem(bs, "div", "class", "public-location-hours-LocationHours__hoursPopover--2h1HP")
    # cuisine_details = utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-DetailsSectionOverviewCard__tagText--1OH6h")

    excellency_certificate = False

    if(utils.get_text_elem(bs, "div", "class", "restaurants-detail-overview-cards-RatingsOverviewCard__award--31yzt")):
        excellency_certificate = True



    print(name + " " + direction + " " + phone + " " + " Score: " + score + " Score food: " + str(score_food) + " Score service: " + str(score_service) + " Score price: " + str(score_price) + " " + str(excellency_certificate))

    return None


def fetch_restaurant_reviews(name: str, restaurant_url: str) -> typing.List[Review]:
    """
    POST TO https://www.tripadvisor.es/Restaurant_Review-g187500-d995334-Reviews-Xalet_Suis-Lleida_Province_of_Lleida_Catalonia.html

    To change the reviews page, change the "[...]-Reviews-[...]" part of the
    request to "[...]-Reviews-or<N>-[...]", where N is a multiple of 10 that
    refers to the offset of the reviews.

    with headers:
        x-requested-with: XMLHttpRequest
        Content-Type: application/x-www-form-urlencoded
    with data
        filterLang=ALL&
        filterSafety=FALSE&
        reqNum=1&
        paramSeqId=6&
        changeSet=REVIEW_LIST&
    """
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "filterLang": "ALL",
        "filterSafety": "FALSE",
        "reqNum": 1,
        "paramSeqId": 6,
        "changeSet": "REVIEW_LIST",
    }
    bs = utils.post_bs(BASE_URL + restaurant_url, headers=headers, data=data)

    reviews_div = bs.find(id="taplc_location_reviews_list_resp_rr_resp_0")

    reviews = reviews_div.find_all(class_="review-container")
    for review in reviews:
        member_info = review.find(class_="member_info").find(class_="info_text")
        # There are 2 divs inside member_info, the first is for the user and
        # the second for the user location
        name = member_info.find("div").text  # Fetch first div
        print(name)


if __name__ == "__main__":
    restaurant_offset = sys.argv[1]
    restaurants_divs = get_restaurants_list(GEO_LLEIDA, restaurant_offset)
    restaurants_urls = (parse_div(restaurant)
                        for restaurant in restaurants_divs)

    # restaurants = [fetch_restaurant_info(name, restaurant)
    #                for name, restaurant in restaurants_urls]

    first = list(restaurants_urls)[0]
    fetch_restaurant_reviews(*first)
