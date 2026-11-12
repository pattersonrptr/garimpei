"""
Tests for src/scrapers/mercado_livre.py (Playwright async-based version).

Strategy: mock Playwright async API so no real browser is launched.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scrapers.mercado_livre import MercadoLivreScraper, _ProxyBlockedError

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _mock_element(text: str = "", attribute: str | None = None):
    """Create a mock Playwright ElementHandle."""
    el = AsyncMock()
    el.inner_text = AsyncMock(return_value=text)
    el.get_attribute = AsyncMock(return_value=attribute)
    return el


def _mock_page(
    title: str = "Notebook Dell",
    price_meta: str = "3500.00",
    description: str = "Descrição do produto",
    stock_text: str | None = "Disponível: 10 unidades",
    image_src: str | None = "https://http2.mlstatic.com/img.jpg",
    seller: str | None = "Loja Oficial",
    location: str | None = "São Paulo",
    search_links: list[str] | None = None,
    has_next_page: bool = False,
):
    """Create a mock Playwright Page with configurable query_selector results."""
    page = AsyncMock()

    async def query_selector(selector):
        if selector == "h1.ui-pdp-title":
            return _mock_element(text=title) if title else None
        if selector == 'meta[itemprop="price"]':
            if price_meta:
                return _mock_element(attribute=price_meta)
            return None
        if selector == ".andes-money-amount__fraction":
            return None
        if selector == "p.ui-pdp-description__content":
            return _mock_element(text=description) if description else None
        if selector == ".ui-pdp-stock-information__title":
            if stock_text:
                return _mock_element(text=stock_text)
            return None
        if selector == "img.ui-pdp-image.ui-pdp-gallery__figure__image":
            if image_src:
                return _mock_element(attribute=image_src)
            return None
        if selector == "figure.ui-pdp-gallery__figure img":
            return None
        if selector == ".ui-pdp-seller__link-trigger-button":
            if seller:
                return _mock_element(text=seller)
            return None
        if selector == ".ui-pdp-seller__header__title":
            return None
        if selector == ".ui-pdp-media__body p":
            if location:
                return _mock_element(text=location)
            return None
        if selector == "a.andes-pagination__link[title='Seguinte']":
            return MagicMock() if has_next_page else None
        return None

    page.query_selector = MagicMock(side_effect=query_selector)
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()

    # For _extract_links
    if search_links is not None:
        mock_links = []
        for href in search_links:
            el = AsyncMock()
            el.get_attribute = AsyncMock(return_value=href)
            mock_links.append(el)
        page.query_selector_all = AsyncMock(return_value=mock_links)
    else:
        page.query_selector_all = AsyncMock(return_value=[])

    return page


def _mock_context(page=None):
    ctx = AsyncMock()
    ctx.close = AsyncMock()
    if page is not None:
        ctx.new_page = AsyncMock(return_value=page)
    else:
        ctx.new_page = AsyncMock()
    return ctx


@pytest.fixture
def scraper():
    with (
        patch.object(MercadoLivreScraper, "_load_user_agents", return_value=[]),
        patch(
            "src.scrapers.base.playwright_scraper.get_proxy_rotator",
            return_value=None,
        ),
    ):
        s = MercadoLivreScraper()
    return s


# ---------------------------------------------------------------------------
# __init__ / BASE_URL
# ---------------------------------------------------------------------------


def test_base_url(scraper):
    assert scraper.BASE_URL == "https://lista.mercadolivre.com.br"


def test_str(scraper):
    assert str(scraper) == "Mercado Livre Scraper"


# ---------------------------------------------------------------------------
# _build_default_headers
# ---------------------------------------------------------------------------


def test_build_default_headers_keys():
    headers = MercadoLivreScraper._build_default_headers()
    assert "Accept" in headers
    assert "Accept-Language" in headers


# ---------------------------------------------------------------------------
# headers()
# ---------------------------------------------------------------------------


def test_headers_always_uses_chrome_ua(scraper):
    result = scraper.headers()
    assert "Accept" in result
    assert "User-Agent" in result
    assert "Chrome" in result["User-Agent"]


def test_headers_uses_class_chrome_ua(scraper):
    result = scraper.headers()
    assert result["User-Agent"] == MercadoLivreScraper._CHROME_UA


# ---------------------------------------------------------------------------
# _build_search_url
# ---------------------------------------------------------------------------


def test_build_search_url_first_page(scraper):
    url = scraper._build_search_url("notebook", offset=0)
    assert url == "https://lista.mercadolivre.com.br/notebook"


def test_build_search_url_subsequent_page(scraper):
    url = scraper._build_search_url("notebook", offset=48)
    assert "notebook" in url
    assert "_Desde_49_" in url
    assert "_NoIndex_True" in url


# ---------------------------------------------------------------------------
# _extract_links (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_links_returns_product_links(scraper):
    elements = []
    for href in ["https://ml.com/a", "https://ml.com/b"]:
        el = MagicMock()
        el.get_attribute = AsyncMock(return_value=href)
        elements.append(el)
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=elements)
    links = await scraper._extract_links(page)
    assert "https://ml.com/a" in links
    assert "https://ml.com/b" in links


@pytest.mark.asyncio
async def test_extract_links_filters_click1_tracker(scraper):
    elements = []
    for href in ["https://ml.com/a", "https://click1.mercadolivre.com.br/tracker"]:
        el = MagicMock()
        el.get_attribute = AsyncMock(return_value=href)
        elements.append(el)
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=elements)
    links = await scraper._extract_links(page)
    assert "https://ml.com/a" in links
    assert not any("click1" in link for link in links)


@pytest.mark.asyncio
async def test_extract_links_empty_when_no_items(scraper):
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[])
    links = await scraper._extract_links(page)
    assert links == []


@pytest.mark.asyncio
async def test_extract_links_deduplicates(scraper):
    elements = []
    for href in ["https://ml.com/a", "https://ml.com/a", "https://ml.com/b"]:
        el = MagicMock()
        el.get_attribute = AsyncMock(return_value=href)
        elements.append(el)
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=elements)
    links = await scraper._extract_links(page)
    assert links == ["https://ml.com/a", "https://ml.com/b"]


@pytest.mark.asyncio
async def test_extract_links_skips_empty_href(scraper):
    elements = []
    for href in ["", None, "https://ml.com/a"]:
        el = MagicMock()
        el.get_attribute = AsyncMock(return_value=href)
        elements.append(el)
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=elements)
    links = await scraper._extract_links(page)
    assert links == ["https://ml.com/a"]


# ---------------------------------------------------------------------------
# search (async via _run_async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_collects_links_across_pages(scraper):
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.set_default_timeout = MagicMock()
    page.url = "https://lista.mercadolivre.com.br/notebook"

    call_count = 0

    async def fake_extract_links(p):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ["https://ml.com/a", "https://ml.com/b"]
        return []

    next_btn_count = 0

    async def fake_query_selector(selector):
        nonlocal next_btn_count
        if selector == "a.andes-pagination__link[title='Seguinte']":
            next_btn_count += 1
            if next_btn_count == 1:
                return MagicMock()
            return None
        return None

    page.query_selector = MagicMock(side_effect=fake_query_selector)

    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
        patch.object(scraper, "_extract_links", side_effect=fake_extract_links),
        patch("src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await scraper._search_with_current_proxy("notebook", max_pages=5)

    assert "https://ml.com/a" in result
    assert "https://ml.com/b" in result
    assert len(result) == 2
    ctx.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_stops_on_empty_links(scraper):
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.set_default_timeout = MagicMock()
    page.url = "https://lista.mercadolivre.com.br/notebook"
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
        patch.object(scraper, "_extract_links", return_value=[]),
        pytest.raises(Exception, match="No results found"),
    ):
        await scraper._search_with_current_proxy("notebook", max_pages=5)

    ctx.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_stops_on_page_load_error(scraper):
    page = MagicMock()
    page.goto = AsyncMock(side_effect=Exception("Timeout"))
    page.wait_for_selector = AsyncMock()
    page.set_default_timeout = MagicMock()
    page.url = "https://lista.mercadolivre.com.br/notebook"
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
        pytest.raises(Exception, match="No results found"),
    ):
        await scraper._search_with_current_proxy("notebook", max_pages=3)

    ctx.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_stops_when_no_next_button(scraper):
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)  # No next button
    page.set_default_timeout = MagicMock()
    page.url = "https://lista.mercadolivre.com.br/notebook"
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
        patch.object(
            scraper,
            "_extract_links",
            new_callable=AsyncMock,
            return_value=["https://ml.com/a"],
        ),
        patch("src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await scraper._search_with_current_proxy("notebook", max_pages=5)

    assert result == ["https://ml.com/a"]


@pytest.mark.asyncio
async def test_search_context_closed_on_error(scraper):
    """Ensure the context is closed even when an unexpected error occurs."""
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.set_default_timeout = MagicMock()
    page.url = "https://lista.mercadolivre.com.br/notebook"
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
        patch.object(scraper, "_extract_links", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await scraper._search_with_current_proxy("notebook", max_pages=1)

    ctx.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# _extract_price (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_price_from_meta(scraper):
    page = _mock_page(price_meta="1500.00")
    result = await scraper._extract_price(page)
    assert result == "1500.00"


@pytest.mark.asyncio
async def test_extract_price_fallback_to_fraction(scraper):
    page = AsyncMock()

    async def qs(selector):
        if selector == 'meta[itemprop="price"]':
            return None
        if selector == ".andes-money-amount__fraction":
            return _mock_element(text="2499")
        return None

    page.query_selector = MagicMock(side_effect=qs)
    result = await scraper._extract_price(page)
    assert result == "2499"


@pytest.mark.asyncio
async def test_extract_price_returns_empty_when_missing(scraper):
    page = _mock_page(price_meta=None)
    result = await scraper._extract_price(page)
    assert result == ""


# ---------------------------------------------------------------------------
# _extract_title (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_title(scraper):
    page = _mock_page(title="Notebook Dell")
    result = await scraper._extract_title(page)
    assert result == "Notebook Dell"


@pytest.mark.asyncio
async def test_extract_title_returns_empty_when_missing(scraper):
    page = _mock_page(title=None)
    result = await scraper._extract_title(page)
    assert result == ""


# ---------------------------------------------------------------------------
# _extract_description (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_description(scraper):
    page = _mock_page(description="Bom estado")
    result = await scraper._extract_description(page)
    assert result == "Bom estado"


@pytest.mark.asyncio
async def test_extract_description_returns_empty_when_missing(scraper):
    page = _mock_page(description=None)
    result = await scraper._extract_description(page)
    assert result == ""


# ---------------------------------------------------------------------------
# _extract_availability (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_availability_true_from_stock_info(scraper):
    page = _mock_page(stock_text="Disponível: 5 unidades", price_meta="100")
    result = await scraper._extract_availability(page)
    assert result is True


@pytest.mark.asyncio
async def test_extract_availability_true_from_price_fallback(scraper):
    page = _mock_page(stock_text=None, price_meta="100")
    result = await scraper._extract_availability(page)
    assert result is True


@pytest.mark.asyncio
async def test_extract_availability_false_when_out_of_stock(scraper):
    page = _mock_page(stock_text="Sem estoque", price_meta=None)
    result = await scraper._extract_availability(page)
    assert result is False


@pytest.mark.asyncio
async def test_extract_availability_false_when_nothing(scraper):
    page = _mock_page(stock_text=None, price_meta=None)
    result = await scraper._extract_availability(page)
    assert result is False


# ---------------------------------------------------------------------------
# _extract_product_code (static — unchanged)
# ---------------------------------------------------------------------------


def test_extract_product_code_from_url_path():
    url = "https://www.mercadolivre.com.br/notebook-dell-inspiron-MLB123456789-_JM"
    code = MercadoLivreScraper._extract_product_code(url)
    assert code == "ML - MLB123456789"


def test_extract_product_code_fallback_to_wid_fragment():
    url = "https://www.mercadolivre.com.br/produto#wid=MLB999"
    code = MercadoLivreScraper._extract_product_code(url)
    assert code == "ML - MLB999"


def test_extract_product_code_fallback_to_path_segment():
    url = "https://www.mercadolivre.com.br/categoria/produto-nome"
    code = MercadoLivreScraper._extract_product_code(url)
    assert "ML - " in code
    assert "produto-nome" in code


# ---------------------------------------------------------------------------
# _extract_image_src (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_image_src_returns_src(scraper):
    page = _mock_page(image_src="https://img.com/photo.jpg")
    result = await scraper._extract_image_src(page)
    assert result == "https://img.com/photo.jpg"


@pytest.mark.asyncio
async def test_extract_image_src_fallback_to_figure(scraper):
    page = AsyncMock()

    async def qs(selector):
        if selector == "img.ui-pdp-image.ui-pdp-gallery__figure__image":
            return None
        if selector == "figure.ui-pdp-gallery__figure img":
            return _mock_element(attribute="https://fallback.jpg")
        return None

    page.query_selector = MagicMock(side_effect=qs)
    result = await scraper._extract_image_src(page)
    assert result == "https://fallback.jpg"


@pytest.mark.asyncio
async def test_extract_image_src_returns_none_when_missing(scraper):
    page = _mock_page(image_src=None)
    result = await scraper._extract_image_src(page)
    assert result is None


# ---------------------------------------------------------------------------
# _extract_seller (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_seller(scraper):
    page = _mock_page(seller="Loja Oficial")
    result = await scraper._extract_seller(page)
    assert result == "Loja Oficial"


@pytest.mark.asyncio
async def test_extract_seller_fallback_to_header_title(scraper):
    page = AsyncMock()

    async def qs(selector):
        if selector == ".ui-pdp-seller__link-trigger-button":
            return None
        if selector == ".ui-pdp-seller__header__title":
            return _mock_element(text="Vendedor Teste")
        return None

    page.query_selector = MagicMock(side_effect=qs)
    result = await scraper._extract_seller(page)
    assert result == "Vendedor Teste"


@pytest.mark.asyncio
async def test_extract_seller_not_found(scraper):
    page = _mock_page(seller=None)
    result = await scraper._extract_seller(page)
    assert result == "not found"


# ---------------------------------------------------------------------------
# _extract_location (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_location(scraper):
    page = _mock_page(location="São Paulo")
    result = await scraper._extract_location(page)
    assert result == "São Paulo"


@pytest.mark.asyncio
async def test_extract_location_not_found(scraper):
    page = _mock_page(location=None)
    result = await scraper._extract_location(page)
    assert result == "not found"


# ---------------------------------------------------------------------------
# scrape_data (async via _run_async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_data_returns_expected_fields(scraper):
    page = _mock_page(
        title="Notebook Dell",
        price_meta="3500.00",
        description="Muito bom",
        stock_text="Disponível: 10 unidades",
        image_src="https://http2.mlstatic.com/img.jpg",
        seller="Loja Dell",
        location="Curitiba - PR",
    )
    page.set_default_timeout = MagicMock()
    page.url = "https://www.mercadolivre.com.br/notebook-MLB123456789-_JM"
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
    ):
        url = "https://www.mercadolivre.com.br/notebook-MLB123456789-_JM"
        result = await scraper._scrape_with_current_proxy(url)

    assert result["url"] == url
    assert result["title"] == "Notebook Dell"
    assert result["price"] == "3500.00"
    assert result["description"] == "Muito bom"
    assert result["is_available"] is True
    assert result["image_urls"] == "https://http2.mlstatic.com/img.jpg"
    assert result["source_product_code"] == "ML - MLB123456789"
    assert result["city"] == "Curitiba - PR"
    assert result["state"] == "not found"
    assert result["seller_name"] == "Loja Dell"
    ctx.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_data_unavailable_product(scraper):
    page = _mock_page(stock_text=None, price_meta=None)
    page.set_default_timeout = MagicMock()
    page.url = "https://www.mercadolivre.com.br/item-MLB1"
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
    ):
        result = await scraper._scrape_with_current_proxy(
            "https://www.mercadolivre.com.br/item-MLB1"
        )

    assert result["is_available"] is False
    ctx.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_data_closes_context_on_error(scraper):
    page = MagicMock()
    page.goto = AsyncMock(side_effect=RuntimeError("Timeout"))
    page.set_default_timeout = MagicMock()
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
        pytest.raises(RuntimeError, match="Timeout"),
    ):
        await scraper._scrape_with_current_proxy(
            "https://www.mercadolivre.com.br/item-MLB1"
        )

    ctx.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# update_data
# ---------------------------------------------------------------------------


@patch.object(MercadoLivreScraper, "scrape_data")
@pytest.mark.asyncio
async def test_update_data_merges_fields(mock_scrape, scraper):
    mock_scrape.return_value = {
        "url": "https://ml.com/a",
        "title": "Updated Title",
        "price": "1200",
    }
    product = {"id": "55", "url": "https://ml.com/a", "title": "Old Title"}
    result = scraper.update_data(product)

    assert result["id"] == "55"
    assert result["title"] == "Updated Title"
    mock_scrape.assert_called_once_with("https://ml.com/a")


# ---------------------------------------------------------------------------
# Proxy support
# ---------------------------------------------------------------------------


def test_use_proxy_enabled():
    """ML scraper should declare _USE_PROXY = True."""
    assert MercadoLivreScraper._USE_PROXY is True


def test_proxy_rotator_none_without_env(scraper):
    """Without PROXY_ENABLED env var, proxy_rotator should be a FreeProxyRotator."""
    # When no paid proxy is configured, we fall back to FreeProxyRotator.
    # But in tests we patch get_proxy_rotator to None.
    assert scraper._proxy_rotator is None


# ---------------------------------------------------------------------------
# Block detection
# ---------------------------------------------------------------------------


def test_is_blocked_detects_account_verification():
    url = "https://www.mercadolivre.com.br/gz/account-verification?go=..."
    assert MercadoLivreScraper._is_blocked(url) is True


def test_is_blocked_detects_login():
    url = "https://www.mercadolivre.com.br/login?..."
    assert MercadoLivreScraper._is_blocked(url) is True


def test_is_blocked_normal_url():
    url = "https://lista.mercadolivre.com.br/livros"
    assert MercadoLivreScraper._is_blocked(url) is False


# ---------------------------------------------------------------------------
# Proxy rotation retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_retries_on_proxy_block(scraper):
    """_search_async should retry with the next proxy when blocked."""
    calls = []

    async def fake_search(term, max_pages):
        calls.append(len(calls))
        if len(calls) < 3:
            raise _ProxyBlockedError(proxy={"server": "socks5://1.2.3.4:1080"})
        return ["https://ml.com/a"]

    with (
        patch.object(scraper, "_search_with_current_proxy", side_effect=fake_search),
        patch.object(scraper, "_report_proxy_failure"),
        patch("src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await scraper._search_async("livros")

    assert result == ["https://ml.com/a"]
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_search_raises_after_max_retries(scraper):
    """_search_async should raise after exhausting all proxy retries."""

    async def always_blocked(term, max_pages):
        raise _ProxyBlockedError(proxy={"server": "socks5://dead:1080"})

    with (
        patch.object(scraper, "_search_with_current_proxy", side_effect=always_blocked),
        patch.object(scraper, "_report_proxy_failure"),
        patch("src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(Exception, match="ML search failed after"),
    ):
        await scraper._search_async("livros")


@pytest.mark.asyncio
async def test_scrape_retries_on_proxy_block(scraper):
    """_scrape_data_async should retry with the next proxy when blocked."""
    calls = []

    async def fake_scrape(url):
        calls.append(len(calls))
        if len(calls) < 2:
            raise _ProxyBlockedError(proxy={"server": "socks5://1.2.3.4:1080"})
        return {"url": url, "title": "OK"}

    with (
        patch.object(scraper, "_scrape_with_current_proxy", side_effect=fake_scrape),
        patch.object(scraper, "_report_proxy_failure"),
        patch("src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await scraper._scrape_data_async("https://ml.com/p/MLB1")

    assert result["title"] == "OK"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_search_detects_block_via_url(scraper):
    """When page.url is account-verification, raise _ProxyBlockedError."""
    page = MagicMock()
    page.goto = AsyncMock()
    page.set_default_timeout = MagicMock()
    page.url = "https://www.mercadolivre.com.br/gz/account-verification?go=..."
    ctx = _mock_context(page=page)

    with (
        patch.object(scraper, "start", new_callable=AsyncMock),
        patch.object(scraper, "stop", new_callable=AsyncMock),
        patch.object(
            scraper, "_build_context", new_callable=AsyncMock, return_value=ctx
        ),
        pytest.raises(_ProxyBlockedError),
    ):
        await scraper._search_with_current_proxy("livros", max_pages=1)


# ---------------------------------------------------------------------------
# Rate-limiting / anti-detection
# ---------------------------------------------------------------------------


def test_search_caps_max_pages(scraper):
    """search() should silently cap max_pages to _MAX_SEARCH_PAGES."""
    with patch.object(scraper, "_run_async", return_value=["url1"]) as mock_run:
        scraper.search("kindle", max_pages=50)

    # _run_async was called (search didn't crash)
    assert mock_run.call_count == 1
    # The scraper attribute ensures the cap:
    assert scraper._MAX_SEARCH_PAGES == 20


def test_max_search_pages(scraper):
    """_MAX_SEARCH_PAGES should be 20 (validated: 11 pages, 492 URLs, zero blocks)."""
    assert scraper._MAX_SEARCH_PAGES == 20


def test_search_page_delay_configured(scraper):
    """Search page delay should be 15s (validated: 11 pages with zero blocks)."""
    assert scraper._SEARCH_PAGE_DELAY == 15.0


def test_product_scrape_delay_configured(scraper):
    """Rate-limiting delay should be set to 10s (experiment-validated)."""
    assert scraper._PRODUCT_SCRAPE_DELAY == 10.0


def test_context_rotation_interval(scraper):
    """Context rotation every 5 requests (experiment-validated)."""
    assert scraper._CONTEXT_ROTATION_INTERVAL == 5


def test_shuffle_urls_enabled(scraper):
    """URL shuffling should be enabled for anti-sequential detection."""
    assert scraper._SHUFFLE_URLS is True


def test_jitter_factor(scraper):
    """Jitter factor should be 20%."""
    assert scraper._JITTER_FACTOR == 0.2


def test_jittered_delay_within_range(scraper):
    """_jittered_delay should return a value within ±JITTER_FACTOR of base."""
    base = 10.0
    results = [scraper._jittered_delay(base) for _ in range(100)]
    min_expected = base * (1 - scraper._JITTER_FACTOR)
    max_expected = base * (1 + scraper._JITTER_FACTOR)
    for r in results:
        assert min_expected <= r <= max_expected, (
            f"{r} not in [{min_expected}, {max_expected}]"
        )


@pytest.mark.asyncio
async def test_scrape_data_async_applies_delay_after_first(scraper):
    """_scrape_data_async should apply delay starting from the 2nd call."""
    scraper._scrape_count = 1  # simulate previous scrape

    async def fake_scrape(url):
        return {"url": url, "title": "OK"}

    with (
        patch.object(scraper, "_scrape_with_current_proxy", side_effect=fake_scrape),
        patch(
            "src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep,
    ):
        await scraper._scrape_data_async("https://ml.com/p/MLB1")

    # Should have slept once (the rate-limit delay)
    assert mock_sleep.call_count == 1
    delay_arg = mock_sleep.call_args[0][0]
    # Delay should be within jitter range of _PRODUCT_SCRAPE_DELAY
    assert 8.0 <= delay_arg <= 12.0


@pytest.mark.asyncio
async def test_scrape_data_async_no_delay_on_first(scraper):
    """_scrape_data_async should NOT delay on the very first scrape."""
    scraper._scrape_count = 0  # first scrape

    async def fake_scrape(url):
        return {"url": url, "title": "OK"}

    with (
        patch.object(scraper, "_scrape_with_current_proxy", side_effect=fake_scrape),
        patch(
            "src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep,
    ):
        await scraper._scrape_data_async("https://ml.com/p/MLB1")

    # No sleep on first request
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_scrape_count_increments(scraper):
    """_scrape_count should increment with each _scrape_data_async call."""
    scraper._scrape_count = 0

    async def fake_scrape(url):
        return {"url": url, "title": "OK"}

    with (
        patch.object(scraper, "_scrape_with_current_proxy", side_effect=fake_scrape),
        patch("src.scrapers.mercado_livre.asyncio.sleep", new_callable=AsyncMock),
    ):
        await scraper._scrape_data_async("https://ml.com/p/MLB1")
        await scraper._scrape_data_async("https://ml.com/p/MLB2")
        await scraper._scrape_data_async("https://ml.com/p/MLB3")

    assert scraper._scrape_count == 3
