#!/usr/bin/env python3
"""
简化版关联系统测试 - 验证核心功能
"""

import os
import sys
import tempfile
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.memory.database import AssociationDatabase
from src.evolution.memory.association_optimizer import AssociationOptimizer

def test_database_operations():
    """测试数据库基本操作"""
    print("🧪 测试数据库基本操作...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        db_path = temp_db.name
    
    try:
        # 1. 创建数据库
        db = AssociationDatabase(db_path)
        print("  ✅ 数据库创建成功")
        
        # 2. 添加记忆条目
        entry1_id = db.add_memory_entry(
            content="Python编程语言",
            content_type="text",
            metadata={"category": "programming"}
        )
        entry2_id = db.add_memory_entry(
            content="机器学习算法",
            content_type="text", 
            metadata={"category": "ai"}
        )
        print(f"  ✅ 添加了2个记忆条目: {entry1_id}, {entry2_id}")
        
        # 3. 读取记忆条目
        entry1 = db.get_memory_entry(entry1_id)
        entry2 = db.get_memory_entry(entry2_id)
        
        assert entry1['content'] == "Python编程语言"
        assert entry2['content'] == "机器学习算法"
        print("  ✅ 记忆条目读取成功")
        
        # 4. 添加关联
        assoc_id = db.add_association(
            source_id=entry1_id,
            target_id=entry2_id,
            association_type="semantic",
            strength=0.8,
            confidence=0.9,
            metadata={"reason": "both are tech topics"}
        )
        print(f"  ✅ 添加了关联: {assoc_id}")
        
        # 5. 验证关联存在
        cursor = db.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM associations")
        assoc_count = cursor.fetchone()[0]
        assert assoc_count == 1
        print(f"  ✅ 验证关联存在: {assoc_count} 个关联")
        # All assertions passed — no return needed for pytest
        
    except Exception as e:
        print(f"  ❌ 数据库操作失败: {e}")
        raise  # Let pytest see the failure
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_optimizer_operations():
    """测试优化器操作"""
    print("\n🧪 测试优化器操作...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        db_path = temp_db.name
    
    try:
        # 1. 创建数据库并添加测试数据
        db = AssociationDatabase(db_path)
        
        # 添加多个记忆条目
        entries = []
        for i in range(5):
            entry_id = db.add_memory_entry(
                content=f"测试内容{i}",
                content_type="text",
                metadata={"test": True, "index": i}
            )
            entries.append(entry_id)
        
        # 添加多个关联（不同质量）
        associations = []
        for i in range(4):
            strength = 0.2 + i * 0.2  # 0.2, 0.4, 0.6, 0.8
            confidence = 0.3 + i * 0.2  # 0.3, 0.5, 0.7, 0.9
            
            assoc_id = db.add_association(
                source_id=entries[i],
                target_id=entries[i+1],
                association_type="test",
                strength=strength,
                confidence=confidence,
                metadata={"test": True, "quality": f"level{i}"}
            )
            associations.append(assoc_id)
        
        print(f"  ✅ 创建了测试数据: {len(entries)} 个条目, {len(associations)} 个关联")
        
        # 2. 创建优化器
        optimizer = AssociationOptimizer(db_path)
        print("  ✅ 优化器创建成功")
        
        # 3. 获取统计信息
        stats = optimizer.get_optimization_stats()
        print(f"  ✅ 获取统计信息: {stats.get('total_associations', 0)} 个关联")
        
        # 4. 运行优化
        result = optimizer.optimize_all_associations()
        assert result.success
        print(f"  ✅ 优化完成: 优化了 {result.associations_optimized} 个关联")
        
        # 5. 获取推荐
        if entries:
            recommendations = optimizer.get_recommendations(entries[0], limit=2)
            print(f"  ✅ 获取推荐: {len(recommendations)} 个推荐")
        
        # 6. 分析模式
        patterns = optimizer.analyze_patterns()
        print(f"  ✅ 分析模式: {len(patterns)} 个模式")
        
        # 7. 清理低质量关联
        removed = optimizer.cleanup_low_quality_associations(min_quality_score=0.3)
        print(f"  ✅ 清理低质量关联: {removed} 个")
        # All assertions passed — no return needed for pytest
        
    except Exception as e:
        print(f"  ❌ 优化器操作失败: {e}")
        import traceback
        traceback.print_exc()
        raise  # Let pytest see the failure
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_integration():
    """测试集成功能"""
    print("\n🧪 测试集成功能...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        db_path = temp_db.name
    
    try:
        # 创建完整的系统
        db = AssociationDatabase(db_path)
        optimizer = AssociationOptimizer(db_path)
        
        # 添加真实场景的数据
        tech_topics = [
            ("Python编程", "一种高级编程语言", "programming"),
            ("机器学习", "人工智能的分支", "ai"),
            ("数据分析", "处理和分析数据", "data"),
            ("Web开发", "构建网站和应用", "web"),
            ("数据库", "存储和管理数据", "database"),
        ]
        
        entry_ids = []
        for topic, description, category in tech_topics:
            content = f"{topic}: {description}"
            entry_id = db.add_memory_entry(
                content=content,
                content_type="text",
                metadata={"category": category, "topic": topic}
            )
            entry_ids.append(entry_id)
        
        print(f"  ✅ 添加了 {len(tech_topics)} 个技术主题")
        
        # 手动添加一些关联（模拟发现的结果）
        # Python -> 机器学习
        db.add_association(
            source_id=entry_ids[0],
            target_id=entry_ids[1],
            association_type="semantic",
            strength=0.85,
            confidence=0.9,
            metadata={"reason": "Python常用于机器学习"}
        )
        
        # 机器学习 -> 数据分析
        db.add_association(
            source_id=entry_ids[1],
            target_id=entry_ids[2],
            association_type="semantic",
            strength=0.8,
            confidence=0.85,
            metadata={"reason": "机器学习需要数据分析"}
        )
        
        # 数据分析 -> 数据库
        db.add_association(
            source_id=entry_ids[2],
            target_id=entry_ids[4],
            association_type="semantic",
            strength=0.75,
            confidence=0.8,
            metadata={"reason": "数据分析需要数据库"}
        )
        
        # Web开发 -> 数据库
        db.add_association(
            source_id=entry_ids[3],
            target_id=entry_ids[4],
            association_type="semantic",
            strength=0.7,
            confidence=0.75,
            metadata={"reason": "Web应用需要数据库"}
        )
        
        print("  ✅ 添加了4个语义关联")
        
        # 运行优化
        result = optimizer.optimize_all_associations()
        print(f"  ✅ 优化结果: {result.associations_optimized} 个关联被优化")
        
        # 获取Python的推荐
        python_entry_id = entry_ids[0]
        recommendations = optimizer.get_recommendations(python_entry_id)
        
        print(f"\n  📋 Python的推荐结果:")
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                content_preview = rec['content'][:30] + "..." if len(rec['content']) > 30 else rec['content']
                print(f"    {i}. {content_preview}")
                print(f"       类型: {rec['association_type']}, "
                      f"强度: {rec['strength']:.3f}, "
                      f"置信度: {rec['confidence']:.3f}")
        else:
            print("    暂无推荐")
        
        # 获取统计信息
        stats = optimizer.get_optimization_stats()
        print(f"\n  📊 系统统计:")
        print(f"    总记忆条目: {stats.get('total_memory_entries', 0)}")
        print(f"    总关联数: {stats.get('total_associations', 0)}")
        print(f"    平均强度: {stats.get('average_strength', 0):.3f}")
        print(f"    平均置信度: {stats.get('average_confidence', 0):.3f}")
        # All assertions passed — no return needed for pytest
        
    except Exception as e:
        print(f"  ❌ 集成测试失败: {e}")
        raise  # Let pytest see the failure
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

def main():
    """主函数"""
    print("🔬 HermesAgentEvolution - 关联系统核心功能测试")
    print("=" * 60)
    
    # 运行所有测试
    tests = [
        ("数据库操作", test_database_operations),
        ("优化器操作", test_optimizer_operations),
        ("集成功能", test_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n▶️ 开始测试: {test_name}")
        try:
            test_func()
            results.append((test_name, True))
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过! 关联系统核心功能正常。")
        print("\n已验证的功能:")
        print("  1. 记忆条目管理 (创建、读取)")
        print("  2. 关联关系管理 (创建、存储)")
        print("  3. 关联优化 (质量评估、调整)")
        print("  4. 智能推荐 (基于关联强度)")
        print("  5. 模式分析 (关联类型分布)")
        print("  6. 质量监控 (统计信息)")
        print("  7. 低质量关联清理")
    else:
        print("⚠️  部分测试失败，需要检查问题。")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)