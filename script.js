// Global variables
let cameraStream = null;
let detectionHistory = JSON.parse(localStorage.getItem('anprHistory')) || [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadDetectionHistory();
});

// Preview Uploaded Image
function previewImage() {
    const fileInput = document.getElementById("fileInput");
    const preview = document.getElementById("preview");
    const detectBtn = document.querySelector('.detect-btn');

    const file = fileInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = () => {
            preview.src = reader.result;
            preview.style.display = 'block';
            detectBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    } else {
        preview.style.display = 'none';
        detectBtn.disabled = true;
    }
}

// Upload Image to Backend
async function uploadImage() {
    const fileInput = document.getElementById("fileInput");
    const plateNumber = document.getElementById("plateNumber");
    const confidence = document.getElementById("confidence");
    const processingTime = document.getElementById("processingTime");
    const resultDetails = document.getElementById("resultDetails");
    const downloadBtn = document.getElementById("downloadBtn");
    const btn = event.target;

    if (!fileInput.files.length) {
        showNotification("⚠️ Please choose an image first!", "warning");
        return;
    }

    // Show loading state
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading"></span>Processing...';
    btn.disabled = true;
    plateNumber.textContent = "Detecting...";
    plateNumber.classList.remove("detected");
    resultDetails.style.display = 'none';

    const startTime = performance.now();

    try {
        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        const res = await fetch("/upload", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }

        const data = await res.json();
        const endTime = performance.now();
        const processTime = Math.round(endTime - startTime);

        if (data.number_plate && data.number_plate !== "No plate detected") {
            plateNumber.textContent = data.number_plate;
            plateNumber.classList.add("detected");
            
            // Show additional details if available
            confidence.textContent = data.confidence ? `${(data.confidence * 100).toFixed(2)}%` : 'N/A';
            processingTime.textContent = processTime;
            resultDetails.style.display = 'block';
            
            downloadBtn.disabled = false;
            
            // Add to history
            addToHistory(data.number_plate, data.confidence, processTime);
            
            showNotification("✅ Number plate detected successfully!", "success");
        } else {
            plateNumber.textContent = "❌ No plate detected";
            plateNumber.classList.remove("detected");
            resultDetails.style.display = 'none';
            downloadBtn.disabled = true;
            showNotification("❌ No number plate found in the image", "error");
        }
    } catch (err) {
        console.error("Upload error:", err);
        plateNumber.textContent = "⚠️ Processing Error!";
        plateNumber.classList.remove("detected");
        resultDetails.style.display = 'none';
        downloadBtn.disabled = true;
        showNotification("⚠️ Failed to process image. Please try again.", "error");
    } finally {
        // Reset button state
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Initialize Webcam
async function initializeWebcam() {
    const webcam = document.getElementById("webcam");
    const cameraOverlay = document.getElementById("cameraOverlay");
    const startCameraBtn = document.getElementById("startCamera");
    const captureBtn = document.getElementById("captureBtn");
    const stopCameraBtn = document.getElementById("stopCamera");

    try {
        startCameraBtn.innerHTML = '<span class="loading"></span>Starting...';
        startCameraBtn.disabled = true;

        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment'
            } 
        });
        
        webcam.srcObject = stream;
        cameraStream = stream;
        cameraOverlay.style.display = 'none';
        
        captureBtn.disabled = false;
        stopCameraBtn.disabled = false;
        
        showNotification("📷 Camera activated successfully!", "success");
    } catch (err) {
        console.error("Camera error:", err);
        cameraOverlay.textContent = "❌ Camera Error";
        showNotification("❌ Camera access denied or not available", "error");
    } finally {
        startCameraBtn.innerHTML = "📷 Start Camera";
        startCameraBtn.disabled = false;
    }
}

// Stop Webcam
function stopWebcam() {
    const webcam = document.getElementById("webcam");
    const cameraOverlay = document.getElementById("cameraOverlay");
    const captureBtn = document.getElementById("captureBtn");
    const stopCameraBtn = document.getElementById("stopCamera");

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
        webcam.srcObject = null;
        cameraOverlay.style.display = 'flex';
        cameraOverlay.textContent = "Camera Off";
        
        captureBtn.disabled = true;
        stopCameraBtn.disabled = true;
        
        showNotification("📷 Camera turned off", "info");
    }
}

// Capture Frame from Webcam
async function captureFromWebcam() {
    const webcam = document.getElementById("webcam");
    const plateNumber = document.getElementById("plateNumber");
    const confidence = document.getElementById("confidence");
    const processingTime = document.getElementById("processingTime");
    const resultDetails = document.getElementById("resultDetails");
    const downloadBtn = document.getElementById("downloadBtn");
    const btn = document.getElementById("captureBtn");

    if (!cameraStream) {
        showNotification("⚠️ Please enable camera first!", "warning");
        return;
    }

    // Show loading state
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading"></span>Capturing...';
    btn.disabled = true;
    plateNumber.textContent = "Processing...";
    plateNumber.classList.remove("detected");
    resultDetails.style.display = 'none';

    const startTime = performance.now();

    try {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        
        canvas.width = webcam.videoWidth;
        canvas.height = webcam.videoHeight;
        ctx.drawImage(webcam, 0, 0, canvas.width, canvas.height);

        // Add visual feedback - flash effect
        webcam.style.transition = "filter 0.3s";
        webcam.style.filter = "brightness(1.5)";
        setTimeout(() => webcam.style.filter = "brightness(1)", 200);

        const blob = await new Promise(resolve => {
            canvas.toBlob(resolve, "image/jpeg", 0.8);
        });

        const formData = new FormData();
        formData.append("file", blob, "capture.jpg");

        const res = await fetch("/upload", {
            method: "POST",
            body: formData,
        });

        const data = await res.json();
        const endTime = performance.now();
        const processTime = Math.round(endTime - startTime);

        if (data.number_plate && data.number_plate !== "No plate detected") {
            plateNumber.textContent = data.number_plate;
            plateNumber.classList.add("detected");
            
            confidence.textContent = data.confidence ? `${(data.confidence * 100).toFixed(2)}%` : 'N/A';
            processingTime.textContent = processTime;
            resultDetails.style.display = 'block';
            
            downloadBtn.disabled = false;
            
            // Add to history
            addToHistory(data.number_plate, data.confidence, processTime);
            
            showNotification("✅ Number plate detected from camera!", "success");
        } else {
            plateNumber.textContent = "❌ No plate detected";
            plateNumber.classList.remove("detected");
            resultDetails.style.display = 'none';
            downloadBtn.disabled = true;
            showNotification("❌ No number plate found in the image", "error");
        }

    } catch (err) {
        console.error("Capture error:", err);
        plateNumber.textContent = "⚠️ Capture failed!";
        plateNumber.classList.remove("detected");
        resultDetails.style.display = 'none';
        downloadBtn.disabled = true;
        showNotification("⚠️ Failed to capture image", "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Download Result
function downloadResult() {
    const plateText = document.getElementById("plateNumber").textContent;
    if (plateText && !plateText.includes("Waiting") && !plateText.includes("No plate") && !plateText.includes("Detecting") && !plateText.includes("Error")) {
        const blob = new Blob([`Detected Number Plate: ${plateText}\nTimestamp: ${new Date().toLocaleString()}`], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `number_plate_${new Date().getTime()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        showNotification("📥 Result downloaded successfully!", "success");
    } else {
        showNotification("⚠️ No valid result to download!", "warning");
    }
}

// Clear All
function clearAll() {
    // Clear file input
    document.getElementById("fileInput").value = "";
    
    // Clear preview
    const preview = document.getElementById("preview");
    preview.src = "";
    preview.style.display = "none";
    
    // Clear results
    document.getElementById("plateNumber").textContent = "Waiting for detection...";
    document.getElementById("plateNumber").classList.remove("detected");
    document.getElementById("resultDetails").style.display = "none";
    document.getElementById("downloadBtn").disabled = true;
    
    // Disable detect button
    document.querySelector('.detect-btn').disabled = true;
    
    showNotification("🗑️ All inputs and results cleared!", "info");
}

// Add to detection history
function addToHistory(plate, confidence, processTime) {
    const historyItem = {
        plate: plate,
        confidence: confidence,
        processTime: processTime,
        timestamp: new Date().toLocaleString()
    };
    
    detectionHistory.unshift(historyItem);
    
    // Keep only last 10 items
    if (detectionHistory.length > 10) {
        detectionHistory = detectionHistory.slice(0, 10);
    }
    
    // Save to localStorage
    localStorage.setItem('anprHistory', JSON.stringify(detectionHistory));
    
    // Update UI
    loadDetectionHistory();
}

// Load detection history
function loadDetectionHistory() {
    const historyList = document.getElementById('historyList');
    
    if (detectionHistory.length === 0) {
        historyList.innerHTML = '<p class="no-history">No detection history yet</p>';
        return;
    }
    
    historyList.innerHTML = detectionHistory.map(item => `
        <div class="history-item">
            <span class="history-plate">${item.plate}</span>
            <span class="history-time">${item.timestamp}</span>
        </div>
    `).join('');
}

// Notification System
function showNotification(message, type = "info") {
    const container = document.getElementById('notificationContainer');
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Remove after 4 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => notification.remove(), 300);
        }
    }, 4000);
}

// Handle page unload to stop camera
window.addEventListener('beforeunload', stopWebcam);