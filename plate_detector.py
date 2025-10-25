# plate_detector.py
"""
Enhanced Number Plate Detection Module
Uses multiple preprocessing techniques for better accuracy
"""

import cv2
import pytesseract
import numpy as np
import re

# Path to Tesseract executable (adjust based on your system)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image):
    """
    Apply multiple preprocessing techniques to enhance image quality
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Noise reduction
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    contrast_enhanced = clahe.apply(denoised)
    
    # Binarization using adaptive threshold
    binary = cv2.adaptiveThreshold(
        contrast_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    return binary, contrast_enhanced, gray

def detect_plate_regions(image):
    """
    Detect potential number plate regions using multiple methods
    """
    height, width = image.shape[:2]
    plates = []
    
    # Method 1: Edge detection + contour analysis
    edged = cv2.Canny(image, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 1000 or area > (height * width * 0.3):  # Filter by area
            continue
            
        # Check for rectangular shape
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        
        if len(approx) == 4:  # Quadrilateral
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            
            # Typical number plate aspect ratios (adjust based on your region)
            if 2.0 <= aspect_ratio <= 5.0 and w > 100 and h > 30:
                plates.append((x, y, w, h))
    
    return plates

def extract_text_from_plate(plate_image):
    """
    Extract text from plate region using multiple OCR configurations
    """
    # Try different Tesseract configurations
    configs = [
        '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        '--psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    ]
    
    best_text = ""
    best_confidence = 0
    
    for config in configs:
        try:
            data = pytesseract.image_to_data(plate_image, config=config, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence for this configuration
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                
                if avg_confidence > best_confidence:
                    best_confidence = avg_confidence
                    # Combine text with reasonable confidence
                    text_parts = []
                    for i, text in enumerate(data['text']):
                        if text.strip() and int(data['conf'][i]) > 30:
                            text_parts.append(text.strip())
                    best_text = ' '.join(text_parts)
        except Exception as e:
            continue
    
    return best_text.strip(), best_confidence

def clean_plate_text(text):
    """
    Clean and validate extracted plate text
    """
    if not text:
        return ""
    
    # Remove special characters and extra spaces
    cleaned = re.sub(r'[^A-Z0-9\s]', '', text.upper())
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Basic validation for Indian number plates (adjust for your region)
    # Format: XX99XX9999 or similar patterns
    if len(cleaned) >= 6 and len(cleaned) <= 12:
        return cleaned
    
    return ""

def detect_number_plate(image_path):
    """
    Main function to detect number plate from image
    Returns: {'number_plate': text, 'confidence': float, 'bounding_box': [x,y,w,h]}
    """
    try:
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            return {'number_plate': 'Error: Could not read image', 'confidence': 0.0}
        
        # Preprocess image
        binary, enhanced, gray = preprocess_image(image)
        
        # Detect plate regions
        plate_regions = detect_plate_regions(binary)
        
        if not plate_regions:
            # Try with enhanced image if no plates found
            plate_regions = detect_plate_regions(enhanced)
        
        best_plate = ""
        best_confidence = 0
        best_region = None
        
        # Process each detected region
        for region in plate_regions:
            x, y, w, h = region
            
            # Extract plate region from enhanced image
            plate_roi = enhanced[y:y+h, x:x+w]
            
            # Resize for better OCR (if too small)
            if w < 200:
                scale_factor = 300 / w
                new_width = int(w * scale_factor)
                new_height = int(h * scale_factor)
                plate_roi = cv2.resize(plate_roi, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # Extract text
            text, confidence = extract_text_from_plate(plate_roi)
            cleaned_text = clean_plate_text(text)
            
            if cleaned_text and confidence > best_confidence:
                best_plate = cleaned_text
                best_confidence = confidence
                best_region = region
        
        if best_plate:
            return {
                'number_plate': best_plate,
                'confidence': best_confidence / 100.0,  # Convert to 0-1 scale
                'bounding_box': best_region
            }
        else:
            return {
                'number_plate': 'No plate detected',
                'confidence': 0.0,
                'bounding_box': None
            }
            
    except Exception as e:
        return {
            'number_plate': f'Error: {str(e)}',
            'confidence': 0.0,
            'bounding_box': None
        }

# Test function
if __name__ == "__main__":
    result = detect_number_plate("test_image.jpg")
    print(f"Detected Plate: {result['number_plate']}")
    print(f"Confidence: {result['confidence']:.2f}")