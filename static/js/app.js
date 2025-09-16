(function () {
  const startBtn = document.getElementById('start-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const resumeBtn = document.getElementById('resume-btn');
  const stopBtn = document.getElementById('stop-btn');
  const saveBtn = document.getElementById('save-btn');
  const statusEl = document.getElementById('status');
  const exportStatusEl = document.getElementById('export-status');
  const resultsSection = document.getElementById('results');
  const summaryEl = document.getElementById('summary');
  const actionItemsEl = document.getElementById('action-items');
  const transcriptEl = document.getElementById('transcript');
  const speakerLabelsContainer = document.getElementById('speaker-labels');
  const fileNameInput = document.getElementById('file-name');
  const sendEmailCheckbox = document.getElementById('send-email');
  const emailAddressWrapper = document.getElementById('email-address-wrapper');
  const emailAddressInput = document.getElementById('email-address');

  let mediaRecorder = null;
  let recordedChunks = [];
  const state = {
    segments: [],
    speakerMap: {},
    summary: '',
    actionItems: [],
    fileName: '',
  };

  function setStatus(text) {
    statusEl.textContent = text || '';
  }

  function setExportStatus(text) {
    exportStatusEl.textContent = text || '';
  }

  function formatTimestamp(seconds) {
    const total = Math.max(0, Math.floor(seconds || 0));
    const hrs = String(Math.floor(total / 3600)).padStart(2, '0');
    const mins = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
    const secs = String(total % 60).padStart(2, '0');
    return `${hrs}:${mins}:${secs}`;
  }

  function updateButtonStates() {
    const recorderState = mediaRecorder ? mediaRecorder.state : 'inactive';
    startBtn.disabled = recorderState !== 'inactive';
    pauseBtn.disabled = recorderState !== 'recording';
    resumeBtn.disabled = recorderState !== 'paused';
    stopBtn.disabled = recorderState === 'inactive';
  }

  function resetRecorder() {
    if (mediaRecorder && mediaRecorder.stream) {
      mediaRecorder.stream.getTracks().forEach((track) => track.stop());
    }
    mediaRecorder = null;
    recordedChunks = [];
    updateButtonStates();
  }

  function renderActionItems(items) {
    actionItemsEl.innerHTML = '';
    if (!items || items.length === 0) {
      const emptyItem = document.createElement('li');
      emptyItem.textContent = 'No action items identified.';
      actionItemsEl.appendChild(emptyItem);
      return;
    }

    items.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      actionItemsEl.appendChild(li);
    });
  }

  function renderTranscript() {
    const lines = state.segments.map((segment) => {
      const speaker = state.speakerMap[segment.speaker] || segment.speaker;
      return `[${formatTimestamp(segment.start)}] ${speaker}: ${segment.text}`;
    });
    transcriptEl.textContent = lines.join('\n');
  }

  function renderSpeakerInputs() {
    speakerLabelsContainer.innerHTML = '';
    const speakers = Array.from(new Set(state.segments.map((segment) => segment.speaker)));
    speakers.forEach((speaker) => {
      if (!state.speakerMap[speaker]) {
        state.speakerMap[speaker] = speaker;
      }
      const wrapper = document.createElement('label');
      wrapper.textContent = `Label for ${speaker}`;
      const input = document.createElement('input');
      input.type = 'text';
      input.value = state.speakerMap[speaker];
      input.dataset.speaker = speaker;
      input.addEventListener('input', (event) => {
        const value = event.target.value.trim();
        state.speakerMap[speaker] = value || speaker;
        renderTranscript();
      });
      wrapper.appendChild(input);
      speakerLabelsContainer.appendChild(wrapper);
    });
  }

  function showResults(data) {
    state.summary = data.summary || 'No summary available.';
    state.actionItems = data.actionItems || [];
    state.segments = data.segments || [];
    state.speakerMap = {};

    summaryEl.textContent = state.summary;
    renderActionItems(state.actionItems);
    renderSpeakerInputs();
    renderTranscript();

    resultsSection.classList.remove('hidden');
    saveBtn.disabled = false;
  }

  function handleError(error) {
    console.error(error);
    setStatus('An error occurred. Check console for details.');
  }

  async function uploadRecording(blob) {
    setStatus('Uploading recording…');
    const formData = new FormData();
    formData.append('audio', blob, `recording_${Date.now()}.webm`);

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || 'Failed to process recording.');
      }
      const payload = await response.json();
      showResults(payload);
      setStatus('Processing complete.');
    } catch (error) {
      handleError(error);
    }
  }

  async function saveResults() {
    if (!state.segments.length) {
      setExportStatus('No results to save yet.');
      return;
    }

    const fileName = fileNameInput.value.trim() || undefined;
    const sendEmail = !!sendEmailCheckbox.checked && !sendEmailCheckbox.disabled;
    const emailAddress = emailAddressInput.value.trim() || undefined;

    const payload = {
      summary: state.summary,
      actionItems: state.actionItems,
      segments: state.segments,
      speakerMap: state.speakerMap,
      fileName,
      sendEmail,
      emailAddress,
    };

    setExportStatus('Saving…');
    try {
      const response = await fetch('/save_result', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to save result.');
      }
      setExportStatus(`Saved to ${data.savedTo}${data.emailStatus ? ' and email sent.' : '.'}`);
    } catch (error) {
      setExportStatus(error.message);
    }
  }

  async function startRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.onstart = () => {
        setStatus('Recording…');
        updateButtonStates();
      };

      mediaRecorder.onpause = () => {
        setStatus('Recording paused.');
        updateButtonStates();
      };

      mediaRecorder.onresume = () => {
        setStatus('Recording…');
        updateButtonStates();
      };

      mediaRecorder.onstop = async () => {
        setStatus('Processing recording…');
        updateButtonStates();
        const blob = new Blob(recordedChunks, { type: 'audio/webm' });
        resetRecorder();
        await uploadRecording(blob);
      };

      mediaRecorder.start();
      updateButtonStates();
    } catch (error) {
      handleError(error);
    }
  }

  function pauseRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.pause();
    }
  }

  function resumeRecording() {
    if (mediaRecorder && mediaRecorder.state === 'paused') {
      mediaRecorder.resume();
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  }

  startBtn.addEventListener('click', startRecording);
  pauseBtn.addEventListener('click', pauseRecording);
  resumeBtn.addEventListener('click', resumeRecording);
  stopBtn.addEventListener('click', stopRecording);
  saveBtn.addEventListener('click', saveResults);

  saveBtn.disabled = true;

  const emailEnabled = Boolean(window.APP_CONFIG && window.APP_CONFIG.emailEnabled);
  if (!emailEnabled) {
    sendEmailCheckbox.checked = false;
    sendEmailCheckbox.disabled = true;
    if (emailAddressWrapper) {
      emailAddressWrapper.style.display = 'none';
    }
    if (emailAddressInput) {
      emailAddressInput.disabled = true;
    }
  }

  sendEmailCheckbox.addEventListener('change', () => {
    if (!emailAddressWrapper) {
      return;
    }
    if (sendEmailCheckbox.checked) {
      emailAddressWrapper.style.display = 'flex';
      if (emailAddressInput) {
        emailAddressInput.disabled = false;
      }
    } else {
      emailAddressWrapper.style.display = 'none';
      if (emailAddressInput) {
        emailAddressInput.disabled = true;
      }
    }
  });

  if (emailAddressWrapper && emailAddressInput && emailEnabled) {
    emailAddressWrapper.style.display = sendEmailCheckbox.checked ? 'flex' : 'none';
    emailAddressInput.disabled = !sendEmailCheckbox.checked;
  }

  updateButtonStates();
})();
