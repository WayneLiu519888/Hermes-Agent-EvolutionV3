"""
学习能力观察器测试
"""
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.evolution.learning.experience import Experience, ExperienceType, Outcome
from src.evolution.learning.observer import LearningObserver


class TestExperience:
    """经验类测试"""
    
    def test_experience_creation(self):
        """测试经验创建"""
        exp = Experience(
            id="test_id",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="test_task",
            description="测试经验",
            outcome=Outcome.SUCCESS
        )
        
        assert exp.id == "test_id"
        assert exp.experience_type == ExperienceType.TOOL_USAGE
        assert exp.task_id == "test_task"
        assert exp.outcome == Outcome.SUCCESS
        assert exp.confidence == 0.0
    
    def test_experience_to_dict(self):
        """测试转换为字典"""
        exp = Experience(
            id="test_id",
            experience_type=ExperienceType.REASONING,
            task_id="test_task",
            description="测试经验",
            outcome=Outcome.SUCCESS
        )
        
        exp_dict = exp.to_dict()
        
        assert exp_dict["id"] == "test_id"
        assert exp_dict["experience_type"] == "reasoning"
        assert exp_dict["outcome"] == "success"
        assert "timestamp" in exp_dict
    
    def test_experience_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": "test_id",
            "experience_type": "problem_solving",
            "task_id": "test_task",
            "timestamp": "2024-01-01T12:00:00",
            "description": "测试经验",
            "outcome": "partial_success",
            "confidence": 0.8,
            "importance": 0.5
        }
        
        exp = Experience.from_dict(data)
        
        assert exp.id == "test_id"
        assert exp.experience_type == ExperienceType.PROBLEM_SOLVING
        assert exp.outcome == Outcome.PARTIAL_SUCCESS
        assert exp.confidence == 0.8
        assert exp.importance == 0.5
    
    def test_experience_json_serialization(self):
        """测试JSON序列化"""
        exp = Experience(
            id="test_id",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="test_task",
            description="测试经验",
            outcome=Outcome.SUCCESS
        )
        
        # 添加一些数据
        exp.add_action("test_tool", {"param": "value"}, "result", 1.5)
        exp.add_reasoning_step("推理步骤1")
        exp.add_lesson_learned("学到的经验")
        exp.add_metric("accuracy", 0.95)
        exp.add_tag("test")
        
        # 转换为JSON
        json_str = exp.to_json()
        assert isinstance(json_str, str)
        
        # 从JSON恢复
        exp2 = Experience.from_json(json_str)
        
        assert exp2.id == exp.id
        assert exp2.experience_type == exp.experience_type
        assert exp2.outcome == exp.outcome
        assert len(exp2.actions) == 1
        assert len(exp2.reasoning_steps) == 1
        assert len(exp2.lessons_learned) == 1
        assert "accuracy" in exp2.metrics
        assert "test" in exp2.tags
    
    def test_experience_confidence_calculation(self):
        """测试置信度计算"""
        # 成功经验
        exp_success = Experience(
            id="test1",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="test_task",
            outcome=Outcome.SUCCESS,
            importance=0.8
        )
        exp_success.add_metric("success_rate", 0.9)
        
        confidence = exp_success.calculate_confidence()
        assert 0.5 <= confidence <= 1.0
        
        # 失败经验
        exp_failure = Experience(
            id="test2",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="test_task",
            outcome=Outcome.FAILURE
        )
        
        confidence = exp_failure.calculate_confidence()
        assert 0.0 <= confidence <= 0.5


class TestLearningObserver:
    """学习观察器测试"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def observer(self, temp_db):
        """创建观察器实例"""
        return LearningObserver(db_path=temp_db)
    
    @pytest.fixture
    def sample_experience(self):
        """创建示例经验"""
        exp = Experience(
            id="test_experience_1",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="test_task_1",
            description="测试工具使用经验",
            outcome=Outcome.SUCCESS,
            importance=0.7
        )
        
        exp.add_action("search_files", {"pattern": "test"}, ["file1.py", "file2.py"], 0.5)
        exp.add_reasoning_step("首先搜索相关文件")
        exp.add_reasoning_step("然后分析文件内容")
        exp.add_lesson_learned("使用正确的搜索模式可以提高效率")
        exp.add_metric("success_rate", 1.0)
        exp.add_metric("duration", 0.5)
        exp.add_tag("tool_usage")
        exp.add_tag("search")
        
        return exp
    
    def test_observer_initialization(self, observer):
        """测试观察器初始化"""
        assert observer.db_path is not None
        assert isinstance(observer._experiences_cache, dict)
        assert observer._statistics_cache is None
    
    def test_record_experience(self, observer, sample_experience):
        """测试记录经验"""
        # 记录经验
        exp_id = observer.record_experience(sample_experience)
        
        assert exp_id == sample_experience.id
        
        # 验证经验已保存
        retrieved = observer.get_experience(exp_id)
        assert retrieved is not None
        assert retrieved.id == sample_experience.id
        assert retrieved.experience_type == sample_experience.experience_type
        assert retrieved.description == sample_experience.description
        
        # 验证缓存
        assert exp_id in observer._experiences_cache
    
    def test_get_nonexistent_experience(self, observer):
        """测试获取不存在的经验"""
        result = observer.get_experience("nonexistent_id")
        assert result is None
    
    def test_query_experiences(self, observer, sample_experience):
        """测试查询经验"""
        # 记录多个经验
        exp1 = sample_experience
        
        exp2 = Experience(
            id="test_experience_2",
            experience_type=ExperienceType.PROBLEM_SOLVING,
            task_id="test_task_2",
            description="测试问题解决经验",
            outcome=Outcome.PARTIAL_SUCCESS,
            importance=0.5
        )
        exp2.add_tag("problem_solving")
        
        observer.record_experience(exp1)
        observer.record_experience(exp2)
        
        # 查询所有经验
        all_exps = observer.query_experiences()
        assert len(all_exps) >= 2
        
        # 按类型查询
        tool_exps = observer.query_experiences(experience_type=ExperienceType.TOOL_USAGE)
        assert len(tool_exps) >= 1
        assert all(exp.experience_type == ExperienceType.TOOL_USAGE for exp in tool_exps)
        
        # 按任务ID查询
        task_exps = observer.query_experiences(task_id="test_task_1")
        assert len(task_exps) >= 1
        assert all(exp.task_id == "test_task_1" for exp in task_exps)
        
        # 按结果查询
        success_exps = observer.query_experiences(outcome=Outcome.SUCCESS)
        assert len(success_exps) >= 1
        assert all(exp.outcome == Outcome.SUCCESS for exp in success_exps)
        
        # 按标签查询
        tagged_exps = observer.query_experiences(tags=["tool_usage"])
        assert len(tagged_exps) >= 1
        
        # 按时间查询
        yesterday = datetime.now() - timedelta(days=1)
        recent_exps = observer.query_experiences(start_time=yesterday)
        assert len(recent_exps) >= 2
    
    def test_get_statistics(self, observer, sample_experience):
        """测试获取统计信息"""
        # 记录一些经验
        observer.record_experience(sample_experience)
        
        exp2 = Experience(
            id="test_experience_2",
            experience_type=ExperienceType.PROBLEM_SOLVING,
            task_id="test_task_2",
            description="另一个测试经验",
            outcome=Outcome.FAILURE
        )
        observer.record_experience(exp2)
        
        # 获取统计信息
        stats = observer.get_statistics()
        
        assert "total_experiences" in stats
        assert stats["total_experiences"] >= 2
        
        assert "by_type" in stats
        assert "tool_usage" in stats["by_type"]
        assert "problem_solving" in stats["by_type"]
        
        assert "by_outcome" in stats
        assert "success" in stats["by_outcome"]
        assert "failure" in stats["by_outcome"]
        
        assert "avg_confidence" in stats
        assert "recent_24h" in stats
        
        # 测试缓存
        stats2 = observer.get_statistics()
        assert stats["total_experiences"] == stats2["total_experiences"]
    
    def test_analyze_learning_patterns(self, observer, sample_experience):
        """测试分析学习模式"""
        # 记录经验
        observer.record_experience(sample_experience)
        
        # 分析学习模式
        analysis = observer.analyze_learning_patterns(window_days=1)
        
        assert "window_days" in analysis
        assert analysis["window_days"] == 1
        
        assert "daily_success_rates" in analysis
        assert isinstance(analysis["daily_success_rates"], dict)
        
        assert "tool_usage_frequency" in analysis
        assert "search_files" in analysis["tool_usage_frequency"]
    
    def test_export_experiences(self, observer, sample_experience):
        """测试导出经验"""
        # 记录经验
        observer.record_experience(sample_experience)
        
        # 导出为JSON
        import tempfile
        json_file = tempfile.mktemp(suffix='.json')
        success = observer.export_experiences(json_file, format="json")
        
        assert success
        assert os.path.exists(json_file)
        
        # 验证JSON文件内容
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # 清理
        os.unlink(json_file)
        
        # 导出为CSV
        csv_file = tempfile.mktemp(suffix='.csv')
        success = observer.export_experiences(csv_file, format="csv")
        
        assert success
        assert os.path.exists(csv_file)
        
        # 清理
        os.unlink(csv_file)
    
    def test_clear_cache(self, observer, sample_experience):
        """测试清空缓存"""
        # 记录经验以填充缓存
        observer.record_experience(sample_experience)
        
        # 获取经验以填充缓存
        observer.get_experience(sample_experience.id)
        
        # 获取统计信息以填充缓存
        observer.get_statistics()
        
        # 验证缓存不为空
        assert len(observer._experiences_cache) > 0
        assert observer._statistics_cache is not None
        
        # 清空缓存
        observer.clear_cache()
        
        # 验证缓存已清空
        assert len(observer._experiences_cache) == 0
        assert observer._statistics_cache is None


def test_integration():
    """集成测试"""
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # 创建观察器
        observer = LearningObserver(db_path=db_path)
        
        # 创建并记录多个经验
        experiences = []
        for i in range(5):
            exp = Experience(
                id=f"exp_{i}",
                experience_type=ExperienceType.TOOL_USAGE if i % 2 == 0 else ExperienceType.REASONING,
                task_id=f"task_{i // 2}",
                description=f"测试经验{i}",
                outcome=Outcome.SUCCESS if i % 3 != 0 else Outcome.PARTIAL_SUCCESS,
                importance=i * 0.1
            )
            
            exp.add_action(f"tool_{i}", {"param": i}, f"result_{i}", i * 0.1)
            exp.add_reasoning_step(f"推理步骤{i}")
            exp.add_tag(f"tag_{i % 3}")
            
            observer.record_experience(exp)
            experiences.append(exp)
        
        # 验证记录
        for exp in experiences:
            retrieved = observer.get_experience(exp.id)
            assert retrieved is not None
            assert retrieved.id == exp.id
            assert retrieved.experience_type == exp.experience_type
        
        # 验证统计
        stats = observer.get_statistics()
        assert stats["total_experiences"] == 5
        
        # 验证查询
        tool_exps = observer.query_experiences(experience_type=ExperienceType.TOOL_USAGE)
        assert len(tool_exps) >= 2
        
        # 验证分析
        analysis = observer.analyze_learning_patterns(window_days=7)
        assert "daily_success_rates" in analysis
        
    finally:
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])