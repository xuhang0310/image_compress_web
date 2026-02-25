import cv2
import numpy as np
import torch
import random
import time
import logging
from PIL import Image
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response

from watermark.lama.schema import Config
from watermark.lama.helper import load_img, pil_to_bytes
from watermark.detector.strategies import PositionStrategy
from .deps import get_lama_model_manager, get_watermark_remover

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Strategy Pattern Interfaces ---

class InpaintingStrategy:
    """Abstract base class for inpainting mask generation strategies"""
    async def get_mask(self, image_np: np.ndarray, **kwargs) -> np.ndarray:
        raise NotImplementedError

class ManualMaskStrategy(InpaintingStrategy):
    """Strategy that uses a user-provided mask file"""
    async def get_mask(self, image_np: np.ndarray, mask_file: UploadFile, **kwargs) -> np.ndarray:
        logger.info("Strategy: Manual Mask")
        mask_bytes = await mask_file.read()
        mask_np, _ = load_img(mask_bytes, gray=True)
        # Ensure binary mask
        mask_np = cv2.threshold(mask_np, 127, 255, cv2.THRESH_BINARY)[1]
        
        # Resize if necessary
        if image_np.shape[:2] != mask_np.shape[:2]:
            logger.warning(f"Mask shape {mask_np.shape[:2]} mismatch Image shape {image_np.shape[:2]}. Resizing mask.")
            mask_np = cv2.resize(mask_np, (image_np.shape[1], image_np.shape[0]), interpolation=cv2.INTER_NEAREST)
            
        return mask_np

class AutoDetectionStrategy(InpaintingStrategy):
    """Strategy that automatically detects watermark to generate mask using smart position detection"""
    async def get_mask(self, image_np: np.ndarray, **kwargs) -> np.ndarray:
        logger.info("Strategy: Auto Detection (Smart Position)")
        
        # Define presets specifically for Doubao AI and common watermarks (Bottom-Right)
        # We prioritize bottom-right detection as requested by user
        
        # DYNAMIC PRESET CALCULATION
        # Analyze image dimensions to create tighter masks for different aspect ratios
        h, w = image_np.shape[:2]
        is_landscape = w > h
        
        # Base percentages
        if is_landscape:
            # For landscape (16:9), width is large, so we need a smaller percentage
            # e.g., 2730px * 10% = 273px (Enough for watermark)
            base_w_pct = 10
            # INCREASED HEIGHT: User reported residue, so we increase height coverage
            base_h_pct = 6  # Increased from 4 to 6
        else:
            # For portrait, width is smaller, so we need a larger percentage
            # e.g., 1000px * 20% = 200px
            base_w_pct = 20
            base_h_pct = 5
            
        # MAX PIXEL CAP (Crucial for high-res images)
        # Watermarks usually don't scale infinitely with resolution. 
        # Cap the mask size to avoid covering valid content in 4K+ images.
        max_watermark_w = 300  
        max_watermark_h = 120   # Increased from 70 to 120 to avoid residue
        
        # Convert max pixels to percentage
        max_w_pct = (max_watermark_w / w) * 100
        max_h_pct = (max_watermark_h / h) * 100
        
        # Use the smaller of the two (Base vs Max Cap)
        final_w_pct = min(base_w_pct, max_w_pct)
        final_h_pct = min(base_h_pct, max_h_pct)
        
        # Ensure minimums (don't go too small)
        final_w_pct = max(final_w_pct, 8) 
        final_h_pct = max(final_h_pct, 4)  # Increased min height from 3 to 4
        
        presets = [
            {
                'name': 'bottom-right-dynamic',
                'desc': f'Bottom Right (Dynamic: {final_w_pct:.1f}% x {final_h_pct:.1f}%)',
                'right_margin': 0, # Tight fit
                'bottom_margin': 0, # Tight fit
                'width_percent': final_w_pct,
                'height_percent': final_h_pct,
                'priority': 1
            },
            {
                'name': 'bottom-right-fallback',
                'desc': 'Bottom Right (Fallback)',
                'right_margin': 1, 
                'bottom_margin': 1,
                'width_percent': 25, 
                'height_percent': 8,
                'priority': 2
            }
        ]
        
        # Use existing PositionStrategy logic but with custom presets
        strategy = PositionStrategy(presets=presets)
        results = strategy.detect(image_np)
        
        mask_np = np.zeros(image_np.shape[:2], dtype=np.uint8)
        
        if results:
            # PositionStrategy returns results sorted by confidence/priority
            # We take the best result
            best_result = results[0]
            x1, y1, x2, y2 = best_result.bbox
            
            logger.info(f"Auto-detected watermark position: {best_result.bbox} (confidence: {best_result.confidence:.2f})")
            
            # Draw white rectangle on black mask
            cv2.rectangle(mask_np, (x1, y1), (x2, y2), (255), -1)
        else:
            # Fallback (Should rarely happen with PositionStrategy as it always checks presets)
            logger.warning("Position strategy returned no results. Using generic fallback.")
            
            h, w = image_np.shape[:2]
            
            # Generic bottom-right fallback
            mask_w = int(w * 0.20)  # Reduced from 0.35 to 0.20
            mask_w = max(mask_w, 200) # Reduced min width
            mask_w = min(mask_w, w)
            
            mask_h = int(h * 0.08)  # Reduced from 0.15 to 0.08
            mask_h = max(mask_h, 60)  # Reduced min height
            mask_h = min(mask_h, h)
            
            x1 = w - mask_w
            y1 = h - mask_h
            x2 = w
            y2 = h
            
            cv2.rectangle(mask_np, (x1, y1), (x2, y2), (255), -1)
            logger.info(f"Applied generic fallback mask at: {x1},{y1},{x2},{y2}")
            
        # Dilate mask slightly to ensure coverage (expand the mask region)
        # Doubao AI watermark might have some artifacts near edges
        kernel = np.ones((15, 15), np.uint8)
        mask_np = cv2.dilate(mask_np, kernel, iterations=1)
        
        return mask_np

async def _core_inpaint(
    image_np: np.ndarray,
    mask_np: np.ndarray,
    alpha_channel: np.ndarray,
    exif: bytes,
    config: Config
) -> Response:
    """Core inpainting logic shared by different endpoints"""
    model_manager = get_lama_model_manager()
    original_shape = image_np.shape
    
    if config.sd_seed == -1:
        config.sd_seed = random.randint(1, 999999999)
    if config.paint_by_example_seed == -1:
        config.paint_by_example_seed = random.randint(1, 999999999)

    # --- Enhanced Logging ---
    logger.info("="*50)
    logger.info("Starting Inpainting Process")
    logger.info(f"Image Shape: {original_shape}")
    logger.info(f"Mask Shape: {mask_np.shape}")
    
    # Calculate mask coverage
    mask_pixels = np.count_nonzero(mask_np)
    total_pixels = mask_np.size
    coverage = (mask_pixels / total_pixels) * 100
    logger.info(f"Mask Coverage: {mask_pixels} pixels ({coverage:.2f}%)")
    
    # Log Config Parameters
    logger.info("Inpainting Configuration:")
    # Convert config to dict if possible, or iterate attributes
    try:
        config_dict = config.dict() if hasattr(config, 'dict') else config.__dict__
        for key, value in config_dict.items():
            # Skip large binary data in logs
            if key in ['paint_by_example_example_image'] and value is not None:
                logger.info(f"  {key}: <Image Data>")
            else:
                logger.info(f"  {key}: {value}")
    except Exception as e:
        logger.warning(f"Failed to log detailed config: {e}")
    logger.info("="*50)
    # ------------------------

    logger.info(f"Origin image shape: {original_shape}")
    
    start = time.time()
    try:
        res_np_img = model_manager(image_np, mask_np, config)
    except RuntimeError as e:
        torch.cuda.empty_cache()
        if "CUDA out of memory" in str(e):
            raise HTTPException(status_code=500, detail="CUDA out of memory")
        else:
            logger.exception(e)
            raise HTTPException(status_code=500, detail=str(e))
    finally:
        logger.info(f"process time: {(time.time() - start) * 1000}ms")
        torch.cuda.empty_cache()

    # Post processing
    res_np_img = cv2.cvtColor(res_np_img.astype(np.uint8), cv2.COLOR_BGR2RGB)
    if alpha_channel is not None:
        if alpha_channel.shape[:2] != res_np_img.shape[:2]:
            alpha_channel = cv2.resize(
                alpha_channel, dsize=(res_np_img.shape[1], res_np_img.shape[0])
            )
        res_np_img = np.concatenate(
            (res_np_img, alpha_channel[:, :, np.newaxis]), axis=-1
        )

    ext = "png"
    if exif is not None:
        image_bytes = pil_to_bytes(Image.fromarray(res_np_img), ext, quality=95, exif=exif)
    else:
        image_bytes = pil_to_bytes(Image.fromarray(res_np_img), ext, quality=95)

    return Response(content=image_bytes, media_type=f"image/{ext}")

# --- Endpoints ---

@router.post("/api/watermark/auto-remove")
async def watermark_auto_remove(
    file: UploadFile = File(...),
    min_confidence: float = Form(0.5),
    visualize: bool = Form(False)
):
    """
    全自动检测并去除水印 (Legacy endpoint)
    """
    import uuid
    temp_id = uuid.uuid4().hex[:12]
    input_path = f"/tmp/watermark_input_{temp_id}.jpg"
    output_path = f"/tmp/watermark_output_{temp_id}.jpg"
    vis_path = f"/tmp/watermark_vis_{temp_id}.jpg" if visualize else None

    try:
        # 保存上传的文件
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 获取去除器实例
        watermark_remover = get_watermark_remover()

        # 执行去除
        result = watermark_remover.remove(
            input_path,
            output_path,
            min_confidence=min_confidence,
            visualize=visualize,
            visualization_path=vis_path
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Processing failed'))

        response = {
            "success": True,
            "detection": result['detection'],
            "processing_time": result['processing_time'],
            "output_url": f"/api/watermark/download/{temp_id}" # Note: Download endpoint might need implementation if not exists
        }
        return response
    except Exception as e:
        logger.error(f"Auto remove error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pass

@router.post("/inpaint")
async def inpaint_process(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    ldmSteps: int = Form(25),
    ldmSampler: str = Form("plms"),
    hdStrategy: str = Form("Original"),
    zitsWireframe: bool = Form(True),
    hdStrategyCropMargin: int = Form(128),
    hdStrategyCropTrigerSize: int = Form(2048),
    hdStrategyResizeLimit: int = Form(2048),
    prompt: str = Form(""),
    negativePrompt: str = Form(""),
    useCroper: bool = Form(False),
    croperX: int = Form(0),
    croperY: int = Form(0),
    croperHeight: int = Form(512),
    croperWidth: int = Form(512),
    sdScale: float = Form(1.0),
    sdMaskBlur: int = Form(5),
    sdStrength: float = Form(0.75),
    sdSteps: int = Form(50),
    sdGuidanceScale: float = Form(7.5),
    sdSampler: str = Form("uni_pc"),
    sdSeed: int = Form(-1),
    sdMatchHistograms: bool = Form(False),
    cv2Flag: str = Form("INPAINT_NS"),
    cv2Radius: int = Form(5),
    paintByExampleSteps: int = Form(50),
    paintByExampleGuidanceScale: float = Form(7.5),
    paintByExampleMaskBlur: int = Form(5),
    paintByExampleSeed: int = Form(-1),
    paintByExampleMatchHistograms: bool = Form(False),
    p2pSteps: int = Form(50),
    p2pImageGuidanceScale: float = Form(1.5),
    p2pGuidanceScale: float = Form(7.5),
    controlnet_conditioning_scale: float = Form(0.4),
    controlnet_method: str = Form("control_v11p_sd15_canny"),
    paintByExampleImage: UploadFile = File(None)
):
    """
    Inpainting API based on Lama Cleaner logic (Manual Mask)
    """
    # Read image
    origin_image_bytes = await image.read()
    image_np, alpha_channel, exif = load_img(origin_image_bytes, return_exif=True)
    
    # Strategy: Manual Mask
    strategy = ManualMaskStrategy()
    mask_np = await strategy.get_mask(image_np, mask_file=mask)
    
    # Handle Paint By Example
    pbe_image = None
    if paintByExampleImage:
        pbe_bytes = await paintByExampleImage.read()
        pbe_np, _ = load_img(pbe_bytes)
        pbe_image = Image.fromarray(pbe_np)

    # Config
    config = Config(
        ldm_steps=ldmSteps,
        ldm_sampler=ldmSampler,
        hd_strategy=hdStrategy,
        zits_wireframe=zitsWireframe,
        hd_strategy_crop_margin=hdStrategyCropMargin,
        hd_strategy_crop_trigger_size=hdStrategyCropTrigerSize,
        hd_strategy_resize_limit=hdStrategyResizeLimit,
        prompt=prompt,
        negative_prompt=negativePrompt,
        use_croper=useCroper,
        croper_x=croperX,
        croper_y=croperY,
        croper_height=croperHeight,
        croper_width=croperWidth,
        sd_scale=sdScale,
        sd_mask_blur=sdMaskBlur,
        sd_strength=sdStrength,
        sd_steps=sdSteps,
        sd_guidance_scale=sdGuidanceScale,
        sd_sampler=sdSampler,
        sd_seed=sdSeed,
        sd_match_histograms=sdMatchHistograms,
        cv2_flag=cv2Flag,
        cv2_radius=cv2Radius,
        paint_by_example_steps=paintByExampleSteps,
        paint_by_example_guidance_scale=paintByExampleGuidanceScale,
        paint_by_example_mask_blur=paintByExampleMaskBlur,
        paint_by_example_seed=paintByExampleSeed,
        paint_by_example_match_histograms=paintByExampleMatchHistograms,
        paint_by_example_example_image=pbe_image,
        p2p_steps=p2pSteps,
        p2p_image_guidance_scale=p2pImageGuidanceScale,
        p2p_guidance_scale=p2pGuidanceScale,
        controlnet_conditioning_scale=controlnet_conditioning_scale,
    )

    return await _core_inpaint(image_np, mask_np, alpha_channel, exif, config)

@router.post("/auto_inpaint")
async def auto_inpaint_process(
    image: UploadFile = File(...),
    ldmSteps: int = Form(25),
    ldmSampler: str = Form("plms"),
    hdStrategy: str = Form("Original"),
    zitsWireframe: bool = Form(True),
    hdStrategyCropMargin: int = Form(128),
    hdStrategyCropTrigerSize: int = Form(2048),
    hdStrategyResizeLimit: int = Form(2048),
    prompt: str = Form(""),
    negativePrompt: str = Form(""),
    useCroper: bool = Form(False),
    croperX: int = Form(0),
    croperY: int = Form(0),
    croperHeight: int = Form(512),
    croperWidth: int = Form(512),
    sdScale: float = Form(1.0),
    sdMaskBlur: int = Form(5),
    sdStrength: float = Form(0.75),
    sdSteps: int = Form(50),
    sdGuidanceScale: float = Form(7.5),
    sdSampler: str = Form("uni_pc"),
    sdSeed: int = Form(-1),
    sdMatchHistograms: bool = Form(False),
    cv2Flag: str = Form("INPAINT_NS"),
    cv2Radius: int = Form(5),
    paintByExampleSteps: int = Form(50),
    paintByExampleGuidanceScale: float = Form(7.5),
    paintByExampleMaskBlur: int = Form(5),
    paintByExampleSeed: int = Form(-1),
    paintByExampleMatchHistograms: bool = Form(False),
    p2pSteps: int = Form(50),
    p2pImageGuidanceScale: float = Form(1.5),
    p2pGuidanceScale: float = Form(7.5),
    controlnet_conditioning_scale: float = Form(0.4),
    controlnet_method: str = Form("control_v11p_sd15_canny"),
    paintByExampleImage: UploadFile = File(None)
):
    """
    Auto Inpainting API that automatically detects watermark and removes it.
    """
    # Read image
    origin_image_bytes = await image.read()
    image_np, alpha_channel, exif = load_img(origin_image_bytes, return_exif=True)
    
    # Strategy: Auto Detection
    strategy = AutoDetectionStrategy()
    mask_np = await strategy.get_mask(image_np)
    
    # Handle Paint By Example
    pbe_image = None
    if paintByExampleImage:
        pbe_bytes = await paintByExampleImage.read()
        pbe_np, _ = load_img(pbe_bytes)
        pbe_image = Image.fromarray(pbe_np)

    # Config
    config = Config(
        ldm_steps=ldmSteps,
        ldm_sampler=ldmSampler,
        hd_strategy=hdStrategy,
        zits_wireframe=zitsWireframe,
        hd_strategy_crop_margin=hdStrategyCropMargin,
        hd_strategy_crop_trigger_size=hdStrategyCropTrigerSize,
        hd_strategy_resize_limit=hdStrategyResizeLimit,
        prompt=prompt,
        negative_prompt=negativePrompt,
        use_croper=useCroper,
        croper_x=croperX,
        croper_y=croperY,
        croper_height=croperHeight,
        croper_width=croperWidth,
        sd_scale=sdScale,
        sd_mask_blur=sdMaskBlur,
        sd_strength=sdStrength,
        sd_steps=sdSteps,
        sd_guidance_scale=sdGuidanceScale,
        sd_sampler=sdSampler,
        sd_seed=sdSeed,
        sd_match_histograms=sdMatchHistograms,
        cv2_flag=cv2Flag,
        cv2_radius=cv2Radius,
        paint_by_example_steps=paintByExampleSteps,
        paint_by_example_guidance_scale=paintByExampleGuidanceScale,
        paint_by_example_mask_blur=paintByExampleMaskBlur,
        paint_by_example_seed=paintByExampleSeed,
        paint_by_example_match_histograms=paintByExampleMatchHistograms,
        paint_by_example_example_image=pbe_image,
        p2p_steps=p2pSteps,
        p2p_image_guidance_scale=p2pImageGuidanceScale,
        p2p_guidance_scale=p2pGuidanceScale,
        controlnet_conditioning_scale=controlnet_conditioning_scale,
    )

    return await _core_inpaint(image_np, mask_np, alpha_channel, exif, config)
