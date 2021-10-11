"""
App Services
"""
import asyncio
import json
import logging
import math
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from bgd.clients import ApiClient
from bgd.responses import GameLocation, GameOwner, GameSearchResult

BELARUS = "Belarus"

log = logging.getLogger(__name__)


def convert_byn_to_usd(byn_in_cents: int) -> int:
    """Convert prices from BYN to USD"""
    exchange_rate = 250  # @todo: do not hardcode it
    return math.floor(byn_in_cents * 100 / exchange_rate)


class DataSource:
    """Abstract search service"""

    def __init__(self, client: ApiClient, game_category_id: Union[str, int]) -> None:
        """Init Search Service"""
        self._client = client
        self.game_category_id = game_category_id

    @abstractmethod
    async def do_search(self, query: str, *args, **kwargs) -> List[GameSearchResult]:
        """search query"""

    async def search(self, query: str, *args, **kwargs) -> List[GameSearchResult]:
        """Searching games"""
        responses = await asyncio.gather(
            self.do_search(query, *args, **kwargs), return_exceptions=True
        )
        self._log_errors(responses)
        # filter BaseExceptions
        ret: List[GameSearchResult] = [
            resp for resp in responses if isinstance(resp, list) and len(resp)
        ]
        return ret[0] if ret else ret

    @staticmethod
    def _log_errors(all_responses: Tuple[Union[Any, Exception]]):
        """Log errors if any occur"""
        for resp in all_responses:
            if not isinstance(resp, list):
                log.warning("Error appeared during searching: %s", resp)


class KufarSearchService(DataSource):
    """Service for work with Kufar api"""

    KUFAR = "Kufar"
    IMAGE_URL = "https://yams.kufar.by/api/v1/kufar-ads/images/{}/{}.jpg?rule=gallery"

    async def do_search(
        self, game_name: str, *args, **kwargs
    ) -> List[GameSearchResult]:
        """Search ads by game name"""
        ads = await self._client.search(game_name, {"category": self.game_category_id})
        return [self._build_item(ad) for ad in ads.response.get("ads")]

    def _build_item(self, ad_item: dict) -> GameSearchResult:
        """Convert ads to internal data format"""
        return GameSearchResult(
            description="",  # @TODO: how to get it?
            images=self._extract_images(ad_item),
            location=self._extract_product_location(ad_item),
            owner=self._extract_owner_info(ad_item),
            prices=self._extract_prices(ad_item),
            source=self.KUFAR,
            subject=ad_item.get("subject"),
            url=ad_item.get("ad_link"),
        )

    @staticmethod
    def _extract_prices(ad_item: dict) -> list:
        """Extract ad prices in different currencies (BYN, USD)"""
        return [
            {"byn": int(ad_item.get("price_byn"))},
            {"usd": int(ad_item.get("price_usd"))},
        ]

    def _extract_images(self, ad_item: dict) -> list:
        """Extracts ad images"""
        return [
            self.IMAGE_URL.format(img.get("id")[:2], img.get("id"))
            for img in ad_item.get("images")
            if img.get("yams_storage")
        ]

    def _extract_product_location(self, ad_item: dict) -> GameLocation:
        """Extract location of item"""
        params = ad_item.get("ad_parameters")
        return GameLocation(
            area=self._extract_ad_area(params) or "",
            city=self._extract_ad_city(params) or "",
            country=BELARUS,
        )

    @staticmethod
    def _extract_ad_city(ad_params: list) -> Optional[str]:
        """Extracts add city"""
        for param in ad_params:
            if param.get("pu") == "rgn":
                return param.get("vl")

    @staticmethod
    def _extract_ad_area(ad_params: list) -> Optional[str]:
        """Extract ads area"""
        for param in ad_params:
            if param.get("pu") == "ar":
                return param.get("vl")

    @staticmethod
    def _extract_owner_info(ad_item: dict) -> GameOwner:
        """Extract info about ads owner"""
        name = [
            v
            for acc_param in ad_item.get("account_parameters")
            for k, v in acc_param.items()
            if k == "v"
        ]
        return GameOwner(
            id=ad_item.get("account_id"),
            name=" ".join(name),
        )


class WildberriesSearchService(DataSource):
    """Service for work with Wildberries api"""

    WILDBERRIES = "Wildberries"
    ITEM_URL = "https://by.wildberries.ru/catalog/{}/detail.aspx"
    IMAGE_URL = "https://images.wbstatic.net/big/new/{}0000/{}-1.jpg"

    async def do_search(
        self, game_name: str, *args, **kwargs
    ) -> List[GameSearchResult]:
        items = await self._client.search(game_name)
        return [
            self._format_product(product)
            for product in items.response.get("data", {}).get("products")
            if product.get("subjectId") == self.game_category_id
        ]

    def _format_product(self, product: dict) -> GameSearchResult:
        """Convert ads to internal data format"""
        return GameSearchResult(
            description="",
            images=self._extract_images(product),
            location=None,
            owner=None,
            prices=self._extract_prices(product),
            source=self.WILDBERRIES,
            subject=self._extract_subject(product),
            url=self._extract_url(product),
        )

    def _extract_prices(self, product: dict) -> list:
        """Extract prices for product in different currencies"""
        # @todo: currently I hardcoded "currency" in client, and exchange rate
        price_in_byn = product.get("salePriceU")
        return [
            {"byn": price_in_byn},
            {"usd": convert_byn_to_usd(price_in_byn)},
        ]

    def _extract_url(self, product: dict) -> str:
        """Extract url to product"""
        return self.ITEM_URL.format(product.get("id"))

    def _extract_images(self, product: dict) -> list:
        """Extract product images"""
        product_id = str(product.get("id"))
        return [self.IMAGE_URL.format(product_id[:4], product_id)]

    def _extract_subject(self, product: dict) -> str:
        """Extract product subject"""
        return f"{product.get('brand')} / {product.get('name')}"


class OzonSearchService(DataSource):
    """Search Service for ozon api"""

    OZON = "ozon"

    async def do_search(
        self, game_name: str, *args, **kwargs
    ) -> List[GameSearchResult]:
        response = await self._client.search(
            game_name, {"category": self.game_category_id, **kwargs}
        )
        search_results = self._extract_search_results(response.response)
        if not (search_results and len(search_results.get("items"))):
            return []
        return [self._format_item(item) for item in search_results.get("items")]

    def _extract_search_results(self, resp: dict) -> Optional[dict]:
        """Extract search results from response"""
        widget_states = resp.get("widgetStates", {})
        key = self._find_search_v2_key(widget_states)
        return json.loads(widget_states.get(key, "{}"))

    @staticmethod
    def _find_search_v2_key(states: dict) -> Optional[str]:
        """Find a key in widget states"""
        for key in states.keys():
            if "searchResultsV2" in key:
                return key

    def _format_item(self, item: dict) -> GameSearchResult:
        """Format search response item"""
        return GameSearchResult(
            description="",  # @TODO: how to get it?
            images=self._extract_images(item),
            location=None,
            owner=None,
            prices=self._extract_prices(item),
            source=self.OZON,
            subject=self._extract_subject(item),
            url=self._extract_url(item),
        )

    def _extract_url(self, item: dict) -> Optional[str]:
        """Extract url"""
        return item.get("action", {}).get("link")

    def _extract_prices(self, item: dict) -> List[Optional[Dict[str, int]]]:
        """Extract item prices in cents"""
        main_state = item.get("mainState", [])
        price_state = next(filter(lambda it: it.get("id") == "atom", main_state))
        if not price_state:
            return []
        price = price_state.get("atom", {}).get("price", {}).get("price")
        if not price:
            return []

        price_in_byn = int(100 * float(price.split()[0].replace(",", ".")))
        return [
            {"byn": price_in_byn},
            {"usd": convert_byn_to_usd(price_in_byn)},
        ]

    def _extract_images(self, item: dict) -> list:
        """Extract images"""
        return item.get("tileImage", {}).get("images", [])

    def _extract_subject(self, item: dict) -> str:
        """Extract item subject"""
        main_state = item.get("mainState", [])
        name_state = next(filter(lambda it: it.get("id") == "name", main_state))
        if not name_state:
            return ""
        return name_state.get("atom", {}).get("textAtom", {}).get("text", "")
