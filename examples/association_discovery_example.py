"""
关联发现系统使用示例
"""

import sys
import os
import logging

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from evolution.memory.database import AssociationDatabase
    from evolution.memory.association_discoverer import AssociationDiscoverer
    from evolution.memory.association_optimizer import AssociationOptimizer
except ImportError:
    from src.evolution.memory.database import AssociationDatabase
    from src.evolution.memory.association_discoverer import AssociationDiscoverer
    from src.evolution.memory.association_optimizer import AssociationOptimizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("🧪 基本使用示例")
    print("=" * 60)
    
    # 1. 创建数据库
    print("\n1. 📁 创建数据库...")
    db = AssociationDatabase("example_associations.db")
    
    # 2. 添加记忆条目
    print("\n2. 📝 添加记忆条目...")
    memory_ids = []
    
    memories = [
        "机器学习是人工智能的核心技术",
        "深度学习是机器学习的一个分支",
        "神经网络是深度学习的基础模型",
        "Python是数据科学的主要编程语言",
        "TensorFlow和PyTorch是流行的深度学习框架",
        "监督学习需要标注的训练数据",
        "无监督学习可以发现数据中的模式",
        "强化学习通过试错进行学习"
    ]
    
    for i, content in enumerate(memories, 1):
        mem_id = db.add_memory_entry(
            content=content,
            content_type="text",
            metadata={"source": "example", "index": i},
            tags=["AI", "machine_learning", "example"]
        )
        memory_ids.append(mem_id)
        print(f"   添加记忆 {i}: {content[:30]}... (ID: {mem_id})")
    
    # 3. 创建关联发现器
    print("\n3. 🔍 创建关联发现器...")
    discoverer = AssociationDiscoverer(db)
    
    # 4. 发现关联
    print("\n4. 🔗 发现关联关系...")
    all_associations = []
    
    for i, mem_id in enumerate(memory_ids[:3], 1):  # 只处理前3个
        print(f"   处理记忆 {i}/{len(memory_ids)}: {mem_id}")
        associations = discoverer.discover_all_associations(mem_id)
        all_associations.extend(associations)
        
        # 保存到数据库
        for assoc in associations:
            db.add_association(**assoc)
            
        print(f"     发现 {len(associations)} 个关联")
    
    print(f"   总共发现 {len(all_associations)} 个关联")
    
    # 5. 创建关联优化器
    print("\n5. ⚙️ 创建关联优化器...")
    optimizer = AssociationOptimizer(db)
    
    # 6. 优化关联
    print("\n6. 🔧 优化关联关系...")
    optimization_result = optimizer.optimize_associations()
    print(f"   优化结果: {optimization_result}")
    
    # 7. 获取强关联
    print("\n7. 💪 获取强关联...")
    strong_assocs = optimizer.get_strong_associations(
        memory_ids[0],  # 第一个记忆条目
        min_strength=0.7,
        min_confidence=0.7,
        limit=5
    )
    
    print(f"   找到 {len(strong_assocs)} 个强关联:")
    for i, assoc in enumerate(strong_assocs, 1):
        related_id = assoc['target_id'] if assoc['source_id'] == memory_ids[0] else assoc['source_id']
        memory = db.get_memory_entry(related_id)
        content_preview = memory['content'][:40] + "..." if len(memory['content']) > 40 else memory['content']
        print(f"     {i}. {assoc['association_type']}: 强度={assoc['strength']:.2f}, 置信度={assoc['confidence']:.2f}")
        print(f"        关联内容: {content_preview}")
    
    # 8. 获取推荐
    print("\n8. 🎯 获取智能推荐...")
    recommendations = optimizer.get_recommendations(memory_ids[0], limit=3)
    
    print(f"   生成 {len(recommendations)} 个推荐:")
    for i, rec in enumerate(recommendations, 1):
        memory = db.get_memory_entry(rec['memory_id'])
        content_preview = memory['content'][:40] + "..." if len(memory['content']) > 40 else memory['content']
        print(f"     {i}. 推荐分数: {rec['score']:.2f}")
        print(f"        推荐内容: {content_preview}")
        print(f"        通过: {rec['via_memory_id']}")
    
    # 9. 分析模式
    print("\n9. 📊 分析关联模式...")
    patterns = optimizer.analyze_patterns(min_support=2)
    
    print(f"   发现 {len(patterns)} 个模式:")
    for i, pattern in enumerate(patterns[:3], 1):  # 只显示前3个
        print(f"     {i}. 模式类型: {pattern['pattern_type']}")
        print(f"        置信度: {pattern['confidence']:.2f}, 支持度: {pattern['support_count']}")
    
    # 10. 清理
    print("\n10. 🧹 清理资源...")
    db.close()
    
    print("\n" + "=" * 60)
    print("✅ 示例完成!")
    print("数据库文件: example_associations.db")
    print("=" * 60)

def example_batch_discovery():
    """批量发现示例"""
    print("\n" + "=" * 60)
    print("🧪 批量发现示例")
    print("=" * 60)
    
    # 创建新数据库
    db = AssociationDatabase("batch_example.db")
    
    # 添加大量记忆条目
    print("\n1. 📝 添加大量记忆条目...")
    topics = ["机器学习", "深度学习", "自然语言处理", "计算机视觉", "强化学习"]
    memory_ids = []
    
    for topic_idx, topic in enumerate(topics):
        for i in range(5):  # 每个主题5个条目
            content = f"{topic}的相关知识 {i+1}: 这是关于{topic}的详细说明..."
            mem_id = db.add_memory_entry(
                content=content,
                content_type="text",
                metadata={"topic": topic, "index": i},
                tags=[topic, "batch_example"]
            )
            memory_ids.append(mem_id)
    
    print(f"   添加了 {len(memory_ids)} 个记忆条目")
    
    # 批量发现关联
    print("\n2. 🔍 批量发现关联...")
    discoverer = AssociationDiscoverer(db)
    
    result = discoverer.batch_discover_associations(
        memory_ids=memory_ids[:10],  # 只处理前10个
        limit=10
    )
    
    print(f"   批量发现结果:")
    print(f"     处理的记忆条目: {result['total_memories_processed']}")
    print(f"     成功的记忆条目: {result['successful_memories']}")
    print(f"     发现的关联数量: {result['total_associations_discovered']}")
    print(f"     耗时: {result['duration_seconds']:.2f}秒")
    print(f"     平均每个记忆条目的关联数: {result['associations_per_memory']:.2f}")
    
    # 清理
    db.close()
    os.remove("batch_example.db")
    
    print("\n" + "=" * 60)
    print("✅ 批量发现示例完成!")
    print("=" * 60)

def example_advanced_features():
    """高级功能示例"""
    print("\n" + "=" * 60)
    print("🧪 高级功能示例")
    print("=" * 60)
    
    db = AssociationDatabase("advanced_example.db")
    
    # 添加不同类型的记忆条目
    print("\n1. 📝 添加多样化记忆条目...")
    
    # 文本记忆
    text_id = db.add_memory_entry(
        "Python编程的最佳实践",
        "text",
        tags=["programming", "python", "best_practices"]
    )
    
    # 代码记忆
    code_id = db.add_memory_entry(
        "def calculate_sum(numbers):\n    return sum(numbers)",
        "code",
        tags=["python", "function", "example"]
    )
    
    # 概念记忆
    concept_id = db.add_memory_entry(
        "面向对象编程的四大特性：封装、继承、多态、抽象",
        "concept",
        tags=["OOP", "programming", "concepts"]
    )
    
    # 手动添加关联
    print("\n2. 🔗 手动添加关联...")
    db.add_association(text_id, code_id, "example_of", 0.9, 0.8)
    db.add_association(text_id, concept_id, "related_to", 0.7, 0.6)
    db.add_association(code_id, concept_id, "implements", 0.8, 0.7)
    
    # 使用关联
    print("\n3. 📊 记录关联使用...")
    cursor = db.connection.cursor()
    cursor.execute("SELECT id FROM associations WHERE source_id = ? AND target_id = ?", 
                  (text_id, code_id))
    assoc_row = cursor.fetchone()
    
    if assoc_row:
        assoc_id = assoc_row['id']
        db.record_association_usage(
            association_id=assoc_id,
            usage_context="code_review",
            usefulness_score=0.9,
            feedback="这个关联很有用"
        )
        print(f"   记录关联使用: association_id={assoc_id}")
    
    # 获取相关记忆
    print("\n4. 🔍 获取相关记忆...")
    related = db.get_related_memories(text_id)
    print(f"   '{text_id}' 的相关记忆:")
    for i, rel in enumerate(related, 1):
        memory = db.get_memory_entry(
            rel['target_id'] if rel['source_id'] == text_id else rel['source_id']
        )
        content_preview = memory['content'][:30] + "..." if len(memory['content']) > 30 else memory['content']
        print(f"     {i}. {rel['association_type']}: {content_preview}")
    
    # 清理
    db.close()
    os.remove("advanced_example.db")
    
    print("\n" + "=" * 60)
    print("✅ 高级功能示例完成!")
    print("=" * 60)

def main():
    """主函数"""
    print("🚀 关联发现系统使用示例")
    print("=" * 60)
    
    try:
        # 运行示例
        example_basic_usage()
        example_batch_discovery()
        example_advanced_features()
        
        print("\n🎉 所有示例成功完成!")
        print("\n📋 总结:")
        print("  1. ✅ 基本使用: 创建、发现、优化、推荐")
        print("  2. ✅ 批量发现: 高效处理大量记忆条目")
        print("  3. ✅ 高级功能: 多样化记忆类型、手动关联、使用记录")
        print("\n💡 下一步:")
        print("  1. 查看生成的数据库文件")
        print("  2. 运行测试: python -m pytest tests/test_association_discovery.py")
        print("  3. 集成到现有系统中")
        
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
