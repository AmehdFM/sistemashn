"""Pruebas de `ParkedSalesStore`: ventas en espera en memoria, por usuario (T7.5)."""

from sistemashn.comercial.ui.parked_sales_store import ParkedSalesStore


def test_park_and_retrieve_devuelve_copia_del_borrador():
    store = ParkedSalesStore()
    borrador = {"lineas": [1, 2, 3]}

    park_id = store.park(1, borrador)
    recuperado = store.retrieve(park_id)

    assert recuperado == borrador
    assert recuperado is not borrador  # es una copia, no la misma referencia


def test_park_ids_son_unicos():
    store = ParkedSalesStore()

    id1 = store.park(1, {"a": 1})
    id2 = store.park(1, {"a": 2})

    assert id1 != id2


def test_list_for_user_solo_devuelve_los_del_usuario():
    store = ParkedSalesStore()
    id1 = store.park(1, {"usuario": 1})
    store.park(2, {"usuario": 2})

    lista = store.list_for_user(1)

    assert [pid for pid, _ in lista] == [id1]
    assert lista[0][1] == {"usuario": 1}


def test_retrieve_id_inexistente_devuelve_none():
    store = ParkedSalesStore()

    assert store.retrieve("no-existe") is None


def test_discard_elimina_el_borrador():
    store = ParkedSalesStore()
    park_id = store.park(1, {"a": 1})

    store.discard(park_id)

    assert store.retrieve(park_id) is None
    assert store.list_for_user(1) == []


def test_discard_id_inexistente_no_lanza():
    store = ParkedSalesStore()

    store.discard("no-existe")


def test_list_for_user_conserva_orden_de_creacion():
    store = ParkedSalesStore()
    id1 = store.park(1, {"orden": 1})
    id2 = store.park(1, {"orden": 2})

    lista = store.list_for_user(1)

    assert [pid for pid, _ in lista] == [id1, id2]
