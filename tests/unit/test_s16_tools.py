"""
tests.unit.test_s16_tools
==========================
Sprint 16 Unit Test Suite: Tool Registry, Tool Executor, Schema Validation, Timeouts, & Retries.
"""

import time
import unittest
from app.agent.ai.executor import ToolExecutor
from app.agent.ai.models import ToolResult
from app.agent.ai.registry import ToolDefinition, ToolRegistry
from app.security import (
    AuditEventTypeEnum,
    AuthenticationService,
    PermissionEnum,
    RoleEnum,
    get_security_audit_logger,
)


class TestToolRegistryAndExecutor(unittest.TestCase):
    """Test suite for tool execution, permissions, input validation, and timeouts."""

    def test_default_tools_registration_and_metadata(self):
        registry = ToolRegistry()
        tools = registry.list_tools()
        self.assertGreaterEqual(len(tools), 10)

        val_tool = registry.get("validate_invoice")
        self.assertIsNotNone(val_tool)
        self.assertTrue(val_tool.read_only)
        self.assertEqual(val_tool.side_effect_type, "ANALYTICAL")
        self.assertIn(PermissionEnum.TOOL_EXECUTE, val_tool.required_permissions)

    def test_tool_execution_permission_enforcement(self):
        registry = ToolRegistry()
        executor = ToolExecutor(registry=registry)

        investigator = AuthenticationService.authenticate_api_key("key-investigator-123")
        auditor = AuthenticationService.authenticate_api_key("key-auditor-123")

        # Investigator with TOOL_EXECUTE -> SUCCESS
        res1 = executor.execute_tool("get_compliance_result", principal=investigator, invoice_no="INV-8000001")
        self.assertTrue(res1.success)

        # Auditor lacks TOOL_EXECUTE -> FAILS WITH PERMISSION ERROR
        res2 = executor.execute_tool("get_compliance_result", principal=auditor, invoice_no="INV-8000001")
        self.assertFalse(res2.success)
        self.assertIn("Permission denied", res2.errors[0])

    def test_tool_input_validation(self):
        registry = ToolRegistry()
        executor = ToolExecutor(registry=registry)
        investigator = AuthenticationService.authenticate_api_key("key-investigator-123")

        # Missing required field or invalid type
        res = executor.execute_tool("validate_invoice", principal=investigator, invoice_no=12345)
        self.assertFalse(res.success)
        err_msg = res.errors[0].lower()
        self.assertTrue("input validation failed" in err_msg or "expected string" in err_msg)

    def test_tool_timeout_handling(self):
        registry = ToolRegistry()

        def _slow_handler():
            time.sleep(2.0)
            return {"status": "ok"}

        slow_tool = ToolDefinition(
            name="slow_test_tool",
            description="Test tool that times out.",
            handler=_slow_handler,
            timeout_seconds=0.2,
            is_idempotent=False,
            max_retries=1,
            required_permissions=[PermissionEnum.TOOL_EXECUTE],
        )
        registry.register(slow_tool)

        executor = ToolExecutor(registry=registry)
        investigator = AuthenticationService.authenticate_api_key("key-investigator-123")

        res = executor.execute_tool("slow_test_tool", principal=investigator)
        self.assertFalse(res.success)
        self.assertIn("timed out", res.errors[0].lower())

        # Verify TIMEOUT audit event recorded
        audit_logger = get_security_audit_logger()
        events = audit_logger.get_events(event_type=AuditEventTypeEnum.TOOL_TIMEOUT)
        self.assertGreater(len(events), 0)
        self.assertEqual(events[-1].resource_id, "slow_test_tool")
