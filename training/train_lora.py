import argparse

from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer


def parse_args():
    parser = argparse.ArgumentParser(description="Train a LoRA adapter for Science Olympiad reference-sheet generation.")
    parser.add_argument("--base-model", required=True, help="Base model id/path, e.g. mistralai/Mistral-7B-Instruct-v0.3")
    parser.add_argument("--train-file", required=True, help="Prepared training JSONL with a `text` field.")
    parser.add_argument("--output-dir", required=True, help="Where to save LoRA adapter checkpoints.")
    parser.add_argument("--eval-file", default="", help="Optional eval JSONL with same format.")
    parser.add_argument("--num-epochs", type=float, default=2.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--max-seq-len", type=int, default=4096)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--logging-steps", type=int, default=10)
    return parser.parse_args()


def main():
    args = parse_args()

    data_files = {"train": args.train_file}
    if args.eval_file:
        data_files["validation"] = args.eval_file
    dataset = load_dataset("json", data_files=data_files)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        device_map="auto",
        torch_dtype="auto",
    )

    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        fp16=False,
        bf16=True,
        report_to="none",
        save_total_limit=3,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        peft_config=peft_config,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=args.max_seq_len,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main()
