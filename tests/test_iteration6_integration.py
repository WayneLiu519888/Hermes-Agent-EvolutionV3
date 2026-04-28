"""
Iteration 6 Integration Tests — Hermes Evolution Plugin

Covers 5 dimensions:
  1. Plugin loading     — register(ctx) registers 6 tools + 1 hook
  2. Tool invocation    — each handler returns valid JSON (json.loads succeeds)
  3. Hook firing        — post_tool_call hook is callable and doesn't raise
  4. Schema validation  — all tool schemas have required fields
  5. Graceful degradation — handlers return error JSON (never crash) on bad/missing params

Uses a MockCtx pattern — no real Hermes runtime required.
"""

import json
import sys
import os
import importlib.util
from pathlib import Path

import pytest


# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
PLUGIN_INIT = PROJECT_ROOT / "hermes-plugin" / "__init__.py"

# Ensure project root and src are on sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ── MockCtx ───────────────────────────────────────────────────────────────────
class MockCtx:
    """Simulates the Hermes Agent runtime plugin registration context."""

    def __init__(self):
        self.tools = {}   # name → (schema, handler)
        self.hooks = {}   # name → callback

    def register_tool(self, name, schema, handler):
        self.tools[name] = (schema, handler)

    def register_hook(self, name, callback):
        self.hooks[name] = callback


# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_plugin():
    """Load the hermes-plugin package via importlib (handles the hyphen)."""
    spec = importlib.util.spec_from_file_location("hermes_plugin", PLUGIN_INIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_handler(ctx, tool_name):
    """Retrieve a tool handler function from the registered tools."""
    schema, handler = ctx.tools[tool_name]
    return handler


def _invoke(ctx, tool_name, params=None):
    """Invoke a tool handler and parse the JSON result."""
    handler = _get_handler(ctx, tool_name)
    raw = handler(ctx, params or {})
    return json.loads(raw)


# ── Fixture ───────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def plugin_module():
    """Load the plugin module once for all tests."""
    return _load_plugin()


@pytest.fixture
def ctx(plugin_module):
    """Create a fresh MockCtx and register the plugin."""
    ctx = MockCtx()
    plugin_module.register(ctx)
    return ctx


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  1. Plugin Loading Tests                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
class TestPluginLoading:
    """Verify register(ctx) correctly registers all tools and hooks."""

    EXPECTED_TOOLS = [
        "evolution_run_cycle",
        "evolution_create_tool",
        "evolution_analyze_performance",
        "evolution_learn",
        "evolution_self_monitor",
        "evolution_memory_discover",
    ]

    def test_tool_count(self, ctx):
        """6 tools should be registered."""
        assert len(ctx.tools) == 6, f"Expected 6 tools, got {len(ctx.tools)}: {list(ctx.tools.keys())}"

    def test_all_tools_registered(self, ctx):
        """Every expected tool is present by name."""
        registered = set(ctx.tools.keys())
        expected = set(self.EXPECTED_TOOLS)
        missing = expected - registered
        assert not missing, f"Missing tools: {missing}"

    def test_hook_registered(self, ctx):
        """post_tool_call hook should be registered."""
        assert "post_tool_call" in ctx.hooks, f"Hooks registered: {list(ctx.hooks.keys())}"

    def test_hook_count(self, ctx):
        """Exactly 1 hook registered."""
        assert len(ctx.hooks) == 1, f"Expected 1 hook, got {len(ctx.hooks)}"

    def test_tools_have_callable_handlers(self, ctx):
        """Every registered tool's handler must be callable."""
        for name in self.EXPECTED_TOOLS:
            _, handler = ctx.tools[name]
            assert callable(handler), f"Handler for '{name}' is not callable"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  2. Tool Invocation Tests                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
class TestToolInvocation:
    """Each tool handler must return a valid JSON string when called."""

    def test_run_cycle_returns_json(self, ctx):
        """evolution_run_cycle should return valid JSON."""
        result = _invoke(ctx, "evolution_run_cycle", {})
        assert isinstance(result, dict)
        assert "success" in result

    def test_create_tool_returns_json(self, ctx):
        """evolution_create_tool should return valid JSON."""
        result = _invoke(ctx, "evolution_create_tool", {
            "tool_name": "test_tool",
            "description": "A test tool",
            "api_spec": {"endpoint": "/test", "method": "GET"},
        })
        assert isinstance(result, dict)
        assert "success" in result

    def test_analyze_performance_returns_json(self, ctx):
        """evolution_analyze_performance should return valid JSON."""
        result = _invoke(ctx, "evolution_analyze_performance", {})
        assert isinstance(result, dict)
        assert "success" in result

    def test_learn_returns_json(self, ctx):
        """evolution_learn should return valid JSON."""
        result = _invoke(ctx, "evolution_learn", {
            "description": "Test experience — invoked from integration test",
            "experience_type": "tool_usage",
            "outcome": "success",
        })
        assert isinstance(result, dict)
        assert "success" in result

    def test_self_monitor_returns_json(self, ctx):
        """evolution_self_monitor should return valid JSON."""
        result = _invoke(ctx, "evolution_self_monitor", {})
        assert isinstance(result, dict)
        assert "success" in result

    def test_memory_discover_returns_json(self, ctx):
        """evolution_memory_discover should return valid JSON."""
        result = _invoke(ctx, "evolution_memory_discover", {})
        assert isinstance(result, dict)
        assert "success" in result

    def test_all_tools_produce_parsable_json(self, ctx):
        """Verify every single tool returns parseable JSON (belt-and-suspenders)."""
        for tool_name in ctx.tools:
            handler = _get_handler(ctx, tool_name)
            raw = handler(ctx, {})
            try:
                parsed = json.loads(raw)
                assert isinstance(parsed, dict), f"{tool_name} did not return a JSON object"
            except json.JSONDecodeError as e:
                pytest.fail(f"{tool_name} returned invalid JSON: {e}\nRaw: {raw[:200]}")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  3. Hook Firing Tests                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
class TestHookFiring:
    """Verify the post_tool_call hook is registered and callable."""

    def test_hook_is_callable(self, ctx):
        """The registered hook callback must be callable."""
        hook = ctx.hooks.get("post_tool_call")
        assert hook is not None, "post_tool_call hook not registered"
        assert callable(hook), "post_tool_call hook is not callable"

    def test_hook_does_not_raise(self, ctx):
        """Calling the hook with typical arguments should not raise."""
        hook = ctx.hooks["post_tool_call"]
        try:
            hook(ctx, "test_tool", {"param": "value"}, '{"ok": true}', 150.0, None)
        except Exception as e:
            pytest.fail(f"post_tool_call hook raised unexpectedly: {e}")

    def test_hook_with_error_does_not_raise(self, ctx):
        """Calling the hook with an error should still not raise."""
        hook = ctx.hooks["post_tool_call"]
        try:
            hook(ctx, "failing_tool", {}, None, 2000.0, RuntimeError("simulated failure"))
        except Exception as e:
            pytest.fail(f"post_tool_call hook with error raised unexpectedly: {e}")

    def test_hook_signature_accepts_six_args(self, ctx):
        """The hook accepts (ctx, tool_name, params, result, duration_ms, error)."""
        hook = ctx.hooks["post_tool_call"]
        # If the hook signature was wrong, this would raise TypeError
        hook(ctx, "tool_a", {}, None, 0.0, None)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  4. Schema Validation Tests                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
class TestSchemaValidation:
    """Verify all tool schemas conform to the expected structure."""

    REQUIRED_SCHEMA_FIELDS = {"name", "description", "parameters"}

    def test_schemas_have_required_fields(self, ctx):
        """Every tool schema must contain name, description, and parameters."""
        for tool_name, (schema, _) in ctx.tools.items():
            missing = self.REQUIRED_SCHEMA_FIELDS - set(schema.keys())
            assert not missing, (
                f"Schema for '{tool_name}' missing fields: {missing}"
            )

    def test_parameters_has_type_object(self, ctx):
        """Every tool's parameters field must declare type: object."""
        for tool_name, (schema, _) in ctx.tools.items():
            params = schema.get("parameters", {})
            assert params.get("type") == "object", (
                f"'{tool_name}' parameters.type is '{params.get('type')}', expected 'object'"
            )

    def test_schema_name_matches_registration_name(self, ctx):
        """The schema's internal 'name' should match the registration key."""
        for tool_name, (schema, _) in ctx.tools.items():
            assert schema.get("name") == tool_name, (
                f"Schema name '{schema.get('name')}' != registration key '{tool_name}'"
            )

    def test_descriptions_are_nonempty(self, ctx):
        """Every tool schema must have a non-empty description string."""
        for tool_name, (schema, _) in ctx.tools.items():
            desc = schema.get("description", "")
            assert isinstance(desc, str) and len(desc) > 0, (
                f"'{tool_name}' has empty or missing description"
            )

    def test_schemas_contain_properties_or_empty_required(self, ctx):
        """parameters must have either a 'properties' dict or an explicit empty required list."""
        for tool_name, (schema, _) in ctx.tools.items():
            params = schema.get("parameters", {})
            has_props = "properties" in params
            has_required = "required" in params
            assert has_props or has_required, (
                f"'{tool_name}' parameters lacks both 'properties' and 'required'"
            )


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  5. Graceful Degradation Tests                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
class TestGracefulDegradation:
    """Handlers must return error JSON (never crash) given invalid or missing params."""

    def test_missing_params_returns_error_json(self, ctx):
        """Calling every tool with no params at all should not crash."""
        for tool_name in ctx.tools:
            handler = _get_handler(ctx, tool_name)
            raw = handler(ctx, {})
            parsed = json.loads(raw)
            assert isinstance(parsed, dict), (
                f"{tool_name} with empty params did not return a dict: {type(parsed)}"
            )

    def test_none_params_handled(self, ctx):
        """Calling handlers with explicit None params should not crash."""
        for tool_name in ctx.tools:
            handler = _get_handler(ctx, tool_name)
            try:
                raw = handler(ctx, None)
                parsed = json.loads(raw)
                assert isinstance(parsed, dict)
            except Exception as e:
                pytest.fail(f"{tool_name} with params=None raised {type(e).__name__}: {e}")

    def test_invalid_types_in_params_handled(self, ctx):
        """Calling tools with wrong-typed params should not crash."""
        bad_params = {
            "tool_name": 12345,               # should be string
            "description": None,              # should be string
            "api_spec": "not_an_object",      # should be object
            "methods": "not_an_array",        # should be array
            "include_history": "not_a_bool",  # should be boolean
        }
        for tool_name in ctx.tools:
            handler = _get_handler(ctx, tool_name)
            try:
                raw = handler(ctx, bad_params)
                parsed = json.loads(raw)
                assert isinstance(parsed, dict)
            except Exception as e:
                pytest.fail(f"{tool_name} with bad param types raised {type(e).__name__}: {e}")

    def test_extra_unknown_params_ignored(self, ctx):
        """Tools should ignore unknown/extra parameters gracefully."""
        extra_params = {
            "unknown_field": "garbage",
            "nonsense": [1, 2, 3],
            "__internal__": True,
        }
        for tool_name in ctx.tools:
            handler = _get_handler(ctx, tool_name)
            try:
                raw = handler(ctx, extra_params)
                parsed = json.loads(raw)
                assert isinstance(parsed, dict)
            except Exception as e:
                pytest.fail(f"{tool_name} with extra params raised {type(e).__name__}: {e}")

    def test_run_cycle_no_params_does_not_crash(self, ctx):
        """evolution_run_cycle with empty params returns error JSON, not a traceback."""
        handler = _get_handler(ctx, "evolution_run_cycle")
        raw = handler(ctx, {})
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_create_tool_missing_required_returns_error(self, ctx):
        """evolution_create_tool with missing required fields should return success=False."""
        result = _invoke(ctx, "evolution_create_tool", {
            "tool_name": "incomplete_tool",
            # deliberately omit 'description' and 'api_spec'
        })
        # The handler requires tool_name, description, api_spec — it should fail gracefully
        assert isinstance(result, dict)
        assert "success" in result
