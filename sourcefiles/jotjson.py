from __future__ import annotations
import json

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import randosettings as rset


class JOTJSONEncoder(json.JSONEncoder):
    def default(self, obj) -> 'rset.JSONType':
        if hasattr(obj, 'to_jot_json'):
            return obj.to_jot_json()
        return json.JSONEncoder.default(self, obj)
