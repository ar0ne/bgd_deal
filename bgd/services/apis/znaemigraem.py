"""
Api Client for znaemigraem.by
"""
from typing import List, Optional

from bs4 import BeautifulSoup

from bgd.constants import ZNAEMIGRAEM
from bgd.responses import GameSearchResult, Price
from bgd.services.base import GameSearchService
from bgd.services.builders import GameSearchResultBuilder
from bgd.services.constants import GET
from bgd.services.protocols import HtmlHttpApiClient
from bgd.services.responses import APIResponse


class ZnaemIgraemApiClient(HtmlHttpApiClient):
    """Api client for 5element.by"""

    BASE_SEARCH_URL = "https://znaemigraem.by"

    async def search(self, query: str, _: Optional[dict] = None) -> APIResponse:
        """Search query string"""
        query = "+".join(query.split(" "))
        url = f"/catalog/?q={query}"
        return await self.connect(GET, self.BASE_SEARCH_URL, url)


class ZnaemIgraemSearchService(GameSearchService):
    """Search service for znaemigraem.by"""

    def _is_available_game(self, product: dict) -> bool:
        """True if game is available for purchase"""
        return product["available"]

    async def do_search(self, query: str, *args, **kwargs) -> List[GameSearchResult]:
        """Search query"""
        html_page = await self._client.search(query)
        # find products on search page
        soup = BeautifulSoup(html_page.response, "html.parser")

        search_results = soup.find(class_="c-search__results")
        items = search_results.find_all(class_="catalog-item")
        products = []
        for item in items:
            # filter unavailable products
            if item.find(class_="catalog-item__amount").find("span"):
                continue
            name = item.find(class_="name").get_text()
            # filter not relevant products
            if not self._relevant_result(name, query):
                continue
            product = {
                "image": item.find("img")["src"],
                "name": name,
                "price": item.find(class_="catalog-item__price").get_text(),
                "url": item.find(class_="image")["href"],
            }
            products.append(product)

        return self.build_results(products)

    def _relevant_result(self, product_name, query) -> bool:
        """True if search result is relevant to query"""
        words = query.split(" ")
        for word in words:
            if word in product_name:
                return True
        return False


class GameSearchResultZnaemIgraemBuilder(GameSearchResultBuilder):
    """Game search builder for znaemigraem"""

    BASE_URL = "https://znaemigraem.by"

    @classmethod
    def from_search_result(cls, search_result: dict) -> GameSearchResult:
        """Build game search result"""
        return GameSearchResult(
            description="",
            images=cls._extract_images(search_result),
            location=None,
            owner=None,
            price=cls._extract_price(search_result),
            source=ZNAEMIGRAEM,
            subject=search_result["name"],
            url=cls._extract_url(search_result),
        )

    @classmethod
    def _extract_images(cls, product: dict) -> list[str]:
        """Extract product images"""
        return [f"{cls.BASE_URL}{product['image']}"]

    @staticmethod
    def _extract_price(product: dict) -> Price:
        """
        Extract product price.

        Cut the price ending, e.g. `123.4 p.` -> 12340
        """
        amount = int(float(product["price"][:-3]) * 100)
        return Price(amount=amount)

    @classmethod
    def _extract_url(cls, product: dict) -> str:
        """Extract product url"""
        return f"{cls.BASE_URL}{product['url']}"
