    document.addEventListener('DOMContentLoaded', function() {
        const progressTrack = document.getElementById('progressTrack'); const progressFill = document.getElementById('progressFill'); const interactiveArea = document.querySelector('.progress-interactive-area'); const svgWidth = 300; const svgHeight = 14; const midHeight = svgHeight / 2; const amplitude = 6; const frequency = 0.05; const segments = 150; const waveSpeed = songData.waveSpeed;
        let initialTrackId = songData.trackId; const pollingInterval = songData.pollingInterval;
        if (initialTrackId === 'None') { initialTrackId = null; }
        let currentProgress = songData.progressMs; const totalDuration = songData.durationMs; const isPlaying = songData.isPlaying;
        let animationFrameId = null; let animationStartTime = performance.now();
        function generateWavePath(phase) { let path = `M 0 ${midHeight}`; for (let i = 0; i <= segments; i++) { const x = (i / segments) * svgWidth; const fadeWidth = svgWidth * 0.1; let currentAmplitude = amplitude; if (x < fadeWidth) { currentAmplitude = amplitude * Math.sin((x / fadeWidth) * (Math.PI / 2)); } else if (x > svgWidth - fadeWidth) { currentAmplitude = amplitude * Math.sin(((svgWidth - x) / fadeWidth) * (Math.PI / 2)); } const y = midHeight + Math.sin(x * frequency + phase) * currentAmplitude; path += ` L ${x.toFixed(3)} ${y.toFixed(3)}`; } return path; }
        function updateProgressBar(progress) { if (totalDuration > 0) { const progressRatio = Math.min(progress / totalDuration, 1); const dynamicPhase = progressRatio * Math.PI * waveSpeed; const wavePath = generateWavePath(dynamicPhase); progressTrack.setAttribute('d', wavePath); progressFill.setAttribute('d', wavePath); const totalLength = progressFill.getTotalLength(); if (totalLength > 0) { progressFill.style.strokeDasharray = totalLength; progressFill.style.strokeDashoffset = totalLength * (1 - progressRatio); } } }
        function animate(currentTime) { const elapsedTime = currentTime - animationStartTime; const newProgress = currentProgress + elapsedTime; updateProgressBar(newProgress); if (newProgress < totalDuration) { animationFrameId = requestAnimationFrame(animate); } }
        function startAnimation() { if (isPlaying) { animationStartTime = performance.now(); animationFrameId = requestAnimationFrame(animate); } }
        function stopAnimation() { if (animationFrameId) { cancelAnimationFrame(animationFrameId); animationFrameId = null; } }
        updateProgressBar(currentProgress); startAnimation();
        interactiveArea.addEventListener('click', function(event) { if (totalDuration > 0) { stopAnimation(); const rect = interactiveArea.getBoundingClientRect(); const clickX = event.clientX - rect.left; const clickPercentage = Math.max(0, Math.min(1, clickX / rect.width)); const seekPositionMs = Math.round(clickPercentage * totalDuration); currentProgress = seekPositionMs; updateProgressBar(currentProgress); startAnimation(); fetch('/seek', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ position_ms: seekPositionMs }) }).catch(error => console.error('Error seeking track:', error)); } });
        setInterval(function() { fetch('/check-song').then(response => response.ok ? response.json() : Promise.reject('Network response was not ok')).then(data => { if (data && data.track_id !== initialTrackId) { window.location.reload(); } }).catch(error => console.error('Error during polling:', error)); }, pollingInterval);
        const playerModeToggle = document.getElementById('playerMode');
        if (playerModeToggle) { playerModeToggle.addEventListener('change', function() { const isEnabled = this.checked; fetch('/toggle-player-mode', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ playerMode: isEnabled }) }).then(response => response.ok ? response.json() : Promise.reject('Failed to toggle mode')).then(data => { if (data.success) { window.location.reload(); } }).catch(error => console.error('Error:', error)); }); }
        const themePickerToggle = document.getElementById('theme-picker-toggle');
        const themeOptions = document.getElementById('theme-options');
        if (themePickerToggle && themeOptions) {
            themePickerToggle.addEventListener('click', function(event) {
                event.stopPropagation();
                themeOptions.classList.toggle('active');
            });
            document.addEventListener('click', function() {
                if (themeOptions.classList.contains('active')) {
                    themeOptions.classList.remove('active');
                }
            });
        }
    });