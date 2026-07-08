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
            "StoryAxis·分卷大纲",
            "StoryAxis·写作指南",
            "StoryAxis·阶段大纲",
            "StoryAxis·章节大纲",
            "StoryAxis·内容生成",
            "StoryAxis·阶段审核",
            "StoryAxis·章节审核",
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
