# The strings of `i18n/en-US.json`, formatted with `{0}` placeholders.
# Raises KeyError on a missing name and ValueError when the placeholder
# count differs from the argument count. The one `from` import allowed:
# `from i18n import i18n`.
def i18n(name: str, *args: object) -> str: ...
