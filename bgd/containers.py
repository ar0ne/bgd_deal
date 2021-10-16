"""
App containers
"""
import os

from dependency_injector import containers, providers
from starlette.templating import Jinja2Templates

from bgd import services
from bgd.builders import (
    GameSearchResultKufarBuilder,
    GameSearchResultOnlinerBuilder,
    GameSearchResultOzByBuilder,
    GameSearchResultOzonBuilder,
    GameSearchResultWildberriesBuilder,
)
from bgd.clients import (
    BoardGameGeekApiClient,
    KufarApiClient,
    OnlinerApiClient,
    OzByApiClient,
    OzonApiClient,
    WildberriesApiClient,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ApplicationContainer(containers.DeclarativeContainer):
    """App container"""

    config = providers.Configuration()

    kufar_api_client = providers.Factory(
        KufarApiClient,
    )

    kufar_search_service = providers.Factory(
        services.KufarSearchService,
        client=kufar_api_client,
        game_category_id=config.kufar.game_category_id,
        result_builder=GameSearchResultKufarBuilder,
    )

    wildberries_api_client = providers.Factory(
        WildberriesApiClient,
    )
    wildberreis_search_service = providers.Factory(
        services.WildberriesSearchService,
        client=wildberries_api_client,
        game_category_id=config.wildberries.game_category_id,
        result_builder=GameSearchResultWildberriesBuilder,
    )

    ozon_api_client = providers.Factory(
        OzonApiClient,
    )
    ozon_search_service = providers.Factory(
        services.OzonSearchService,
        client=ozon_api_client,
        game_category_id=config.ozon.game_category_id,
        result_builder=GameSearchResultOzonBuilder,
    )

    ozby_api_client = providers.Factory(
        OzByApiClient,
    )
    ozby_search_service = providers.Factory(
        services.OzBySearchService,
        client=ozby_api_client,
        game_category_id=config.ozby.game_category_id,
        result_builder=GameSearchResultOzByBuilder,
    )

    onliner_api_client = providers.Factory(
        OnlinerApiClient,
    )
    onliner_search_service = providers.Factory(
        services.OnlinerSearchService,
        client=onliner_api_client,
        game_category_id="",
        result_builder=GameSearchResultOnlinerBuilder,
    )

    data_sources = providers.List(
        kufar_search_service,
        wildberreis_search_service,
        ozon_search_service,
        ozby_search_service,
        onliner_search_service,
    )

    bgg_api_client = providers.Factory(
        BoardGameGeekApiClient,
    )
    bgg_service = providers.Factory(
        services.BoardGameGeekService,
        client=bgg_api_client,
    )

    templates = providers.Factory(
        Jinja2Templates,
        directory=config.templates.dir,
    )
