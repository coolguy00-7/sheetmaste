import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_pipeline(model_name_or_path, adapter_path):
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name_or_path,
        torch_dtype="auto",
        device_map="auto",
    )

    if adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter_path)

    return pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
    )


def generate_reference_sheet_with_local_model(prompt):
    model_name_or_path = os.getenv("LOCAL_REFERENCE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3").strip()
    adapter_path = os.getenv("LOCAL_REFERENCE_ADAPTER", "").strip()
    max_new_tokens = int(os.getenv("LOCAL_REFERENCE_MAX_NEW_TOKENS", "2800"))
    temperature = float(os.getenv("LOCAL_REFERENCE_TEMPERATURE", "0.2"))
    top_p = float(os.getenv("LOCAL_REFERENCE_TOP_P", "0.95"))

    generator = _load_pipeline(model_name_or_path, adapter_path)
    outputs = generator(
        prompt,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
        top_p=top_p,
        return_full_text=False,
    )
    text = (outputs[0] or {}).get("generated_text", "").strip()
    if not text:
        raise RuntimeError("Local model returned empty output.")

    model_label = adapter_path if adapter_path else model_name_or_path
    return {
        "reference_sheet": text,
        "model_used": f"local:{model_label}",
    }
