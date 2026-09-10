import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_manifest_contract(self):
        manifest = json.loads((ROOT / "plow-agent.json").read_text())
        self.assertEqual(manifest["$schema"], "https://plow.co/schemas/agent/v1.json")
        self.assertRegex(manifest["id"], r"^[a-z0-9][a-z0-9-]*$")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["runtime"]["type"], "hermes")
        self.assertTrue((ROOT / manifest["entry"]).is_file())
        self.assertTrue((ROOT / manifest["icon"]).is_file())
        self.assertEqual(len(manifest["permissions"]), len(set(manifest["permissions"])))
        for permission in manifest["permissions"]:
            self.assertRegex(permission, r"^[a-z0-9][a-z0-9-]*$")

    def test_icon_is_a_bounded_png(self):
        manifest = json.loads((ROOT / "plow-agent.json").read_text())
        icon = ROOT / manifest["icon"]
        self.assertLessEqual(icon.stat().st_size, 512 * 1024)
        self.assertEqual(icon.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_descriptor_has_no_instance_identity(self):
        text = (ROOT / "agent.env").read_text()
        assignments = {
            line.split("=", 1)[0]
            for line in text.splitlines()
            if line and not line.startswith("#") and "=" in line
        }
        self.assertNotIn("AGENT_HOME", assignments)
        self.assertNotIn("AGENT_CONTAINER", assignments)
        self.assertNotIn("AGENT_PROJECT", assignments)
        self.assertNotIn("AGENT_IMAGE", assignments)

    def test_no_obvious_secret_is_tracked(self):
        token_assignment = (
            r"(?:DOMO_MCP_" + r"TOKEN|PLOW_AGENT_" + r"TOKEN)=\S+"
        )
        secret = re.compile(
            r"(?:gh[opsu]" + r"_|sk" + r"-[A-Za-z0-9]|" + token_assignment + r")"
        )
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or path.suffix == ".png" or path.name == "agent_index_client.py":
                continue
            self.assertIsNone(secret.search(path.read_text(errors="ignore")), str(path))


if __name__ == "__main__":
    unittest.main()
