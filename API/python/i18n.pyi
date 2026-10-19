# The strings of `i18n/en-US.json`, formatted with `{0}` placeholders.
# Raises on a missing name or a placeholder count unlike the arguments.
# The one `from` import allowed: `from i18n import i18n`.
def i18n(name: str, *args: object) -> str: ...
