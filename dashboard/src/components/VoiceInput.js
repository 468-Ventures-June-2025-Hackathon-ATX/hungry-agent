import React, { useState, useRef, useEffect } from 'react';

const VoiceInput = ({ onVoiceInput, isProcessing }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState('');
  const [claudeResponse, setClaudeResponse] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const recognitionRef = useRef(null);
  const animationFrameRef = useRef(null);

  useEffect(() => {
    // Initialize Speech Recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';
      
      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }
        
        setTranscript(finalTranscript || interimTranscript);
        
        if (finalTranscript) {
          // Send to Claude for processing
          onVoiceInput({
            text: finalTranscript,
            confidence: event.results[0][0].confidence || 0.95,
            timestamp: new Date().toISOString()
          });
        }
      };
      
      recognitionRef.current.onerror = (event) => {
        setError(`Speech recognition error: ${event.error}`);
        setIsRecording(false);
      };
      
      recognitionRef.current.onend = () => {
        setIsRecording(false);
        stopAudioLevel();
      };
    } else {
      setError('Speech recognition not supported in this browser');
    }
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [onVoiceInput]);

  const startAudioLevel = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      
      analyserRef.current.fftSize = 256;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      const updateAudioLevel = () => {
        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / bufferLength;
        setAudioLevel(average / 255);
        
        if (isRecording) {
          animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
        }
      };
      
      updateAudioLevel();
    } catch (err) {
      setError('Microphone access denied');
    }
  };

  const stopAudioLevel = () => {
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    setAudioLevel(0);
  };

  const startRecording = async () => {
    if (!recognitionRef.current) {
      setError('Speech recognition not available');
      return;
    }
    
    setError('');
    setTranscript('');
    setIsRecording(true);
    
    try {
      await startAudioLevel();
      recognitionRef.current.start();
    } catch (err) {
      setError('Failed to start recording');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current && isRecording) {
      recognitionRef.current.stop();
    }
    setIsRecording(false);
    stopAudioLevel();
  };

  const handleToggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          🎤 Voice Chat with Claude
        </h3>
        
        {/* Microphone Button */}
        <div className="relative inline-block mb-4">
          <button
            onClick={handleToggleRecording}
            disabled={isProcessing}
            className={`
              w-20 h-20 rounded-full border-4 transition-all duration-200 flex items-center justify-center
              ${isRecording 
                ? 'bg-red-500 border-red-600 hover:bg-red-600 animate-pulse' 
                : 'bg-blue-500 border-blue-600 hover:bg-blue-600'
              }
              ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            <svg 
              className="w-8 h-8 text-white" 
              fill="currentColor" 
              viewBox="0 0 20 20"
            >
              <path 
                fillRule="evenodd" 
                d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" 
                clipRule="evenodd" 
              />
            </svg>
          </button>
          
          {/* Audio Level Indicator */}
          {isRecording && (
            <div className="absolute -inset-2 rounded-full border-2 border-red-400 animate-ping"></div>
          )}
        </div>
        
        {/* Audio Level Bar */}
        {isRecording && (
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div 
              className="bg-green-500 h-2 rounded-full transition-all duration-100"
              style={{ width: `${audioLevel * 100}%` }}
            ></div>
          </div>
        )}
        
        {/* Status */}
        <div className="text-sm text-gray-600 mb-4">
          {isProcessing ? (
            <span className="text-blue-600">🤖 Claude is thinking...</span>
          ) : isRecording ? (
            <span className="text-red-600">🔴 Listening... (Click to stop)</span>
          ) : (
            <span>Click microphone to start talking</span>
          )}
        </div>
        
        {/* Live Transcript */}
        {transcript && (
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <div className="text-sm text-gray-500 mb-1">You said:</div>
            <div className="text-gray-800 font-medium">"{transcript}"</div>
          </div>
        )}
        
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <div className="text-red-600 text-sm">⚠️ {error}</div>
          </div>
        )}
        
        {/* Instructions */}
        <div className="text-xs text-gray-500">
          <p>💡 Try saying: "I want to order three al pastor tacos from DoorDash"</p>
          <p>🌮 Or: "Find me the best taco places nearby"</p>
        </div>
      </div>
    </div>
  );
};

export default VoiceInput;
