import { useState, useEffect } from "react";
import axios from "axios";
import "./styles.css";
import PrototypePlayer from "./PrototypePlayer";
import FigmaDesignPanel from "./components/FigmaDesignPanel";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000";

export default function App(){
  const [file,setFile]=useState(null);
  const [job,setJob]=useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [videoPreview, setVideoPreview] = useState(null);
  const [showToolbar, setShowToolbar] = useState(false);
  const [selectedMode, setSelectedMode] = useState(null); // 'taser', 'hawkeye', 'all'

  // Visual customization settings (applied to video)
  const [visualSettings, setVisualSettings] = useState({
    // Person bounding box settings
    personLockedBoxColor: "#34c759",      // Green for locked/targeted (close distance)
    personUnlockedBoxColor: "#ffffff",    // White for unlocked/default
    personFarBoxColor: "#ff3b30",         // Red for far distance when locked
    personBoxStrokeWidth: 1,
    personGreyColor: "#808080",           // Grey for background/non-priority
    
    // Individual person box properties
    personLockedBoxStrokeWidth: 1,
    personLockedBoxBorderRadius: 0,
    personUnlockedBoxStrokeWidth: 1,
    personUnlockedBoxBorderRadius: 0,
    personFarBoxStrokeWidth: 4,
    personFarBoxBorderRadius: 0,
    personGreyStrokeWidth: 1,
    personGreyBorderRadius: 0,
    
    // Person box background fills (new)
    personLockedBoxBackgroundColor: "#34c75920",
    personLockedBoxBackgroundOpacity: 0.2,
    personUnlockedBoxBackgroundColor: "#ffffff20",
    personUnlockedBoxBackgroundOpacity: 0.2,
    personFarBoxBackgroundColor: "#ff3b3020",
    personFarBoxBackgroundOpacity: 0.2,
    personGreyBackgroundColor: "#8e8e9320",
    personGreyBackgroundOpacity: 0.2,
    
    // Vehicle bounding box settings
    vehicleLockedBoxColor: "#007aff",     // Blue for locked vehicles
    vehicleUnlockedBoxColor: "#ffcc00",   // Yellow for unlocked vehicles
    vehicleFarBoxColor: "#ff9500",        // Orange for far vehicles
    vehicleBoxStrokeWidth: 2,             // Thicker for vehicles
    vehicleGreyColor: "#808080",          // Grey for background/non-priority
    
    // General box settings
    boxStyle: "solid",              // "solid" or "dashed"
    
    // Text settings
    textSize: 12,
    personIdTextColor: "#ffffff",         // White text for people
    personIdLockedTextColor: "#34c759",   // Green when locked
    personIdFarTextColor: "#ff3b30",      // Red for far distance
    personIdGreyTextColor: "#808080",     // Grey for background
    vehicleIdTextColor: "#ffcc00",        // Yellow text for vehicles
    vehicleIdLockedTextColor: "#007aff",  // Blue when locked
    distanceTextColor: "#ffd166",         // Gold
    objectTypeTextColor: "#ff6b6b",       // Red for object type
    textBackgroundOpacity: 0.7,
    
    // Enhanced text properties from Figma
    personIdTextSize: 11,
    personIdTextFamily: 'Arial',
    personIdTextWeight: 400,
    distanceTextSize: 11,
    distanceTextFamily: 'Arial', 
    distanceTextWeight: 400,
    objectTypeTextSize: 10,
    objectTypeTextFamily: 'Arial',
    objectTypeTextWeight: 400,
    
    // State-specific object text properties
    objectTypeLockedTextColor: "#ff152d",
    objectTypeLockedTextSize: 10,
    objectTypeLockedTextFamily: 'Arial',
    objectTypeLockedTextWeight: 400,
    objectTypeFarTextColor: "#ff152d",
    objectTypeFarTextSize: 10,
    objectTypeFarTextFamily: 'Arial',
    objectTypeFarTextWeight: 400,
    objectTypeGreyTextColor: "#9c9c9c",
    objectTypeGreyTextSize: 10,
    objectTypeGreyTextFamily: 'Arial',
    objectTypeGreyTextWeight: 400,
    
    // State-specific distance text properties
    distanceLockedTextColor: "#ffaf1c",
    distanceLockedTextSize: 11,
    distanceLockedTextFamily: 'Arial',
    distanceLockedTextWeight: 400,
    distanceFarTextColor: "#ff152d",
    distanceFarTextSize: 11,
    distanceFarTextFamily: 'Arial',
    distanceFarTextWeight: 400,
    distanceGreyTextColor: "#9c9c9c",
    distanceGreyTextSize: 11,
    distanceGreyTextFamily: 'Arial',
    distanceGreyTextWeight: 400,
    
    // Frame background colors for text boxes (extracted from Figma)
    objectTypeBackgroundColor: "rgba(60, 20, 20, 0.7)",
    objectTypeLockedBackgroundColor: "rgba(60, 20, 20, 0.7)",
    objectTypeFarBackgroundColor: "rgba(60, 20, 20, 0.7)",
    objectTypeGreyBackgroundColor: "rgba(60, 20, 20, 0.7)",
    distanceBackgroundColor: "rgba(20, 20, 60, 0.7)",
    distanceLockedBackgroundColor: "rgba(20, 20, 60, 0.7)",
    distanceFarBackgroundColor: "rgba(20, 20, 60, 0.7)",
    distanceGreyBackgroundColor: "rgba(20, 20, 60, 0.7)",
    
    // Background opacity properties
    objectTypeBackgroundOpacity: 0.7,
    objectTypeLockedBackgroundOpacity: 0.7,
    objectTypeFarBackgroundOpacity: 0.7,
    objectTypeGreyBackgroundOpacity: 0.7,
    distanceBackgroundOpacity: 0.7,
    distanceLockedBackgroundOpacity: 0.7,
    distanceFarBackgroundOpacity: 0.7,
    distanceGreyBackgroundOpacity: 0.7,
    
    // ID text background colors (extracted from Figma)
    personIdBackgroundColor: "rgba(0, 0, 0, 0.7)",
    personIdLockedBackgroundColor: "rgba(0, 0, 0, 0.7)",
    personIdFarBackgroundColor: "rgba(0, 0, 0, 0.7)",
    personIdGreyBackgroundColor: "rgba(0, 0, 0, 0.7)",
    
    // ID background opacity properties
    personIdBackgroundOpacity: 0.7,
    personIdLockedBackgroundOpacity: 0.7,
    personIdFarBackgroundOpacity: 0.7,
    personIdGreyBackgroundOpacity: 0.7,
    
    // Crosshair settings (Taser & All modes only)
    crosshairColor: "#ffd166",      // Gold
    crosshairSize: 20,
    crosshairWidth: 2,
    crosshairStyle: "lines",        // "lines", "circle", "cross", "custom"
    customCrosshairImage: null,
    crosshairDefaultImage: null,    // Figma default crosshair
    crosshairActiveImage: null,     // Figma active crosshair
    crosshairDefaultSize: null,     // Figma default crosshair size
    crosshairActiveSize: null,      // Figma active crosshair size
    useFigmaCrosshair: false,       // Flag to enable Figma crosshairs
    
    // Tracking dot settings (people only)
    trackingDotColor: "#34c759",    // Green
    trackingDotSize: 6,
    trackingDotStyle: "solid",      // "solid", "ring", "cross", "custom"
    customTrackingImage: null,
    
    // Body Tracker (Figma variant-based component)
    bodyTrackerChargingProperties: null,
    bodyTrackerReadyProperties: null,
    useFigmaBodyTracker: false,
    
    // Background/overlay settings
    overlayOpacity: 1.0,
    showStats: true,
    showObjectTypes: true,          // Show object type labels
    
    // Mode-specific settings
    enableCrosshair: true,          // Disabled in Hawkeye mode
    showStatusSquare: false,        // Enabled in Hawkeye mode
  });

  // Pending visual settings (before applying)
  const [pendingSettings, setPendingSettings] = useState(visualSettings);
  const [hasUnappliedChanges, setHasUnappliedChanges] = useState(false);

  // Function to apply mode-specific settings
  const applyModeSettings = (mode) => {
    setVisualSettings(prev => {
      const newSettings = { ...prev };
      
      switch(mode) {
        case 'taser':
          // People priority, vehicles grey, crosshair enabled
          newSettings.enableCrosshair = true;
          newSettings.showStatusSquare = false;
          break;
          
        case 'hawkeye':
          // Vehicles priority, people grey, no crosshair, status square
          newSettings.enableCrosshair = false;
          newSettings.showStatusSquare = true;
          break;
          
        case 'all':
          // Full functionality
          newSettings.enableCrosshair = true;
          newSettings.showStatusSquare = false;
          break;
          
        default:
          break;
      }
      
      return newSettings;
    });
    
    // Also update pending settings
    setPendingSettings(prev => {
      const newSettings = { ...prev };
      
      switch(mode) {
        case 'taser':
          newSettings.enableCrosshair = true;
          newSettings.showStatusSquare = false;
          break;
          
        case 'hawkeye':
          newSettings.enableCrosshair = false;
          newSettings.showStatusSquare = true;
          break;
          
        case 'all':
          newSettings.enableCrosshair = true;
          newSettings.showStatusSquare = false;
          break;
          
        default:
          break;
      }
      
      return newSettings;
    });
  };

  // Function to update pending visual settings
  const updateVisualSetting = (key, value) => {
    setPendingSettings(prev => ({
      ...prev,
      [key]: value
    }));
    setHasUnappliedChanges(true);
  };

  // Function to apply pending changes
  const applyVisualChanges = () => {
    setVisualSettings({...pendingSettings});
    setHasUnappliedChanges(false);
  };

  // Function to reset to current applied settings
  const resetVisualChanges = () => {
    setPendingSettings({...visualSettings});
    setHasUnappliedChanges(false);
  };

  // Function to apply Figma design
  const applyFigmaDesign = (figmaSettings, applyDirectly = false) => {
    const newSettings = {...figmaSettings};
    
    // Load crosshair images and sizes if available (from cache or sync response)
    if (figmaSettings.crosshairDefaultImage) {
      newSettings.crosshairDefaultImage = figmaSettings.crosshairDefaultImage;
      newSettings.useFigmaCrosshair = true;
    }
    if (figmaSettings.crosshairActiveImage) {
      newSettings.crosshairActiveImage = figmaSettings.crosshairActiveImage;
      newSettings.useFigmaCrosshair = true;
    }
    if (figmaSettings.crosshairDefaultSize) {
      newSettings.crosshairDefaultSize = figmaSettings.crosshairDefaultSize;
    }
    if (figmaSettings.crosshairActiveSize) {
      newSettings.crosshairActiveSize = figmaSettings.crosshairActiveSize;
    }
    
    // Load body tracker data if available
    if (figmaSettings.bodyTrackerChargingProperties) {
      newSettings.bodyTrackerChargingProperties = figmaSettings.bodyTrackerChargingProperties;
      newSettings.useFigmaBodyTracker = true;
    }
    if (figmaSettings.bodyTrackerReadyProperties) {
      newSettings.bodyTrackerReadyProperties = figmaSettings.bodyTrackerReadyProperties;
      newSettings.useFigmaBodyTracker = true;
    }
    
    if (applyDirectly) {
      // Apply directly to video preview (bypass pending settings)
      const mergedSettings = {
        ...visualSettings,
        ...newSettings
      };
      setVisualSettings(mergedSettings);
      setPendingSettings(mergedSettings);
      setHasUnappliedChanges(false);
    } else {
      // Apply to pending settings (existing behavior)
      const mergedSettings = {
        ...pendingSettings,
        ...newSettings
      };
      setPendingSettings(mergedSettings);
      setHasUnappliedChanges(true);
    }
  };

  // Handle image upload for custom crosshair/tracking dot
  const handleImageUpload = (type, file) => {
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        updateVisualSetting(type, e.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  function handleFileSelect(e) {
    const selectedFile = e.target.files?.[0];
    setFile(selectedFile);
    
    if (selectedFile) {
      // Create video preview URL
      const previewUrl = URL.createObjectURL(selectedFile);
      setVideoPreview(previewUrl);
    } else {
      setVideoPreview(null);
    }
  }

  async function onUpload(){
    if(!file || !selectedMode) return;
    
    setIsProcessing(true);
    try {
    const form = new FormData();
    form.append("video", file);
    form.append("mode", selectedMode);
      
      const { data } = await axios.post(`${API}/api/upload`, form, { 
        headers: { "Content-Type": "multipart/form-data"} 
      });
    setJob(data);
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Cleanup video preview URL when component unmounts or file changes
  useEffect(() => {
    return () => {
      if (videoPreview) {
        URL.revokeObjectURL(videoPreview);
      }
    };
  }, [videoPreview]);

  return (
    <div style={{minHeight:"100vh", padding:"0 16px"}}>
      {!selectedMode ? (
        // Mode Selection - First step
        <div style={{
          display:"flex", 
          flexDirection:"column", 
          alignItems:"center", 
          justifyContent:"center", 
          minHeight:"100vh",
          textAlign:"center",
          maxWidth:"900px",
          margin:"0 auto"
        }}>
          <h1 style={{
            letterSpacing:"1px", 
            fontSize:"4rem", 
            marginBottom:"16px",
            color:"var(--lcars-gold)",
            textShadow:"0 0 24px rgba(255, 209, 102, 0.25)",
            fontWeight:"700"
          }}>
            PROTOCAM 1.0
          </h1>
          <p style={{
            color:"var(--muted)", 
            fontSize:"1.3rem", 
            marginBottom:"48px",
            lineHeight:"1.6"
          }}>
            Select your detection mode:
          </p>
          
          {/* Mode Selection Buttons */}
          <div style={{
            display:"flex",
            gap:"24px",
            width:"100%",
            maxWidth:"800px"
          }}>
            {/* Taser Mode */}
            <button 
              className="mode-btn"
              onClick={() => {
                setSelectedMode('taser');
                applyModeSettings('taser');
              }}
              style={{
                padding:"32px 24px",
                background:"var(--panel)",
                border:"2px solid var(--lcars-orange)",
                borderRadius:"16px",
                color:"var(--text)",
                cursor:"pointer",
                transition:"all 0.3s ease",
                textAlign:"center"
              }}
              onMouseEnter={(e) => {
                e.target.style.background = "rgba(245, 166, 35, 0.1)";
                e.target.style.transform = "translateY(-4px)";
                e.target.style.boxShadow = "0 8px 24px rgba(245, 166, 35, 0.3)";
              }}
              onMouseLeave={(e) => {
                e.target.style.background = "var(--panel)";
                e.target.style.transform = "translateY(0)";
                e.target.style.boxShadow = "none";
              }}
            >
              <div style={{fontSize:"2rem", marginBottom:"12px"}}>⚡</div>
              <h3 style={{margin:"0 0 8px 0", color:"var(--lcars-orange)"}}>TASER</h3>
              <p style={{margin:"0", fontSize:"14px", color:"var(--muted)", lineHeight:"1.4"}}>
                Officer POV • People Priority • Crosshair Targeting
              </p>
            </button>

            {/* Hawkeye Mode */}
            <button 
              className="mode-btn"
              onClick={() => {
                setSelectedMode('hawkeye');
                applyModeSettings('hawkeye');
              }}
              style={{
                padding:"32px 24px",
                background:"var(--panel)",
                border:"2px solid var(--lcars-blue)",
                borderRadius:"16px",
                color:"var(--text)",
                cursor:"pointer",
                transition:"all 0.3s ease",
                textAlign:"center"
              }}
              onMouseEnter={(e) => {
                e.target.style.background = "rgba(100, 181, 246, 0.1)";
                e.target.style.transform = "translateY(-4px)";
                e.target.style.boxShadow = "0 8px 24px rgba(100, 181, 246, 0.3)";
              }}
              onMouseLeave={(e) => {
                e.target.style.background = "var(--panel)";
                e.target.style.transform = "translateY(0)";
                e.target.style.boxShadow = "none";
              }}
            >
              <div style={{fontSize:"2rem", marginBottom:"12px"}}>🚗</div>
              <h3 style={{margin:"0 0 8px 0", color:"var(--lcars-blue)"}}>HAWKEYE</h3>
              <p style={{margin:"0", fontSize:"14px", color:"var(--muted)", lineHeight:"1.4"}}>
                Dash Cam • Vehicle Priority • Status Monitoring
              </p>
            </button>

            {/* All Mode */}
            <button 
              className="mode-btn"
              onClick={() => {
                setSelectedMode('all');
                applyModeSettings('all');
              }}
              style={{
                padding:"32px 24px",
                minWidth:"180px",
                background: "rgba(255, 255, 255, 0.1)",
                border:"2px solid white",
                borderRadius:"16px",
                color:"white",
                cursor:"pointer",
                transition:"all 0.3s ease",
                textAlign:"center"
              }}
              onMouseEnter={(e) => {
                e.target.style.background = "rgba(255, 255, 255, 0.1)";
                e.target.style.transform = "translateY(-4px)";
                e.target.style.boxShadow = "0 8px 24px rgba(255, 255, 255, 0.3)";
              }}
              onMouseLeave={(e) => {
                e.target.style.background = "rgba(255, 255, 255, 0.1)";
                e.target.style.transform = "translateY(0)";
                e.target.style.boxShadow = "none";
              }}
            >
              <div style={{fontSize:"2rem", marginBottom:"12px"}}></div>
              <h3 style={{margin:"0 0 8px 0", color:"var(--lcars-gold)"}}>ALL</h3>
              <p style={{margin:"0", fontSize:"14px", color:"var(--muted)", lineHeight:"1.4"}}>
                No guard rails
              </p>
            </button>
          </div>
        </div>
      ) : !job?.resultUrl ? (
        // Landing page - centered upload interface
        <div style={{
          display:"flex", 
          flexDirection:"column", 
          alignItems:"center", 
          justifyContent:"center", 
          minHeight:"100vh",
          textAlign:"center",
          maxWidth:"800px",
          margin:"0 auto"
        }}>
          {/* Back Button */}
          <div style={{
            position:"absolute",
            top:"24px",
            left:"24px"
          }}>
            <button 
              onClick={() => {
                setSelectedMode(null);
                setFile(null);
                setVideoPreview(null);
                setJob(null);
              }}
              style={{
                padding:"12px 20px",
                background:"var(--panel)",
                border:"1px solid var(--muted)",
                borderRadius:"8px",
                color:"var(--text)",
                cursor:"pointer",
                fontSize:"14px",
                transition:"all 0.2s ease"
              }}
              onMouseEnter={(e) => {
                e.target.style.background = "var(--muted)";
                e.target.style.color = "var(--bg-void)";
              }}
              onMouseLeave={(e) => {
                e.target.style.background = "var(--panel)";
                e.target.style.color = "var(--text)";
              }}
            >
              ← Back to Mode Selection
            </button>
          </div>

          {/* Mode Indicator */}
          <div style={{
            padding:"8px 16px",
            background:"var(--panel)",
            border:"1px solid " + (selectedMode === 'taser' ? 'var(--lcars-orange)' : selectedMode === 'hawkeye' ? 'var(--lcars-blue)' : 'var(--lcars-gold)'),
            borderRadius:"20px",
            color: selectedMode === 'taser' ? 'var(--lcars-orange)' : selectedMode === 'hawkeye' ? 'var(--lcars-blue)' : 'var(--lcars-gold)',
            fontSize:"14px",
            fontWeight:"600",
            marginBottom:"24px",
            textTransform:"uppercase"
          }}>
            {selectedMode === 'taser' ? '⚡ TASER MODE' : selectedMode === 'hawkeye' ? '🚗 HAWKEYE MODE' : '🎯 ALL MODE'}
          </div>

          <h1 style={{
            letterSpacing:"1px", 
            fontSize:"4rem", 
            marginBottom:"4px",
            color:"var(--lcars-gold)",
            textShadow:"0 0 24px rgba(255, 209, 102, 0.25)",
            fontWeight:"700"
          }}>
            PROTOCAM
          </h1>
          <p style={{
            color:"var(--muted)", 
            fontSize:"1.3rem", 
            marginBottom:"16px",
            lineHeight:"1.6"
          }}>
            Upload your video:
          </p>
          
          {/* Main Upload Panel */}
          <div className="panel" style={{
            padding:"32px", 
            width:"100%",
            maxWidth:"600px",
            background:"var(--bg-raised)",
            border:"2px solid rgb(33, 33, 33)",
            boxShadow:"0 20px 40px rgba(0, 0, 0, 0.4)",
            borderRadius:"20px"
          }}>
            {!isProcessing ? (
              <>
                {/* File Upload Area */}
                <div style={{
                  position:"relative",
                  minHeight:"120px",
                  border:`2px dashed ${file ? 'var(--lcars-gold)' : '#5b819f'}`,
                  borderRadius:"16px",
                  background:`${file ? 'rgba(255, 209, 102, 0.1)' : 'rgba(100, 181, 246, 0.05)'}`,
                  display:"flex",
                  alignItems:"center",
                  justifyContent:"center",
                  cursor:"pointer",
                  transition:"all 0.3s ease",
                  marginBottom:"32px",
                  padding:"32px",
                  overflow:"hidden"
                }}
                onClick={() => document.getElementById('file-upload').click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const files = e.dataTransfer.files;
                  if (files[0]) {
                    handleFileSelect({target: {files}});
                  }
                }}
                >
                  <input 
                    id="file-upload"
                    type="file" 
                    accept="video/*" 
                    onChange={handleFileSelect}
                    style={{
                      display:"none"
                    }}
                  />
                  
                  {!file ? (
                    <div style={{textAlign:"center", color:"var(--text)"}}>
                      <div style={{fontSize:"3rem", marginBottom:"12px"}}>📁</div>
                      <div style={{fontSize:"1.2rem", fontWeight:"600", marginBottom:"8px"}}>
                        Click to select or drag & drop video
                      </div>
                      <div style={{fontSize:"1rem", color:"var(--muted)"}}>
                        Supports MP4 & MOV formats
                      </div>
                    </div>
                  ) : (
                    <div style={{textAlign:"center", color:"var(--lcars-gold)"}}>
                      <div style={{fontSize:"3rem", marginBottom:"12px"}}>✅</div>
                      <div style={{fontSize:"1.2rem", fontWeight:"bold", marginBottom:"8px"}}>
                        {file.name}
                      </div>
                      <div style={{fontSize:"1rem", color:"var(--muted)"}}>
                        {formatFileSize(file.size)} • Ready for processing
                      </div>
                    </div>
                  )}
      </div>

                {/* Submit Button - only show when file is selected */}
                {file && (
                  <div style={{
                    display:"flex", 
                    justifyContent:"center",
                    marginTop:"24px"
                  }}>
                    <button 
                      className="lcars-btn" 
                      onClick={onUpload}
                      style={{
                        padding:"16px 32px",
                        fontSize:"1.1rem",
                        fontWeight:"600",
                        background:"var(--lcars-blue)",
                        color:"var(--bg-void)",
                        border:"none",
                        borderRadius:"12px",
                        cursor:"pointer",
                        transition:"all 0.3s ease",
                        boxShadow:"0 4px 12px rgba(100, 181, 246, 0.3)"
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.background = "var(--lcars-gold)";
                        e.target.style.transform = "translateY(-2px)";
                        e.target.style.boxShadow = "0 6px 16px rgba(255, 209, 102, 0.4)";
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.background = "var(--lcars-blue)";
                        e.target.style.transform = "translateY(0)";
                        e.target.style.boxShadow = "0 4px 12px rgba(100, 181, 246, 0.3)";
                      }}
                    >
                      🚀 Start Processing
                    </button>
                  </div>
                )}
              </>
            ) : (
              // Processing State
              <div style={{textAlign:"center", padding:"40px 0"}}>
                <div style={{
                  width:"60px",
                  height:"60px",
                  border:"4px solid var(--lcars-blue)",
                  borderTop:"4px solid transparent",
                  borderRadius:"50%",
                  animation:"spin 1s linear infinite",
                  margin:"0 auto 24px auto"
                }}></div>
                <h3 style={{
                  color:"var(--lcars-blue)", 
                  fontSize:"1.4rem",
                  marginBottom:"16px"
                }}>
                  Processing Video...
                </h3>
                <div style={{
                  padding:"16px 24px",
                  background:"rgba(100, 181, 246, 0.1)",
                  borderRadius:"12px",
                  color:"var(--lcars-blue)",
                  fontSize:"1.1rem",
                  fontWeight:"500"
                }}>
                  ⚡ Beep Boop Beep Bop...
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        // Results page - full interface
        <div style={{maxWidth:"1400px", margin:"0 auto", padding:"24px 0"}}>
          {/* Back Button */}
          <div style={{
            position:"absolute",
            top:"24px",
            left:"24px"
          }}>
            <button 
              onClick={() => {
                setSelectedMode(null);
                setFile(null);
                setVideoPreview(null);
                setJob(null);
              }}
              style={{
                padding:"12px 20px",
                background:"var(--panel)",
                border:"1px solid var(--muted)",
                borderRadius:"8px",
                color:"var(--text)",
                cursor:"pointer",
                fontSize:"14px",
                transition:"all 0.2s ease"
              }}
              onMouseEnter={(e) => {
                e.target.style.background = "var(--muted)";
                e.target.style.color = "var(--bg-void)";
              }}
              onMouseLeave={(e) => {
                e.target.style.background = "var(--panel)";
                e.target.style.color = "var(--text)";
              }}
            >
              ← Back to Mode Selection
            </button>
          </div>

          <h1 style={{letterSpacing:"1px", marginBottom:"24px"}}>PROTOCAM</h1>

          {/* Mode Indicator */}
          <div style={{
            padding:"8px 16px",
            background:"var(--panel)",
            border:"1px solid " + (selectedMode === 'taser' ? 'var(--lcars-orange)' : selectedMode === 'hawkeye' ? 'var(--lcars-blue)' : 'var(--lcars-gold)'),
            borderRadius:"20px",
            color: selectedMode === 'taser' ? 'var(--lcars-orange)' : selectedMode === 'hawkeye' ? 'var(--lcars-blue)' : 'var(--lcars-gold)',
            fontSize:"14px",
            fontWeight:"600",
            marginBottom:"24px",
            textTransform:"uppercase",
            display:"inline-block"
          }}>
            {selectedMode === 'taser' ? '⚡ TASER MODE' : selectedMode === 'hawkeye' ? '🚗 HAWKEYE MODE' : '🎯 ALL MODE'}
          </div>

          {/* File Preview Section */}
          {file && (
        <div className="panel" style={{marginTop:16}}>
          <h3 style={{margin:"0 0 12px 0", color:"var(--lcars-gold)"}}>Selected Video</h3>
          <div style={{display:"flex", gap:16, alignItems:"flex-start"}}>
            {videoPreview && (
              <div style={{flex:"0 0 200px"}}>
                <video 
                  src={videoPreview} 
                  style={{
                    width:"100%", 
                    height:"120px", 
                    objectFit:"cover", 
                    borderRadius:"8px",
                    background:"var(--bg-void)"
                  }}
                  muted
                  controls={false}
                  poster=""
                />
              </div>
            )}
            <div style={{flex:1}}>
              <div style={{marginBottom:8}}>
                <strong style={{color:"var(--text)"}}>{file.name}</strong>
              </div>
              <div style={{color:"var(--muted)", fontSize:"14px"}}>
                <div>Size: {formatFileSize(file.size)}</div>
                <div>Type: {file.type}</div>
                <div>Last Modified: {new Date(file.lastModified).toLocaleString()}</div>
              </div>
              {isProcessing && (
                <div 
                  className="processing"
                  style={{
                    marginTop:12, 
                    padding:"8px 12px", 
                    background:"var(--lcars-blue)", 
                    color:"var(--bg-void)", 
                    borderRadius:"6px",
                    fontSize:"14px",
                    fontWeight:"600"
                  }}
                >
                  ⚡ Beep Boop Beep Bop...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

          {/* Figma Design Integration Panel */}
          <FigmaDesignPanel 
            onApplyDesign={applyFigmaDesign}
            visualSettings={visualSettings}
          />

          {/* Visual Customization Toolbar */}
          <div className="panel" style={{marginBottom:16}}>
            <div style={{display:"flex", alignItems:"center", marginBottom:12}}>
              <h3 style={{margin:0, color:"var(--lcars-gold)", flex:1}}>Visual Customization</h3>
              <button 
                className="lcars-btn"
                onClick={() => setShowToolbar(!showToolbar)}
                style={{padding:"6px 12px", fontSize:"14px"}}
              >
                {showToolbar ? "Hide Settings" : "Show Settings"}
              </button>
            </div>
            
            {showToolbar && (
              <div className="visual-toolbar" style={{
                display:"grid", 
                gridTemplateColumns:"repeat(auto-fit, minmax(280px, 1fr))", 
                gap:16,
                padding:"16px 0"
              }}>
                
                {/* Person Bounding Box Settings */}
                <div className="setting-group">
                  <h4 style={{color:"var(--lcars-blue)", margin:"0 0 8px 0"}}>👤 Person Boxes</h4>
                  <div className="setting-item">
                    <label>Locked Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.personLockedBoxColor}
                      onChange={(e) => updateVisualSetting('personLockedBoxColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Default Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.personUnlockedBoxColor}
                      onChange={(e) => updateVisualSetting('personUnlockedBoxColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Far Distance Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.personFarBoxColor}
                      onChange={(e) => updateVisualSetting('personFarBoxColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Stroke Width:</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="8" 
                      value={pendingSettings.personBoxStrokeWidth}
                      onChange={(e) => updateVisualSetting('personBoxStrokeWidth', parseInt(e.target.value))}
                    />
                    <span>{pendingSettings.personBoxStrokeWidth}px</span>
                  </div>
                </div>

                {/* Vehicle Bounding Box Settings */}
                <div className="setting-group">
                  <h4 style={{color:"var(--lcars-blue)", margin:"0 0 8px 0"}}>🚗 Vehicle Boxes</h4>
                  <div className="setting-item">
                    <label>Locked Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.vehicleLockedBoxColor}
                      onChange={(e) => updateVisualSetting('vehicleLockedBoxColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Default Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.vehicleUnlockedBoxColor}
                      onChange={(e) => updateVisualSetting('vehicleUnlockedBoxColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Far Distance Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.vehicleFarBoxColor}
                      onChange={(e) => updateVisualSetting('vehicleFarBoxColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Stroke Width:</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="8" 
                      value={pendingSettings.vehicleBoxStrokeWidth}
                      onChange={(e) => updateVisualSetting('vehicleBoxStrokeWidth', parseInt(e.target.value))}
                    />
                    <span>{pendingSettings.vehicleBoxStrokeWidth}px</span>
                  </div>
                  <div className="setting-item">
                    <label>Line Style:</label>
                    <select 
                      value={pendingSettings.boxStyle}
                      onChange={(e) => updateVisualSetting('boxStyle', e.target.value)}
                    >
                      <option value="solid">Solid</option>
                      <option value="dashed">Dashed</option>
                    </select>
                  </div>
                </div>

                {/* Text Settings */}
                <div className="setting-group">
                  <h4 style={{color:"var(--lcars-blue)", margin:"0 0 8px 0"}}>Text Labels</h4>
                  <div className="setting-item">
                    <label>Text Size:</label>
                    <input 
                      type="range" 
                      min="8" 
                      max="20" 
                      value={pendingSettings.textSize}
                      onChange={(e) => updateVisualSetting('textSize', parseInt(e.target.value))}
                    />
                    <span>{pendingSettings.textSize}px</span>
                  </div>
                  <div className="setting-item">
                    <label>Person ID Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.personIdTextColor}
                      onChange={(e) => updateVisualSetting('personIdTextColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Person Locked Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.personIdLockedTextColor}
                      onChange={(e) => updateVisualSetting('personIdLockedTextColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Vehicle ID Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.vehicleIdTextColor}
                      onChange={(e) => updateVisualSetting('vehicleIdTextColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Vehicle Locked Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.vehicleIdLockedTextColor}
                      onChange={(e) => updateVisualSetting('vehicleIdLockedTextColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Distance Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.distanceTextColor}
                      onChange={(e) => updateVisualSetting('distanceTextColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Object Type Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.objectTypeTextColor}
                      onChange={(e) => updateVisualSetting('objectTypeTextColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Show Object Types:</label>
                    <input 
                      type="checkbox" 
                      checked={pendingSettings.showObjectTypes}
                      onChange={(e) => updateVisualSetting('showObjectTypes', e.target.checked)}
                      style={{
                        width:"20px", 
                        height:"20px", 
                        accentColor:"var(--lcars-orange)",
                        cursor:"pointer"
                      }}
                    />
                  </div>
                </div>

                {/* Crosshair Settings */}
                <div className="setting-group">
                  <h4 style={{color:"var(--lcars-blue)", margin:"0 0 8px 0"}}>Crosshair</h4>
                  <div className="setting-item">
                    <label>Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.crosshairColor}
                      onChange={(e) => updateVisualSetting('crosshairColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Size:</label>
                    <input 
                      type="range" 
                      min="10" 
                      max="40" 
                      value={pendingSettings.crosshairSize}
                      onChange={(e) => updateVisualSetting('crosshairSize', parseInt(e.target.value))}
                    />
                    <span>{pendingSettings.crosshairSize}px</span>
                  </div>
                  <div className="setting-item">
                    <label>Width:</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="5" 
                      value={pendingSettings.crosshairWidth}
                      onChange={(e) => updateVisualSetting('crosshairWidth', parseInt(e.target.value))}
                    />
                    <span>{pendingSettings.crosshairWidth}px</span>
                  </div>
                  <div className="setting-item">
                    <label>Style:</label>
                    <select 
                      value={pendingSettings.crosshairStyle}
                      onChange={(e) => updateVisualSetting('crosshairStyle', e.target.value)}
                    >
                      <option value="lines">Lines</option>
                      <option value="circle">Circle</option>
                      <option value="cross">Cross</option>
                      <option value="custom">Custom Image</option>
                    </select>
                  </div>
                  {pendingSettings.crosshairStyle === 'custom' && (
                    <div className="setting-item">
                      <label>Upload Image:</label>
                      <input 
                        type="file" 
                        accept="image/*"
                        onChange={(e) => handleImageUpload('customCrosshairImage', e.target.files[0])}
                      />
                    </div>
                  )}
                </div>

                {/* Tracking Dot Settings */}
                <div className="setting-group">
                  <h4 style={{color:"var(--lcars-blue)", margin:"0 0 8px 0"}}>Tracking Dot</h4>
                  <div className="setting-item">
                    <label>Color:</label>
                    <input 
                      type="color" 
                      value={pendingSettings.trackingDotColor}
                      onChange={(e) => updateVisualSetting('trackingDotColor', e.target.value)}
                    />
                  </div>
                  <div className="setting-item">
                    <label>Size:</label>
                    <input 
                      type="range" 
                      min="3" 
                      max="15" 
                      value={pendingSettings.trackingDotSize}
                      onChange={(e) => updateVisualSetting('trackingDotSize', parseInt(e.target.value))}
                    />
                    <span>{pendingSettings.trackingDotSize}px</span>
                  </div>
                  <div className="setting-item">
                    <label>Style:</label>
                    <select 
                      value={pendingSettings.trackingDotStyle}
                      onChange={(e) => updateVisualSetting('trackingDotStyle', e.target.value)}
                    >
                      <option value="solid">Solid Dot</option>
                      <option value="ring">Ring</option>
                      <option value="cross">Cross</option>
                      <option value="custom">Custom Image</option>
                    </select>
                  </div>
                  {pendingSettings.trackingDotStyle === 'custom' && (
                    <div className="setting-item">
                      <label>Upload Image:</label>
                      <input 
                        type="file" 
                        accept="image/*"
                        onChange={(e) => handleImageUpload('customTrackingImage', e.target.files[0])}
                      />
                    </div>
                  )}
                </div>
                
                {/* Apply/Reset Buttons */}
                <div style={{
                  display:"flex", 
                  justifyContent:"flex-end", 
                  gap:8, 
                  paddingTop:12, 
                  borderTop:"1px solid var(--lcars-blue)",
                  marginTop:16
                }}>
                  
                  
                  <button 
                    className="lcars-btn"
                    onClick={resetVisualChanges}
                    disabled={!hasUnappliedChanges}
                    style={{
                      padding:"8px 16px",
                      height:"40px",
                      background: hasUnappliedChanges ? "rgb(255 255 255 .5)" : "var(--muted)", 
                      opacity: hasUnappliedChanges ? 1 : 0.6
                    }}
                  >
                    ↺ Reset
                  </button>
                  <button 
                    className="lcars-btn"
                    onClick={applyVisualChanges}
                    disabled={!hasUnappliedChanges}
                    style={{
                      padding:"8px 16px",
                      background: hasUnappliedChanges ? "var(--lcars-blue)" : "var(--muted)",
                      height:"40px",
                      opacity: hasUnappliedChanges ? 1 : 0.6
                    }}
                  >
                    {hasUnappliedChanges ? "Apply Changes" : "✅ Changes Applied"}
                  </button>
                </div>
              </div>
            )}
          </div>
          <PrototypePlayer 
            jobId={job.jobId} 
            resultsUrl={job.resultUrl}
            videoUrl={job.videoUrl}
            visualSettings={visualSettings}
            mode={selectedMode}
          />
        </div>
      )}
    </div>
  );
}
