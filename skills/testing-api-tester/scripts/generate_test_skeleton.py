#!/usr/bin/env python3
"""Generate test skeleton files from an OpenAPI/Swagger JSON specification.

Reads an OpenAPI 3.x or Swagger 2.x JSON spec and produces test stubs for
each endpoint, including method, path, expected status codes, and example
request bodies derived from the schema.
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


FRAMEWORK_TEMPLATES = {
    "pytest": {
        "header": (
            '"""Auto-generated API test skeleton from OpenAPI spec."""\n'
            "\n"
            "import pytest\n"
            "import requests\n"
            "\n"
            'BASE_URL = "http://localhost:8000"\n'
        ),
        "test_func": (
            "\n"
            "\n"
            "def test_{safe_name}():\n"
            '    """Test {method} {path}\n'
            "\n"
            "    {summary}\n"
            '    Expected status codes: {status_codes}\n'
            '    """\n'
            '    url = f"{{BASE_URL}}{path}"\n'
            "{body_section}"
            "    response = requests.{lower_method}(url{body_arg})\n"
            "    assert response.status_code in {status_codes}\n"
        ),
    },
    "vitest": {
        "header": (
            '// Auto-generated API test skeleton from OpenAPI spec\n'
            "import {{ describe, it, expect }} from 'vitest';\n"
            "\n"
            "const BASE_URL = 'http://localhost:8000';\n"
        ),
        "test_func": (
            "\n"
            "describe('{method} {path}', () => {{\n"
            "  it('{summary}', async () => {{\n"
            "{body_section}"
            "    const response = await fetch(`${{BASE_URL}}{path}`, {{\n"
            "      method: '{method}',\n"
            "{fetch_body}"
            "    }});\n"
            "    expect({status_codes}).toContain(response.status);\n"
            "  }});\n"
            "}});\n"
        ),
    },
    "playwright": {
        "header": (
            '// Auto-generated API test skeleton from OpenAPI spec\n'
            "import {{ test, expect }} from '@playwright/test';\n"
            "\n"
            "const BASE_URL = 'http://localhost:8000';\n"
        ),
        "test_func": (
            "\n"
            "test('{method} {path} - {summary}', async ({{ request }}) => {{\n"
            "{body_section}"
            "  const response = await request.{lower_method}(`${{BASE_URL}}{path}`{pw_body});\n"
            "  expect({status_codes}).toContain(response.status());\n"
            "}});\n"
        ),
    },
}


def make_safe_name(method: str, path: str) -> str:
    """Convert an HTTP method and path to a safe Python function name."""
    safe = path.replace("/", "_").replace("{", "").replace("}", "").replace("-", "_")
    safe = safe.strip("_")
    if not safe:
        safe = "root"
    return f"{method.lower()}_{safe}"


def resolve_ref(ref: str, spec: dict) -> Optional[dict]:
    """Resolve a $ref pointer within the spec (only handles #/... local refs)."""
    if not ref.startswith("#/"):
        return None
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node if isinstance(node, dict) else None


def schema_to_example(schema: dict, spec: dict, depth: int = 0) -> Any:
    """Generate an example value from a JSON Schema object."""
    if depth > 5:
        return "..."

    if "$ref" in schema:
        resolved = resolve_ref(schema["$ref"], spec)
        if resolved:
            return schema_to_example(resolved, spec, depth + 1)
        return {}

    if "example" in schema:
        return schema["example"]

    if "default" in schema:
        return schema["default"]

    if "enum" in schema:
        return schema["enum"][0]

    schema_type = schema.get("type", "object")

    if schema_type == "object":
        result = {}
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            result[prop_name] = schema_to_example(prop_schema, spec, depth + 1)
        return result
    elif schema_type == "array":
        items = schema.get("items", {})
        return [schema_to_example(items, spec, depth + 1)]
    elif schema_type == "string":
        fmt = schema.get("format", "")
        if fmt == "email":
            return "user@example.com"
        if fmt == "date":
            return "2026-01-01"
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        if fmt == "uri" or fmt == "url":
            return "https://example.com"
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        return "string"
    elif schema_type == "integer":
        return 0
    elif schema_type == "number":
        return 0.0
    elif schema_type == "boolean":
        return True
    else:
        return None


def extract_request_body(operation: dict, spec: dict) -> Optional[dict]:
    """Extract an example request body from an operation object."""
    # OpenAPI 3.x
    request_body = operation.get("requestBody", {})
    if request_body:
        if "$ref" in request_body:
            request_body = resolve_ref(request_body["$ref"], spec) or {}
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        if schema:
            return schema_to_example(schema, spec)

    # Swagger 2.x body parameter
    for param in operation.get("parameters", []):
        if param.get("in") == "body" and "schema" in param:
            return schema_to_example(param["schema"], spec)

    return None


def extract_status_codes(operation: dict) -> List[int]:
    """Extract expected status codes from an operation's responses."""
    responses = operation.get("responses", {})
    codes = []
    for code_str in responses:
        try:
            codes.append(int(code_str))
        except ValueError:
            # Handle 'default' or other non-numeric keys
            continue
    if not codes:
        codes = [200]
    return sorted(codes)


def extract_endpoints(spec: dict) -> List[dict]:
    """Extract all endpoints from an OpenAPI/Swagger spec."""
    endpoints = []
    paths = spec.get("paths", {})
    http_methods = {"get", "post", "put", "patch", "delete", "head", "options"}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in http_methods:
            if method not in path_item:
                continue
            operation = path_item[method]
            if not isinstance(operation, dict):
                continue

            summary = operation.get("summary", operation.get("operationId", "No description"))
            status_codes = extract_status_codes(operation)
            body = extract_request_body(operation, spec)

            endpoints.append({
                "path": path,
                "method": method.upper(),
                "summary": summary,
                "status_codes": status_codes,
                "body": body,
            })

    return endpoints


def generate_pytest(endpoints: List[dict]) -> str:
    """Generate pytest test file content."""
    tmpl = FRAMEWORK_TEMPLATES["pytest"]
    lines = [tmpl["header"]]

    for ep in endpoints:
        safe_name = make_safe_name(ep["method"], ep["path"])
        body_section = ""
        body_arg = ""

        if ep["body"] is not None:
            body_json = json.dumps(ep["body"], indent=8)
            body_section = f"    body = {body_json}\n"
            body_arg = ", json=body"

        test_code = tmpl["test_func"].format(
            safe_name=safe_name,
            method=ep["method"],
            path=ep["path"],
            summary=ep["summary"],
            status_codes=ep["status_codes"],
            lower_method=ep["method"].lower(),
            body_section=body_section,
            body_arg=body_arg,
        )
        lines.append(test_code)

    return "".join(lines)


def generate_vitest(endpoints: List[dict]) -> str:
    """Generate vitest test file content."""
    tmpl = FRAMEWORK_TEMPLATES["vitest"]
    lines = [tmpl["header"]]

    for ep in endpoints:
        body_section = ""
        fetch_body = ""

        if ep["body"] is not None:
            body_json = json.dumps(ep["body"], indent=6)
            body_section = f"    const body = {body_json};\n"
            fetch_body = (
                "      headers: { 'Content-Type': 'application/json' },\n"
                "      body: JSON.stringify(body),\n"
            )

        test_code = tmpl["test_func"].format(
            method=ep["method"],
            path=ep["path"],
            summary=ep["summary"],
            status_codes=json.dumps(ep["status_codes"]),
            body_section=body_section,
            fetch_body=fetch_body,
        )
        lines.append(test_code)

    return "".join(lines)


def generate_playwright(endpoints: List[dict]) -> str:
    """Generate Playwright API test file content."""
    tmpl = FRAMEWORK_TEMPLATES["playwright"]
    lines = [tmpl["header"]]

    for ep in endpoints:
        body_section = ""
        pw_body = ""

        if ep["body"] is not None:
            body_json = json.dumps(ep["body"], indent=4)
            body_section = f"  const body = {body_json};\n"
            pw_body = ", { data: body }"

        test_code = tmpl["test_func"].format(
            method=ep["method"],
            path=ep["path"],
            summary=ep["summary"],
            status_codes=json.dumps(ep["status_codes"]),
            lower_method=ep["method"].lower(),
            body_section=body_section,
            pw_body=pw_body,
        )
        lines.append(test_code)

    return "".join(lines)


GENERATORS = {
    "pytest": generate_pytest,
    "vitest": generate_vitest,
    "playwright": generate_playwright,
}


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate test skeleton files from an OpenAPI/Swagger JSON spec. "
            "Produces test stubs for each endpoint with method, path, expected "
            "status codes, and example request bodies."
        )
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="Path to the OpenAPI/Swagger JSON specification file",
    )
    parser.add_argument(
        "--framework",
        required=True,
        choices=["pytest", "vitest", "playwright"],
        help="Test framework to generate stubs for (pytest, vitest, or playwright)",
    )

    args = parser.parse_args()

    try:
        with open(args.spec, "r") as f:
            spec = json.load(f)
    except FileNotFoundError:
        print(f"Error: Spec file not found: {args.spec}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in spec file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(spec, dict):
        print("Error: Spec file must contain a JSON object at the top level.", file=sys.stderr)
        sys.exit(1)

    if "paths" not in spec:
        print("Error: No 'paths' key found in spec. Is this a valid OpenAPI/Swagger file?", file=sys.stderr)
        sys.exit(1)

    endpoints = extract_endpoints(spec)
    if not endpoints:
        print("Warning: No endpoints found in the spec.", file=sys.stderr)
        sys.exit(0)

    generator = GENERATORS[args.framework]
    output = generator(endpoints)
    print(output)


if __name__ == "__main__":
    main()
