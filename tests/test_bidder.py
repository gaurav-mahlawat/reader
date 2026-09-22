import asyncio

from app.bot import bidder


class FakeLocator:
    def __init__(self, page, selector: str):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    async def count(self):
        if self.selector in bidder.AMOUNT_SELECTORS:
            return 1 if self.page.form_open else 0
        return 1 if self.selector in self.page.visible_selectors else 0

    async def is_visible(self):
        if self.selector in bidder.AMOUNT_SELECTORS:
            return self.page.form_open
        return self.selector in self.page.visible_selectors

    async def scroll_into_view_if_needed(self):
        self.page.scrolled.append(self.selector)

    async def click(self):
        self.page.clicked.append(self.selector)
        if self.selector == self.page.opens_form_selector:
            self.page.form_open = True


class FakePage:
    def __init__(self):
        self.form_open = False
        self.clicked = []
        self.scrolled = []
        self.opens_form_selector = 'a:has-text("Place a Bid")'
        self.visible_selectors = {
            'a:has-text("Bid Now")',
            self.opens_form_selector,
        }

    def locator(self, selector: str):
        return FakeLocator(self, selector)


def test_open_bid_form_continues_after_non_opening_button(monkeypatch):
    async def no_delay(*args, **kwargs):
        return None

    monkeypatch.setattr(bidder, "human_delay", no_delay)
    page = FakePage()

    result = asyncio.run(bidder._open_bid_form(page))

    assert result is True
    assert page.clicked[:2] == ['a:has-text("Bid Now")', 'a:has-text("Place a Bid")']
    assert page.scrolled[:2] == ['a:has-text("Bid Now")', 'a:has-text("Place a Bid")']
