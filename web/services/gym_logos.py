"""Bounded decoding of private gym branding; browser metadata is not authority."""
from io import BytesIO
import warnings

from PIL import Image, ImageOps

from web.constants import UPLOAD_MAX_LOGO_SIZE_BYTES

MAX_LOGO_PIXELS = 16_000_000
_FORMATS = {"PNG": ({".png"}, "image/png"),
    "JPEG": ({".jpg", ".jpeg"}, "image/jpeg"), "WEBP": ({".webp"}, "image/webp")}


def normalize_logo(content: bytes, extension: str) -> tuple[bytes, str]:
    """Validate decoded pixels and re-encode without EXIF or other source metadata."""
    if not 0 < len(content) <= UPLOAD_MAX_LOGO_SIZE_BYTES:
        raise ValueError("El logo debe contener una imagen de hasta 2 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                output_format = image.format
                allowed, content_type = _FORMATS[output_format]
                if (extension not in allowed or image.width * image.height > MAX_LOGO_PIXELS
                        or getattr(image, "n_frames", 1) != 1):
                    raise ValueError("Invalid logo dimensions or format")
                image.load()
                normalized = ImageOps.exif_transpose(image).convert("RGB" if output_format == "JPEG" else "RGBA")
                normalized.info.clear()
                output = BytesIO()
                normalized.save(output, format=output_format)
                result = output.getvalue()
                if len(result) > UPLOAD_MAX_LOGO_SIZE_BYTES:
                    raise ValueError("Normalized logo exceeds size limit")
                return result, content_type
    except (OSError, ValueError, KeyError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValueError("El logo debe ser una imagen PNG, JPG o WebP válida, sin animación y de hasta 16 megapíxeles.") from None
