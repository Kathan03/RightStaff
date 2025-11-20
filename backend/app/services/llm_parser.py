"""
LLM-based resume parser using Phi-3-Mini for accurate field extraction.

REPLACES: Regex-based extraction (extract_name, extract_email, etc.)
KEEPS: Unstructured library for PDF/DOCX parsing

Why Phi-3-Mini?
- Small: 3.8B parameters (~8GB RAM)
- Fast: 50-100 tokens/sec on CPU
- Accurate: 85-90% for structured extraction
- Runs on: CPU (no GPU needed)
- Better than: spaCy NER + regex for names, skills, experience
"""

import asyncio
import json
import logging
import re
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy imports (only load when needed)
_torch = None
_transformers = None


def _import_dependencies():
    """Lazy import of heavy dependencies."""
    global _torch, _transformers

    if _torch is None or _transformers is None:
        try:
            import torch as t
            import transformers as tf
            _torch = t
            _transformers = tf
            logger.info("✅ Loaded torch and transformers")
        except ImportError as e:
            logger.error(f"❌ Failed to import dependencies: {e}")
            raise ImportError(
                "Missing dependencies. Install with: pip install torch transformers accelerate"
            ) from e

    return _torch, _transformers


class LLMResumeParser:
    """
    Lightweight LLM for resume field extraction.

    Uses microsoft/Phi-3-mini-4k-instruct for structured field extraction.
    All methods are async to prevent blocking the event loop.
    """

    def __init__(self, model_name: str = "microsoft/Phi-3-mini-4k-instruct"):
        """
        Initialize LLM parser (lazy loading).

        Args:
            model_name: HuggingFace model ID
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self._loading = False
        self._load_lock = asyncio.Lock()
        logger.info(f"🤖 LLM parser initialized (model will load on first use): {model_name}")

    async def _ensure_loaded(self):
        """
        Ensure model and tokenizer are loaded (lazy loading with lock).

        Why lazy loading?
        - Doesn't delay server startup
        - Only loads if LLM parsing is actually used
        - Saves memory if feature is disabled
        """
        if self.model is not None and self.tokenizer is not None:
            return  # Already loaded

        async with self._load_lock:
            # Double-check after acquiring lock
            if self.model is not None and self.tokenizer is not None:
                return

            logger.info(f"🔄 Loading LLM model: {self.model_name} (this may take 20-30 seconds)...")

            # Run loading in thread pool to avoid blocking
            await asyncio.to_thread(self._load_model)

            logger.info("✅ LLM model loaded successfully")

    def _load_model(self):
        """
        Load model and tokenizer (runs in thread pool).

        This is a synchronous method that runs in a separate thread.
        """
        torch, transformers = _import_dependencies()

        try:
            # Load tokenizer
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )

            # Load model with float16 for efficiency
            self.model = transformers.AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto",  # Auto CPU/GPU placement
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )

            logger.info(f"✅ Model loaded on device: {self.model.device}")

        except Exception as e:
            logger.error(f"❌ Failed to load LLM model: {e}")
            raise

    async def parse_resume(self, resume_text: str) -> Dict:
        """
        Extract structured fields from resume using LLM (async).

        Args:
            resume_text: Raw resume text (from Unstructured parser)

        Returns:
            {
                "full_name": str,
                "email": str,
                "phone": str,
                "location": {"city": str, "state": str, "country": str},
                "years_experience": float,
                "professional_summary": str,
                "skills": List[str]
            }
        """
        logger.info("📄 Starting LLM-based resume parsing")

        # Ensure model is loaded
        await self._ensure_loaded()

        # Truncate to 2000 chars (fits in 4k context)
        resume_snippet = resume_text[:2000]

        # Construct prompt
        prompt = f"""Extract information from this resume and return ONLY valid JSON.

Resume:
{resume_snippet}

Extract these fields:
1. full_name (string) - Candidate's full name
2. email (string) - Email address
3. phone (string) - Phone number
4. location (object) - {{"city": "...", "state": "...", "country": "..."}}
5. years_experience (number) - Total years calculated from employment dates
6. professional_summary (string) - 2-3 sentence summary of candidate's background
7. skills (array) - List of technical skills mentioned in resume

IMPORTANT:
- Return ONLY valid JSON, no explanation
- If field not found, use null
- Calculate years_experience from dates in resume
- Extract ALL skills mentioned (programming languages, frameworks, tools, etc.)

JSON:
{{"""

        # Run inference in thread pool to avoid blocking
        try:
            parsed_data = await asyncio.to_thread(self._run_inference, prompt)

            logger.info(f"✅ Parsed resume: {parsed_data.get('full_name', 'Unknown')}")
            logger.info(f"   Email: {parsed_data.get('email', 'N/A')}")
            logger.info(f"   Years: {parsed_data.get('years_experience', 'N/A')}")
            logger.info(f"   Skills: {len(parsed_data.get('skills', []))} found")

            return parsed_data

        except Exception as e:
            logger.error(f"❌ LLM parsing failed: {e}")
            return self._empty_structure()

    def _run_inference(self, prompt: str) -> Dict:
        """
        Run LLM inference (synchronous, runs in thread pool).

        Args:
            prompt: Formatted prompt

        Returns:
            Parsed data dictionary
        """
        torch, transformers = _import_dependencies()

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=3000
        )

        # Move to same device as model
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=500,
                temperature=0.1,  # Low temp for deterministic output
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        logger.debug(f"LLM response: {response[:200]}...")

        # Extract JSON from response
        parsed_data = self._extract_json(response)

        # Post-process and validate
        parsed_data = self._validate_and_clean(parsed_data)

        return parsed_data

    def _extract_json(self, response: str) -> Dict:
        """
        Extract JSON from LLM response.

        Handles cases where LLM adds text before/after JSON.
        """
        try:
            # Find JSON boundaries
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in response")
                return self._empty_structure()

            json_str = response[json_start:json_end]

            # Parse JSON
            parsed = json.loads(json_str)
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response: {response[:500]}")
            return self._empty_structure()

    def _validate_and_clean(self, data: Dict) -> Dict:
        """
        Validate and clean extracted data.

        - Ensure all expected keys exist
        - Clean phone/email formats
        - Validate years_experience is numeric
        - Ensure skills is a list
        """
        cleaned = {
            "full_name": self._clean_string(data.get("full_name")),
            "email": self._clean_email(data.get("email")),
            "phone": self._clean_phone(data.get("phone")),
            "location": self._clean_location(data.get("location")),
            "years_experience": self._clean_years(data.get("years_experience")),
            "professional_summary": self._clean_string(data.get("professional_summary")),
            "skills": self._clean_skills(data.get("skills"))
        }

        return cleaned

    def _clean_string(self, value) -> Optional[str]:
        """Clean string value."""
        if not value or value == "null":
            return None
        return str(value).strip()

    def _clean_email(self, value) -> Optional[str]:
        """Validate and clean email."""
        if not value:
            return None

        email = str(value).strip().lower()

        # Basic email validation
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email

        return None

    def _clean_phone(self, value) -> Optional[str]:
        """Clean phone number."""
        if not value:
            return None

        return str(value).strip()

    def _clean_location(self, value) -> Dict[str, Optional[str]]:
        """Clean location object."""
        if not value or not isinstance(value, dict):
            return {"city": None, "state": None, "country": None}

        return {
            "city": self._clean_string(value.get("city")),
            "state": self._clean_string(value.get("state")),
            "country": self._clean_string(value.get("country"))
        }

    def _clean_years(self, value) -> Optional[float]:
        """Clean years of experience."""
        if not value:
            return None

        try:
            years = float(value)
            # Sanity check: 0-50 years
            if 0 <= years <= 50:
                return round(years, 1)
        except (ValueError, TypeError):
            pass

        return None

    def _clean_skills(self, value) -> list:
        """Clean skills list."""
        if not value:
            return []

        if isinstance(value, list):
            return [str(s).strip() for s in value if s]

        if isinstance(value, str):
            # Split by comma if single string
            return [s.strip() for s in value.split(',') if s.strip()]

        return []

    def _empty_structure(self) -> Dict:
        """Return empty structure when parsing fails."""
        return {
            "full_name": None,
            "email": None,
            "phone": None,
            "location": {"city": None, "state": None, "country": None},
            "years_experience": None,
            "professional_summary": None,
            "skills": []
        }


# ═══════════════════════════════════════════════════════════════
# Singleton instance with lazy loading
# ═══════════════════════════════════════════════════════════════

_llm_parser_instance = None


def get_llm_parser() -> LLMResumeParser:
    """
    Get or create singleton LLM parser instance.

    Model loading is deferred until first parse_resume() call.
    Uses model name from settings (default: Qwen/Qwen2-1.5B-Instruct).
    """
    global _llm_parser_instance

    if _llm_parser_instance is None:
        from app.config import settings
        _llm_parser_instance = LLMResumeParser(model_name=settings.llm_parser_model)

    return _llm_parser_instance
