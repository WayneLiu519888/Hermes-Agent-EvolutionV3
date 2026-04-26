"""
权限控制系统 - Hermes Agent Evolution 安全增强模块

基于角色的访问控制 (RBAC)，支持：
- 四级角色: ADMIN/DEVELOPER/OPERATOR/VIEWER
- 权限继承链: ADMIN > DEVELOPER > OPERATOR > VIEWER
- 五种操作类型: READ/WRITE/EXECUTE/DELETE/CONFIGURE
- Agent级权限检查
- 与AuditLogger集成记录权限变更
"""

import logging
from enum import Enum
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================
# 枚举定义
# ============================================================

class Operation(str, Enum):
    """操作类型"""
    READ = "READ"            # 读取数据
    WRITE = "WRITE"          # 写入数据
    EXECUTE = "EXECUTE"      # 执行代码/工具
    DELETE = "DELETE"        # 删除资源
    CONFIGURE = "CONFIGURE"  # 配置系统


class Role(str, Enum):
    """角色定义"""
    ADMIN = "ADMIN"          # 管理员 — 所有权限
    DEVELOPER = "DEVELOPER"  # 开发者 — 读写执行配置
    OPERATOR = "OPERATOR"    # 操作员 — 读写执行
    VIEWER = "VIEWER"        # 观察者 — 只读

    @classmethod
    def from_string(cls, s: str) -> "Role":
        try:
            return cls(s.upper())
        except ValueError:
            return cls.VIEWER  # 默认最低权限


# ============================================================
# 数据类
# ============================================================

@dataclass
class AgentPermission:
    """Agent权限配置"""
    agent_id: str
    role: Role = Role.VIEWER
    allowed_operations: Optional[Set[Operation]] = None
    allowed_resources: Optional[Set[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.allowed_operations is None:
            self.allowed_operations = set()
        if self.allowed_resources is None:
            self.allowed_resources = set()


@dataclass
class PermissionCheckResult:
    """权限检查结果"""
    agent_id: str
    action: str
    operation: Operation
    resource: str
    allowed: bool
    role: Role
    reason: str = ""


# ============================================================
# 权限矩阵定义
# ============================================================

# 每个角色默认拥有的操作权限
# 高等级角色通过继承自动获得低等级角色的所有权限
_ROLE_BASE_PERMISSIONS: Dict[Role, Set[Operation]] = {
    Role.VIEWER: {
        Operation.READ,
    },
    Role.OPERATOR: {
        Operation.WRITE,
        Operation.EXECUTE,
    },
    Role.DEVELOPER: {
        Operation.DELETE,
        Operation.CONFIGURE,
    },
    Role.ADMIN: set(),  # ADMIN通过继承获得所有，额外无限制
}

# 角色优先级（用于权限继承判断）
_ROLE_HIERARCHY: Dict[Role, int] = {
    Role.VIEWER: 0,
    Role.OPERATOR: 1,
    Role.DEVELOPER: 2,
    Role.ADMIN: 3,
}


def _get_effective_permissions(role: Role) -> Set[Operation]:
    """获取角色的有效权限（包含继承）

    继承链: ADMIN(3) → DEVELOPER(2) → OPERATOR(1) → VIEWER(0)
    """
    effective = set()
    role_level = _ROLE_HIERARCHY.get(role, 0)
    for r, level in _ROLE_HIERARCHY.items():
        if level <= role_level:
            effective.update(_ROLE_BASE_PERMISSIONS.get(r, set()))
    return effective


# ============================================================
# PermissionManager 主类
# ============================================================

class PermissionManager:
    """权限管理器

    管理Agent的角色和权限，执行权限检查。
    支持与AuditLogger集成记录权限相关事件。
    """

    # 系统保留资源前缀
    SYSTEM_RESOURCES_PREFIXES = ("system.", "internal.", "admin.")

    def __init__(self, audit_logger=None):
        """初始化权限管理器

        Args:
            audit_logger: 可选AuditLogger实例，用于记录权限变更
        """
        self.audit_logger = audit_logger
        # agent_id → AgentPermission
        self._agent_permissions: Dict[str, AgentPermission] = {}
        # 全局资源所有权: resource → owner_agent_id
        self._resource_ownership: Dict[str, str] = {}

    # ---- Role管理 ----

    def assign_role(self, agent_id: str, role: Role, metadata: Dict[str, Any] = None) -> AgentPermission:
        """为Agent分配角色

        Args:
            agent_id: Agent标识
            role: 角色
            metadata: 附加元数据

        Returns:
            AgentPermission: 更新后的权限配置
        """
        role_obj = role if isinstance(role, Role) else Role.from_string(str(role))
        if agent_id in self._agent_permissions:
            perm = self._agent_permissions[agent_id]
            old_role = perm.role
            perm.role = role_obj
            if metadata:
                perm.metadata.update(metadata)
        else:
            perm = AgentPermission(agent_id=agent_id, role=role_obj, metadata=metadata or {})
            self._agent_permissions[agent_id] = perm

        # 审计记录
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type="SYSTEM_CONFIG",
                level="INFO",
                agent_id="permission_manager",
                action="assign_role",
                description=f"Role assigned: {agent_id} → {role_obj.value}",
                details={
                    "agent_id": agent_id,
                    "role": role_obj.value,
                    "previous_role": old_role.value if 'old_role' in dir() else "NEW",
                    "metadata": metadata or {},
                },
                source_module="permission_manager",
            )

        logger.info("角色分配: agent=%s, role=%s", agent_id, role_obj.value)
        return perm

    def get_role(self, agent_id: str) -> Role:
        """获取Agent的当前角色"""
        perm = self._agent_permissions.get(agent_id)
        return perm.role if perm else Role.VIEWER

    def remove_agent(self, agent_id: str) -> bool:
        """移除Agent的权限配置"""
        if agent_id in self._agent_permissions:
            del self._agent_permissions[agent_id]
            # 同时移除资源所有权
            resources_to_remove = [
                r for r, owner in self._resource_ownership.items() if owner == agent_id
            ]
            for r in resources_to_remove:
                del self._resource_ownership[r]

            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="SYSTEM_CONFIG",
                    level="WARNING",
                    agent_id="permission_manager",
                    action="remove_agent",
                    description=f"Agent permissions removed: {agent_id}",
                    source_module="permission_manager",
                )
            return True
        return False

    # ---- 权限检查 ----

    def check_permission(
        self,
        agent_id: str,
        action: str,
        resource: str = "",
        operation: Optional[Operation] = None,
    ) -> PermissionCheckResult:
        """检查Agent是否有权限执行指定操作

        Args:
            agent_id: Agent标识
            action: 操作名称 (如 "read_config", "execute_tool")
            operation: 操作类型枚举，如未提供则从action推断
            resource: 目标资源标识

        Returns:
            PermissionCheckResult: 检查结果
        """
        # 获取Agent角色
        perm = self._agent_permissions.get(agent_id)
        role = perm.role if perm else Role.VIEWER

        # 推断操作类型
        if operation is None:
            operation = self._infer_operation(action)

        # ADMIN拥有所有权限（无限制）
        if role == Role.ADMIN:
            return PermissionCheckResult(
                agent_id=agent_id,
                action=action,
                operation=operation,
                resource=resource,
                allowed=True,
                role=role,
                reason="ADMIN has unrestricted access",
            )

        # 检查系统资源保护
        if self._is_system_resource(resource) and role != Role.ADMIN:
            return PermissionCheckResult(
                agent_id=agent_id,
                action=action,
                operation=operation,
                resource=resource,
                allowed=False,
                role=role,
                reason=f"System resource '{resource}' requires ADMIN role",
            )

        # 检查资源所有权
        if resource and resource in self._resource_ownership:
            owner = self._resource_ownership[resource]
            if owner != agent_id and role not in (Role.ADMIN, Role.DEVELOPER):
                return PermissionCheckResult(
                    agent_id=agent_id,
                    action=action,
                    operation=operation,
                    resource=resource,
                    allowed=False,
                    role=role,
                    reason=f"Resource '{resource}' is owned by '{owner}'",
                )

        # 获取有效权限集
        effective_permissions = _get_effective_permissions(role)

        # 检查Agent特定的额外权限或限制
        if perm and perm.allowed_operations:
            # 如果在白名单中显式添加
            if operation in perm.allowed_operations:
                allowed = True
            else:
                allowed = operation in effective_permissions
        else:
            allowed = operation in effective_permissions

        # 资源白名单检查
        if allowed and resource and perm and perm.allowed_resources:
            if resource not in perm.allowed_resources and "*" not in perm.allowed_resources:
                allowed = False

        reason = f"Role {role.value} {'has' if allowed else 'does not have'} {operation.value} permission"
        if not allowed and resource:
            reason += f" for '{resource}'"

        # 记录审计日志（拒绝时记录WARNING）
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type="AGENT_ACTION",
                level="WARNING" if not allowed else "INFO",
                agent_id=agent_id,
                action=f"permission_check:{action}",
                description=f"Permission {'denied' if not allowed else 'granted'} for {action}",
                details={
                    "operation": operation.value,
                    "resource": resource,
                    "role": role.value,
                    "allowed": allowed,
                    "reason": reason,
                },
                source_module="permission_manager",
                outcome="failure" if not allowed else "success",
            )

        return PermissionCheckResult(
            agent_id=agent_id,
            action=action,
            operation=operation,
            resource=resource,
            allowed=allowed,
            role=role,
            reason=reason,
        )

    def check_permission_simple(self, agent_id: str, action: str) -> bool:
        """简化权限检查 — 仅返回bool"""
        result = self.check_permission(agent_id, action)
        return result.allowed

    def check_batch(
        self, agent_id: str, actions: List[Dict[str, str]]
    ) -> List[PermissionCheckResult]:
        """批量权限检查"""
        results = []
        for act in actions:
            results.append(
                self.check_permission(
                    agent_id=agent_id,
                    action=act.get("action", ""),
                    resource=act.get("resource", ""),
                    operation=Operation(act["operation"]) if "operation" in act else None,
                )
            )
        return results

    # ---- 资源所有权管理 ----

    def register_resource(self, resource: str, owner_agent_id: str) -> bool:
        """注册资源所有权

        Returns:
            bool: 成功返回True
        """
        if self._is_system_resource(resource):
            logger.warning("无法注册系统保留资源: %s", resource)
            return False
        self._resource_ownership[resource] = owner_agent_id
        return True

    def get_resource_owner(self, resource: str) -> Optional[str]:
        """获取资源所有者"""
        return self._resource_ownership.get(resource)

    def transfer_resource(self, resource: str, new_owner: str) -> bool:
        """转移资源所有权"""
        if self._is_system_resource(resource):
            return False
        old_owner = self._resource_ownership.get(resource)
        self._resource_ownership[resource] = new_owner

        if self.audit_logger and old_owner:
            self.audit_logger.log_event(
                event_type="SYSTEM_CONFIG",
                level="INFO",
                agent_id="permission_manager",
                action="transfer_resource",
                description=f"Resource '{resource}' transferred from '{old_owner}' to '{new_owner}'",
                source_module="permission_manager",
            )
        return True

    # ---- 辅助方法 ----

    def _infer_operation(self, action: str) -> Operation:
        """从action名称推断操作类型"""
        action_lower = action.lower()
        if any(kw in action_lower for kw in ("config", "configure", "setup", "settings")):
            return Operation.CONFIGURE
        if any(kw in action_lower for kw in ("delete", "remove", "destroy", "purge")):
            return Operation.DELETE
        if any(kw in action_lower for kw in ("exec", "run", "invoke", "call", "apply")):
            return Operation.EXECUTE
        if any(kw in action_lower for kw in ("write", "create", "save", "update", "modify", "set")):
            return Operation.WRITE
        return Operation.READ

    def _is_system_resource(self, resource: str) -> bool:
        """判断是否为系统保留资源"""
        if not resource:
            return False
        return any(resource.startswith(prefix) for prefix in self.SYSTEM_RESOURCES_PREFIXES)

    # ---- 查询方法 ----

    def get_agent_permission(self, agent_id: str) -> Optional[AgentPermission]:
        """获取Agent的完整权限配置"""
        return self._agent_permissions.get(agent_id)

    def list_agents(self) -> Dict[str, Role]:
        """列出所有已配置Agent及其角色"""
        return {aid: perm.role for aid, perm in self._agent_permissions.items()}

    def get_effective_permissions(self, agent_id: str) -> Set[Operation]:
        """获取Agent的有效权限集（含继承）"""
        role = self.get_role(agent_id)
        return _get_effective_permissions(role)

    def list_resources(self) -> Dict[str, str]:
        """列出所有已注册资源及其所有者"""
        return dict(self._resource_ownership)

    def __repr__(self) -> str:
        return f"PermissionManager(agents={len(self._agent_permissions)}, resources={len(self._resource_ownership)})"
