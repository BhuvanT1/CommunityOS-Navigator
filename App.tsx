import { useState, useRef, useEffect } from 'react'
import LensView from './components/views/LensView'
import PreviewView from './components/views/PreviewView'
import ProcessingView from './components/views/ProcessingView'
import SuccessView from './components/views/SuccessView'
import AuthButton from './components/citizen/AuthButton'
import MyReportsView from './components/citizen/MyReportsView'
import ProfileView from './components/citizen/ProfileView'
import NotificationTray from './components/citizen/NotificationTray'
import { useAuth } from './contexts/AuthContext'

export type AppState = 'LENS' | 'PREVIEW' | 'PROCESSING' | 'SUCCESS' | 'MY_REPORTS' | 'PROFILE'

function App() {
  const { user } = useAuth()
  const [appState, setAppState] = useState<AppState>('LENS')
  const [reportData, setReportData] = useState<any>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageBlob, setImageBlob] = useState<Blob | null>(null)
  const [location, setLocation] = useState<{lat: number, lng: number, source: string, verified: boolean} | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isOffline, setIsOffline] = useState(!navigator.onLine)
  const [networkError, setNetworkError] = useState(false)
  const [errorMessage, setErrorMessage] = useState("There was a problem communicating with the server. Ensure you have a stable connection.")
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)
  const transitionTimerRef = useRef<any>(null)
  const dataTimerRef = useRef<any>(null)

  // Global Offline Detection
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Cleanup pending timeouts and fetch requests on unmount or reset
  const resetApp = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    clearTimeout(transitionTimerRef.current)
    clearTimeout(dataTimerRef.current)
    setImagePreview(null)
    setReportData(null)
    setNetworkError(false)
    setDuplicateWarning(null)
    setErrorMessage("There was a problem communicating with the server. Ensure you have a stable connection.")
    setAppState('LENS')
  }

  const handleCapture = async (blob: Blob, url: string, lat: number, lng: number, source: string, verified: boolean) => {
    if (isOffline) {
      // Handled by global banner
    }

    console.log(`[STAGE 1] Original Blob size: ${blob.size} bytes, type: ${blob.type}`);
    const img = new Image();
    img.onload = () => {
      console.log(`[STAGE 1] Original Image Dimensions: ${img.width}x${img.height}`);
    };
    img.src = url;

    setImagePreview(url)
    setImageBlob(blob)
    setLocation({ lat, lng, source, verified })
    setAppState('PREVIEW')
  }

  const compressImage = async (file: Blob): Promise<Blob> => {
    // If under 2MB, return as is
    if (file.size < 2 * 1024 * 1024) return file;
    
    return new Promise((resolve) => {
      const img = new Image();
      img.src = URL.createObjectURL(file);
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;
        
        // Scale down by 2 if large
        if (width > 1200) {
          height = Math.round((height * 1200) / width);
          width = 1200;
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob((blob) => {
          resolve(blob || file);
        }, 'image/jpeg', 0.7);
      };
    });
  }

  const confirmUpload = async () => {
    if (!imageBlob || !location) return;

    setAppState('PROCESSING')
    setReportData(null)
    setUploadProgress(0)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      console.log("[STAGE 1] Compressing image...");
      const compressedBlob = await compressImage(imageBlob);
      console.log(`[STAGE 1] Compressed Blob size: ${compressedBlob.size} bytes, type: ${compressedBlob.type}`);
      
      const formData = new FormData()
      formData.append('image', compressedBlob, 'capture.jpg')
      formData.append('lat', location.lat.toString())
      formData.append('lng', location.lng.toString())
      formData.append('location_source', location.source)
      formData.append('gps_verified', location.verified.toString())
      if (user) {
        formData.append('reporter_uid', user.uid)
      }
      
      // If we have a duplicate warning, force it this time
      if (duplicateWarning) {
        formData.append('force', 'true')
        setDuplicateWarning(null)
      }

      console.log("[STAGE 1] Uploading to backend...");

      // Use XMLHttpRequest for real upload progress
      const xhr = new XMLHttpRequest();
      
      const data = await new Promise((resolve, reject) => {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            setUploadProgress(percent);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              resolve(response.data);
            } catch (e) {
              reject(new Error("Invalid JSON response"));
            }
          } else if (xhr.status === 409) {
            // Duplicate warning
            try {
              const response = JSON.parse(xhr.responseText);
              reject(new Error(`DUPLICATE:${response.detail}`));
            } catch (e) {
              reject(new Error("DUPLICATE:Duplicate Warning"));
            }
          } else if (xhr.status === 429) {
            reject(new Error("AI Rate limits exceeded. Please try again later."));
          } else {
            try {
              const response = JSON.parse(xhr.responseText);
              reject(new Error(response.detail || `HTTP Error ${xhr.status}`));
            } catch (e) {
              reject(new Error(`HTTP Error ${xhr.status}`));
            }
          }
        };

        xhr.onerror = () => reject(new Error("Network Error"));
        xhr.onabort = () => reject(new Error("AbortError"));

        xhr.open("POST", `${import.meta.env.VITE_API_URL}/api/reports/analyze`);
        xhr.send(formData);

        // Hook up abort controller
        controller.signal.addEventListener('abort', () => xhr.abort());
      });

      if (!controller.signal.aborted) {
        setReportData(data);
        setAppState('SUCCESS');
      }

    } catch (error: any) {
      if (error.message === 'AbortError') return
      console.error(error)
      if (!controller.signal.aborted) {
        if (error.message.startsWith('DUPLICATE:')) {
          setDuplicateWarning(error.message.split('DUPLICATE:')[1]);
        } else {
          setErrorMessage(error.message)
          setNetworkError(true)
        }
      }
    }
  }

  return (
    <main className="w-full h-[100dvh] bg-black text-white overflow-hidden relative font-sans">
      <AuthButton />
      <NotificationTray />
      
      {/* Persistent Offline Banner */}
      {isOffline && (
        <div className="absolute top-10 inset-x-0 mx-auto w-[90%] bg-amber-500 text-amber-950 rounded-xl p-3 shadow-2xl z-50 flex items-center justify-center font-bold text-sm">
          You are currently offline. Check your connection.
        </div>
      )}

      {/* Duplicate Warning Dialog */}
      {duplicateWarning && (
        <div className="absolute inset-0 z-[100] bg-black/80 flex items-center justify-center p-6 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-amber-500/50 rounded-2xl p-6 w-full max-w-sm text-center shadow-2xl">
            <div className="w-16 h-16 bg-amber-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-amber-500 text-2xl font-bold">!</span>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Duplicate Detected</h2>
            <p className="text-zinc-400 text-sm mb-6">{duplicateWarning}</p>
            <div className="flex gap-3">
              <button 
                onClick={resetApp}
                className="flex-1 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl font-semibold text-white transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  setAppState('LENS')
                  // It will retry with force=true via state, wait!
                  // I should call confirmUpload directly. It will use the current imageBlob and duplicateWarning will be true in confirmUpload before it's set to null.
                  // Actually `confirmUpload` reads state, so let's call it.
                  confirmUpload()
                }}
                className="flex-1 py-3 bg-amber-500 hover:bg-amber-400 text-amber-950 rounded-xl font-bold transition-colors"
              >
                Proceed Anyway
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Network Error Retry Dialog */}
      {networkError && (
        <div className="absolute inset-0 z-[100] bg-black/80 flex items-center justify-center p-6 backdrop-blur-sm">
          <div className="bg-zinc-900 border border-white/10 rounded-2xl p-6 w-full max-w-sm text-center shadow-2xl">
            <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-red-500 text-2xl font-bold">!</span>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Upload Failed</h2>
            <p className="text-zinc-400 text-sm mb-6">{errorMessage}</p>
            <div className="flex gap-3">
              <button 
                onClick={resetApp}
                className="flex-1 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl font-semibold text-white transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  setNetworkError(false)
                  confirmUpload()
                }}
                className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 rounded-xl font-bold transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )}

      {appState === 'LENS' && (
        <LensView onCapture={handleCapture} />
      )}

      {appState === 'PREVIEW' && (
        <PreviewView 
          imagePreview={imagePreview} 
          onConfirm={confirmUpload} 
          onRetake={resetApp} 
        />
      )}

      {appState === 'PROCESSING' && (
        <ProcessingView progress={uploadProgress} />
      )}

      {appState === 'SUCCESS' && (
        <SuccessView onReset={resetApp} reportData={reportData} />
      )}

      {appState === 'MY_REPORTS' && (
        <MyReportsView />
      )}

      {appState === 'PROFILE' && (
        <ProfileView />
      )}

      {/* Bottom Navigation for Signed In Users */}
      {user && (
        <div className="absolute bottom-0 inset-x-0 h-16 bg-zinc-950 border-t border-white/10 flex items-center justify-around z-50">
          <button 
            onClick={() => setAppState('LENS')}
            className={`flex flex-col items-center gap-1 transition-colors ${appState === 'LENS' ? 'text-emerald-500' : 'text-zinc-500 hover:text-zinc-300'}`}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" /></svg>
            <span className="text-[10px] font-bold">Report</span>
          </button>
          
          <button 
            onClick={() => setAppState('MY_REPORTS')}
            className={`flex flex-col items-center gap-1 transition-colors ${appState === 'MY_REPORTS' ? 'text-emerald-500' : 'text-zinc-500 hover:text-zinc-300'}`}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            <span className="text-[10px] font-bold">My Reports</span>
          </button>
          
          <button 
            onClick={() => setAppState('PROFILE')}
            className={`flex flex-col items-center gap-1 transition-colors ${appState === 'PROFILE' ? 'text-emerald-500' : 'text-zinc-500 hover:text-zinc-300'}`}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
            <span className="text-[10px] font-bold">Profile</span>
          </button>
        </div>
      )}
    </main>
  )
}

export default App
