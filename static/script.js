// Global variables
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
    document.getElementById('multipleResultsContainer').classList.remove('show');
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

function showDownloadSuccess(htmlResults) {
    // Set up the download button to generate DOCX from HTML
    const downloadBtn = document.getElementById('downloadZipBtn');
    downloadBtn.onclick = function() {
        if (htmlResults && htmlResults.length > 0) {
            // Use the first HTML result to generate DOCX
            convertHtmlToDocx(htmlResults[0]);
        }
    };
    
    downloadBtn.textContent = 'Download DOCX file!';
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
            console.log(responseData);
            
            if (responseData.error) {
                throw new Error(responseData.error);
            }
            
            // Show editable results form with JSON data
            showEditableResults(responseData.json_data);
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
            
            // Show editable results form for all results
            if (responseData.json_results && responseData.json_results.length > 0) {
                showMultipleEditableResults(responseData.json_results);
            }
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
            
            // Show editable results form for all results
            if (responseData.json_results && responseData.json_results.length > 0) {
                showMultipleEditableResults(responseData.json_results);
            }
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
let currentJsonDataArray = [];
let originalHtmlResult = null;

// Show editable results form with populated data (single result for text processing)
function showEditableResults(jsonData) {
    showMultipleEditableResults([jsonData]);
}

// Show multiple editable results forms
function showMultipleEditableResults(jsonDataArray) {
    currentJsonDataArray = jsonDataArray;
    
    const container = document.getElementById('dynamicResultsForms');
    const multipleActions = document.getElementById('multipleActions');
    
    // Clear previous forms
    container.innerHTML = '';
    
    // Create form for each result
    jsonDataArray.forEach((jsonData, index) => {
        const formHtml = createEditableForm(jsonData, index);
        container.innerHTML += formHtml;
    });
    
    // Show multiple actions if more than one result
    if (jsonDataArray.length > 1) {
        multipleActions.style.display = 'block';
        document.querySelector('.results-header').display = 'block';
    } else {
        multipleActions.style.display = 'none';
    }
    
    // Hide loading and show editable forms
    document.getElementById('loading').classList.remove('show');
    document.getElementById('multipleResultsContainer').classList.add('show');
    
    // Attach event listeners for individual download buttons
    attachDownloadButtonListeners();
}

// Create HTML for a single editable form
function createEditableForm(jsonData, index) {
    const filename = jsonData.source_filename || `File ${index + 1}`;
    const sourceType = jsonData.source_type || 'file';
    
    return `
        <div class="single-result-form" data-index="${index}">
            <div class="file-header">
                <h4>${sourceType === 'audio' ? '🎵' : '📄'} ${filename}</h4>
            </div>
            
            <form class="editable-form" data-index="${index}">
                <div class="form-grid">
                    <div class="form-field form-field-full">
                        <label for="edit_recipients_info_${index}">Recipients Info:</label>
                        <textarea id="edit_recipients_info_${index}" name="recipients_info" placeholder="Enter recipients information" class='recipients_info_textarea'>${jsonData.recipients_info || ''}</textarea>
                    </div>
                    
                    <div class="form-field">
                        <label for="edit_diagnosis_${index}">Diagnosis:</label>
                        <textarea id="edit_diagnosis_${index}" name="diagnosis" placeholder="Enter diagnosis" class="diagnosis-textarea">${jsonData.diagnosis || ''}</textarea>
                    </div>
                    
                    <div class="form-field">
                        <label for="edit_next_review_${index}">Plan:</label>
                        <input type="text" id="edit_next_review_${index}" name="next_review" placeholder="Next review date" value="${jsonData.next_review || ''}">
                    </div>
                    
                    <div class="form-field">
                        <label for="edit_corrected_visual_acuity_right_${index}">Visual Acuity Right:</label>
                        <input type="text" id="edit_corrected_visual_acuity_right_${index}" name="corrected_visual_acuity_right" placeholder="Right eye visual acuity" value="${jsonData.corrected_visual_acuity_right || ''}">
                    </div>
                    
                    <div class="form-field">
                        <label for="edit_corrected_visual_acuity_left_${index}">Visual Acuity Left:</label>
                        <input type="text" id="edit_corrected_visual_acuity_left_${index}" name="corrected_visual_acuity_left" placeholder="Left eye visual acuity" value="${jsonData.corrected_visual_acuity_left || ''}">
                    </div>
                    
                    <div class="form-field form-field-full">
                        <label for="edit_letter_to_patient_${index}">Letter to Patient:</label>
                        <textarea id="edit_letter_to_patient_${index}" name="letter_to_patient" placeholder="Enter the letter content for the patient..." rows="8">${jsonData.letter_to_patient || ''}</textarea>
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn-download individual-download-btn" data-index="${index}">📥 Download DOCX</button>
                </div>
            </form>
        </div>
    `;
}


// Attach event listeners for individual download buttons
function attachDownloadButtonListeners() {
    document.querySelectorAll('.individual-download-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const index = parseInt(this.dataset.index);
            await downloadSingleDocx(index, this);
        });
    });
}

// Download single DOCX for a specific form
async function downloadSingleDocx(index, btnElement) {
    const originalText = btnElement.textContent;
    
    btnElement.disabled = true;
    btnElement.textContent = 'Generating DOCX...';
    
    try {
        // Collect form data for this specific form
        const form = document.querySelector(`form.editable-form[data-index="${index}"]`);
        const formData = new FormData(form);
        const updatedData = {
            recipients_info: formData.get('recipients_info'),
            diagnosis: formData.get('diagnosis'),
            next_review: formData.get('next_review'),
            corrected_visual_acuity_right: formData.get('corrected_visual_acuity_right'),
            corrected_visual_acuity_left: formData.get('corrected_visual_acuity_left'),
            letter_to_patient: formData.get('letter_to_patient')
        };
        
        // Send to download_docx endpoint
        const response = await fetch('/api/download_docx', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedData)
        });
        
        if (response.ok) {
            const responseData = await response.json();
            
            if (responseData.error) {
                throw new Error(responseData.error);
            }
            
            // Download the DOCX file
            const base64Data = responseData.docx_base64;
            const sourceFilename = currentJsonDataArray[index].source_filename || `result_${index + 1}`;
            const filename = `${sourceFilename.split('.')[0]}_report.docx`;
            
            downloadBase64AsDocx(base64Data, filename);
            
        } else {
            throw new Error('DOCX generation failed');
        }
        
    } catch (error) {
        alert('Error generating DOCX: ' + error.message);
    } finally {
        btnElement.disabled = false;
        btnElement.textContent = originalText;
    }
}

// Helper function to download base64 as DOCX
function downloadBase64AsDocx(base64Data, filename) {
    // Convert base64 to blob and download
    const byteCharacters = atob(base64Data);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Handle download all DOCX button click
document.getElementById('downloadAllDocxBtn').addEventListener('click', async function() {
    const btn = this;
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Generating All DOCX...';
    
    try {
        const downloadPromises = [];
        
        // Download each form's DOCX
        for (let i = 0; i < currentJsonDataArray.length; i++) {
            const form = document.querySelector(`form.editable-form[data-index="${i}"]`);
            const formData = new FormData(form);
            const updatedData = {
                recipients_info: formData.get('recipients_info'),
                diagnosis: formData.get('diagnosis'),
                next_review: formData.get('next_review'),
                corrected_visual_acuity_right: formData.get('corrected_visual_acuity_right'),
                corrected_visual_acuity_left: formData.get('corrected_visual_acuity_left'),
                letter_to_patient: formData.get('letter_to_patient')
            };
            
            const downloadPromise = fetch('/api/download_docx', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedData)
            }).then(response => {
                if (response.ok) {
                    return response.json().then(data => {
                        if (data.error) throw new Error(data.error);
                        const sourceFilename = currentJsonDataArray[i].source_filename || `result_${i + 1}`;
                        const filename = `${sourceFilename.split('.')[0]}_report.docx`;
                        return { base64: data.docx_base64, filename };
                    });
                } else {
                    throw new Error(`Failed to generate DOCX for ${currentJsonDataArray[i].source_filename}`);
                }
            });
            
            downloadPromises.push(downloadPromise);
        }
        
        // Wait for all DOCX files to be generated
        const results = await Promise.all(downloadPromises);
        
        // Download each file
        results.forEach(result => {
            setTimeout(() => {
                downloadBase64AsDocx(result.base64, result.filename);
            }, 100); // Small delay between downloads
        });
        
    } catch (error) {
        alert('Error generating DOCX files: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
});

// Handle cancel all button
document.getElementById('cancelAllEditBtn').addEventListener('click', function() {
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
            // Use the same MIME type that was used for recording
            const mimeType = mediaRecorder.mimeType || 'audio/webm';
            const audioBlob = new Blob(audioChunks, { type: mimeType });
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
            
            // Show editable results form for all results
            if (responseData.json_results && responseData.json_results.length > 0) {
                showMultipleEditableResults(responseData.json_results);
            }
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
