"""Servicio de catálogo: unidades, categorías y productos (plan T2.1)."""

import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.models import Category, Product, Unit
from sistemashn.comercial.catalogo.schemas import (
    CategoryInput,
    CategoryView,
    ProductInput,
    ProductView,
    UnitInput,
    UnitView,
)
from sistemashn.comercial.catalogo.search import ProductSearchProvider, normalize_search
from sistemashn.comercial.inventario.models import Stock
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.text import LIKE_ESCAPE, escape_like
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.pagination import Page, normalize_page

# `core` no puede importar de `comercial`, pero lo inverso sí está permitido: reusamos la
# validación de firma de bytes ya escrita para el logo del negocio en vez de duplicarla.
from sistemashn.core.settings.service import sniff_image_extension

MAX_PRODUCT_IMAGE_BYTES = 2 * 1024 * 1024


def _utcnow() -> datetime:
    return datetime.now(UTC)


def save_product_image(data_dir: Path, product_id: int, source: Path) -> str:
    """Valida y copia `source` a `data_dir/productos/<product_id>.<ext>`.

    Reemplaza cualquier imagen anterior del mismo producto. Retorna la ruta relativa a
    `data_dir` (p. ej. `"productos/7.png"`), consistente con `Business.logo_path`.
    """
    contenido = source.read_bytes()
    if len(contenido) > MAX_PRODUCT_IMAGE_BYTES:
        raise ValidationError(
            f"la imagen no puede superar {MAX_PRODUCT_IMAGE_BYTES // (1024 * 1024)} MB"
        )
    extension = sniff_image_extension(contenido)

    carpeta = data_dir / "productos"
    carpeta.mkdir(parents=True, exist_ok=True)
    for existente in carpeta.glob(f"{product_id}.*"):
        existente.unlink()

    destino = carpeta / f"{product_id}.{extension}"
    shutil.copyfile(source, destino)
    return f"productos/{destino.name}"


def _unit_to_view(unit: Unit) -> UnitView:
    return UnitView(
        id=unit.id,
        code=unit.code,
        name=unit.name,
        allows_fraction=unit.allows_fraction,
        active=unit.active,
    )


def _category_to_view(category: Category) -> CategoryView:
    return CategoryView(id=category.id, name=category.name, active=category.active)


class CatalogService:
    """Alta, edición y búsqueda de unidades, categorías y productos."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
        search_providers: list[ProductSearchProvider] | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.search_providers = search_providers or []
        self.data_dir = data_dir

    # -- Unidades ---------------------------------------------------------

    def create_unit(self, actor: Actor, data: UnitInput) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            existente = session.scalar(select(Unit).where(Unit.code == data.code))
            if existente is not None:
                raise ValidationError(f"la unidad '{data.code}' ya existe")
            unit = Unit(
                code=data.code,
                name=data.name,
                allows_fraction=data.allows_fraction,
                active=True,
            )
            session.add(unit)
            session.flush()
            return unit.id

        return run_in_transaction(self.factory, _op)

    def update_unit(self, actor: Actor, unit_id: int, data: UnitInput) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            unit = session.get(Unit, unit_id)
            if unit is None:
                raise NotFound(f"unidad {unit_id} no existe")
            duplicada = session.scalar(
                select(Unit).where(Unit.code == data.code, Unit.id != unit_id)
            )
            if duplicada is not None:
                raise ValidationError(f"la unidad '{data.code}' ya existe")
            unit.code = data.code
            unit.name = data.name
            unit.allows_fraction = data.allows_fraction
            session.flush()

        run_in_transaction(self.factory, _op)

    def list_units(self, actor: Actor, *, include_inactive: bool = False) -> list[UnitView]:
        def _op(session: Session) -> list[UnitView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            stmt = select(Unit).order_by(Unit.name)
            if not include_inactive:
                stmt = stmt.where(Unit.active.is_(True))
            return [_unit_to_view(u) for u in session.scalars(stmt).all()]

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Categorías ---------------------------------------------------------

    def create_category(self, actor: Actor, data: CategoryInput) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            existente = session.scalar(select(Category).where(Category.name == data.name))
            if existente is not None:
                raise ValidationError(f"la categoría '{data.name}' ya existe")
            category = Category(name=data.name, active=True)
            session.add(category)
            session.flush()
            return category.id

        return run_in_transaction(self.factory, _op)

    def update_category(self, actor: Actor, category_id: int, data: CategoryInput) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            category = session.get(Category, category_id)
            if category is None:
                raise NotFound(f"categoría {category_id} no existe")
            duplicada = session.scalar(
                select(Category).where(Category.name == data.name, Category.id != category_id)
            )
            if duplicada is not None:
                raise ValidationError(f"la categoría '{data.name}' ya existe")
            category.name = data.name
            session.flush()

        run_in_transaction(self.factory, _op)

    def list_categories(
        self, actor: Actor, *, include_inactive: bool = False
    ) -> list[CategoryView]:
        def _op(session: Session) -> list[CategoryView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            stmt = select(Category).order_by(Category.name)
            if not include_inactive:
                stmt = stmt.where(Category.active.is_(True))
            return [_category_to_view(c) for c in session.scalars(stmt).all()]

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Productos ---------------------------------------------------------

    def create_product(self, actor: Actor, data: ProductInput) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            self._validar_referencias(session, data)
            self._validar_unicidad(session, data, product_id=None)

            ahora = self.clock()
            product = Product(
                code=data.code,
                barcode=data.barcode,
                name=data.name,
                name_search=normalize_search(data.name),
                description=data.description,
                category_id=data.category_id,
                unit_id=data.unit_id,
                tax_rate=data.tax_rate,
                sale_price=data.sale_price,
                min_stock=data.min_stock,
                is_kit=data.is_kit,
                active=data.active,
                created_at=ahora,
                updated_at=ahora,
            )
            session.add(product)
            session.flush()

            if not data.is_kit:
                session.add(
                    Stock(
                        product_id=product.id,
                        on_hand=Decimal("0"),
                        reserved=Decimal("0"),
                        unsellable=Decimal("0"),
                        avg_cost=Decimal("0"),
                        updated_at=ahora,
                    )
                )
                session.flush()

            audit(
                session,
                actor,
                "com.producto.creado",
                entity_type="com_product",
                entity_id=str(product.id),
                summary=f"Producto '{product.code}' creado",
                detail={
                    "product_code": product.code,
                    "sale_price": product.sale_price,
                    "tax_rate": product.tax_rate,
                },
                clock=self.clock,
            )
            return product.id

        return run_in_transaction(self.factory, _op)

    def update_product(self, actor: Actor, product_id: int, data: ProductInput) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            product = session.get(Product, product_id)
            if product is None:
                raise NotFound(f"producto {product_id} no existe")

            self._validar_referencias(session, data)
            self._validar_unicidad(session, data, product_id=product_id)

            antes = {"sale_price": product.sale_price, "tax_rate": product.tax_rate}

            product.code = data.code
            product.barcode = data.barcode
            product.name = data.name
            product.name_search = normalize_search(data.name)
            product.description = data.description
            product.category_id = data.category_id
            product.unit_id = data.unit_id
            product.tax_rate = data.tax_rate
            product.sale_price = data.sale_price
            product.min_stock = data.min_stock
            product.is_kit = data.is_kit
            product.updated_at = self.clock()
            session.flush()

            despues = {"sale_price": product.sale_price, "tax_rate": product.tax_rate}

            audit(
                session,
                actor,
                "com.producto.editado",
                entity_type="com_product",
                entity_id=str(product.id),
                summary=f"Producto '{product.code}' editado",
                detail={"antes": antes, "despues": despues},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def set_active(self, actor: Actor, product_id: int, active: bool) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            product = session.get(Product, product_id)
            if product is None:
                raise NotFound(f"producto {product_id} no existe")

            product.active = active
            product.updated_at = self.clock()
            session.flush()

            audit(
                session,
                actor,
                "com.producto.activo",
                entity_type="com_product",
                entity_id=str(product.id),
                summary=f"Producto '{product.code}' {'activado' if active else 'inactivado'}",
                detail={"active": active},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def set_image(self, actor: Actor, product_id: int, source: Path) -> None:
        if self.data_dir is None:
            raise ValidationError("no hay directorio de datos configurado para imágenes")

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            product = session.get(Product, product_id)
            if product is None:
                raise NotFound(f"producto {product_id} no existe")

            nombre_archivo = save_product_image(self.data_dir, product_id, source)
            product.image_path = nombre_archivo
            product.updated_at = self.clock()
            session.flush()

            audit(
                session,
                actor,
                "com.catalogo.imagen_actualizada",
                entity_type="com_product",
                entity_id=str(product.id),
                summary=f"Imagen del producto '{product.code}' actualizada",
                detail={"image_path": nombre_archivo},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def get_product(self, actor: Actor, product_id: int) -> ProductView:
        def _op(session: Session) -> ProductView:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            product = session.get(Product, product_id)
            if product is None:
                raise NotFound(f"producto {product_id} no existe")
            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
            return self._to_view(session, product, ver_costos)

        return run_in_transaction(self.factory, _op, readonly=True)

    def find_by_code_or_barcode(self, actor: Actor, code: str) -> ProductView | None:
        def _op(session: Session) -> ProductView | None:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            normalizado = code.strip().upper()
            if not normalizado:
                return None
            product = session.scalar(
                select(Product).where(
                    or_(Product.code == normalizado, Product.barcode == normalizado)
                )
            )
            if product is None:
                return None
            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
            return self._to_view(session, product, ver_costos)

        return run_in_transaction(self.factory, _op, readonly=True)

    def search(
        self,
        actor: Actor,
        text: str,
        *,
        page: int = 1,
        page_size: int = 50,
        include_inactive: bool = False,
    ) -> Page[ProductView]:
        def _op(session: Session) -> Page[ProductView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            page_num, size, offset = normalize_page(page, page_size)
            texto = text.strip()
            texto_normalizado = normalize_search(texto)
            codigo = texto.strip().upper()

            ids_externos: set[int] = set()
            for proveedor in self.search_providers:
                ids_externos.update(proveedor.search(session, texto, limit=size * 5))

            condiciones = []
            if texto:
                condiciones.append(
                    Product.code.like(f"%{escape_like(codigo)}%", escape=LIKE_ESCAPE)
                )
                condiciones.append(
                    Product.barcode.like(f"%{escape_like(codigo)}%", escape=LIKE_ESCAPE)
                )
                condiciones.append(
                    Product.name_search.like(
                        f"%{escape_like(texto_normalizado)}%", escape=LIKE_ESCAPE
                    )
                )
            if ids_externos:
                condiciones.append(Product.id.in_(ids_externos))

            stmt = select(Product)
            if condiciones:
                stmt = stmt.where(or_(*condiciones))
            if not include_inactive:
                stmt = stmt.where(Product.active.is_(True))

            todos = session.scalars(stmt).all()

            def _orden(producto: Product) -> tuple[int, str]:
                exacto = 0 if producto.code == codigo else 1
                return (exacto, producto.name_search)

            todos_ordenados = sorted(todos, key=_orden)
            total = len(todos_ordenados)
            pagina = todos_ordenados[offset : offset + size]

            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
            items = [self._to_view(session, p, ver_costos) for p in pagina]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos ---------------------------------------------------------

    def _validar_referencias(self, session: Session, data: ProductInput) -> None:
        unit = session.get(Unit, data.unit_id)
        if unit is None:
            raise ValidationError(f"unidad {data.unit_id} no existe")
        if data.category_id is not None:
            category = session.get(Category, data.category_id)
            if category is None:
                raise ValidationError(f"categoría {data.category_id} no existe")

    def _validar_unicidad(
        self, session: Session, data: ProductInput, *, product_id: int | None
    ) -> None:
        condiciones_code = [Product.code == data.code]
        if product_id is not None:
            condiciones_code.append(Product.id != product_id)
        if session.scalar(select(Product).where(and_(*condiciones_code))) is not None:
            raise ValidationError(f"el código '{data.code}' ya existe")

        if data.barcode is not None:
            condiciones_barcode = [Product.barcode == data.barcode]
            if product_id is not None:
                condiciones_barcode.append(Product.id != product_id)
            if session.scalar(select(Product).where(and_(*condiciones_barcode))) is not None:
                raise ValidationError(f"el código de barras '{data.barcode}' ya existe")

    def _to_view(self, session: Session, product: Product, ver_costos: bool) -> ProductView:
        stock = session.get(Stock, product.id)
        on_hand = stock.on_hand if stock is not None else Decimal("0")
        reserved = stock.reserved if stock is not None else Decimal("0")
        avg_cost = None
        if ver_costos and stock is not None:
            avg_cost = stock.avg_cost

        return ProductView(
            id=product.id,
            code=product.code,
            barcode=product.barcode,
            name=product.name,
            description=product.description,
            category_id=product.category_id,
            unit_id=product.unit_id,
            tax_rate=product.tax_rate,
            sale_price=product.sale_price,
            min_stock=product.min_stock,
            is_kit=product.is_kit,
            active=product.active,
            on_hand=on_hand,
            reserved=reserved,
            available=on_hand - reserved,
            avg_cost=avg_cost,
            image_path=product.image_path,
        )
