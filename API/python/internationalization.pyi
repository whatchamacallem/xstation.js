# The strings of `i18n/en-US.json`, formatted with `{0}` placeholders.
# Raises on a missing name or a placeholder count unlike the arguments.
# Imported as `from internationalization import i18n` in most modules.
def i18n(name: str, *args: object) -> str: ...
