// Global variable to store download URL
let currentDownloadUrl = null;
let uploadedDocuments = [];
let uploadedAudioFiles = [];

// Tab functionality
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', function() {
        const tabName = this.dataset.tab;
        
        // Remove active class from all tabs and contents
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Add active class to clicked tab and corresponding content
        this.classList.add('active');
        document.getElementById(tabName).classList.add('active');
    });
});

// Utility functions
function showLoading(text = "Processing your request... This may take a moment.") {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loading').classList.add('show');
    document.getElementById('result').classList.remove('show');
    document.getElementById('downloadInfo').style.display = 'none';
}

function hideResultAndLoading() {
    document.getElementById('loading').classList.remove('show');
    document.getElementById('result').classList.remove('show');
    document.getElementById('downloadInfo').style.display = 'none';
    document.getElementById('editableResults').classList.remove('show');
    // Clean up the previous download URL
    if (currentDownloadUrl) {
        window.URL.revokeObjectURL(currentDownloadUrl);
        currentDownloadUrl = null;
    }
}

function showResult(content, title = "Processed Result:", isError = false) {
    const result = document.getElementById('result');
    const resultTitle = document.getElementById('resultTitle');
    const resultContent = document.getElementById('resultContent');
    
    resultTitle.textContent = title;
    resultContent.innerHTML = content;
    
    if (isError) {
        result.classList.add('error');
    } else {
        result.classList.remove('error');
    }
    
    result.classList.add('show');
    document.getElementById('loading').classList.remove('show');
}

function showDownloadSuccess(downloadUrl, filename) {
    // Store the download URL globally
    currentDownloadUrl = downloadUrl;
    
    // Set up the download button
    const downloadBtn = document.getElementById('downloadZipBtn');
    downloadBtn.onclick = function() {
        const a = document.createElement('a');
        a.href = currentDownloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };
    
    document.getElementById('downloadInfo').style.display = 'block';
    document.getElementById('loading').classList.remove('show');
}

function showDownloadSuccessBase64(base64Data, filename, contentType) {
    // Set up the download button with base64 data
    const downloadBtn = document.getElementById('downloadZipBtn');
    downloadBtn.onclick = function() {
        downloadBase64File(base64Data, filename, contentType);
    };
    
    // Update button text based on file type
    if (contentType && contentType.includes('zip')) {
        downloadBtn.textContent = 'Download ZIP file!';
    } else {
        downloadBtn.textContent = 'Download PDF file!';
    }
    
    document.getElementById('downloadInfo').style.display = 'block';
    document.getElementById('loading').classList.remove('show');
}

// File Management Functionality
function renderDocumentFiles() {
    const documentFileList = document.getElementById('documentFileList');
    const documentFiles = document.getElementById('documentFiles');
    
    if (uploadedDocuments.length === 0) {
        documentFileList.style.display = 'none';
        return;
    }

    documentFileList.style.display = 'block';
    documentFiles.innerHTML = uploadedDocuments.map((file, index) => {
        const fileIcon = getFileIcon(file.name);
        return `
            <div class="attached-file">
                <div class="file-info-compact">
                    <span class="file-type-icon">${fileIcon}</span>
                    <div class="file-name-size">
                        <div class="file-name-compact" title="${file.name}">${file.name}</div>
                        <div class="file-size-compact">${formatFileSize(file.size)}</div>
                    </div>
                </div>
                <button type="button" class="remove-file-btn" onclick="removeDocumentFile(${index})" title="Remove file">×</button>
            </div>
        `;
    }).join('');
}

function renderAudioFiles() {
    const audioFileList = document.getElementById('audioFileList');
    const audioFiles = document.getElementById('audioFiles');
    
    if (uploadedAudioFiles.length === 0) {
        audioFileList.style.display = 'none';
        return;
    }

    audioFileList.style.display = 'block';
    audioFiles.innerHTML = uploadedAudioFiles.map((file, index) => {
        const fileIcon = getFileIcon(file.name);
        return `
            <div class="attached-file">
                <div class="file-info-compact">
                    <span class="file-type-icon">${fileIcon}</span>
                    <div class="file-name-size">
                        <div class="file-name-compact" title="${file.name}">${file.name}</div>
                        <div class="file-size-compact">${formatFileSize(file.size)}</div>
                    </div>
                </div>
                <button type="button" class="remove-file-btn" onclick="removeAudioFile(${index})" title="Remove file">×</button>
            </div>
        `;
    }).join('');
}

// Global functions to remove files
window.removeDocumentFile = function(index) {
    uploadedDocuments.splice(index, 1);
    renderDocumentFiles();
};

window.removeAudioFile = function(index) {
    uploadedAudioFiles.splice(index, 1);
    renderAudioFiles();
};

function getFileIcon(filename) {
    const ext = filename.toLowerCase().split('.').pop();
    switch (ext) {
        case 'pdf': return '📄';
        case 'doc': return '📝';
        case 'docx': return '📝';
        case 'txt': return '📃';
        case 'html': return '🌐';
        case 'mp3': return '📝';
        case 'm4a': return '🎵';
        default: return '📎';
    }
}

// Tab 1: Text input processing
document.getElementById('textForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const textInput = document.getElementById('textInput');
    if (!textInput.value.trim()) {
        alert('Please enter some text to process.');
        return;
    }

    const btn = document.getElementById('downloadBtn');
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Processing...';
    hideResultAndLoading();
    showLoading("Processing text and extracting fields...");
    
    try {
        const response = await fetch('/api/process_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'text': textInput.value
            })
        });
        
        if (response.ok) {
            const responseData = await response.json();
            
            if (responseData.error) {
                throw new Error(responseData.error);
            }
            
            // Show editable results form with JSON data and original file
            showEditableResults(responseData.json_data, {
                file_data: responseData.file_data,
                filename: responseData.filename,
                content_type: responseData.content_type
            });
        } else {
            throw new Error('Processing failed');
        }
        
    } catch (error) {
        showResult('An error occurred while processing the text. Please try again.', 'Error', true);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
});

// Tab 2: Document upload functionality
const documentUpload = document.getElementById('documentUpload');
const documentInput = document.getElementById('documentInput');

documentUpload.addEventListener('click', () => documentInput.click());

documentUpload.addEventListener('dragover', (e) => {
    e.preventDefault();
    documentUpload.classList.add('dragover');
});

documentUpload.addEventListener('dragleave', () => {
    documentUpload.classList.remove('dragover');
});

documentUpload.addEventListener('drop', (e) => {
    e.preventDefault();
    documentUpload.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(file => 
        file.name.toLowerCase().endsWith('.txt') || 
        file.name.toLowerCase().endsWith('.docx') || 
        file.name.toLowerCase().endsWith('.html')
    );
    files.forEach(file => {
        const exists = uploadedDocuments.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
            uploadedDocuments.push(file);
        }
    });
    renderDocumentFiles();
});

documentInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
        const exists = uploadedDocuments.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
            uploadedDocuments.push(file);
        }
    });
    renderDocumentFiles();
    e.target.value = '';
});

async function handleDocumentFiles(files) {
    if (files.length === 0) return;

    const btn = document.getElementById('processDocumentsBtn');
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Processing...';
    hideResultAndLoading();
    showLoading("Processing and converting documents...");

    try {
        // Convert files to base64
        const base64Files = [];
        for (const file of files) {
            const base64Content = await fileToBase64(file);
            base64Files.push({
                filename: file.name,
                content: base64Content,
                content_type: file.type
            });
        }

        const response = await fetch('/api/process_documents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                files: base64Files
            })
        });

        if (response.ok) {
            const responseData = await response.json();
            
            if (responseData.error) {
                throw new Error(responseData.error);
            }
            
            // Clear the uploaded documents after successful processing
            uploadedDocuments = [];
            renderDocumentFiles();
            
            // Show download button with base64 data
            showDownloadSuccessBase64(responseData.file_data, responseData.filename, responseData.content_type);
        } else {
            throw new Error('Processing failed');
        }

    } catch (error) {
        showResult('Error processing documents: ' + error.message, 'Processing Error', true);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

document.getElementById('processDocumentsBtn').addEventListener('click', () => {
    if (uploadedDocuments.length === 0) {
        documentInput.click();
    } else {
        handleDocumentFiles(uploadedDocuments);
    }
});

// Tab 3: Audio upload functionality
const audioUpload = document.getElementById('audioUpload');
const audioInput = document.getElementById('audioInput');

audioUpload.addEventListener('click', () => audioInput.click());

audioUpload.addEventListener('dragover', (e) => {
    e.preventDefault();
    audioUpload.classList.add('dragover');
});

audioUpload.addEventListener('dragleave', () => {
    audioUpload.classList.remove('dragover');
});

audioUpload.addEventListener('drop', (e) => {
    e.preventDefault();
    audioUpload.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(file => 
        file.name.toLowerCase().endsWith('.mp3') || file.name.toLowerCase().endsWith('.m4a')
    );
    files.forEach(file => {
        const exists = uploadedAudioFiles.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
            uploadedAudioFiles.push(file);
        }
    });
    renderAudioFiles();
});

audioInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
        const exists = uploadedAudioFiles.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
            uploadedAudioFiles.push(file);
        }
    });
    renderAudioFiles();
    e.target.value = '';
});

async function handleAudioFiles(files) {
    if (files.length === 0) return;

    const btn = document.getElementById('processAudioBtn');
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Processing...';
    hideResultAndLoading();
    showLoading("Transcribing and processing audio files...");

    try {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        
        const response = await fetch('/api/process_audio', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const responseData = await response.json();
            
            if (responseData.error) {
                throw new Error(responseData.error);
            }
            
            // Clear the uploaded audio files after successful processing
            uploadedAudioFiles = [];
            renderAudioFiles();
            
            // Show download button with base64 data
            showDownloadSuccessBase64(responseData.file_data, responseData.filename, responseData.content_type);
        } else {
            throw new Error('Processing failed');
        }

    } catch (error) {
        showResult('Error processing audio files: ' + error.message, 'Processing Error', true);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

document.getElementById('processAudioBtn').addEventListener('click', () => {
    if (uploadedAudioFiles.length === 0) {
        audioInput.click();
    } else {
        handleAudioFiles(uploadedAudioFiles);
    }
});

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            // Remove the data URL prefix (e.g., "data:text/plain;base64,")
            const base64String = reader.result.split(',')[1];
            resolve(base64String);
        };
        reader.onerror = error => reject(error);
    });
}

// Global variables to store current data
let currentJsonData = null;
let originalFileData = null;

// Show editable results form with populated data
function showEditableResults(jsonData, fileData = null) {
    currentJsonData = jsonData;
    originalFileData = fileData;
    
    // Populate form fields
    document.getElementById('edit_recipients_info').value = jsonData.recipients_info || '';
    document.getElementById('edit_diagnosis').value = jsonData.diagnosis || '';
    document.getElementById('edit_next_review').value = jsonData.next_review || '';
    document.getElementById('edit_corrected_visual_acuity_right').value = jsonData.corrected_visual_acuity_right || '';
    document.getElementById('edit_corrected_visual_acuity_left').value = jsonData.corrected_visual_acuity_left || '';
    
    // Handle letter_to_patient - use the prepared text version
    let letterText = jsonData.letter_to_patient_text || '';
    if (!letterText && Array.isArray(jsonData.letter_to_patient)) {
        letterText = jsonData.letter_to_patient.join('\n\n');
    } else if (!letterText && typeof jsonData.letter_to_patient === 'string') {
        // Remove HTML tags and convert to plain text
        letterText = jsonData.letter_to_patient
            .replace(/<p[^>]*>/g, '')
            .replace(/<\/p>/g, '\n')
            .replace(/<span[^>]*>/g, '')
            .replace(/<\/span>/g, '')
            .replace(/\n\s*\n/g, '\n\n')
            .trim();
    }
    document.getElementById('edit_letter_to_patient').value = letterText;
    
    // Show/hide download original button
    const downloadOriginalBtn = document.getElementById('downloadOriginalBtn');
    if (originalFileData) {
        downloadOriginalBtn.style.display = 'inline-block';
        // Update button text based on file type
        if (originalFileData.content_type && originalFileData.content_type.includes('zip')) {
            downloadOriginalBtn.textContent = '📥 Download Original ZIP';
        } else {
            downloadOriginalBtn.textContent = '📥 Download Original PDF';
        }
        downloadOriginalBtn.onclick = function() {
            downloadBase64File(originalFileData.file_data, originalFileData.filename, originalFileData.content_type);
        };
    } else {
        downloadOriginalBtn.style.display = 'none';
    }
    
    // Hide loading and show editable form
    document.getElementById('loading').classList.remove('show');
    document.getElementById('editableResults').classList.add('show');
}

// Function to download base64 file
function downloadBase64File(base64Data, filename, contentType) {
    try {
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], {type: contentType});
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error downloading file:', error);
        alert('Error downloading file. Please try again.');
    }
}

// Handle form submission for regenerating document
document.getElementById('editableForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const btn = document.getElementById('regenerateBtn');
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Generating...';
    hideResultAndLoading();
    showLoading("Regenerating document with updated fields...");
    
    try {
        // Collect form data
        const formData = new FormData(this);
        const updatedData = {
            recipients_info: formData.get('recipients_info'),
            diagnosis: formData.get('diagnosis'),
            next_review: formData.get('next_review'),
            corrected_visual_acuity_right: formData.get('corrected_visual_acuity_right'),
            corrected_visual_acuity_left: formData.get('corrected_visual_acuity_left'),
            letter_to_patient: formData.get('letter_to_patient').split('\n\n') // Convert back to array
        };
        
        // Send to process_json endpoint
        const response = await fetch('/api/process_json', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                document: updatedData
            })
        });
        
        if (response.ok) {
            const contentType = response.headers.get('content-type');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            
            // Determine filename based on content type
            let filename = 'processed_document.pdf';
            if (contentType && contentType.includes('zip')) {
                filename = 'processed_documents.zip';
            }
            
            showDownloadSuccess(url, filename);
        } else {
            throw new Error('Document generation failed');
        }
        
    } catch (error) {
        showResult('Error generating document: ' + error.message, 'Generation Error', true);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
});

// Handle cancel button
document.getElementById('cancelEditBtn').addEventListener('click', function() {
    hideResultAndLoading();
});

// Recording functionality
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let recordingTimer = null;
let isRecordingPaused = false;
let pausedTime = 0;

// Recording UI elements
const startRecordBtn = document.getElementById('startRecordBtn');
const pauseRecordBtn = document.getElementById('pauseRecordBtn');
const stopRecordBtn = document.getElementById('stopRecordBtn');
const recordingState = document.getElementById('recordingState');
const recordingTime = document.getElementById('recordingTime');
const recordingIcon = document.getElementById('recordingIcon');
const audioPreview = document.getElementById('audioPreview');
const audioPlayback = document.getElementById('audioPlayback');
const discardRecordBtn = document.getElementById('discardRecordBtn');
const sendRecordBtn = document.getElementById('sendRecordBtn');

// Format time for display
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Update recording timer
function updateRecordingTime() {
    if (recordingStartTime && !isRecordingPaused) {
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        recordingTime.textContent = formatTime(elapsed);
    }
}

// Reset recording UI
function resetRecordingUI() {
    startRecordBtn.disabled = false;
    pauseRecordBtn.disabled = true;
    stopRecordBtn.disabled = true;
    recordingState.textContent = 'Ready to record';
    recordingTime.textContent = '00:00';
    recordingIcon.className = 'recording-icon';
    audioPreview.style.display = 'none';
    
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
    
    recordingStartTime = null;
    pausedTime = 0;
    isRecordingPaused = false;
    audioChunks = [];
}

// Start recording
startRecordBtn.addEventListener('click', async function() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/wav'
        });
        
        audioChunks = [];
        
        mediaRecorder.ondataavailable = function(event) {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = function() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
            const audioUrl = URL.createObjectURL(audioBlob);
            audioPlayback.src = audioUrl;
            audioPreview.style.display = 'block';
            
            // Store the blob for sending to backend
            audioPlayback.recordedBlob = audioBlob;
            
            // Stop all tracks to release microphone
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        
        recordingStartTime = Date.now();
        pausedTime = 0;
        isRecordingPaused = false;
        
        startRecordBtn.disabled = true;
        pauseRecordBtn.disabled = false;
        stopRecordBtn.disabled = false;
        
        recordingState.textContent = 'Recording...';
        recordingIcon.className = 'recording-icon recording';
        
        recordingTimer = setInterval(updateRecordingTime, 1000);
        
    } catch (error) {
        alert('Error accessing microphone: ' + error.message);
        console.error('Error accessing microphone:', error);
    }
});

// Pause/Resume recording
pauseRecordBtn.addEventListener('click', function() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.pause();
        isRecordingPaused = true;
        // Store the total elapsed time up to this pause
        pausedTime = Math.floor((Date.now() - recordingStartTime + pausedTime) / 1000);
        
        pauseRecordBtn.textContent = '▶️ Resume';
        recordingState.textContent = 'Paused';
        recordingIcon.className = 'recording-icon paused';
        
    } else if (mediaRecorder && mediaRecorder.state === 'paused') {
        mediaRecorder.resume();
        isRecordingPaused = false;
        // Reset start time and convert pausedTime back to milliseconds
        recordingStartTime = Date.now() - (pausedTime * 1000);
        pausedTime = 0;
        
        pauseRecordBtn.textContent = '⏸️ Pause';
        recordingState.textContent = 'Recording...';
        recordingIcon.className = 'recording-icon recording';
    }
});

// Stop recording
stopRecordBtn.addEventListener('click', function() {
    if (mediaRecorder && (mediaRecorder.state === 'recording' || mediaRecorder.state === 'paused')) {
        mediaRecorder.stop();
        
        startRecordBtn.disabled = false;
        pauseRecordBtn.disabled = true;
        pauseRecordBtn.textContent = '⏸️ Pause';
        stopRecordBtn.disabled = true;
        
        recordingState.textContent = 'Recording complete';
        recordingIcon.className = 'recording-icon';
        
        if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
        }
    }
});

// Discard recording
discardRecordBtn.addEventListener('click', function() {
    if (audioPlayback.src) {
        URL.revokeObjectURL(audioPlayback.src);
    }
    resetRecordingUI();
});

// Send recording to backend
sendRecordBtn.addEventListener('click', async function() {
    if (!audioPlayback.recordedBlob) {
        alert('No recording available to send.');
        return;
    }

    const btn = sendRecordBtn;
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Sending...';
    hideResultAndLoading();
    showLoading("Processing recorded audio...");
    
    try {
        const formData = new FormData();
        const filename = `recording_${Date.now()}.mp3`;
        formData.append('files', audioPlayback.recordedBlob, filename);
        
        const response = await fetch('/api/process_audio', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const responseData = await response.json();
            
            if (responseData.error) {
                throw new Error(responseData.error);
            }
            
            // Reset recording UI after successful processing
            resetRecordingUI();
            
            // Show download button with base64 data
            showDownloadSuccessBase64(responseData.file_data, responseData.filename, responseData.content_type);
        } else {
            throw new Error('Processing failed');
        }

    } catch (error) {
        showResult('Error processing recording: ' + error.message, 'Processing Error', true);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
});

// Check for microphone support
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    document.getElementById('recording').innerHTML = `
        <div class="form-group">
            <div class="recording-container">
                <div class="recording-status">
                    <div class="recording-icon">❌</div>
                    <div class="recording-info">
                        <div class="recording-state" style="color: #e74c3c;">Microphone not supported</div>
                        <p style="color: #7f8c8d; margin-top: 15px;">
                            Your browser doesn't support microphone recording. Please use the Audio Files tab to upload pre-recorded files.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    `;
}
