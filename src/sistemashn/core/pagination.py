"""Resultado paginado común a las consultas de servicio."""

from dataclasses import dataclass

MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


def normalize_page(page: int, page_size: int) -> tuple[int, int, int]:
    """Devuelve (page, page_size, offset) acotados; page empieza en 1."""
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    return page, page_size, (page - 1) * page_size
