"""Template rendering utilities for platform routes."""

from pathlib import Path
from typing import Optional

from fastapi.responses import HTMLResponse


def get_template_path(template_name: str) -> Path:
    """Get the full path to a template file.

    Args:
        template_name: Name of the template file (e.g., 'index.html')

    Returns:
        Path object pointing to the template file
    """
    templates_dir = Path(__file__).parent / "templates"
    return templates_dir / template_name


def render_template(
    template_name: str,
    context: Optional[dict] = None,
    encoding: str = "utf-8",
) -> HTMLResponse:
    """Render an HTML template file.

    Args:
        template_name: Name of the template file (e.g., 'index.html')
        context: Optional dictionary of variables to inject into the template.
                 Variables are replaced using {{variable_name}} syntax.
        encoding: File encoding (default: utf-8)

    Returns:
        HTMLResponse with the rendered template content

    Raises:
        FileNotFoundError: If the template file doesn't exist
    """
    template_path = get_template_path(template_name)

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    with open(template_path, "r", encoding=encoding) as file:
        content = file.read()

    # Simple template variable replacement if context is provided
    # Replace {{variable_name}} with the value from context
    if context:
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))

    return HTMLResponse(content=content)


def inject_asset_types(content: str) -> str:
    """Inject AssetType enum values into HTML content.

    This function replaces the placeholder '// ASSET_TYPES_PLACEHOLDER'
    with a JavaScript constant containing all AssetType values.

    Args:
        content: HTML content string

    Returns:
        HTML content with AssetType values injected
    """
    from bot.types import AssetType

    asset_types = [e.value for e in AssetType]
    asset_types_json = str(asset_types).replace("'", '"')
    return content.replace(
        "// ASSET_TYPES_PLACEHOLDER", f"const ASSET_TYPES = {asset_types_json};"
    )
