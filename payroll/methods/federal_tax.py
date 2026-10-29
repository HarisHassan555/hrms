"""
federal_tax.py

Default sandboxed tax code template for filing statuses with use_py enabled.
Uses slab + rate + fixed-amount semantics (same as DB TaxBracket).
"""

CODE = '''
"""
Income tax calculation (slab + rate + fixed amount)
"""

YEARLY_TAXABLE_INCOME = 3600000


def calculate_federal_tax(yearly_income: int, **kwargs) -> float:
    """
    Annual income tax for salaried persons.

    Formula for the matching slab:
        fixed_amount + (yearly_income - income_exceeds) * tax_rate / 100
    """
    # (income_exceeds, does_not_exceed, tax_rate_%, fixed_amount)
    brackets = [
        (0, 600000, 0, 0),
        (600000, 1200000, 1, 0),
        (1200000, 2200000, 11, 6000),
        (2200000, 3200000, 20, 116000),
        (3200000, 4100000, 25, 316000),
        (4100000, 5600000, 29, 541000),
        (5600000, 7000000, 32, 976000),
        (7000000, None, 35, 1424000),
    ]

    income = float(yearly_income or 0)
    if income <= 0:
        return 0.0

    for exceeds, does_not_exceed, rate, fixed in brackets:
        upper = does_not_exceed if does_not_exceed is not None else float("inf")
        if income > exceeds and income <= upper:
            return fixed + (income - exceeds) * (rate / 100.0)

    # Above the last closed slab — apply the open-ended top bracket.
    exceeds, _upper, rate, fixed = brackets[-1]
    return fixed + (income - exceeds) * (rate / 100.0)
'''
