import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ValidationError
import requests
from io import BytesIO
from PIL import Image
import os
import mimetypes

logger = logging.getLogger(__name__)

# Constants
MAX_USER_INPUT_LENGTH = getattr(settings, 'MAX_USER_INPUT_LENGTH', 1000)
MAX_IMAGE_SIZE = getattr(settings, 'MAX_IMAGE_SIZE', 10 * 1024 * 1024)  # 10MB
MAX_IMAGE_DIMENSION = getattr(settings, 'MAX_IMAGE_DIMENSION', 5000)
ALLOWED_EXTENSIONS = getattr(settings, 'ALLOWED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
ALLOWED_MIME_TYPES = getattr(settings, 'ALLOWED_IMAGE_MIME_TYPES', ['image/jpeg', 'image/png', 'image/gif', 'image/webp'])


def index(request):
    """Shows the home page"""
    return render(request, 'index.html')


def validate_image_file(uploaded_file):
    """Validate uploaded image file for security and size"""
    errors = []
    
    # Check file size
    uploaded_file.seek(0, os.SEEK_END)
    file_size = uploaded_file.tell()
    uploaded_file.seek(0)  # Reset to beginning
    
    if file_size > MAX_IMAGE_SIZE:
        errors.append(f'File too large. Maximum size is {MAX_IMAGE_SIZE / (1024*1024):.1f}MB')
    
    if file_size == 0:
        errors.append('File is empty')
    
    # Check file extension
    filename = uploaded_file.name.lower()
    file_ext = os.path.splitext(filename)[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        errors.append(f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}')
    
    # Check MIME type
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type not in ALLOWED_MIME_TYPES:
        errors.append('Invalid file type detected')
    
    return errors


def validate_user_input(user_idea):
    """Validate and sanitize user input"""
    if not user_idea or not user_idea.strip():
        return None, 'Please describe what you want!'
    
    user_idea = user_idea.strip()
    
    if len(user_idea) > MAX_USER_INPUT_LENGTH:
        return None, f'Input too long. Maximum {MAX_USER_INPUT_LENGTH} characters allowed.'
    
    # Basic sanitization - remove potentially dangerous characters
    # Keep it simple for now, but could add more sophisticated sanitization
    user_idea = user_idea[:MAX_USER_INPUT_LENGTH]
    
    return user_idea, None


def generate_prompt(request):
    """Analyzes photo and generates prompt using FREE Groq AI"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    # Validate user input
    user_idea = request.POST.get('idea', '').strip()
    user_idea, input_error = validate_user_input(user_idea)
    if input_error:
        logger.warning(f"Invalid user input: {input_error}")
        return JsonResponse({'error': input_error}, status=400)
    
    # Validate uploaded file
    uploaded_image = request.FILES.get('photo')
    if not uploaded_image:
        return JsonResponse({'error': 'Please upload a photo!'}, status=400)
    
    # Validate image file
    validation_errors = validate_image_file(uploaded_image)
    if validation_errors:
        logger.warning(f"Image validation failed: {validation_errors}")
        return JsonResponse({'error': validation_errors[0]}, status=400)
    
    # Check API key
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '')
    if not groq_api_key or groq_api_key == 'YOUR_GROQ_KEY_HERE':
        logger.error("Groq API key not configured")
        return JsonResponse({
            'error': 'API key not configured. Please set GROQ_API_KEY in settings.py'
        }, status=500)
    
    try:
        # Open and validate image with PIL
        try:
            image = Image.open(uploaded_image)
            # Verify it's actually an image by trying to load it
            image.verify()
            # Reopen because verify() closes the image
            uploaded_image.seek(0)
            image = Image.open(uploaded_image)
        except Exception as e:
            logger.error(f"Invalid or corrupted image: {e}")
            return JsonResponse({'error': 'Invalid or corrupted image file'}, status=400)
        
        # Get image dimensions
        width, height = image.size
        
        # Validate dimensions
        if width == 0 or height == 0:
            return JsonResponse({'error': 'Invalid image dimensions'}, status=400)
        
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return JsonResponse({
                'error': f'Image too large. Maximum dimension is {MAX_IMAGE_DIMENSION}px'
            }, status=400)
        
        # Analyze image
        try:
            image_description = analyze_image_basic(image)
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            image_description = f"{width}x{height}px image"
        
        # Call Groq AI to generate prompt
        try:
            prompt_text = generate_prompt_with_groq(user_idea, image_description, width, height, groq_api_key)
        except requests.exceptions.Timeout:
            logger.error("Groq API timeout")
            prompt_text = generate_fallback_prompt(user_idea, width, height)
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {e}")
            prompt_text = generate_fallback_prompt(user_idea, width, height)
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            prompt_text = generate_fallback_prompt(user_idea, width, height)
        
        return JsonResponse({
            'success': True,
            'prompt': prompt_text
        })
                
    except Exception as e:
        logger.exception(f"Unexpected error in generate_prompt: {e}")
        return JsonResponse({
            'error': 'An error occurred processing your request. Please try again.'
        }, status=500)


def analyze_image_basic(image):
    """Basic image analysis without AI"""
    try:
        width, height = image.size
        
        # Prevent division by zero
        if height == 0:
            return "square oriented photo, medium lighting"
        
        aspect_ratio = width / height
        
        # Determine orientation
        if aspect_ratio > 1.3:
            orientation = "landscape"
        elif aspect_ratio < 0.8:
            orientation = "portrait"
        else:
            orientation = "square"
        
        # Analyze brightness safely
        try:
            grayscale = image.convert('L')
            pixels = list(grayscale.getdata())
            if pixels:
                avg_brightness = sum(pixels) / len(pixels)
                
                if avg_brightness > 170:
                    brightness = "bright"
                elif avg_brightness < 85:
                    brightness = "dark"
                else:
                    brightness = "medium"
            else:
                brightness = "medium"
        except Exception:
            brightness = "medium"
        
        description = f"{orientation} oriented photo, {brightness} lighting"
        return description
    except Exception as e:
        logger.error(f"Error in analyze_image_basic: {e}")
        return "photo with standard characteristics"


def generate_prompt_with_groq(user_idea, image_info, width, height, api_key):
    """Call FREE Groq AI to generate professional prompt"""
    
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are an expert at creating detailed prompts for AI image editing tools. Create professional, technical prompts.'
                    },
                    {
                        'role': 'user',
                        'content': f"""Image details: {image_info}, dimensions {width}x{height}px

User wants to: {user_idea}

Create a SPECIFIC, DETAILED prompt for AI image editing that:
- References the current image characteristics
- Specifies exact changes needed
- Includes technical details (lighting values, color codes, blur radius, etc.)
- Uses professional photography/editing terminology
- Is 2-4 sentences long

Respond ONLY with the prompt, nothing else."""
                    }
                ],
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            # Safely extract prompt with validation
            if 'choices' in data and len(data['choices']) > 0:
                if 'message' in data['choices'][0] and 'content' in data['choices'][0]['message']:
                    prompt_text = data['choices'][0]['message']['content'].strip()
                    if prompt_text:
                        return prompt_text
            
            # If structure is unexpected, use fallback
            logger.warning("Unexpected API response structure")
            return generate_fallback_prompt(user_idea, width, height)
        else:
            logger.error(f"Groq API Error {response.status_code}: {response.text[:200]}")
            return generate_fallback_prompt(user_idea, width, height)
            
    except requests.exceptions.Timeout:
        logger.error("Groq API timeout")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Groq API request exception: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_prompt_with_groq: {e}")
        raise


def generate_fallback_prompt(user_idea, width, height):
    """Generate prompt if API fails (backup system)"""
    user_lower = user_idea.lower()
    
    if 'blur' in user_lower and 'background' in user_lower:
        return f"Apply gaussian blur (50px radius) to background while keeping foreground sharp. Use bokeh effect at f/1.8. Maintain {width}x{height}px dimensions."
    
    elif 'sunset' in user_lower or 'golden hour' in user_lower:
        return f"Transform to golden hour lighting with 3200K color temperature. Add warm orange (#FFA500) and amber tones. Create long shadows. Preserve {width}x{height}px."
    
    elif 'professional' in user_lower:
        return f"Apply professional color grading with balanced tones. Enhance sharpness and clarity. Add subtle vignette. Studio-quality output at {width}x{height}px."
    
    elif 'bright' in user_lower or 'brighter' in user_lower:
        return f"Increase exposure by +1.5 stops. Boost luminosity in midtones and shadows. Maintain highlight detail. Output: {width}x{height}px."
    
    elif 'vibrant' in user_lower or 'colorful' in user_lower:
        return f"Increase color saturation by 30%. Boost vibrancy while maintaining natural tones. Output: {width}x{height}px."
    
    else:
        return f"Enhance photo with: {user_idea}. Apply professional editing techniques while maintaining natural appearance. Output: {width}x{height}px."

def generate_edit(request):
    """Original photo edit prompt generator"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    # Validate user input
    user_idea = request.POST.get('idea', '').strip()
    user_idea, input_error = validate_user_input(user_idea)
    if input_error:
        logger.warning(f"Invalid user input: {input_error}")
        return JsonResponse({'error': input_error}, status=400)
    
    # Validate uploaded file
    uploaded_image = request.FILES.get('photo')
    if not uploaded_image:
        return JsonResponse({'error': 'Please upload a photo!'}, status=400)
    
    # Validate image file
    validation_errors = validate_image_file(uploaded_image)
    if validation_errors:
        logger.warning(f"Image validation failed: {validation_errors}")
        return JsonResponse({'error': validation_errors[0]}, status=400)
    
    # Check API key
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '')
    if not groq_api_key or groq_api_key == 'YOUR_GROQ_KEY_HERE':
        logger.error("Groq API key not configured")
        return JsonResponse({
            'error': 'API key not configured. Please set GROQ_API_KEY in settings.py'
        }, status=500)
    
    try:
        # Open and validate image with PIL
        try:
            image = Image.open(uploaded_image)
            image.verify()
            uploaded_image.seek(0)
            image = Image.open(uploaded_image)
        except Exception as e:
            logger.error(f"Invalid or corrupted image: {e}")
            return JsonResponse({'error': 'Invalid or corrupted image file'}, status=400)
        
        width, height = image.size
        
        if width == 0 or height == 0:
            return JsonResponse({'error': 'Invalid image dimensions'}, status=400)
        
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return JsonResponse({
                'error': f'Image too large. Maximum dimension is {MAX_IMAGE_DIMENSION}px'
            }, status=400)
        
        # Analyze image
        try:
            image_description = analyze_image_basic(image)
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            image_description = f"{width}x{height}px image"
        
        # Call Groq AI
        try:
            prompt_text = generate_prompt_with_groq(user_idea, image_description, width, height, groq_api_key)
        except requests.exceptions.Timeout:
            logger.error("Groq API timeout")
            prompt_text = generate_fallback_prompt(user_idea, width, height)
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {e}")
            prompt_text = generate_fallback_prompt(user_idea, width, height)
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            prompt_text = generate_fallback_prompt(user_idea, width, height)
        
        return JsonResponse({'success': True, 'prompt': prompt_text})
                
    except Exception as e:
        logger.exception(f"Unexpected error in generate_edit: {e}")
        return JsonResponse({
            'error': 'An error occurred processing your request. Please try again.'
        }, status=500)


def generate_thumbnail(request):
    """Thumbnail prompt generator"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    thumbnail_text = request.POST.get('text', '').strip()
    style_desc = request.POST.get('style', '').strip()
    uploaded_image = request.FILES.get('photo')  # Optional
    
    if not thumbnail_text:
        return JsonResponse({'error': 'Please enter text for thumbnail'}, status=400)
    
    if not style_desc:
        return JsonResponse({'error': 'Please describe thumbnail style'}, status=400)
    
    if len(thumbnail_text) > MAX_USER_INPUT_LENGTH:
        return JsonResponse({'error': f'Text too long. Maximum {MAX_USER_INPUT_LENGTH} characters'}, status=400)
    
    if len(style_desc) > MAX_USER_INPUT_LENGTH:
        return JsonResponse({'error': f'Style description too long. Maximum {MAX_USER_INPUT_LENGTH} characters'}, status=400)
    
    # Check API key
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '')
    if not groq_api_key or groq_api_key == 'YOUR_GROQ_KEY_HERE':
        logger.error("Groq API key not configured")
        return JsonResponse({
            'error': 'API key not configured. Please set GROQ_API_KEY in settings.py'
        }, status=500)
    
    try:
        image_info = ""
        if uploaded_image:
            # Validate optional image
            validation_errors = validate_image_file(uploaded_image)
            if validation_errors:
                logger.warning(f"Image validation failed: {validation_errors}")
                # Don't fail, just skip image info
            else:
                try:
                    image = Image.open(uploaded_image)
                    image.verify()
                    uploaded_image.seek(0)
                    image = Image.open(uploaded_image)
                    width, height = image.size
                    if width > 0 and height > 0:
                        image_info = f"Base image: {width}x{height}px. "
                except Exception as e:
                    logger.warning(f"Could not process optional image: {e}")
        
        # Call Groq AI
        try:
            prompt_text = generate_thumbnail_prompt_with_groq(
                thumbnail_text,
                style_desc,
                image_info,
                groq_api_key
            )
        except requests.exceptions.Timeout:
            logger.error("Groq API timeout")
            prompt_text = generate_fallback_thumbnail_prompt(thumbnail_text, style_desc)
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {e}")
            prompt_text = generate_fallback_thumbnail_prompt(thumbnail_text, style_desc)
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            prompt_text = generate_fallback_thumbnail_prompt(thumbnail_text, style_desc)
        
        return JsonResponse({'success': True, 'prompt': prompt_text})
                
    except Exception as e:
        logger.exception(f"Unexpected error in generate_thumbnail: {e}")
        return JsonResponse({
            'error': 'An error occurred processing your request. Please try again.'
        }, status=500)


def generate_style(request):
    """Style transfer prompt generator"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    description = request.POST.get('description', '').strip()
    original_image = request.FILES.get('original')
    inspired_image = request.FILES.get('inspired')
    
    if not description:
        return JsonResponse({'error': 'Please describe what to match'}, status=400)
    
    if not original_image:
        return JsonResponse({'error': 'Please upload your photo to edit'}, status=400)
    
    if not inspired_image:
        return JsonResponse({'error': 'Please upload inspiration photo'}, status=400)
    
    if len(description) > MAX_USER_INPUT_LENGTH:
        return JsonResponse({'error': f'Description too long. Maximum {MAX_USER_INPUT_LENGTH} characters'}, status=400)
    
    # Validate images
    validation_errors = validate_image_file(original_image)
    if validation_errors:
        logger.warning(f"Original image validation failed: {validation_errors}")
        return JsonResponse({'error': f'Original image: {validation_errors[0]}'}, status=400)
    
    validation_errors = validate_image_file(inspired_image)
    if validation_errors:
        logger.warning(f"Inspired image validation failed: {validation_errors}")
        return JsonResponse({'error': f'Inspiration image: {validation_errors[0]}'}, status=400)
    
    # Check API key
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '')
    if not groq_api_key or groq_api_key == 'YOUR_GROQ_KEY_HERE':
        logger.error("Groq API key not configured")
        return JsonResponse({
            'error': 'API key not configured. Please set GROQ_API_KEY in settings.py'
        }, status=500)
    
    try:
        # Analyze original image
        try:
            orig_img = Image.open(original_image)
            orig_img.verify()
            original_image.seek(0)
            orig_img = Image.open(original_image)
            orig_width, orig_height = orig_img.size
            
            if orig_width == 0 or orig_height == 0:
                return JsonResponse({'error': 'Invalid original image dimensions'}, status=400)
            
            orig_analysis = analyze_image_basic(orig_img)
        except Exception as e:
            logger.error(f"Invalid original image: {e}")
            return JsonResponse({'error': 'Invalid or corrupted original image'}, status=400)
        
        # Analyze inspiration image
        try:
            insp_img = Image.open(inspired_image)
            insp_img.verify()
            inspired_image.seek(0)
            insp_img = Image.open(inspired_image)
            insp_width, insp_height = insp_img.size
            
            if insp_width == 0 or insp_height == 0:
                return JsonResponse({'error': 'Invalid inspiration image dimensions'}, status=400)
            
            insp_analysis = analyze_image_basic(insp_img)
        except Exception as e:
            logger.error(f"Invalid inspiration image: {e}")
            return JsonResponse({'error': 'Invalid or corrupted inspiration image'}, status=400)
        
        # Call Groq AI
        try:
            prompt_text = generate_style_transfer_prompt_with_groq(
                orig_analysis,
                insp_analysis,
                description,
                orig_width,
                orig_height,
                groq_api_key
            )
        except requests.exceptions.Timeout:
            logger.error("Groq API timeout")
            prompt_text = generate_fallback_style_prompt(description, orig_width, orig_height)
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {e}")
            prompt_text = generate_fallback_style_prompt(description, orig_width, orig_height)
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            prompt_text = generate_fallback_style_prompt(description, orig_width, orig_height)
        
        return JsonResponse({'success': True, 'prompt': prompt_text})
                
    except Exception as e:
        logger.exception(f"Unexpected error in generate_style: {e}")
        return JsonResponse({
            'error': 'An error occurred processing your request. Please try again.'
        }, status=500)        
def generate_thumbnail_prompt_with_groq(text, style, image_info, api_key):
    """Generate YouTube thumbnail prompt"""
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{
                    'role': 'system',
                    'content': 'You are a YouTube thumbnail expert. Create viral, click-worthy thumbnail prompts with perfect text placement and composition.'
                }, {
                    'role': 'user',
                    'content': f"""{image_info}

Create a YouTube thumbnail with text: "{text}"
Style: {style}

Generate a DETAILED prompt for AI image generation that includes:
- Exact text placement and typography
- Bold, attention-grabbing visual elements
- High contrast colors (specify hex codes)
- Facial expressions (if applicable)
- Background composition
- Visual indicators (arrows, circles, highlights)
- Lighting setup
- Output: 1920x1080px, optimized for small screens

Make it VIRAL-WORTHY. Respond with ONLY the prompt."""
                }],
                'temperature': 0.8,
                'max_tokens': 600
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                if 'message' in data['choices'][0] and 'content' in data['choices'][0]['message']:
                    prompt_text = data['choices'][0]['message']['content'].strip()
                    if prompt_text:
                        return prompt_text
            
            logger.warning("Unexpected API response structure for thumbnail")
            return generate_fallback_thumbnail_prompt(text, style)
        else:
            logger.error(f"Groq API Error {response.status_code}: {response.text[:200]}")
            return generate_fallback_thumbnail_prompt(text, style)
    except Exception as e:
        logger.error(f"Error in generate_thumbnail_prompt_with_groq: {e}")
        raise


def generate_style_transfer_prompt_with_groq(orig_analysis, insp_analysis, description, width, height, api_key):
    """Generate style transfer prompt"""
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{
                    'role': 'system',
                    'content': 'You are an expert at analyzing photos and creating style transfer prompts that precisely replicate visual qualities.'
                }, {
                    'role': 'user',
                    'content': f"""Original photo to edit: {orig_analysis}, {width}x{height}px
Inspiration photo qualities: {insp_analysis}

User wants to: {description}

Create a DETAILED prompt that will transform the original photo to match the inspiration's:
- Lighting setup (direction, intensity, temperature)
- Color grading (specific values, LUTs)
- Atmosphere and mood
- Contrast and tonal range
- Texture and detail level
- Post-processing style

Be SPECIFIC with technical values. Respond with ONLY the prompt."""
                }],
                'temperature': 0.7,
                'max_tokens': 700
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                if 'message' in data['choices'][0] and 'content' in data['choices'][0]['message']:
                    prompt_text = data['choices'][0]['message']['content'].strip()
                    if prompt_text:
                        return prompt_text
            
            logger.warning("Unexpected API response structure for style transfer")
            return generate_fallback_style_prompt(description, width, height)
        else:
            logger.error(f"Groq API Error {response.status_code}: {response.text[:200]}")
            return generate_fallback_style_prompt(description, width, height)
    except Exception as e:
        logger.error(f"Error in generate_style_transfer_prompt_with_groq: {e}")
        raise


def generate_fallback_thumbnail_prompt(text, style):
    """Fallback thumbnail prompt"""
    return f"""Create a YouTube thumbnail with bold text "{text}". {style} style. Use high-contrast colors (red #FF0000, yellow #FFD700, blue #0080FF). Include dramatic lighting with strong shadows. Add visual elements like arrows or circles to draw attention. Bold, thick typography with white outline. Face with exaggerated expression if applicable. Background: dramatic, blurred, complementary colors. Output: 1920x1080px, optimized for mobile viewing."""


def generate_fallback_style_prompt(description, width, height):
    """Fallback style transfer prompt"""
    return f"""Transform image to match inspiration photo. Apply the following based on reference: match lighting direction and temperature (3200K-6500K range), replicate color grading with similar saturation and hue shifts, copy contrast levels and tonal curve, match texture and detail sharpness, apply similar post-processing effects. User request: {description}. Maintain {width}x{height}px. Preserve subject while adapting style."""
