import argparse
import json


PROMPT_TEMPLATE = """
Create a highly compressed Science Olympiad reference sheet from the analysis below.

Constraints:
- Cover every topic and skill in the analysis.
- Plain text only.
- Aggressively compact format suitable for two letter-sized pages at 6pt.
- Include topic map, key facts/formulas, traps, fast solving patterns, mini examples, and final checklist.

Analysis to transform:
{analysis}
""".strip()


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare JSONL data for reference-sheet SFT training.")
    parser.add_argument("--input", required=True, help="Path to raw JSONL with fields: analysis, reference_sheet.")
    parser.add_argument("--output", required=True, help="Path to output training JSONL.")
    return parser.parse_args()


def main():
    args = parse_args()
    written = 0

    with open(args.input, "r", encoding="utf-8") as infile, open(args.output, "w", encoding="utf-8") as outfile:
        for line_no, line in enumerate(infile, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            analysis = (row.get("analysis") or "").strip()
            reference_sheet = (row.get("reference_sheet") or "").strip()
            if not analysis or not reference_sheet:
                continue

            prompt = PROMPT_TEMPLATE.format(analysis=analysis)
            sample = {
                "text": f"### Instruction\n{prompt}\n\n### Response\n{reference_sheet}",
                "meta": {
                    "event": row.get("event"),
                    "division": row.get("division"),
                    "source": row.get("source"),
                    "line_no": line_no,
                },
            }
            outfile.write(json.dumps(sample, ensure_ascii=False) + "\n")
            written += 1

    print(f"Wrote {written} training examples to {args.output}")


if __name__ == "__main__":
    main()
