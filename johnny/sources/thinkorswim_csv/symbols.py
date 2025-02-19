"""Symbols parsing for TD Ameritrade.
"""

from decimal import Decimal
import datetime

from johnny.base import futures
from johnny.base import instrument
from johnny.base.etl import Record
Instrument = instrument.Instrument


# Symbol name changes sometimes occur out of sync in the TOS platform. You may
# find the old symbol name in the trading history and the new one in the cash
# statement.
SYMBOL_NAME_CHANGES = {
    # https://investorplace.com/2021/03/chpt-stock-12-things-to-know-as-chargepoint-trading-spac-merger-sbe-stock/
    'CHPT': 'SBE',
}


def ToInstrument(rec: Record) -> str:
    """Generate an Instrument symbol from the row."""

    # Normalize and fixup the symbols to remove the multiplier and month
    # string. '/CLK21 1/1000 MAY 21' is redundant.
    underlying = rec.symbol.split()[0]
    underlying = SYMBOL_NAME_CHANGES.get(underlying, underlying)

    if rec.instype == 'Equity':
        return instrument.Instrument(underlying=underlying,
                                     multiplier=1)

    if rec.instype == 'Future':
        short_under = underlying[:-3]
        multiplier = futures.MULTIPLIERS[short_under]
        return instrument.Instrument(underlying=underlying,
                                     multiplier=multiplier)

    if rec.instype == 'Equity Option':
        expiration = datetime.datetime.strptime(rec.exp.upper(), '%d %b %y').date()
        assert rec.type in {'CALL', 'PUT'}
        return instrument.Instrument(underlying=underlying,
                                     expiration=expiration,
                                     strike=Decimal(rec.strike),
                                     putcall=rec.type[0],
                                     multiplier=futures.OPTION_CONTRACT_SIZE)

    if rec.instype == 'Future Option':
        assert rec.exp.startswith('/')
        # TODO(blais): Infer the actual expiration date from CME specs. The
        # software does not provide it.
        short_under = underlying[:-3]
        multiplier = futures.MULTIPLIERS[short_under]
        return instrument.Instrument(underlying=underlying,
                                     expiration=None,
                                     expcode=rec.exp,
                                     strike=Decimal(rec.strike),
                                     putcall=rec.type[0],
                                     multiplier=multiplier)

    raise ValueError("Could not infer Beansym for {}".format(rec))


def FromInstrument(inst: Instrument) -> str:
    """Convert instrument to a TD symbol."""

    instype = inst.instype
    if instype == 'FutureOption':
        # Note: For options on futures, the correct expiration date isn't always
        # available (e.g. from TOS). We ignore it for that reason, the date is
        # implicit in the option code. It's not very precise, but better to be
        # consistent.
        return "{}_{}{}{}".format(
            inst.underlying, inst.expcode, inst.putcall, inst.strike)

    elif instype == 'Future':
        return inst.underlying

    elif instype == 'EquityOption':
        return "{}_{:%m%d%y}{}{}".format(
            inst.underlying, inst.expiration, inst.putcall, inst.strike)

    elif instype == 'Equity':
        return inst.underlying

    raise ValueError('Invalid instrument type: {}'.format(instype))
