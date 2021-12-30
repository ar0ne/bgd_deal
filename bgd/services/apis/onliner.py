"""
Onliner (catalog) API Client
"""
from typing import List, Optional

from bgd.constants import ONLINER
from bgd.responses import GameSearchResult, Price
from bgd.services.api_clients import JsonHttpApiClient
from bgd.services.base import GameSearchService
from bgd.services.builders import GameSearchResultBuilder
from bgd.services.constants import GET
from bgd.services.responses import APIResponse
from bgd.services.utils import remove_backslashes


class OnlinerApiClient(JsonHttpApiClient):
    """Api client for onliner.by"""

    BASE_SEARCH_URL = "https://catalog.onliner.by/sdapi"
    SEARCH_PATH = "/catalog.api/search/products"

    async def search(self, query: str, _: Optional[dict] = None) -> APIResponse:
        """Search by query string"""
        url = f"{self.SEARCH_PATH}?query={query}"
        return await self.connect(GET, self.BASE_SEARCH_URL, url)


class OnlinerSearchService(GameSearchService):
    """Search service for onliner.by"""

    async def do_search(self, query: str, *args, **kwargs) -> List[GameSearchResult]:
        response = await self._client.search(query, **kwargs)
        products = self.filter_results(response.response["products"], self._is_available_game)
        return self.build_results(products)

    def _is_available_game(self, product: dict) -> bool:
        """True if it's available board game"""
        return product["schema"]["key"] == "boardgame" and product["prices"]


class GameSearchResultOnlinerBuilder(GameSearchResultBuilder):
    """GameSearchResult builder for search results from onliner.by"""

    @classmethod
    def from_search_result(cls, search_result: dict) -> GameSearchResult:
        """Builds game search result from ozon data source search result"""
        return GameSearchResult(
            description=search_result["description"],
            images=cls._extract_images(search_result),
            location=None,
            owner=None,
            price=cls._extract_price(search_result),
            source=ONLINER,
            subject=search_result["name"],
            url=cls._extract_url(search_result),
        )

    @staticmethod
    def _extract_price(product: dict) -> Optional[Price]:
        """Extract product price"""
        price = product.get("prices")
        if not price:
            return None
        price_in_byn = price["price_min"]["amount"]
        price_cents = int(float(price_in_byn) * 100)
        return Price(amount=price_cents)

    @staticmethod
    def _extract_url(product: dict) -> str:
        """Extract product page url"""
        return remove_backslashes(product.get("html_url", ""))

    @staticmethod
    def _extract_images(product: dict) -> list:
        """Extract product images"""
        image_url = remove_backslashes(product["images"]["header"])
        return [f"https:{image_url}"]
