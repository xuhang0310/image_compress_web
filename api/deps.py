import torch
import logging
from watermark.lama.model_manager import ModelManager
from watermark import AutoWatermarkRemover

logger = logging.getLogger(__name__)

# Global instances
_lama_model_manager = None
_watermark_remover = None

# Global config for Lama
LAMA_CONFIG = {
    "model": "lama",
    "device": None, # Will be auto-detected if None
}

def get_lama_model_manager():
    global _lama_model_manager
    if _lama_model_manager is None:
        if LAMA_CONFIG["device"]:
            device = torch.device(LAMA_CONFIG["device"])
        else:
            device = torch.device("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"Initializing Lama ModelManager on {device} with model {LAMA_CONFIG['model']}...")
        _lama_model_manager = ModelManager(LAMA_CONFIG["model"], device)
    return _lama_model_manager

def get_watermark_remover():
    global _watermark_remover
    if _watermark_remover is None:
        logger.info("Initializing AutoWatermarkRemover...")
        _watermark_remover = AutoWatermarkRemover()
    return _watermark_remover

def set_lama_config(model: str, device: str = None):
    LAMA_CONFIG["model"] = model
    if device:
        LAMA_CONFIG["device"] = device
