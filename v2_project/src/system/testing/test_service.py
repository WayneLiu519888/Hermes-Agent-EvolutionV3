"""
测试框架模块 - 自动化测试、性能测试、集成测试
支持单元测试、集成测试、端到端测试、性能基准测试
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
import inspect
import json
from datetime import datetime
import statistics
import traceback
import sys

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """测试状态"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class TestType(Enum):
    """测试类型"""
    UNIT = "unit"          # 单元测试
    INTEGRATION = "integration"  # 集成测试
    E2E = "e2e"           # 端到端测试
    PERFORMANCE = "performance"  # 性能测试
    SECURITY = "security"  # 安全测试


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    test_type: TestType
    status: TestStatus
    duration: float  # 秒
    start_time: datetime
    end_time: datetime
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "test_type": self.test_type.value,
            "status": self.status.value,
            "duration": self.duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "assertions": self.assertions,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
            "metrics": self.metrics,
            "metadata": self.metadata
        }


@dataclass
class TestSuiteResult:
    """测试套件结果"""
    suite_id: str
    suite_name: str
    start_time: datetime
    end_time: datetime
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    timeout_tests: int
    test_results: List[TestResult]
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "suite_id": self.suite_id,
            "suite_name": self.suite_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "error_tests": self.error_tests,
            "timeout_tests": self.timeout_tests,
            "test_results": [r.to_dict() for r in self.test_results],
            "duration": self.duration,
            "metadata": self.metadata
        }


class TestCase:
    """测试用例基类"""
    
    def __init__(self, name: str = None, test_type: TestType = TestType.UNIT):
        self.name = name or self.__class__.__name__
        self.test_type = test_type
        self.setup_called = False
        self.teardown_called = False
        self.assertions = []
        
    async def setup(self) -> None:
        """测试前置设置"""
        pass
    
    async def run_test(self) -> None:
        """运行测试"""
        raise NotImplementedError("子类必须实现 run_test 方法")
    
    async def teardown(self) -> None:
        """测试后置清理"""
        pass
    
    def assert_true(self, condition: bool, message: str = None) -> None:
        """断言为真"""
        self.assertions.append({
            "type": "assert_true",
            "condition": condition,
            "message": message,
            "passed": condition
        })
        
        if not condition:
            raise AssertionError(message or "条件不为真")
    
    def assert_false(self, condition: bool, message: str = None) -> None:
        """断言为假"""
        self.assertions.append({
            "type": "assert_false",
            "condition": condition,
            "message": message,
            "passed": not condition
        })
        
        if condition:
            raise AssertionError(message or "条件不为假")
    
    def assert_equal(self, actual, expected, message: str = None) -> None:
        """断言相等"""
        passed = actual == expected
        self.assertions.append({
            "type": "assert_equal",
            "actual": str(actual),
            "expected": str(expected),
            "message": message,
            "passed": passed
        })
        
        if not passed:
            raise AssertionError(message or f"期望 {expected}，实际 {actual}")
    
    def assert_not_equal(self, actual, expected, message: str = None) -> None:
        """断言不相等"""
        passed = actual != expected
        self.assertions.append({
            "type": "assert_not_equal",
            "actual": str(actual),
            "expected": str(expected),
            "message": message,
            "passed": passed
        })
        
        if not passed:
            raise AssertionError(message or f"期望不等于 {expected}，实际 {actual}")
    
    def assert_in(self, item, container, message: str = None) -> None:
        """断言包含"""
        passed = item in container
        self.assertions.append({
            "type": "assert_in",
            "item": str(item),
            "container": str(container),
            "message": message,
            "passed": passed
        })
        
        if not passed:
            raise AssertionError(message or f"{item} 不在 {container} 中")
    
    def assert_not_in(self, item, container, message: str = None) -> None:
        """断言不包含"""
        passed = item not in container
        self.assertions.append({
            "type": "assert_not_in",
            "item": str(item),
            "container": str(container),
            "message": message,
            "passed": passed
        })
        
        if not passed:
            raise AssertionError(message or f"{item} 在 {container} 中")
    
    def assert_is_none(self, value, message: str = None) -> None:
        """断言为None"""
        passed = value is None
        self.assertions.append({
            "type": "assert_is_none",
            "value": str(value),
            "message": message,
            "passed": passed
        })
        
        if not passed:
            raise AssertionError(message or f"期望 None，实际 {value}")
    
    def assert_is_not_none(self, value, message: str = None) -> None:
        """断言不为None"""
        passed = value is not None
        self.assertions.append({
            "type": "assert_is_not_none",
            "value": str(value),
            "message": message,
            "passed": passed
        })
        
        if not passed:
            raise AssertionError(message or "值为 None")
    
    def assert_raises(self, exception_type, func, *args, **kwargs) -> None:
        """断言抛出异常"""
        try:
            func(*args, **kwargs)
            passed = False
            error = None
        except exception_type as e:
            passed = True
            error = str(e)
        except Exception as e:
            passed = False
            error = str(e)
        
        self.assertions.append({
            "type": "assert_raises",
            "exception_type": exception_type.__name__,
            "function": func.__name__,
            "message": f"期望抛出 {exception_type.__name__}",
            "passed": passed,
            "error": error
        })
        
        if not passed:
            raise AssertionError(f"期望抛出 {exception_type.__name__}，实际 {error}")


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.test_cases: List[Type[TestCase]] = []
        self.test_results: List[TestResult] = []
        self.timeout_seconds = 30  # 默认超时时间
        
        logger.info("测试运行器初始化完成")
    
    def register_test_case(self, test_case_class: Type[TestCase]) -> None:
        """注册测试用例"""
        self.test_cases.append(test_case_class)
        logger.debug(f"测试用例已注册: {test_case_class.__name__}")
    
    def register_test_cases(self, test_case_classes: List[Type[TestCase]]) -> None:
        """批量注册测试用例"""
        for test_case_class in test_case_classes:
            self.register_test_case(test_case_class)
    
    async def run_test_case(
        self,
        test_case_class: Type[TestCase],
        test_id: str = None
    ) -> TestResult:
        """运行单个测试用例"""
        import uuid
        
        test_id = test_id or str(uuid.uuid4())
        test_instance = test_case_class()
        
        start_time = datetime.now()
        status = TestStatus.PASSED
        error_message = None
        error_traceback = None
        metrics = {}
        
        try:
            # 执行前置设置
            logger.debug(f"执行测试前置设置: {test_instance.name}")
            await test_instance.setup()
            test_instance.setup_called = True
            
            # 执行测试
            logger.debug(f"执行测试: {test_instance.name}")
            await asyncio.wait_for(
                test_instance.run_test(),
                timeout=self.timeout_seconds
            )
            
        except asyncio.TimeoutError:
            status = TestStatus.TIMEOUT
            error_message = f"测试超时 ({self.timeout_seconds}秒)"
            logger.error(f"测试超时: {test_instance.name}")
            
        except AssertionError as e:
            status = TestStatus.FAILED
            error_message = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"测试断言失败: {test_instance.name} - {error_message}")
            
        except Exception as e:
            status = TestStatus.ERROR
            error_message = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"测试执行错误: {test_instance.name} - {error_message}")
            
        finally:
            # 执行后置清理
            try:
                if test_instance.setup_called and not test_instance.teardown_called:
                    logger.debug(f"执行测试后置清理: {test_instance.name}")
                    await test_instance.teardown()
                    test_instance.teardown_called = True
            except Exception as e:
                logger.error(f"测试后置清理失败: {test_instance.name} - {str(e)}")
                if status == TestStatus.PASSED:
                    status = TestStatus.ERROR
                    error_message = f"后置清理失败: {str(e)}"
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 创建测试结果
        result = TestResult(
            test_id=test_id,
            test_name=test_instance.name,
            test_type=test_instance.test_type,
            status=status,
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            assertions=test_instance.assertions,
            error_message=error_message,
            error_traceback=error_traceback,
            metrics=metrics,
            metadata={
                "timeout_seconds": self.timeout_seconds,
                "class_name": test_case_class.__name__
            }
        )
        
        self.test_results.append(result)
        return result
    
    async def run_test_suite(
        self,
        suite_name: str = "default_suite",
        test_filter: Callable[[Type[TestCase]], bool] = None
    ) -> TestSuiteResult:
        """运行测试套件"""
        import uuid
        
        suite_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # 过滤测试用例
        test_cases_to_run = self.test_cases
        if test_filter:
            test_cases_to_run = [tc for tc in self.test_cases if test_filter(tc)]
        
        total_tests = len(test_cases_to_run)
        logger.info(f"开始运行测试套件: {suite_name}, 测试用例数: {total_tests}")
        
        # 运行所有测试用例
        test_results = []
        for test_case_class in test_cases_to_run:
            result = await self.run_test_case(test_case_class)
            test_results.append(result)
        
        # 统计结果
        passed_tests = sum(1 for r in test_results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in test_results if r.status == TestStatus.FAILED)
        skipped_tests = sum(1 for r in test_results if r.status == TestStatus.SKIPPED)
        error_tests = sum(1 for r in test_results if r.status == TestStatus.ERROR)
        timeout_tests = sum(1 for r in test_results if r.status == TestStatus.TIMEOUT)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 创建套件结果
        suite_result = TestSuiteResult(
            suite_id=suite_id,
            suite_name=suite_name,
            start_time=start_time,
            end_time=end_time,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            error_tests=error_tests,
            timeout_tests=timeout_tests,
            test_results=test_results,
            duration=duration,
            metadata={
                "test_filter": test_filter.__name__ if test_filter else None
            }
        )
        
        # 输出摘要
        self._print_summary(suite_result)
        
        return suite_result
    
    def _print_summary(self, suite_result: TestSuiteResult) -> None:
        """输出测试摘要"""
        print("\n" + "="*60)
        print(f"测试套件: {suite_result.suite_name}")
        print(f"运行时间: {suite_result.duration:.2f}秒")
        print(f"测试总数: {suite_result.total_tests}")
        print(f"通过: {suite_result.passed_tests} | 失败: {suite_result.failed_tests} | "
              f"错误: {suite_result.error_tests} | 超时: {suite_result.timeout_tests} | "
              f"跳过: {suite_result.skipped_tests}")
        print("="*60)
        
        # 输出失败测试详情
        failed_tests = [r for r in suite_result.test_results 
                       if r.status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]]
        
        if failed_tests:
            print("\n失败测试详情:")
            for result in failed_tests:
                print(f"  - {result.test_name}: {result.status.value}")
                if result.error_message:
                    print(f"    错误: {result.error_message}")
        
        # 输出通过率
        if suite_result.total_tests > 0:
            pass_rate = (suite_result.passed_tests / suite_result.total_tests) * 100
            print(f"\n通过率: {pass_rate:.1f}%")
        
        print("="*60)
    
    def clear_results(self) -> None:
        """清空测试结果"""
        self.test_results.clear()
        logger.info("测试结果已清空")
    
    def export_results(self, format: str = "json") -> Dict[str, Any]:
        """导出测试结果"""
        if format == "json":
            return {
                "timestamp": datetime.now().isoformat(),
                "total_results": len(self.test_results),
                "results": [r.to_dict() for r in self.test_results]
            }
        else:
            raise ValueError(f"不支持的格式: {format}")


class PerformanceTest(TestCase):
    """性能测试基类"""
    
    def __init__(self, name: str = None, iterations: int = 100):
        super().__init__(name, TestType.PERFORMANCE)
        self.iterations = iterations
        self.performance_metrics = {}
    
    async def run_test(self) -> None:
        """运行性能测试"""
        execution_times = []
        
        for i in range(self.iterations):
            start_time = time.perf_counter()
            await self.execute_operation()
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
        
        # 计算性能指标
        self.performance_metrics = {
            "iterations": self.iterations,
            "total_time": sum(execution_times),
            "avg_time": statistics.mean(execution_times),
            "min_time": min(execution_times),
            "max_time": max(execution_times),
            "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            "p50": statistics.median(execution_times),
            "p95": sorted(execution_times)[int(len(execution_times) * 0.95)] if execution_times else 0,
            "p99": sorted(execution_times)[int(len(execution_times) * 0.99)] if execution_times else 0,
            "operations_per_second": self.iterations / sum(execution_times) if sum(execution_times) > 0 else 0
        }
        
        # 将指标添加到测试结果
        self.metrics.update(self.performance_metrics)
        
        # 输出性能报告
        self._print_performance_report()
    
    async def execute_operation(self) -> None:
        """执行待测操作（子类实现）"""
        raise NotImplementedError("子类必须实现 execute_operation 方法")
    
    def _print_performance_report(self) -> None:
        """输出性能报告"""
        print(f"\n性能测试报告: {self.name}")
        print(f"迭代次数: {self.performance_metrics['iterations']}")
        print(f"总时间: {self.performance_metrics['total_time']:.4f}秒")
        print(f"平均时间: {self.performance_metrics['avg_time']:.4f}秒")
        print(f"最小时间: {self.performance_metrics['min_time']:.4f}秒")
        print(f"最大时间: {self.performance_metrics['max_time']:.4f}秒")
        print(f"标准差: {self.performance_metrics['std_dev']:.4f}秒")
        print(f"中位数: {self.performance_metrics['p50']:.4f}秒")
        print(f"P95: {self.performance_metrics['p95']:.4f}秒")
        print(f"P99: {self.performance_metrics['p99']:.4f}秒")
        print(f"操作/秒: {self.performance_metrics['operations_per_second']:.2f}")


class IntegrationTest(TestCase):
    """集成测试基类"""
    
    def __init__(self, name: str = None):
        super().__init__(name, TestType.INTEGRATION)
        self.components = {}
    
    async def setup(self) -> None:
        """集成测试前置设置"""
        await super().setup()
        # 初始化集成组件
        self.components = await self.initialize_components()
    
    async def teardown(self) -> None:
        """集成测试后置清理"""
        # 清理集成组件
        await self.cleanup_components(self.components)
        await super().teardown()
    
    async def initialize_components(self) -> Dict[str, Any]:
        """初始化集成组件（子类实现）"""
        return {}
    
    async def cleanup_components(self, components: Dict[str, Any]) -> None:
        """清理集成组件（子类实现）"""
        pass


class TestService:
    """测试服务"""
    
    def __init__(self):
        self.test_runner = TestRunner()
        self.test_suites: Dict[str, TestSuiteResult] = {}
        
        logger.info("测试服务初始化完成")
    
    async def run_tests(
        self,
        test_cases: List[Type[TestCase]],
        suite_name: str = "default_suite",
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """运行测试"""
        try:
            # 配置测试运行器
            self.test_runner.timeout_seconds = timeout_seconds
            self.test_runner.register_test_cases(test_cases)
            
            # 运行测试套件
            suite_result = await self.test_runner.run_test_suite(suite_name)
            
            # 保存套件结果
            self.test_suites[suite_result.suite_id] = suite_result
            
            return {
                "success": True,
                "suite_result": suite_result.to_dict()
            }
            
        except Exception as e:
            logger.error(f"运行测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_performance_test(
        self,
        performance_test_class: Type[PerformanceTest],
        iterations: int = 100
    ) -> Dict[str, Any]:
        """运行性能测试"""
        try:
            # 创建性能测试实例
            test_instance = performance_test_class(iterations=iterations)
            
            # 运行测试
            result = await self.test_runner.run_test_case(
                type(test_instance),
                test_id=f"perf_{performance_test_class.__name__}"
            )
            
            return {
                "success": True,
                "performance_test": result.to_dict()
            }
            
        except Exception as e:
            logger.error(f"运行性能测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_test_results(self, suite_id: str = None) -> Dict[str, Any]:
        """获取测试结果"""
        try:
            if suite_id:
                suite_result = self.test_suites.get(suite_id)
                if not suite_result:
                    return {
                        "success": False,
                        "error": f"测试套件不存在: {suite_id}"
                    }
                
                return {
                    "success": True,
                    "suite_result": suite_result.to_dict()
                }
            else:
                # 返回所有套件结果
                return {
                    "success": True,
                    "suite_results": {
                        sid: suite.to_dict()
                        for sid, suite in self.test_suites.items()
                    },
                    "total_suites": len(self.test_suites)
                }
            
        except Exception as e:
            logger.error(f"获取测试结果失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear_test_results(self) -> Dict[str, Any]:
        """清空测试结果"""
        try:
            self.test_runner.clear_results()
            self.test_suites.clear()
            
            logger.info("测试结果已清空")
            
            return {
                "success": True,
                "message": "测试结果已清空"
            }
            
        except Exception as e:
            logger.error(f"清空测试结果失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_test_report(self, format: str = "json") -> Dict[str, Any]:
        """生成测试报告"""
        try:
            if format == "json":
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "total_suites": len(self.test_suites),
                    "suites": {
                        sid: suite.to_dict()
                        for sid, suite in self.test_suites.items()
                    },
                    "summary": self._generate_summary()
                }
                
                return {
                    "success": True,
                    "report": report,
                    "format": format
                }
            else:
                return {
                    "success": False,
                    "error": f"不支持的报告格式: {format}"
                }
            
        except Exception as e:
            logger.error(f"生成测试报告失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成摘要"""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        total_timeouts = 0
        total_skipped = 0
        total_duration = 0
        
        for suite in self.test_suites.values():
            total_tests += suite.total_tests
            total_passed += suite.passed_tests
            total_failed += suite.failed_tests
            total_errors += suite.error_tests
            total_timeouts += suite.timeout_tests
            total_skipped += suite.skipped_tests
            total_duration += suite.duration
        
        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "timeouts": total_timeouts,
            "skipped": total_skipped,
            "pass_rate": pass_rate,
            "total_duration": total_duration
        }


# 示例测试用例
class ExampleUnitTest(TestCase):
    """示例单元测试"""
    
    async def run_test(self) -> None:
        """运行测试"""
        # 测试断言
        self.assert_true(True, "True应该为真")
        self.assert_false(False, "False应该为假")
        self.assert_equal(1 + 1, 2, "1+1应该等于2")
        self.assert_not_equal(1 + 1, 3, "1+1不应该等于3")
        self.assert_in(2, [1, 2, 3], "2应该在列表中")
        self.assert_not_in(4, [1, 2, 3], "4不应该在列表中")
        self.assert_is_none(None, "值应该为None")
        self.assert_is_not_none("value", "值不应该为None")
        
        # 测试异常断言
        def raise_value_error():
            raise ValueError("测试异常")
        
        self.assert_raises(ValueError, raise_value_error)


class ExamplePerformanceTest(PerformanceTest):
    """示例性能测试"""
    
    async def execute_operation(self) -> None:
        """执行待测操作"""
        # 模拟一些计算
        result = 0
        for i in range(1000):
            result += i * i
        await asyncio.sleep(0.001)  # 模拟异步操作


# 全局测试服务实例
test_service = TestService()