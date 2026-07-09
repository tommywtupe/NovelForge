import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.bootstrap import prompts as prompt_bootstrap
from app.bootstrap import workflows as workflow_bootstrap
from app.services.workflow import trigger_extractor


class StoryAxisBootstrapResourceTests(unittest.TestCase):
    def test_storyaxis_prompt_files_are_bootstrapped(self) -> None:
        prompt_files = prompt_bootstrap.get_all_prompt_files()

        required_prompts = {
            "StoryAxis·金手指生成",
            "StoryAxis·一句话梗概",
            "StoryAxis·一段话大纲",
            "StoryAxis·世界观设定",
            "StoryAxis·核心蓝图",
            "StoryAxis·关系提取",
            "StoryAxis·分卷大纲",
            "StoryAxis·写作指南",
            "StoryAxis·场景状态提取",
            "StoryAxis·扩写",
            "StoryAxis·拆书_全案拆解_人物脉络",
            "StoryAxis·拆书_全案拆解_基础骨架",
            "StoryAxis·拆书_全案拆解_技法行动",
            "StoryAxis·拆书_章节大纲摘要",
            "StoryAxis·拆书_阶段划分",
            "StoryAxis·概念掌握提取",
            "StoryAxis·润色",
            "StoryAxis·灵感对话-React",
            "StoryAxis·灵感对话",
            "StoryAxis·物品状态提取",
            "StoryAxis·阶段大纲",
            "StoryAxis·章节大纲",
            "StoryAxis·内容生成",
            "StoryAxis·章节审核",
            "StoryAxis·组织状态提取",
            "StoryAxis·角色动态信息提取",
            "StoryAxis·通用审核",
            "StoryAxis·正文翻译",
            "StoryAxis·术语翻译",
            "StoryAxis·阶段审核",
            "StoryAxis·人物审核",
            "StoryAxis·故事诊断",
            "StoryAxis·内容生成 copy",
            "StoryAxis·内容生成-女频",
            "StoryAxis·内容生成单独润色",
            "StoryAxis·逐行审核",
            "StoryAxis·逐行润色",
            "StoryAxis·正文翻译-英文",
            "StoryAxis·正文翻译-日文",
            "StoryAxis·正文翻译-韩文",
            "StoryAxis·正文翻译-繁體中文",
        }

        self.assertTrue(required_prompts.issubset(set(prompt_files.keys())))

    def test_storyaxis_workflows_are_namespaced_and_use_storyaxis_template(self) -> None:
        workflow_files = workflow_bootstrap.get_all_workflow_files()

        self.assertIn("StoryAxis·项目创建", workflow_files)
        self.assertIn("StoryAxis·阶段大纲派生", workflow_files)

        project_workflow = workflow_files["StoryAxis·项目创建"]["code"]
        project_triggers = trigger_extractor.extract_triggers_from_code(project_workflow)
        self.assertIn(
            {"event": "project.created", "match": {"template": "storyaxis"}},
            project_triggers,
        )

        stage_workflow = workflow_files["StoryAxis·阶段大纲派生"]["code"]
        self.assertIn('card_type="StoryAxis·阶段大纲"', stage_workflow)
        self.assertIn('card_type="StoryAxis·章节正文"', stage_workflow)
        self.assertIn('card_type="StoryAxis·正文翻译卡"', stage_workflow)


if __name__ == "__main__":
    unittest.main()
