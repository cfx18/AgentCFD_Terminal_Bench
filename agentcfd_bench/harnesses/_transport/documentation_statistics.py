"""Normalize historical/current docs counters without inventing reception."""
import re
from .documentation_service import transport_usage as usage

COMMON={'bundle_digest','queries','searches','reads','rejected','unresolved'}
OLD=COMMON|{'returned_characters'}
NEW=COMMON|{'response_characters_generated','transport_writes_completed',
            'transport_writes_failed','transport_unknown','client_receipt_unknown'}


def normalize_doc_usage(value):
    if value is None:
        return None
    if not isinstance(value,dict) or set(value) not in (OLD,NEW):
        raise ValueError('Unsupported documentation usage schema')
    result=dict(value)
    digest=result['bundle_digest']
    if digest is not None and (not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest)):
        raise ValueError('Invalid documentation usage identity')
    if any(type(v) is not int or v<0 for k,v in result.items() if k!='bundle_digest'):
        raise ValueError('Documentation counters must be nonnegative integers')
    if result['queries']!=sum(result[k] for k in ('searches','reads','rejected','unresolved')):
        raise ValueError('Documentation query counters disagree')
    if set(result)==OLD:
        result['response_characters_generated']=result.pop('returned_characters')
        result.update(transport_writes_completed=0,transport_writes_failed=0,
                      transport_unknown=result['queries'],client_receipt_unknown=result['queries'])
    if (result['queries']!=sum(result[k] for k in ('transport_writes_completed','transport_writes_failed','transport_unknown'))
            or result['client_receipt_unknown']!=result['queries']):
        raise ValueError('Documentation transport counters disagree or invent reception')
    return result


def merge_doc_usage(left,right):
    a,b=normalize_doc_usage(left),normalize_doc_usage(right)
    if a is None:return b
    if b is None:return a
    if a['bundle_digest']!=b['bundle_digest']:
        raise ValueError('Cannot merge different documentation conditions')
    return {key:a[key] if key=='bundle_digest' else a[key]+b[key] for key in NEW}


