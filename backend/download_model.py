#!/usr/bin/env python3
"""
Pre-download LLM models for instant inference.

Run this script ONCE before using the resume parser:
    python download_model.py

This downloads and caches the models so they're ready for instant use.
The models are stored in ~/.cache/huggingface/hub/

Benefits:
- First resume parse will be instant (no download delay)
- Can verify models work before running the application
- Download during setup rather than during first user request
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings


def download_models():
    """Download and cache both primary and fallback models."""
    print("=" * 60)
    print("RightStaff LLM Model Downloader")
    print("=" * 60)

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        print(f"\n❌ Missing dependencies: {e}")
        print("Install with: pip install torch transformers")
        sys.exit(1)

    models = [
        (settings.llm_parser_model, "Primary"),
        (settings.llm_fallback_model, "Fallback"),
    ]

    print(f"\nModels to download:")
    for model_name, role in models:
        print(f"  - {role}: {model_name}")

    print(f"\nCache directory: ~/.cache/huggingface/hub/")
    print("-" * 60)

    for model_name, role in models:
        print(f"\n📥 Downloading {role} model: {model_name}")

        try:
            # Download tokenizer
            print(f"   Downloading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            print(f"   ✅ Tokenizer downloaded")

            # Download model
            print(f"   Downloading model weights...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float32,  # Download in FP32
                low_cpu_mem_usage=True
            )
            print(f"   ✅ Model downloaded")

            # Get model size
            param_count = sum(p.numel() for p in model.parameters())
            size_mb = param_count * 4 / (1024 * 1024)  # FP32 = 4 bytes
            print(f"   📊 Parameters: {param_count:,} ({size_mb:.0f} MB in FP32)")

            # Cleanup to free memory
            del model
            del tokenizer

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            import gc
            gc.collect()

            print(f"   ✅ {role} model ready!")

        except Exception as e:
            print(f"   ❌ Failed to download {model_name}: {e}")
            continue

    print("\n" + "=" * 60)
    print("✅ Model download complete!")
    print("=" * 60)
    print("\nThe models are now cached and ready for instant inference.")
    print("Start your backend server and the first parse will be fast!")
    print("\nTo clear old models and free disk space:")
    print("  rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen2-1.5B-Instruct")
    print("  rm -rf ~/.cache/huggingface/hub/models--microsoft--Phi-3-mini-4k-instruct")
    print("  rm -rf ~/.cache/huggingface/hub/models--TinyLlama--TinyLlama-1.1B-Chat-v1.0")


if __name__ == "__main__":
    download_models()
