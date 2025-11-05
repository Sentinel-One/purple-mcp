"""OpenAI Function Schema Generation Utility.

This module provides utilities for generating OpenAI-compatible function schemas
from Python functions. It handles type introspection, Optional type detection,
and schema validation to ensure compatibility with OpenAI's function calling API.

Key Components:
    - OpenAISchemaGenerator: Main class for schema generation and validation
    - Type introspection utilities for handling Optional types and unions
    - Schema validation for OpenAI compatibility requirements
    - JSON schema type mapping for Python types

Usage:
    ```python
    from purple_mcp.openai_schema import OpenAISchemaGenerator

    generator = OpenAISchemaGenerator()
    schema = generator.generate_schema(my_function)
    errors = generator.validate_schema(schema, "my_function")
    ```

Security:
    This module only performs type introspection and schema generation.
    It does not execute any user code or perform unsafe operations.
"""

import inspect
from typing import Optional, Protocol, get_args, get_origin


class MCPToolFunction(Protocol):
    """Protocol for MCP tool functions."""

    def __call__(
        self, *args: str | int | float | bool | None, **kwargs: str | int | float | bool | None
    ) -> str:
        """Call the tool function."""
        ...


# Schema-specific type definitions for OpenAI compatibility
SchemaValue = str | int | float | bool | None
ParameterSchema = dict[str, SchemaValue]
PropertiesDict = dict[str, ParameterSchema]
ParametersSchema = dict[str, PropertiesDict | list[str] | str | bool]
OpenAIFunctionSchema = dict[str, str | ParametersSchema]


class OpenAISchemaGenerator:
    """Generator for OpenAI-compatible function schemas.

    This class provides methods to generate and validate OpenAI function schemas
    from Python functions using type introspection and annotation analysis.
    """

    def generate_schema(self, func: MCPToolFunction) -> OpenAIFunctionSchema:
        """Generate OpenAI-compatible schema from a function signature.

        Args:
            func: The function to generate schema for

        Returns:
            Dict containing OpenAI-compatible function schema with name, description, and parameters

        Example:
            ```python
            def example_func(query: str, limit: Optional[int] = 10) -> str:
                '''Example function.'''
                pass


            generator = OpenAISchemaGenerator()
            schema = generator.generate_schema(example_func)
            # Returns: {
            #     "name": "example_func",
            #     "description": "Example function.",
            #     "parameters": {
            #         "type": "object",
            #         "properties": {
            #             "query": {"type": "string", "description": "Parameter query"},
            #             "limit": {"type": "integer", "description": "Parameter limit", "default": 10}
            #         },
            #         "required": ["query"],
            #         "additionalProperties": False
            #     }
            # }
            ```
        """
        sig = inspect.signature(func)
        properties: PropertiesDict = {}
        required: list[str] = []

        parameters: ParametersSchema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue

            param_type = param.annotation
            is_optional = self._is_optional_type(param_type)
            actual_type = self._extract_actual_type(param_type, is_optional)
            json_type = self._get_json_type(actual_type)

            param_schema: ParameterSchema = {
                "type": json_type,
                "description": f"Parameter {param_name}",
            }

            if param.default is not param.empty:
                param_schema["default"] = param.default

            properties[param_name] = param_schema

            if not is_optional and param.default is param.empty:
                required.append(param_name)

        func_doc = getattr(func, "__doc__", None)
        func_name = getattr(func, "__name__", "unknown")
        description = func_doc.split("\n")[0] if func_doc else f"Function {func_name}"

        return {
            "name": func_name,
            "description": description.strip(),
            "parameters": parameters,
        }

    def validate_schema(self, schema: OpenAIFunctionSchema, func_name: str) -> list[str]:
        """Validate that a function schema meets OpenAI requirements.

        Args:
            schema: The schema to validate
            func_name: Name of the function for error reporting

        Returns:
            List of validation error messages (empty if valid)

        Example:
            ```python
            generator = OpenAISchemaGenerator()
            schema = {"name": "test", "parameters": {}}  # Invalid schema
            errors = generator.validate_schema(schema, "test_func")
            # Returns: ["test_func: Missing required field 'description'", ...]
            ```
        """
        errors: list[str] = []

        errors.extend(self._validate_required_fields(schema, func_name))
        errors.extend(self._validate_parameters_section(schema, func_name))

        return errors

    def validate_search_alerts_filters(self, schema: OpenAIFunctionSchema) -> list[str]:
        """Check that search_alerts filters parameter is optional.

        Args:
            schema: The schema to check

        Returns:
            List of validation error messages for filters parameter
        """
        errors: list[str] = []

        parameters = schema.get("parameters")
        if not isinstance(parameters, dict):
            return errors

        properties = parameters.get("properties")
        required = parameters.get("required")

        if (
            isinstance(properties, dict)
            and isinstance(required, list)
            and "filters" in properties
            and "filters" in required
        ):
            errors.append("search_alerts: 'filters' parameter should not be required")

        return errors

    def _is_optional_type(self, param_type: type) -> bool:
        """Determine whether a type annotation represents an optional parameter.

        Checks if the type is Optional[T] or a Union containing NoneType,
        indicating that the parameter can accept None as a value.

        Args:
            param_type: Type annotation to analyze

        Returns:
            True if the type accepts None, False otherwise
        """
        return get_origin(param_type) is Optional or (
            hasattr(param_type, "__args__") and type(None) in param_type.__args__
        )

    def _extract_actual_type(self, param_type: type, is_optional: bool) -> type:
        """Extract the underlying non-None type from an optional type annotation.

        Unwraps Optional[T] or Union[T, None] type annotations to retrieve
        the actual type T, which is needed for JSON schema type mapping.

        Args:
            param_type: Type annotation to unwrap
            is_optional: Whether the type is optional (pre-computed for efficiency)

        Returns:
            The underlying non-None type, or str as a safe default
        """
        if is_optional:
            if get_origin(param_type) is Optional:
                args = get_args(param_type)
                return args[0] if args else str
            else:
                args = get_args(param_type)
                non_none_args = [arg for arg in args if arg is not type(None)]
                return non_none_args[0] if non_none_args else str
        return param_type

    def _get_json_type(self, actual_type: type) -> str:
        """Convert Python type to JSON schema type.

        Args:
            actual_type: The Python type to convert

        Returns:
            JSON schema type string
        """
        type_mapping: dict[type, str] = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        # Use isinstance to check for type compatibility
        for python_type, json_type in type_mapping.items():
            if actual_type is python_type:
                return json_type
        return "string"

    def _validate_required_fields(self, schema: OpenAIFunctionSchema, func_name: str) -> list[str]:
        """Ensure schema contains all required top-level fields.

        Verifies presence of 'name', 'description', and 'parameters' fields
        required by the OpenAI function calling specification.

        Args:
            schema: Schema dictionary to validate
            func_name: Function name for error message context

        Returns:
            List of error messages for missing required fields
        """
        errors: list[str] = []
        required_fields = ["name", "description", "parameters"]
        for field in required_fields:
            if field not in schema:
                errors.append(f"{func_name}: Missing required field '{field}'")
        return errors

    def _validate_parameters_section(
        self, schema: OpenAIFunctionSchema, func_name: str
    ) -> list[str]:
        """Validate the parameters section of the schema.

        Args:
            schema: The schema to validate
            func_name: Function name for error reporting

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        if "parameters" not in schema:
            return errors

        params = schema.get("parameters")
        if not isinstance(params, dict):
            return errors

        errors.extend(self._validate_parameters_structure(params, func_name))
        errors.extend(self._validate_parameter_defaults(params, func_name))

        return errors

    def _validate_parameters_structure(
        self, params: ParametersSchema, func_name: str
    ) -> list[str]:
        """Validate the basic structure of parameters.

        Args:
            params: The parameters section to validate
            func_name: Function name for error reporting

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        if params.get("type") != "object":
            errors.append(f"{func_name}: Parameters 'type' must be 'object'")

        if "properties" not in params:
            errors.append(f"{func_name}: Parameters must have 'properties' field")

        return errors

    def _validate_parameter_defaults(self, params: ParametersSchema, func_name: str) -> list[str]:
        """Validate that parameters with defaults are not marked as required.

        Args:
            params: The parameters section to validate
            func_name: Function name for error reporting

        Returns:
            List of validation errors
        """
        errors: list[str] = []

        if "properties" not in params or "required" not in params:
            return errors

        properties = params.get("properties")
        required = params.get("required")

        if not isinstance(properties, dict) or not isinstance(required, list):
            return errors

        for param_name, param_schema in properties.items():
            if (
                isinstance(param_schema, dict)
                and "default" in param_schema
                and param_name in required
            ):
                errors.append(
                    f"{func_name}: Parameter '{param_name}' has a default value but is marked as required"
                )

        return errors


class OpenAIToolExtractor:
    """Utility for extracting functions from various tool formats.

    This class handles the extraction of callable functions from different
    wrapper formats used by MCP frameworks and testing environments.
    """

    def extract_function_from_tool(self, tool: MCPToolFunction) -> MCPToolFunction | None:
        """Extract the actual function from a tool wrapper.

        Args:
            tool: The tool object to extract function from

        Returns:
            The extracted callable function, or None if not found

        Example:
            ```python
            extractor = OpenAIToolExtractor()
            func = extractor.extract_function_from_tool(wrapped_tool)
            if func:
                # Use the extracted function
                pass
            ```
        """
        if hasattr(tool, "fn"):
            fn = tool.fn
            return fn if callable(fn) else None
        elif hasattr(tool, "__wrapped__"):
            wrapped = tool.__wrapped__
            return wrapped if callable(wrapped) else None
        elif callable(tool):
            return tool
        return None
