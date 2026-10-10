import base64
import io
import logging
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Attempt imports for Pillow and pytesseract
try:
    from PIL import Image, ImageStat, ImageOps, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageStat = None
    ImageOps = None
    ImageEnhance = None
    ImageFilter = None

try:
    import pytesseract
    from pytesseract import Output
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None
    Output = None


class OCRStatus(str, Enum):
    OCR_SUCCESS = "OCR_SUCCESS"
    OCR_FAILED = "OCR_FAILED"
    OCR_LOW_CONFIDENCE = "OCR_LOW_CONFIDENCE"
    OCR_PENDING = "OCR_PENDING"
    OCR_NOT_REQUIRED = "OCR_NOT_REQUIRED"


class OCRResult(BaseModel):
    extracted_text: str = ""
    confidence: float = 0.0
    status: OCRStatus = OCRStatus.OCR_PENDING
    error_message: Optional[str] = None


class HandwrittenOCRService:
    """
    Production-oriented OCR Service for extracting handwritten text from uploaded student answer images.
    Features:
    - Preprocessing: EXIF transpose, scaling, grayscale conversion, contrast enhancement, sharpening
    - Validation: Rejects meaningless noise/symbols ('--', '..', '---'), enforces min alphanumeric count
    - Multi-pass OCR: Bounded 2-pass deterministic Tesseract configurations (--psm 6 and --psm 3)
    """

    def validate_image(self, image_bytes: bytes) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        Performs basic capture validation on image bytes:
        - Image can be decoded by PIL
        - Resolution is sufficient (width >= 100, height >= 100)
        - Image is not completely blank (variance/stddev > 3.0)
        """
        if not PIL_AVAILABLE or Image is None:
            return False, "Image processing library (Pillow) is not available.", None

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return False, f"Invalid or corrupt image format: {str(e)}", None

        width, height = img.size
        if width < 100 or height < 100:
            return False, f"Image resolution too low ({width}x{height}). Minimum required resolution is 100x100.", img

        try:
            # Respect EXIF orientation tag if present
            if ImageOps is not None:
                img = ImageOps.exif_transpose(img)
        except Exception as e:
            logger.debug(f"EXIF transpose check skipped: {e}")

        # Blank check via image pixel variation
        try:
            grayscale = img.convert("L")
            stat = ImageStat.Stat(grayscale) if ImageStat is not None else None
            stddev = stat.stddev[0] if stat and stat.stddev else 0.0
            if stddev < 3.0:
                return False, "Image appears to be blank or completely uniform.", img
        except Exception as e:
            logger.warning(f"Could not compute image stddev check: {e}")

        return True, None, img

    def _preprocess_image(self, pil_img: Any, pass_mode: str = "enhanced_grayscale") -> Any:
        """
        Preprocesses PIL image copy for Tesseract OCR:
        - EXIF transpose correction
        - Resizing preserving aspect ratio (scaling small text, capping giant dimensions)
        - Grayscale conversion
        - Autocontrast & contrast enhancement
        - Sharpening or binarization
        """
        try:
            if ImageOps is not None:
                img = ImageOps.exif_transpose(pil_img)
            else:
                img = pil_img.copy()
        except Exception:
            img = pil_img.copy()

        w, h = img.size
        max_dim = max(w, h)

        if max_dim < 1200:
            scale_factor = 1400.0 / max_dim
            new_w = max(100, int(w * scale_factor))
            new_h = max(100, int(h * scale_factor))
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize((new_w, new_h), resample_method)
        elif max_dim > 2400:
            scale_factor = 2000.0 / max_dim
            new_w = max(100, int(w * scale_factor))
            new_h = max(100, int(h * scale_factor))
            resample_method = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize((new_w, new_h), resample_method)

        grayscale = img.convert("L")

        if pass_mode == "enhanced_grayscale":
            try:
                if ImageOps is not None:
                    grayscale = ImageOps.autocontrast(grayscale, cutoff=1)
            except Exception:
                pass
            if ImageEnhance is not None:
                grayscale = ImageEnhance.Contrast(grayscale).enhance(1.6)
                grayscale = ImageEnhance.Sharpness(grayscale).enhance(1.4)
            return grayscale

        elif pass_mode == "binarized_high_contrast":
            if ImageEnhance is not None:
                grayscale = ImageEnhance.Contrast(grayscale).enhance(2.0)
            try:
                mean_val = ImageStat.Stat(grayscale).mean[0] if ImageStat is not None else 128
                threshold = max(80, min(200, int(mean_val)))
                grayscale = grayscale.point(lambda p: 255 if p > threshold else 0)
            except Exception:
                pass
            return grayscale

        return grayscale

    def _validate_ocr_text_and_confidence(
        self, text: str, confidences: List[float]
    ) -> Tuple[OCRStatus, float, str]:
        """
        Validates OCR text output to ensure:
        1. Non-empty normalized text
        2. Sufficient alphanumeric character count (>= 3)
        3. Excludes noise/symbol-only strings like '--', '..', '- -'
        4. Validates confidence score against thresholds
        """
        raw_normalized = text.strip()
        clean_lines = [line.strip() for line in raw_normalized.splitlines() if line.strip()]
        normalized_text = "\n".join(clean_lines)

        alphanumerics = [c for c in normalized_text if c.isalnum()]
        words = [w for w in normalized_text.split() if any(c.isalnum() for c in w)]

        # Valid confidences (Tesseract returns -1 for empty blocks)
        valid_confs = [c for c in confidences if isinstance(c, (int, float)) and c >= 0]
        avg_conf = (sum(valid_confs) / len(valid_confs) / 100.0) if valid_confs else (0.75 if alphanumerics else 0.0)
        avg_conf = max(0.0, min(1.0, round(avg_conf, 2)))

        # Rule 1: No alphanumeric characters or fewer than 3 alphanumerics -> Noise / Unreadable
        if len(alphanumerics) < 3 or len(words) == 0:
            return OCRStatus.OCR_FAILED, 0.0, ""

        non_space_chars = [c for c in normalized_text if not c.isspace()]
        alnum_ratio = len(alphanumerics) / len(non_space_chars) if non_space_chars else 0.0

        # Rule 2: High proportion of symbol noise (e.g. ------.....------)
        if alnum_ratio < 0.30:
            return OCRStatus.OCR_FAILED, 0.0, ""

        # Rule 3: Valid text with good confidence score
        if avg_conf >= 0.35 and alnum_ratio >= 0.35:
            return OCRStatus.OCR_SUCCESS, avg_conf, normalized_text

        # Rule 4: Marginal text or lower confidence -> Queue for examiner review
        if len(alphanumerics) >= 3 and alnum_ratio >= 0.25 and avg_conf >= 0.15:
            return OCRStatus.OCR_LOW_CONFIDENCE, avg_conf, normalized_text

        return OCRStatus.OCR_FAILED, 0.0, ""

    def _run_single_ocr_pass(
        self, pil_img: Any, pass_mode: str, psm_mode: int
    ) -> Tuple[OCRStatus, float, str, Optional[str]]:
        """Executes a single Tesseract OCR pass with given preprocessing pass_mode and psm_mode."""
        if not PYTESSERACT_AVAILABLE or pytesseract is None:
            return OCRStatus.OCR_FAILED, 0.0, "", "PyTesseract library unavailable."

        ocr_img = self._preprocess_image(pil_img, pass_mode=pass_mode)
        config_str = f"--psm {psm_mode}"

        try:
            text = pytesseract.image_to_string(ocr_img, config=config_str).strip()

            confidences = []
            if Output is not None:
                data = pytesseract.image_to_data(ocr_img, config=config_str, output_type=Output.DICT)
                for conf in data.get("conf", []):
                    if conf is not None and isinstance(conf, (int, float)) and conf >= 0:
                        confidences.append(float(conf))

            status, conf, clean_text = self._validate_ocr_text_and_confidence(text, confidences)
            return status, conf, clean_text, None
        except Exception as e:
            return OCRStatus.OCR_FAILED, 0.0, "", str(e)

    def extract_text(self, image_data: str) -> OCRResult:
        """
        Extracts handwritten text using a 2-pass deterministic Tesseract OCR pipeline with strict validation.
        """
        if not image_data:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                status=OCRStatus.OCR_FAILED,
                error_message="No image data provided.",
            )

        # 1. Parse base64 string
        try:
            if "," in image_data:
                header, encoded = image_data.split(",", 1)
            else:
                encoded = image_data
            image_bytes = base64.b64decode(encoded)
        except Exception as e:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                status=OCRStatus.OCR_FAILED,
                error_message=f"Failed to decode base64 image data: {str(e)}",
            )

        # 2. Validate Image
        is_valid, val_err, pil_img = self.validate_image(image_bytes)
        if not is_valid or pil_img is None:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                status=OCRStatus.OCR_FAILED,
                error_message=val_err or "Image validation failed.",
            )

        if not PYTESSERACT_AVAILABLE or pytesseract is None:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                status=OCRStatus.OCR_FAILED,
                error_message="OCR engine is not installed or available.",
            )

        # 3. Multi-Pass OCR Execution
        # Pass 1: Enhanced Grayscale with PSM 6 (Uniform text block)
        status1, conf1, text1, err1 = self._run_single_ocr_pass(
            pil_img, pass_mode="enhanced_grayscale", psm_mode=6
        )

        # If Pass 1 is high confidence OCR_SUCCESS, return immediately
        if status1 == OCRStatus.OCR_SUCCESS and conf1 >= 0.50 and len(text1) >= 10:
            return OCRResult(
                extracted_text=text1,
                confidence=conf1,
                status=OCRStatus.OCR_SUCCESS,
                error_message=None,
            )

        # Pass 2: Binarized High Contrast with PSM 3 (Auto page segmentation)
        status2, conf2, text2, err2 = self._run_single_ocr_pass(
            pil_img, pass_mode="binarized_high_contrast", psm_mode=3
        )

        # Compare Pass 1 and Pass 2 results deterministically
        def score_pass(st: OCRStatus, cf: float, txt: str) -> float:
            if st == OCRStatus.OCR_SUCCESS:
                alnum_count = len([c for c in txt if c.isalnum()])
                return 100.0 + cf * 10.0 + min(alnum_count, 50)
            elif st == OCRStatus.OCR_LOW_CONFIDENCE:
                return 50.0 + cf * 10.0
            return 0.0

        score1 = score_pass(status1, conf1, text1)
        score2 = score_pass(status2, conf2, text2)

        if score1 >= score2 and score1 > 0:
            final_status, final_conf, final_text = status1, conf1, text1
        elif score2 > score1 and score2 > 0:
            final_status, final_conf, final_text = status2, conf2, text2
        else:
            final_status, final_conf, final_text = OCRStatus.OCR_FAILED, 0.0, ""

        if final_status == OCRStatus.OCR_FAILED:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                status=OCRStatus.OCR_FAILED,
                error_message="No clear handwritten text recognized in answer image.",
            )

        return OCRResult(
            extracted_text=final_text,
            confidence=final_conf,
            status=final_status,
            error_message="Low OCR confidence score." if final_status == OCRStatus.OCR_LOW_CONFIDENCE else None,
        )


handwritten_ocr_service = HandwrittenOCRService()
