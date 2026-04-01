"""
决策树引擎测试
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.decision_tree import (
    DecisionTreeEngine, TreeNode, TreeQuestion, TreeRecommendation,
    TILE_DECISION_TREE, FLOORING_DECISION_TREE, BUDGET_DECISION_TREE,
    INSPECTION_DECISION_TREE, ALL_TREES, parse_decision_tree_payload,
)


class TestTreeDataIntegrity:
    """决策树数据完整性测试"""

    def test_all_trees_registered(self):
        assert "选材_瓷砖" in ALL_TREES
        assert "选材_地板" in ALL_TREES
        assert "全屋_预算规划" in ALL_TREES
        assert "施工_验收" in ALL_TREES

    def test_tile_tree_has_required_fields(self):
        tree = TILE_DECISION_TREE
        assert tree["id"] == "选材_瓷砖"
        assert tree["root"] in tree["nodes"]
        assert len(tree["trigger_keywords"]) > 0

    def test_all_next_map_targets_exist(self):
        """所有 next_map 指向的节点都存在或是 COMPLETE"""
        for tree_id, tree in ALL_TREES.items():
            nodes = tree["nodes"]
            for node_id, node in nodes.items():
                for answer, target in node.next_map.items():
                    assert target == "COMPLETE" or target in nodes, \
                        f"Tree {tree_id}, node {node_id}: target '{target}' not found"

    def test_all_nodes_reachable(self):
        """所有节点都可以从 root 到达"""
        for tree_id, tree in ALL_TREES.items():
            nodes = tree["nodes"]
            reachable = set()
            queue = [tree["root"]]
            while queue:
                current = queue.pop(0)
                if current == "COMPLETE" or current in reachable:
                    continue
                reachable.add(current)
                if current in nodes:
                    for target in nodes[current].next_map.values():
                        queue.append(target)
            for node_id in nodes:
                assert node_id in reachable, \
                    f"Tree {tree_id}: node '{node_id}' is unreachable from root"


class TestDecisionTreeEngine:
    """决策树引擎核心逻辑测试"""

    def setup_method(self):
        self.engine = DecisionTreeEngine()
        self.user_id = "test_user_001"

    def test_detect_tile_tree(self):
        assert self.engine.detect_tree("瓷砖怎么选") == "选材_瓷砖"
        assert self.engine.detect_tree("卫生间地砖选什么好") == "选材_瓷砖"

    def test_detect_flooring_tree(self):
        assert self.engine.detect_tree("地板选实木还是复合") == "选材_地板"
        assert self.engine.detect_tree("木地板怎么选") == "选材_地板"

    def test_detect_budget_tree(self):
        assert self.engine.detect_tree("装修预算怎么分配") == "全屋_预算规划"
        assert self.engine.detect_tree("花多少钱装修合适") == "全屋_预算规划"

    def test_detect_inspection_tree(self):
        assert self.engine.detect_tree("瓦工验收怎么做") == "施工_验收"

    def test_detect_no_match(self):
        assert self.engine.detect_tree("今天天气怎么样") is None

    def test_first_question_is_root(self):
        q = self.engine.get_next_question("选材_瓷砖", self.user_id)
        assert q is not None
        assert q.node_id == "space_usage"
        assert q.progress == 0.0
        assert len(q.options) > 0

    def test_answer_advances_tree(self):
        # 回答第一个问题
        self.engine.record_answer(self.user_id, "选材_瓷砖", "space_usage", "客厅")
        q = self.engine.get_next_question("选材_瓷砖", self.user_id)
        assert q is not None
        assert q.node_id == "has_floor_heating"  # 客厅 → has_floor_heating
        assert q.progress > 0

    def test_bathroom_path(self):
        """卫生间路径应该经过 bathroom_area"""
        self.engine.record_answer(self.user_id, "选材_瓷砖", "space_usage", "卫生间")
        q = self.engine.get_next_question("选材_瓷砖", self.user_id)
        assert q.node_id == "bathroom_area"

    def test_complete_tile_tree(self):
        """完整走完瓷砖决策树"""
        tree_id = "选材_瓷砖"
        answers = [
            ("space_usage", "客厅"),
            ("has_floor_heating", "有地暖"),
            ("budget_level", "中档（80-200元/片）"),
            ("style_preference", "现代简约"),
            ("family_situation", "有小孩"),
        ]
        for node_id, answer in answers:
            self.engine.record_answer(self.user_id, tree_id, node_id, answer)

        # 应该没有更多问题了
        q = self.engine.get_next_question(tree_id, self.user_id)
        assert q is None

        # 应该能生成推荐上下文
        rec = self.engine.get_recommendation_context(tree_id, self.user_id)
        assert rec is not None
        assert "客厅" in rec.recommendation_context
        assert "有地暖" in rec.recommendation_context
        assert len(rec.key_factors) > 0

    def test_incomplete_tree_no_recommendation(self):
        """未完成的树不应该生成推荐"""
        self.engine.record_answer(self.user_id, "选材_瓷砖", "space_usage", "客厅")
        rec = self.engine.get_recommendation_context("选材_瓷砖", self.user_id)
        assert rec is None

    def test_try_match_answer_exact(self):
        """精确匹配选项文本"""
        matched = self.engine.try_match_answer("选材_瓷砖", "space_usage", "我想选客厅的瓷砖")
        assert matched == "客厅"

    def test_try_match_answer_keyword(self):
        """关键词匹配"""
        matched = self.engine.try_match_answer("选材_瓷砖", "space_usage", "厕所的砖怎么选")
        assert matched == "卫生间"

    def test_try_match_answer_no_match(self):
        matched = self.engine.try_match_answer("选材_瓷砖", "space_usage", "你好")
        assert matched is None

    def test_auto_extract_from_message(self):
        """从用户消息中自动提取答案"""
        q = self.engine.get_next_question(
            "选材_瓷砖", self.user_id, message="客厅的瓷砖怎么选"
        )
        # space_usage 应该被自动匹配为"客厅"，下一个问题应该是 has_floor_heating
        assert q is not None
        assert q.node_id == "has_floor_heating"

    def test_auto_extract_persists_answer(self):
        """自动抽取的答案应持久化到用户会话"""
        self.engine.get_next_question(
            "选材_瓷砖", self.user_id, message="客厅的瓷砖怎么选"
        )
        q = self.engine.get_next_question("选材_瓷砖", self.user_id)
        assert q is not None
        assert q.node_id == "has_floor_heating"

    def test_clear_session(self):
        self.engine.record_answer(self.user_id, "选材_瓷砖", "space_usage", "客厅")
        self.engine.clear_session(self.user_id, "选材_瓷砖")
        q = self.engine.get_next_question("选材_瓷砖", self.user_id)
        assert q.node_id == "space_usage"  # 回到起点

    def test_clear_all_sessions(self):
        self.engine.record_answer(self.user_id, "选材_瓷砖", "space_usage", "客厅")
        self.engine.record_answer(self.user_id, "选材_地板", "has_floor_heating_floor", "有地暖")
        self.engine.clear_session(self.user_id)
        q1 = self.engine.get_next_question("选材_瓷砖", self.user_id)
        q2 = self.engine.get_next_question("选材_地板", self.user_id)
        assert q1.node_id == "space_usage"
        assert q2.node_id == "has_floor_heating_floor"


class TestDecisionTreePayload:
    def test_parse_payload(self):
        payload = "dt:选材_瓷砖:space_usage:客厅"
        result = parse_decision_tree_payload(payload)
        assert result == ("选材_瓷砖", "space_usage", "客厅")

    def test_parse_payload_invalid(self):
        assert parse_decision_tree_payload("客厅") is None
        assert parse_decision_tree_payload("dt:only:two") is None


class TestProfileExtraction:
    """从 UserProfile 自动提取答案的测试"""

    def setup_method(self):
        self.engine = DecisionTreeEngine()
        self.user_id = "test_profile_user"

    def test_extract_house_area(self):
        """从 profile 的 house_area 自动填充"""
        class MockProfile:
            house_area = 110.0
            budget_range = None
            preferred_styles = []

        q = self.engine.get_next_question(
            "全屋_预算规划", self.user_id, profile=MockProfile()
        )
        # house_area=110 应该匹配 "100-120平"，跳到下一个问题
        assert q is not None
        assert q.node_id == "budget_total"

    def test_extract_budget_range(self):
        """从 profile 的 budget_range 自动填充"""
        class MockProfile:
            house_area = 110.0
            budget_range = (150000, 250000)
            preferred_styles = []

        q = self.engine.get_next_question(
            "全屋_预算规划", self.user_id, profile=MockProfile()
        )
        # house_area 和 budget_total 都应该被自动填充
        # 25万 → "20-30万"
        assert q is not None
        assert q.node_id == "decoration_mode"

    def test_extract_preferred_styles(self):
        """从 profile 的 preferred_styles 自动填充"""
        class MockProfile:
            house_area = None
            budget_range = None
            preferred_styles = ["现代简约"]

        # 瓷砖树的 style_preference 节点应该被自动填充
        self.engine.record_answer(self.user_id, "选材_瓷砖", "space_usage", "客厅")
        self.engine.record_answer(self.user_id, "选材_瓷砖", "has_floor_heating", "没有地暖")
        self.engine.record_answer(self.user_id, "选材_瓷砖", "budget_level", "中档（80-200元/片）")

        q = self.engine.get_next_question(
            "选材_瓷砖", self.user_id, profile=MockProfile()
        )
        # style_preference 应该被自动填充为"现代简约"，跳到 family_situation
        assert q is not None
        assert q.node_id == "family_situation"


class TestStageDetection:
    """阶段匹配加分测试"""

    def setup_method(self):
        self.engine = DecisionTreeEngine()

    def test_stage_boost(self):
        """施工阶段应该优先匹配施工相关的树"""
        # "验收"同时可能匹配多棵树，但施工阶段应该加分
        result = self.engine.detect_tree("验收怎么做", stage="施工")
        assert result == "施工_验收"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
