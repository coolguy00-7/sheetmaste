import argparse
import json

from training.local_generator import generate_reference_sheet_with_local_model


def parse_args():
    parser = argparse.ArgumentParser(description="Run simple eval generation against held-out analyses.")
    parser.add_argument("--input", required=True, help="JSONL with `analysis` and optional `reference_sheet`.")
    parser.add_argument("--output", required=True, help="Where to write generated outputs JSONL.")
    return parser.parse_args()


def main():
    args = parse_args()
    count = 0
    with open(args.input, "r", encoding="utf-8") as infile, open(args.output, "w", encoding="utf-8") as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            analysis = (row.get("analysis") or "").strip()
            if not analysis:
                continue
            prompt = f"Analysis to transform:\n{analysis}"
            result = generate_reference_sheet_with_local_model(prompt)
            output = {
                "analysis": analysis,
                "gold_reference_sheet": row.get("reference_sheet"),
                "generated_reference_sheet": result["reference_sheet"],
                "model_used": result["model_used"],
            }
            outfile.write(json.dumps(output, ensure_ascii=False) + "\n")
            count += 1
    print(f"Wrote {count} eval generations to {args.output}")


if __name__ == "__main__":
    main()
