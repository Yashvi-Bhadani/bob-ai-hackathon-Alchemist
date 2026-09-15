"""
Single Point of Failure (SPOF) detection
=========================================

Definition
----------
A material has a SPOF when **exactly one qualified supplier** exists for it.

This is a stricter definition than share-based concentration:

* High HHI alone does NOT make a material SPOF.
* A dominant supplier with a 90 % share is NOT a SPOF if a second qualified
  supplier exists — the fab could pivot, albeit with pain.
* SPOF = True only when qualified_supplier_count == 1.

Example
-------
    Neon:
        Supplier A  → qualified   = True
        Supplier B  → qualified   = False

    Qualified count = 1  →  SPOF = True

    Gallium:
        Supplier A  → qualified   = True   (70 %)
        Supplier B  → qualified   = True   (20 %)
        Supplier C  → qualified   = True   (10 %)

    Qualified count = 3  →  SPOF = False  (despite high HHI = 5400)
"""

from __future__ import annotations

from typing import Sequence


def is_spof(supplier_rows: Sequence[dict]) -> bool:
    """
    Determine whether a material is a Single Point of Failure.

    Parameters
    ----------
    supplier_rows:
        List of dicts, each with at minimum a ``"qualified"`` key (bool).
        These represent **all** supplier-rows for a single material.

    Returns
    -------
    bool
        True  → exactly one qualified supplier  (SPOF)
        False → zero or more than one qualified supplier

    Notes
    -----
    Zero qualified suppliers is an extreme case (material fully disqualified);
    returning False keeps the SPOF logic narrow and avoids a different,
    separate alert from being conflated with SPOF.
    """
    qualified_count = sum(1 for row in supplier_rows if row.get("qualified", False))
    return qualified_count == 1


def qualified_supplier_count(supplier_rows: Sequence[dict]) -> int:
    """Return the number of qualified suppliers for a material."""
    return sum(1 for row in supplier_rows if row.get("qualified", False))
