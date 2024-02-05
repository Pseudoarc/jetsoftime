import objectivehints as obhint


def test_objective_hint_aliases_valid():
    '''Check that all obhint aliases map to valid hints.'''
    obhint_aliases = obhint.get_objective_hint_aliases()

    assert obhint_aliases, 'Failed to get objective hint aliases'

    for alias in obhint_aliases.keys():
        valid, err = obhint.is_hint_valid(alias)
        assert valid, f"Invalid hint alias ({alias}): {err}"
