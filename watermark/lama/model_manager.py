import torch
import gc

from watermark.lama.const import SD15_MODELS
from watermark.lama.helper import switch_mps_device
from watermark.lama.model.controlnet import ControlNet
from watermark.lama.model.fcf import FcF
from watermark.lama.model.lama import LaMa
from watermark.lama.model.ldm import LDM
from watermark.lama.model.manga import Manga
from watermark.lama.model.mat import MAT
from watermark.lama.model.paint_by_example import PaintByExample
from watermark.lama.model.instruct_pix2pix import InstructPix2Pix
from watermark.lama.model.sd import SD15, SD2, Anything4, RealisticVision14
from watermark.lama.model.zits import ZITS
from watermark.lama.model.opencv2 import OpenCV2
from watermark.lama.schema import Config

models = {
    "lama": LaMa,
    "ldm": LDM,
    "zits": ZITS,
    "mat": MAT,
    "fcf": FcF,
    SD15.name: SD15,
    Anything4.name: Anything4,
    RealisticVision14.name: RealisticVision14,
    "cv2": OpenCV2,
    "manga": Manga,
    "sd2": SD2,
    "paint_by_example": PaintByExample,
    "instruct_pix2pix": InstructPix2Pix,
}


class ModelManager:
    def __init__(self, name: str, device: torch.device, **kwargs):
        self.name = name
        self.device = device
        self.kwargs = kwargs
        self.model = self.init_model(name, device, **kwargs)

    def init_model(self, name: str, device, **kwargs):
        if name in SD15_MODELS and kwargs.get("sd_controlnet", False):
            return ControlNet(device, **{**kwargs, "name": name})

        if name in models:
            model = models[name](device, **kwargs)
        else:
            raise NotImplementedError(f"Not supported model: {name}")
        return model

    def is_downloaded(self, name: str) -> bool:
        if name in models:
            return models[name].is_downloaded()
        else:
            raise NotImplementedError(f"Not supported model: {name}")

    def __call__(self, image, mask, config: Config):
        return self.model(image, mask, config)

    def switch(self, new_name: str):
        if new_name == self.name:
            return
        try:
            if torch.cuda.memory_allocated() > 0:
                # Clear current loaded model from memory
                torch.cuda.empty_cache()
                del self.model
                gc.collect()

            self.model = self.init_model(
                new_name, switch_mps_device(new_name, self.device), **self.kwargs
            )
            self.name = new_name
        except NotImplementedError as e:
            raise e
