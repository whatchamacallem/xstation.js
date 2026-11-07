# The strings of `i18n/en-US.json`, formatted with `{0}` placeholders.
# Raises on a missing name or a placeholder count unlike the arguments.
# The file is read at import, from the `i18n` directory beside the module's
# own directory, and the import raises unless it is a JSON object of strings.
# Imported as `from internationalization import i18n` in most modules.
def i18n(name: str, *args: object) -> str: ...
