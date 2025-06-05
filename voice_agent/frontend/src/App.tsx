import React, { useRef, useState, useEffect } from "react";
import "./App.css";

const WS_URL = "ws://127.0.0.1:8001/ws/voice-chat";

// Silence detection thresholds
const PAUSE_THRESHOLD = 2; // Short pause (2 seconds) - process speech but keep listening
const SILENCE_THRESHOLD = 5; // Long silence (5 seconds) - stop recording completely

function App() {
  const [transcript, setTranscript] = useState("");
  const [aiResponse, setAIResponse] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false); // True when AI audio is playing OR when waiting for AI response
  const [isPaused, setIsPaused] = useState(false); // True when user has paused speaking but we're still listening
  const [isProcessing, setIsProcessing] = useState(false); // True when processing a pause but still listening
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const silentChunksRef = useRef<number>(0);
  const currentAudioChunksRef = useRef<Blob[]>([]);

  // Helper function to stop recording and cleanup
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      console.log("Stopping recording (MediaRecorder state: " + mediaRecorderRef.current.state + ")");
      mediaRecorderRef.current.stop(); // This will trigger onstop for track cleanup
      // Note: We don't setIsRecording(false) here directly.
      // It's better to let the onstop handler or WebSocket events manage this
      // to avoid race conditions, especially if stop is called from multiple places.
      // However, for user-initiated stop, it's generally safe.
      setIsRecording(false);
      setIsPaused(false);
      setIsProcessing(false);
    }
    // Reset silence counter
    silentChunksRef.current = 0;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // We no longer close the WebSocket here. It stays open for the session.
      // The server controls when it's ready for more audio.
      console.log("MediaRecorder stopped, WebSocket remains open.");
    }
  };
  
  // Process current audio chunks during a pause but keep listening
  const processPausedAudio = () => {
    if (currentAudioChunksRef.current.length === 0 || isProcessing) {
      return; // Nothing to process or already processing
    }
    
    setIsProcessing(true);
    console.log("Processing audio during pause, but continuing to listen...");
    
    // Create a copy of the current audio chunks
    const chunksToProcess = [...currentAudioChunksRef.current];
    
    // Send a special message to indicate this is a pause, not end of recording
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // First send a message indicating this is a pause
      wsRef.current.send("PAUSE_PROCESSING");
      
      // Then send all accumulated audio chunks
      const blob = new Blob(chunksToProcess, { type: mediaRecorderRef.current?.mimeType || 'audio/webm' });
      wsRef.current.send(blob);
      
      // Clear the current chunks to start fresh, but keep recording
      currentAudioChunksRef.current = [];
    }
  };

  // Play audio from array buffer
  const playAudio = (audioData: ArrayBuffer) => {
    stopRecording(); // Ensure any active recording is stopped before playing
    setIsPlaying(true); // AI is now "speaking"
    console.log("playAudio called, setIsPlaying(true)");
    const blob = new Blob([audioData], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    audio.onended = () => {
      console.log("Audio playback finished - informing backend");
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send("CLIENT_DONE_PLAYING");
      }
      // isPlaying will be set to false when backend sends CLIENT_READY
      // or if WebSocket closes/errors.
    };
    
    audio.onerror = (e) => {
      console.error("Error playing audio:", e);
      setAIResponse("Error playing AI response.");
      // If audio playback fails, we should probably allow user to try again
      setIsPlaying(false); 
      console.log("Audio playback error, setIsPlaying(false)");
    };
    
    audio.play().catch(e => {
        console.error("Audio play() failed:", e);
        setAIResponse("Could not play AI response.");
        setIsPlaying(false);
        console.log("Audio play() failed, setIsPlaying(false)");
    });
  };

  // Handle WebSocket messages
  const handleWSMessage = (event: MessageEvent) => {
    if (typeof event.data === "string") {
      console.log("Received message:", event.data);
      
      if (event.data.startsWith("[Transcript] ")) {
        setTranscript(event.data.replace("[Transcript] ", ""));
      } else if (event.data.startsWith("[AI] ")) {
        setAIResponse(event.data.replace("[AI] ", ""));
      } else if (event.data.startsWith("[Error] ")) {
        setAIResponse(event.data);
        setIsPlaying(false); // If server sends error, stop "playing" state
        console.log("Server error, setIsPlaying(false)");
      } else if (event.data === "[Status] AI_SPEAKING") {
        console.log("Backend reports AI is speaking, setIsPlaying(true)");
        setIsPlaying(true); 
      } else if (event.data === "[Status] AI_DONE_SPEAKING") {
        console.log("Backend reports AI is done speaking (audio data should follow or be in flight)");
        // isPlaying remains true until audio.onended sends CLIENT_DONE_PLAYING
        // and backend responds with CLIENT_READY
      } else if (event.data === "[Status] CLIENT_READY") {
        console.log("Backend is ready for next input, setIsPlaying(false), enabling mic.");
        setIsPlaying(false); // This will re-enable the mic button
        setIsProcessing(false); // Reset processing state
      } else if (event.data.startsWith("[Warning] ")) {
        console.warn(event.data);
      } else if (event.data === "[Status] SKIPPING_EMPTY_INPUT") {
        setAIResponse("Input was too short or silent, please try speaking again.");
        setIsPlaying(false); // No audio will be played, so allow user to speak again
        setIsProcessing(false); // Reset processing state
        console.log("Skipping empty input, setIsPlaying(false)");
      } else if (event.data === "[Status] PAUSE_PROCESSED") {
        console.log("Backend processed pause audio, continuing to listen");
        setIsProcessing(false); // Allow sending new audio chunks
      }
    } else if (event.data instanceof Blob) {
      console.log("Received audio blob, size:", event.data.size);
      event.data.arrayBuffer().then(playAudio);
    }
  };

  const setupMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/ogg;codecs=opus',
        'audio/wav'
      ];
      let MimeType = '';
      for (const type of mimeTypes) {
        if (MediaRecorder.isTypeSupported(type)) {
          MimeType = type;
          break;
        }
      }
      if (!MimeType) {
        console.warn("No preferred MIME type supported, using default.");
        mediaRecorderRef.current = new MediaRecorder(stream);
      } else {
        mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: MimeType });
      }
      console.log("Using MIME type:", mediaRecorderRef.current.mimeType);

      const audioTracks = stream.getAudioTracks();
      mediaRecorderRef.current.onstop = () => {
        audioTracks.forEach(track => track.stop());
        console.log("MediaRecorder stopped and audio tracks released.");
        // setIsRecording(false); // Moved to user-initiated stopRecording or WS close/error
      };
      
      mediaRecorderRef.current.ondataavailable = (e) => {
        audioChunksRef.current.push(e.data);
        
        // Always add to current chunks for potential pause processing
        if (!isProcessing) {
          currentAudioChunksRef.current.push(e.data);
        }
        
        if (isPlaying || isProcessing) {
          console.log(isPlaying ? "AI is speaking, not sending audio chunk." : "Processing paused audio, collecting new chunks.");
          return;
        }
        
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          console.log("WebSocket not open, not sending audio chunk.");
          stopRecording(); // Stop if WS is not open
          return;
        }

        const isSilent = e.data.size < 1000;
        
        if (isSilent) { 
          silentChunksRef.current += 1;
          console.log(`Silent chunk detected (${silentChunksRef.current}/${SILENCE_THRESHOLD}), size: ${e.data.size}`);
          
          // Check for pause threshold first (shorter than full silence)
          if (silentChunksRef.current >= PAUSE_THRESHOLD && !isPaused) {
            console.log("Pause detected - processing current speech but continuing to listen");
            setIsPaused(true);
            processPausedAudio();
            // Don't return - we want to keep recording
          }
          
          // Check for complete silence threshold
          if (silentChunksRef.current >= SILENCE_THRESHOLD) {
            console.log("Auto-stopping due to prolonged silence");
            stopRecording();
            return;
          }
        } else {
          // If we hear speech again after a pause, reset pause state
          if (isPaused) {
            console.log("Speech resumed after pause");
            setIsPaused(false);
          }
          silentChunksRef.current = 0;
          
          // Only send audio directly if we're not in a processing state
          if (!isProcessing) {
            console.log("Sending audio chunk of size:", e.data.size, "bytes");
            wsRef.current.send(e.data);
          }
        }
      };
      
      mediaRecorderRef.current.start(1000); 
      setIsRecording(true);
      setTranscript(""); 
      setAIResponse(""); 
    } catch (err) {
      console.error("Error setting up MediaRecorder:", err);
      setAIResponse("Error initializing audio recording. Please check permissions.");
      setIsRecording(false);
    }
  };

  // Start or stop recording and streaming
  const handleMicClick = async () => {
    if (isPlaying) {
      console.log("Cannot start recording: AI is speaking or system is processing.");
      return;
    }

    if (!isRecording) {
      // Start recording
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED || wsRef.current.readyState === WebSocket.CLOSING) {
        console.log(`Attempting to connect to WebSocket at: ${WS_URL}`);
        wsRef.current = new WebSocket(WS_URL);
        wsRef.current.binaryType = "blob";

        wsRef.current.onopen = (event) => {
          console.log("WebSocket connection established successfully!", event);
          setupMediaRecorder();
        };

        wsRef.current.onmessage = handleWSMessage;
        wsRef.current.onclose = (event) => {
          console.log("WebSocket connection closed:", event.code, event.reason);
          setIsRecording(false);
          setIsPlaying(false); 
          setAIResponse("Connection to server lost. Please refresh or try again.");
          wsRef.current = null; // Clear the ref
        };
        wsRef.current.onerror = (error) => {
          console.error("WebSocket error:", error);
          setAIResponse("WebSocket connection error. Please refresh or try again.");
          setIsRecording(false);
          setIsPlaying(false);
          if (wsRef.current && wsRef.current.readyState !== WebSocket.OPEN) {
            wsRef.current = null; // Clear ref if error on non-open socket
          }
        };
      } else if (wsRef.current.readyState === WebSocket.OPEN) {
        setupMediaRecorder();
      }
    } else {
      // Stop recording
      stopRecording();
    }
  };
  
  // Cleanup WebSocket on component unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        console.log("Closing WebSocket on component unmount.");
        wsRef.current.close();
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);


  // Status message based on current state
  const getStatusMessage = () => {
    if (isPlaying) return "AI is speaking / processing... please wait";
    if (isProcessing) return "Processing your speech while listening...";
    if (isPaused) return "Detected pause, processing speech...";
    if (isRecording) return "Listening to you...";
    return "Ready for conversation";
  };

  return (
    <div style={{ padding: 40, fontFamily: 'sans-serif', maxWidth: 600, margin: '0 auto' }}>
      <h2>🎤 Real-Time Voice AI Agent</h2>
      
      <div style={{ 
        padding: '8px 12px',
        borderRadius: 4,
        marginBottom: 12,
        backgroundColor: isPlaying ? '#e3f2fd' : isProcessing ? '#fff8e1' : isPaused ? '#e8f5e9' : isRecording ? '#f1f8e9' : '#f5f5f5',
        color: isPlaying ? '#0d47a1' : isProcessing ? '#ff6f00' : isPaused ? '#2e7d32' : isRecording ? '#33691e' : '#616161',
        border: `1px solid ${isPlaying ? '#bbdefb' : isProcessing ? '#ffe082' : isPaused ? '#a5d6a7' : isRecording ? '#dcedc8' : '#e0e0e0'}`, // Status indicator border
        fontWeight: 500
      }}>
        <span style={{ marginRight: 8 }}>
          {isPlaying ? '🔊' : isProcessing ? '⚡' : isPaused ? '✋' : isRecording ? '🎙️' : '⏲️'}
        </span>
        {getStatusMessage()}
      </div>
      
      <button
        onClick={handleMicClick}
        disabled={isPlaying} // Disable button if AI is speaking or processing
        style={{
          backgroundColor: isPlaying
            ? "#bdbdbd"
            : isRecording
            ? "#e57373"
            : "#81c784",
          color: isPlaying ? "#757575" : "#fff",
          cursor: isPlaying ? "not-allowed" : "pointer",
          fontWeight: "bold",
          fontSize: "1.1rem",
          padding: "0.7em 2em",
          border: "none",
          borderRadius: "2em",
          boxShadow: isPlaying
            ? "0 2px 8px rgba(150,150,150,0.1)"
            : "0 2px 8px rgba(33,150,83,0.1)"
        }}
        aria-disabled={isPlaying}
        tabIndex={isPlaying ? -1 : 0}
        title={
          isPlaying
            ? "Wait for the AI to finish speaking or processing."
            : isRecording
            ? "Click to stop recording."
            : "Click to start talking."
        }
      >
        {isRecording ? "Stop" : "Start Talking"}
      </button>
      <div style={{ marginTop: 20 }}>
        <h4>You said:</h4>
        <div style={{ background: '#f0f0f0', padding: 16, minHeight: 40, borderRadius: 4 }}>{transcript}</div>
      </div>
      <div style={{ marginTop: 20 }}>
        <h4>AI Response:</h4>
        <div style={{ background: '#eef', padding: 16, minHeight: 40, borderRadius: 4 }}>{aiResponse}</div>
      </div>
    </div>
  );
}

export default App;
