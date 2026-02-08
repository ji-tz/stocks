"""截图脚本 CLI 测试"""
import unittest

from tests.guitests.screenshot_main import build_output_plan, resolve_targets


class TestScreenshotCli(unittest.TestCase):
    """截图脚本 CLI 的纯逻辑测试"""

    def test_resolve_targets_all(self):
        """all 目标应返回全部任务"""
        targets = resolve_targets("all", run_all=True)
        self.assertIn("main", targets)
        self.assertIn("strategy", targets)

    def test_resolve_targets_single(self):
        """单个目标应只返回自身"""
        targets = resolve_targets("main", run_all=False)
        self.assertEqual(targets, ["main"])

    def test_build_output_plan_defaults(self):
        """默认输出路径应符合约定"""
        plan = build_output_plan(["main", "strategy"], output_dir="shots")
        self.assertEqual(plan["main"], "shots/main_gui.png")
        self.assertEqual(plan["strategy"], "shots")

    def test_build_output_plan_override(self):
        """覆盖输出路径应生效"""
        plan = build_output_plan(
            ["main"],
            output_dir="shots",
            output_main="custom/main.png",
        )
        self.assertEqual(plan["main"], "custom/main.png")


if __name__ == "__main__":
    unittest.main()
