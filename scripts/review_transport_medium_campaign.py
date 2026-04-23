from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from oqs_transport import agent_stack_payload  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the human approval packet for the medium campaign.")
    parser.add_argument(
        "--campaign-dir",
        default=str(ROOT / "outputs" / "transport_networks" / "medium_propagation" / "latest"),
        help="Path to the campaign output directory.",
    )
    parser.add_argument("--json", action="store_true", help="Print the approval packet as JSON.")
    args = parser.parse_args(argv)

    campaign_dir = Path(args.campaign_dir).resolve()
    review_file = campaign_dir / "analyst_review.json"
    if not review_file.exists():
        raise FileNotFoundError(review_file)

    review = json.loads(review_file.read_text(encoding="utf-8"))
    packet = {
        "campaign_dir": str(campaign_dir),
        "agents": agent_stack_payload(),
        "next_action": review["planner"]["next_action"],
        "next_action_reason": review["planner"]["reason"],
        "critic": review["critic"],
        "figure_explanations": review["figure_explanations"],
        "files_to_open": [
            str(campaign_dir / "figures" / "medium_geometry_overview.png"),
            str(campaign_dir / "figures" / "transport_success_maps.png"),
            str(campaign_dir / "figures" / "spreading_maps.png"),
            str(campaign_dir / "figures" / "mixing_maps.png"),
            str(campaign_dir / "figures" / "regime_maps.png"),
            str(ROOT / "reports" / "transport_medium_campaign_report" / "transport_medium_campaign_report.pdf"),
        ],
    }
    (campaign_dir / "approval_packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.json:
        print(json.dumps(packet, indent=2, ensure_ascii=False))
    else:
        print(f"Next action: {packet['next_action']}")
        print(f"Reason: {packet['next_action_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
