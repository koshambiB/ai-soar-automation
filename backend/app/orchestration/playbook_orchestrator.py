import yaml
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

PLAYBOOK_DIR = Path("playbooks")


class PlaybookOrchestrator:

    def __init__(self):
        self.playbook_map = {
        "isolate_host": "isolate_host.yaml",
        "block_ip": "block_source_ip.yaml",
        "manual_review": "notify_analyst.yaml",

        # ✅ ADD THESE
        "notify_soc_lead": "notify_analyst.yaml",
        "notify_analyst": "notify_analyst.yaml",
        "log_event": "notify_analyst.yaml",
        "periodic_review": "notify_analyst.yaml",
        "investigate_further": "notify_analyst.yaml"
    }

    def load_playbook(self, playbook_file):
        path = PLAYBOOK_DIR / playbook_file

        if not path.exists():
            raise FileNotFoundError(f"Playbook not found: {path}")

        with open(path, "r") as f:
            return yaml.safe_load(f)

    def execute_step(self, step, context):
        action = step.get("action")

        logger.info(f"[STEP] {step['name']}")

        # ---- FAKE BUT BELIEVABLE ACTIONS ----
        if action == "isolate_host":
            logger.info(f"→ Isolating host: {context.get('affected_assets')}")

        elif action == "block_ip":
            logger.info(f"→ Blocking IP: {context.get('source_ip')}")

        elif action == "send_notification":
            logger.info(f"→ Notifying: {step.get('recipients')}")

        elif action == "create_ticket":
            logger.info("→ Ticket created in ServiceNow")

        elif action == "preserve_logs":
            logger.info("→ Logs preserved")

        else:
            logger.warning(f"Unknown action: {action}")

        time.sleep(0.5)

        return {
            "step": step["name"],
            "action": action,
            "status": "success"
        }

    def run_playbook(self, playbook_file, context):
        playbook = self.load_playbook(playbook_file)

        logger.info(f"\n[PLAYBOOK] {playbook['name']} STARTED")

        results = []
        for step in playbook["steps"]:
            result = self.execute_step(step, context)
            results.append(result)

        logger.info(f"[PLAYBOOK] {playbook['name']} COMPLETED\n")

        return results

    def execute_recommendations(self, recommendations, context):
        total = 0
        success = 0
        all_results = []

        for rec in recommendations:
            playbook_file = self.playbook_map.get(rec)

            if not playbook_file:
                logger.info(f"Mapped to default playbook for: {rec}")
                continue

            total += 1

            try:
                result = self.run_playbook(playbook_file, context)
                success += 1
                all_results.append({
                    "playbook": playbook_file,
                    "status": "success",
                    "steps": result
                })

            except Exception as e:
                logger.error(f"Playbook failed: {e}")
                all_results.append({
                    "playbook": playbook_file,
                    "status": "failed"
                })

        return {
            "total_playbooks": total,
            "successful": success,
            "results": all_results
        }