"""Pruebas de numeración consecutiva de documentos (plan T3.1)."""

from sistemashn.comercial import sequences


def test_primer_numero_es_uno(session_factory) -> None:
    with session_factory() as session:
        assert sequences.next_number(session, "compra") == 1
        session.commit()


def test_numeracion_consecutiva(session_factory) -> None:
    with session_factory() as session:
        assert sequences.next_number(session, "compra") == 1
        assert sequences.next_number(session, "compra") == 2
        assert sequences.next_number(session, "compra") == 3
        session.commit()


def test_secuencias_independientes_por_nombre(session_factory) -> None:
    with session_factory() as session:
        assert sequences.next_number(session, "compra") == 1
        assert sequences.next_number(session, "venta") == 1
        assert sequences.next_number(session, "compra") == 2
        session.commit()


def test_rollback_no_consume_numero(session_factory) -> None:
    with session_factory() as session:
        assert sequences.next_number(session, "compra") == 1
        session.commit()

    # Una transacción que pide número y luego se revierte no debe avanzar la secuencia.
    with session_factory() as session:
        assert sequences.next_number(session, "compra") == 2
        session.rollback()

    with session_factory() as session:
        assert sequences.next_number(session, "compra") == 2
        session.commit()


def test_format_number() -> None:
    assert sequences.format_number("C", 1) == "C-000001"
    assert sequences.format_number("C", 123456) == "C-123456"
