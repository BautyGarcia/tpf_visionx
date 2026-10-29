"""Errores propios de VisionX.

Los errores de contrato heredan de ValueError: un dato mal formado es un valor inválido.
Los fallos de cámara o de modelo heredan de RuntimeError: no son "cero resultados".
"""

from __future__ import annotations


class ContractError(ValueError):
    """Un mensaje no cumple el contrato."""


class InvalidInput(ContractError):
    """Tipo de dato, tamaño o valor fuera de lo que el contrato permite."""


class SchemaMismatch(ContractError):
    """El mensaje viene de otra versión del esquema."""


class IdentityMismatch(ContractError):
    """Se intentaron combinar datos de frames, sesiones o geometrías distintas."""


class Expired(ContractError):
    """Un pedido o evento pasó su fecha límite."""


class SourceError(RuntimeError):
    """La fuente de frames falló (cámara desconectada, archivo roto).

    Distinto del fin normal de una grabación, que se indica devolviendo None.
    """


class EstimatorError(RuntimeError):
    """Un modelo o algoritmo falló al procesar un frame.

    Distinto de "no hay objetos" o "no se pudo medir", que son resultados válidos.
    """
