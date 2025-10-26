import { useEffect, useRef, useState } from "react";

export default function PrototypePlayer({ jobId, resultsUrl, videoUrl, visualSettings, mode }){
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [results,setResults] = useState(null);
  
  // Hawkeye mode tracking state
  const [vehicleTrackingHistory, setVehicleTrackingHistory] = useState(new Map());
  const [lastKnownPositions, setLastKnownPositions] = useState(new Map());
  
  // Sticky priority tracking state
  const [currentPriorityId, setCurrentPriorityId] = useState(null);
  const [priorityLockTime, setPriorityLockTime] = useState(null);
  const [challengerHistory, setChallengerHistory] = useState(new Map());
  
  // Cache for crosshair images
  const crosshairImagesRef = useRef({
    default: null,
    active: null,
    defaultLoaded: false,
    activeLoaded: false
  });
  
  // Track lock timestamps for body tracker charging timer (5 seconds)
  const lockTimestampsRef = useRef({});

      // Default visual settings if none provided
  const settings = visualSettings || {
    // Person settings
    personLockedBoxColor: "#34c759",
    personUnlockedBoxColor: "#ffffff",
    personFarBoxColor: "#ff3b30",
    personBoxStrokeWidth: 1,
    personIdTextColor: "#ffffff",
    personIdLockedTextColor: "#34c759",
    personGreyColor: "#808080",
    
    // Vehicle settings
    vehicleLockedBoxColor: "#007aff",
    vehicleUnlockedBoxColor: "#ffcc00",
    vehicleFarBoxColor: "#ff9500",
    vehicleBoxStrokeWidth: 2,
    vehicleIdTextColor: "#ffcc00",
    vehicleIdLockedTextColor: "#007aff",
    vehicleGreyColor: "#808080",
    
    // General settings
    boxStyle: "solid",
    textSize: 12,
    distanceTextColor: "#ffd166",
    objectTypeTextColor: "#ff6b6b",
    textBackgroundOpacity: 0.7,
    crosshairColor: "#ffd166",
    crosshairSize: 20,
    crosshairWidth: 2,
    crosshairStyle: "lines",
    trackingDotColor: "#34c759",
    trackingDotSize: 6,
    trackingDotStyle: "solid",
    overlayOpacity: 1.0,
    showStats: true,
    showObjectTypes: true,
    enableCrosshair: true,
    showStatusSquare: false,
  };

  useEffect(()=>{
    (async ()=>{
      const r = await fetch(resultsUrl);
      const j = await r.json();
      setResults(j);
    })();
  },[resultsUrl]);
  
  // Load crosshair images when settings change
  useEffect(() => {
    if (settings.crosshairDefaultImage && settings.crosshairDefaultImage !== crosshairImagesRef.current.defaultSrc) {
      const img = new Image();
      img.onload = () => {
        crosshairImagesRef.current.default = img;
        crosshairImagesRef.current.defaultLoaded = true;
        crosshairImagesRef.current.defaultSrc = settings.crosshairDefaultImage;
      };
      img.onerror = () => {
        console.warn('Failed to load default crosshair image');
        crosshairImagesRef.current.defaultLoaded = false;
      };
      img.src = settings.crosshairDefaultImage;
    }
    
    if (settings.crosshairActiveImage && settings.crosshairActiveImage !== crosshairImagesRef.current.activeSrc) {
      const img = new Image();
      img.onload = () => {
        crosshairImagesRef.current.active = img;
        crosshairImagesRef.current.activeLoaded = true;
        crosshairImagesRef.current.activeSrc = settings.crosshairActiveImage;
      };
      img.onerror = () => {
        console.warn('Failed to load active crosshair image');
        crosshairImagesRef.current.activeLoaded = false;
      };
      img.src = settings.crosshairActiveImage;
    }
  }, [settings.crosshairDefaultImage, settings.crosshairActiveImage]);

  useEffect(()=>{
    if(!results || !videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    const meta = results.meta;
    const track = results.tracks; // [{frame,id,x,y,w,h,score}...]

    function resize(){
      const w = 960; 
      const h = Math.round(w * (meta.height/meta.width));
      
      // Size video element
      video.style.width = `${w}px`;
      video.style.height = `${h}px`;
      
      // Size canvas to match video
      canvas.width = w * window.devicePixelRatio;
      canvas.height = h * window.devicePixelRatio;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(window.devicePixelRatio,0,0,window.devicePixelRatio,0,0);
    }
    
    // Helper functions for Hawkeye mode
    const filterValidVehicles = (vehicles, canvasWidth) => {
      return vehicles.filter(v => {
        const centerX = v.x + v.w / 2;
        // Filter vehicles that are too far left/right (10% margins)
        return centerX >= 0.1 && centerX <= 0.9;
      });
    };

    const calculateDistance = (boxHeight, isVehicle) => {
      if (isVehicle) {
        const averageVehicleHeight = 1.5; // meters
        if (boxHeight > 0.6) return Math.round(averageVehicleHeight / boxHeight * 0.8);
        if (boxHeight > 0.3) return Math.round(averageVehicleHeight / boxHeight * 2);
        if (boxHeight > 0.15) return Math.round(averageVehicleHeight / boxHeight * 4);
        if (boxHeight > 0.08) return Math.round(averageVehicleHeight / boxHeight * 6);
        return Math.round(averageVehicleHeight / boxHeight * 10);
      } else {
        const averageHumanHeight = 1.7; // meters
        if (boxHeight > 0.8) return Math.round(averageHumanHeight / boxHeight * 0.5);
        if (boxHeight > 0.4) return Math.round(averageHumanHeight / boxHeight * 1.5);
        if (boxHeight > 0.2) return Math.round(averageHumanHeight / boxHeight * 3);
        if (boxHeight > 0.1) return Math.round(averageHumanHeight / boxHeight * 5);
        return Math.round(averageHumanHeight / boxHeight * 8);
      }
    };

    const selectPriorityVehicle = (vehicles, centerX, centerY, history, currentTime) => {
      if (vehicles.length === 0) {
        // No vehicles available, clear priority
        setCurrentPriorityId(null);
        setPriorityLockTime(null);
        setChallengerHistory(new Map());
        return null;
      }
      
      // Constants for sticky priority system
      const LOCK_DURATION_MS = 5000; // 5 seconds lock duration
      const SWITCHING_THRESHOLD = 0.4; // 40% better positioning required
      const TRACKING_MULTIPLIER = 2; // 2x more tracking history required
      const BOUNDARY_LIMIT = 0.85; // 85% screen width limit
      const CONFIDENCE_DECAY_MS = 2000; // 2 seconds for gradual transition
      
      // Check if current priority vehicle is still available and within boundaries
      let currentPriorityVehicle = null;
      if (currentPriorityId) {
        currentPriorityVehicle = vehicles.find(v => v.id === currentPriorityId);
        
        // Check if current priority is out of bounds
        if (currentPriorityVehicle) {
          const vehicleCenterX = currentPriorityVehicle.x + currentPriorityVehicle.w / 2;
          if (vehicleCenterX < (1 - BOUNDARY_LIMIT) || vehicleCenterX > BOUNDARY_LIMIT) {
            // Current priority is out of bounds, release it
            setCurrentPriorityId(null);
            setPriorityLockTime(null);
            setChallengerHistory(new Map());
            currentPriorityVehicle = null;
          }
        }
      }
      
      // If no current priority or it disappeared, select new one immediately
      if (!currentPriorityVehicle) {
        const newPriority = selectBestVehicle(vehicles, history);
        if (newPriority) {
          setCurrentPriorityId(newPriority.id);
          setPriorityLockTime(currentTime);
          setChallengerHistory(new Map());
        }
        return newPriority;
      }
      
      // Check if we're still in lock period
      const timeSinceLock = currentTime - (priorityLockTime || 0);
      const isInLockPeriod = timeSinceLock < LOCK_DURATION_MS;
      
      if (isInLockPeriod) {
        // During lock period, only switch if significantly better candidate emerges
        const bestChallenger = selectBestVehicle(vehicles.filter(v => v.id !== currentPriorityId), history);
        
        if (bestChallenger) {
          const currentScore = calculateVehicleScore(currentPriorityVehicle, history);
          const challengerScore = calculateVehicleScore(bestChallenger, history);
          
          // Require significant improvement to switch during lock period
          const improvementRequired = currentScore * (1 + SWITCHING_THRESHOLD);
          const trackingRequired = (history.get(currentPriorityId) || 0) * TRACKING_MULTIPLIER;
          const challengerTracking = history.get(bestChallenger.id) || 0;
          
          if (challengerScore > improvementRequired && challengerTracking > trackingRequired) {
            // Challenger is significantly better, switch immediately
            setCurrentPriorityId(bestChallenger.id);
            setPriorityLockTime(currentTime);
            setChallengerHistory(new Map());
            return bestChallenger;
          }
        }
        
        // Stay with current priority during lock period
        return currentPriorityVehicle;
      }
      
      // After lock period, use gradual transition with confidence decay
      const bestChallenger = selectBestVehicle(vehicles.filter(v => v.id !== currentPriorityId), history);
      
      if (bestChallenger) {
        const currentScore = calculateVehicleScore(currentPriorityVehicle, history);
        const challengerScore = calculateVehicleScore(bestChallenger, history);
        
        if (challengerScore > currentScore) {
          // Track how long this challenger has been better
          const newChallengerHistory = new Map(challengerHistory);
          const challengerFirstSeen = newChallengerHistory.get(bestChallenger.id) || currentTime;
          newChallengerHistory.set(bestChallenger.id, challengerFirstSeen);
          setChallengerHistory(newChallengerHistory);
          
          const timeChallenging = currentTime - challengerFirstSeen;
          
          if (timeChallenging >= CONFIDENCE_DECAY_MS) {
            // Challenger has been consistently better, switch now
            setCurrentPriorityId(bestChallenger.id);
            setPriorityLockTime(currentTime);
            setChallengerHistory(new Map());
            return bestChallenger;
          }
        } else {
          // Clear challenger history if no longer better
          setChallengerHistory(new Map());
        }
      }
      
      // Stay with current priority
      return currentPriorityVehicle;
    };
    
    const selectBestVehicle = (vehicles, history) => {
      if (vehicles.length === 0) return null;
      
      const scoredVehicles = vehicles.map(v => ({
        ...v,
        score: calculateVehicleScore(v, history)
      }));
      
      return scoredVehicles.sort((a, b) => b.score - a.score)[0];
    };
    
    const calculateVehicleScore = (vehicle, history) => {
      const vehicleCenterX = (vehicle.x + vehicle.w / 2);
      const vehicleCenterY = (vehicle.y + vehicle.h / 2);
      const distanceFromCenter = Math.sqrt(
        Math.pow(vehicleCenterX - 0.5, 2) + Math.pow(vehicleCenterY - 0.5, 2)
      );
      
      const trackingFrames = history.get(vehicle.id) || 0;
      
      // Score: closer to center (60%) + longer tracking history (40%)
      return (1 - distanceFromCenter) * 0.6 + (trackingFrames / 100) * 0.4;
    };

    function updateTracking(){
      if (video.paused || video.ended) return;
      
      const currentTime = video.currentTime;
      const frameRate = meta.fps;
      const currentFrame = Math.floor(currentTime * frameRate);
      
      ctx.clearRect(0,0,canvas.width,canvas.height);
      const w = canvas.width / window.devicePixelRatio;
      const h = canvas.height / window.devicePixelRatio;

      // Find boxes for this frame, with fallback for missing frames
      let boxes = track.filter(b=>b.frame===currentFrame);
      
      // If no tracking data for current frame, find nearest frames and interpolate
      if (boxes.length === 0) {
        const prevFrameData = track.filter(b=>b.frame < currentFrame).slice(-20);
        const nextFrameData = track.filter(b=>b.frame > currentFrame).slice(0, 20);
        
        if (prevFrameData.length > 0) {
          const latestFrame = Math.max(...prevFrameData.map(b => b.frame));
          boxes = prevFrameData.filter(b => b.frame === latestFrame);
        }
      }

      // Separate vehicles and people
      const vehicles = boxes.filter(b => b.is_vehicle);
      const people = boxes.filter(b => !b.is_vehicle);
      
      // For Hawkeye mode, filter and prioritize vehicles
      let priorityVehicle = null;
      let validVehicles = vehicles;
      
      if (mode === 'hawkeye') {
        validVehicles = filterValidVehicles(vehicles, w);
        
        // Update tracking history
        const newHistory = new Map(vehicleTrackingHistory);
        validVehicles.forEach(v => {
          const currentCount = newHistory.get(v.id) || 0;
          newHistory.set(v.id, currentCount + 1);
        });
        setVehicleTrackingHistory(newHistory);
        
        // Update last known positions
        const newPositions = new Map(lastKnownPositions);
        validVehicles.forEach(v => {
          newPositions.set(v.id, {
            x: v.x,
            y: v.y,
            w: v.w,
            h: v.h,
            frame: currentFrame,
            distance: calculateDistance(v.h, true)
          });
        });
        setLastKnownPositions(newPositions);
        
        // Select priority vehicle with sticky tracking
        priorityVehicle = selectPriorityVehicle(validVehicles, w/2, h/2, newHistory, Date.now());
        
        // Add distance calculation to priority vehicle
        if (priorityVehicle) {
          priorityVehicle.distance = calculateDistance(priorityVehicle.h, true);
        }
      }

      let lockedObject = null; // Track the object under crosshair
      
      // Render all objects
      for(const b of boxes){
        const x = b.x * w, y = b.y * h, bw = b.w * w, bh = b.h * h;
        const cx = w/2, cy = h/2;
        const isLocked = cx > x && cx < x+bw && cy > y && cy < y+bh;
        const isVehicle = b.is_vehicle || false;
        const objectType = b.object_type || 'person';
        const isSelectedVehicle = mode === 'hawkeye' && priorityVehicle && b.id === priorityVehicle.id;
        
        // Store the locked object for tracking dot (people only)
        if (isLocked && !isVehicle) {
          lockedObject = {
            waistX: x + bw/2,
            waistY: y + bh * 0.35,
            id: b.id
          };
        }
        
        // Skip vehicles that are filtered out in Hawkeye mode
        if (mode === 'hawkeye' && isVehicle && !validVehicles.some(v => v.id === b.id)) {
          continue;
        }
        
        const estimatedDistance = calculateDistance(b.h, isVehicle);
        const distanceText = estimatedDistance > 100 ? "100+ m" : `${Math.max(1, estimatedDistance)} m`;
        
        // Determine box color and styling with individual properties
        let boxColor;
        let strokeWidth;
        let borderRadius = 0;
        let backgroundFillColor = null;
        let backgroundOpacity = 0.2;
        
        const isPriorityObject = (mode === 'taser' && !isVehicle) || 
                                (mode === 'hawkeye' && isVehicle) || 
                                (mode === 'all');
        
        if (!isPriorityObject) {
          // Non-priority objects (grey)
          boxColor = isVehicle ? settings.vehicleGreyColor : settings.personGreyColor;
          strokeWidth = isVehicle ? settings.vehicleBoxStrokeWidth : (settings.personGreyStrokeWidth || settings.personBoxStrokeWidth);
          if (!isVehicle) {
            backgroundFillColor = settings.personGreyBackgroundColor;
            backgroundOpacity = settings.personGreyBackgroundOpacity || 0.2;
            borderRadius = settings.personGreyBorderRadius || 0;
          }
        } else if (isVehicle) {
          strokeWidth = settings.vehicleBoxStrokeWidth;
          
          if (isSelectedVehicle) {
            // Special styling for selected/priority vehicle
            boxColor = estimatedDistance <= 5 ? "#00ff00" : "#ff0000"; // Green if ≤5m, red if >5m
            strokeWidth = 4; // Thicker border for selected vehicle
          } else if (isLocked) {
            boxColor = estimatedDistance > 20 ? settings.vehicleFarBoxColor : settings.vehicleLockedBoxColor;
          } else {
            boxColor = settings.vehicleUnlockedBoxColor;
          }
        } else {
          // Person boxes with full background support and individual properties
          if (isLocked) {
            if (estimatedDistance > 15) {
              // Far distance person
              boxColor = settings.personFarBoxColor;
              strokeWidth = settings.personFarBoxStrokeWidth || settings.personBoxStrokeWidth;
              borderRadius = settings.personFarBoxBorderRadius || 0;
              backgroundFillColor = settings.personFarBoxBackgroundColor;
              backgroundOpacity = settings.personFarBoxBackgroundOpacity || 0.2;
            } else {
              // Locked/targeted person
              boxColor = settings.personLockedBoxColor;
              strokeWidth = settings.personLockedBoxStrokeWidth || settings.personBoxStrokeWidth;
              borderRadius = settings.personLockedBoxBorderRadius || 0;
              backgroundFillColor = settings.personLockedBoxBackgroundColor;
              backgroundOpacity = settings.personLockedBoxBackgroundOpacity || 0.2;
            }
          } else {
            // Default/unlocked person
            boxColor = settings.personUnlockedBoxColor;
            strokeWidth = settings.personUnlockedBoxStrokeWidth || settings.personBoxStrokeWidth;
            borderRadius = settings.personUnlockedBoxBorderRadius || 0;
            backgroundFillColor = settings.personUnlockedBoxBackgroundColor;
            backgroundOpacity = settings.personUnlockedBoxBackgroundOpacity || 0.2;
          }
        }
        
        // Draw background fill first (if available and not null)
        if (backgroundFillColor && backgroundFillColor !== 'null' && !isVehicle) {
          // Handle both RGBA strings and hex colors
          ctx.fillStyle = backgroundFillColor;
          
          // If it's not already an RGBA string, apply the opacity manually
          if (!backgroundFillColor.startsWith('rgba(') && backgroundOpacity !== undefined) {
            ctx.globalAlpha = backgroundOpacity;
          }
          
          // Draw rounded rectangle for background if border radius is specified
          if (borderRadius > 0) {
            ctx.beginPath();
            ctx.roundRect(x, y, bw, bh, borderRadius);
            ctx.fill();
          } else {
            ctx.fillRect(x, y, bw, bh);
          }
          
          // Reset global alpha if it was modified
          if (!backgroundFillColor.startsWith('rgba(')) {
            ctx.globalAlpha = 1.0;
          }
        }
        
        // Draw bounding box stroke
        ctx.strokeStyle = boxColor;
        ctx.setLineDash(isSelectedVehicle ? [8, 4] : (settings.boxStyle === 'dashed' ? (isLocked ? [] : [6,6]) : []));
        ctx.lineWidth = strokeWidth || 1; // Ensure we have a minimum stroke width
        
        // Draw rounded rectangle for stroke if border radius is specified
        if (borderRadius > 0 && !isVehicle) {
          ctx.beginPath();
          ctx.roundRect(x, y, bw, bh, borderRadius);
          ctx.stroke();
        } else {
          ctx.strokeRect(x, y, bw, bh);
        }
        
        // Draw labels
        const idText = `ID: ${b.id}${isSelectedVehicle ? ' [TRACKED]' : ''}`;
        const objectTypeText = objectType.toUpperCase();
        const distanceLabel = distanceText;
        
        ctx.font = "12px Inter, system-ui";
        const idMetrics = ctx.measureText(idText);
        const typeMetrics = ctx.measureText(objectTypeText);
        const distanceMetrics = ctx.measureText(distanceLabel);
        const idWidth = idMetrics.width;
        const typeWidth = typeMetrics.width;
        const distanceWidth = distanceMetrics.width;
        const textHeight = 16;
        const boxPadding = 4;
        const boxSpacing = 4;
        
        let currentX = x - 2;
        const labelY = y - textHeight - 2;
        
        // Determine object state for text styling (needed for all text elements)
        const isFar = isLocked && estimatedDistance > 15;
        const isBackground = !isPriorityObject;
        
        // ID box
        // Determine state-specific ID background color
        let idBackgroundColor = settings.personIdBackgroundColor || `rgba(0, 0, 0, ${settings.textBackgroundOpacity})`;
        
        if (isLocked && !isFar) {
          idBackgroundColor = settings.personIdLockedBackgroundColor || idBackgroundColor;
        } else if (isFar) {
          idBackgroundColor = settings.personIdFarBackgroundColor || idBackgroundColor;
        } else if (isBackground) {
          idBackgroundColor = settings.personIdGreyBackgroundColor || idBackgroundColor;
        }
        
        ctx.fillStyle = idBackgroundColor;
        ctx.fillRect(currentX, labelY, idWidth + boxPadding, textHeight + 2);
        
        // Determine state-specific ID text color
        let idColor;
        if (isVehicle) {
          idColor = (isLocked || isSelectedVehicle) ? settings.vehicleIdLockedTextColor : settings.vehicleIdTextColor;
        } else {
          // Person ID text with state-specific colors
          idColor = settings.personIdTextColor; // default
          
          if (isLocked && !isFar) {
            idColor = settings.personIdLockedTextColor || idColor;
          } else if (isFar) {
            idColor = settings.personIdFarTextColor || idColor;
          } else if (isBackground) {
            idColor = settings.personIdGreyTextColor || idColor;
          }
        }
        
        ctx.fillStyle = idColor;
        
        // Use enhanced text styling from Figma
        const idFontSize = settings.personIdTextSize || settings.textSize;
        const idFontFamily = settings.personIdTextFamily || 'Inter';
        const idFontWeight = settings.personIdTextWeight || 400;
        ctx.font = `${idFontWeight} ${idFontSize}px ${idFontFamily}`;
        ctx.fillText(idText, currentX + 2, y - 5);
        currentX += idWidth + boxSpacing;
        
        // Object type box
        if (settings.showObjectTypes) {
          // Determine state-specific object background color
          let objBackgroundColor = settings.objectTypeBackgroundColor || `rgba(60, 20, 20, ${settings.textBackgroundOpacity})`;
          
          if (isLocked && !isFar) {
            objBackgroundColor = settings.objectTypeLockedBackgroundColor || objBackgroundColor;
          } else if (isFar) {
            objBackgroundColor = settings.objectTypeFarBackgroundColor || objBackgroundColor;
          } else if (isBackground) {
            objBackgroundColor = settings.objectTypeGreyBackgroundColor || objBackgroundColor;
          }
          
          ctx.fillStyle = objBackgroundColor;
          ctx.fillRect(currentX, labelY, typeWidth + boxPadding, textHeight + 2);
          
          // Determine state-specific object text styling
          let objTextColor = settings.objectTypeTextColor;
          let objFontSize = settings.objectTypeTextSize || settings.textSize;
          let objFontFamily = settings.objectTypeTextFamily || 'Inter';
          let objFontWeight = settings.objectTypeTextWeight || 400;
          
          if (isLocked && !isFar) {
            objTextColor = settings.objectTypeLockedTextColor || objTextColor;
            objFontSize = settings.objectTypeLockedTextSize || objFontSize;
            objFontFamily = settings.objectTypeLockedTextFamily || objFontFamily;
            objFontWeight = settings.objectTypeLockedTextWeight || objFontWeight;
          } else if (isFar) {
            objTextColor = settings.objectTypeFarTextColor || objTextColor;
            objFontSize = settings.objectTypeFarTextSize || objFontSize;
            objFontFamily = settings.objectTypeFarTextFamily || objFontFamily;
            objFontWeight = settings.objectTypeFarTextWeight || objFontWeight;
          } else if (isBackground) {
            objTextColor = settings.objectTypeGreyTextColor || objTextColor;
            objFontSize = settings.objectTypeGreyTextSize || objFontSize;
            objFontFamily = settings.objectTypeGreyTextFamily || objFontFamily;
            objFontWeight = settings.objectTypeGreyTextWeight || objFontWeight;
          }
          
          ctx.fillStyle = objTextColor;
          ctx.font = `${objFontWeight} ${objFontSize}px ${objFontFamily}`;
          ctx.fillText(objectTypeText, currentX + 2, y - 5);
          currentX += typeWidth + boxSpacing;
        }
        
        // Distance box
        // Determine state-specific distance background color
        let distBackgroundColor = settings.distanceBackgroundColor || `rgba(20, 20, 60, ${settings.textBackgroundOpacity})`;
        
        if (isLocked && !isFar) {
          distBackgroundColor = settings.distanceLockedBackgroundColor || distBackgroundColor;
        } else if (isFar) {
          distBackgroundColor = settings.distanceFarBackgroundColor || distBackgroundColor;
        } else if (isBackground) {
          distBackgroundColor = settings.distanceGreyBackgroundColor || distBackgroundColor;
        }
        
        ctx.fillStyle = distBackgroundColor;
        ctx.fillRect(currentX, labelY, distanceWidth + boxPadding, textHeight + 2);
        
        // Determine state-specific distance text styling
        let distTextColor = settings.distanceTextColor;
        let distFontSize = settings.distanceTextSize || settings.textSize;
        let distFontFamily = settings.distanceTextFamily || 'Inter';
        let distFontWeight = settings.distanceTextWeight || 400;
        
        if (isLocked && !isFar) {
          distTextColor = settings.distanceLockedTextColor || distTextColor;
          distFontSize = settings.distanceLockedTextSize || distFontSize;
          distFontFamily = settings.distanceLockedTextFamily || distFontFamily;
          distFontWeight = settings.distanceLockedTextWeight || distFontWeight;
        } else if (isFar) {
          distTextColor = settings.distanceFarTextColor || distTextColor;
          distFontSize = settings.distanceFarTextSize || distFontSize;
          distFontFamily = settings.distanceFarTextFamily || distFontFamily;
          distFontWeight = settings.distanceFarTextWeight || distFontWeight;
        } else if (isBackground) {
          distTextColor = settings.distanceGreyTextColor || distTextColor;
          distFontSize = settings.distanceGreyTextSize || distFontSize;
          distFontFamily = settings.distanceGreyTextFamily || distFontFamily;
          distFontWeight = settings.distanceGreyTextWeight || distFontWeight;
        }
        
        ctx.fillStyle = distTextColor;
        ctx.font = `${distFontWeight} ${distFontSize}px ${distFontFamily}`;
        ctx.fillText(distanceLabel, currentX + 2, y - 5);
      }
      
      // Draw customizable chest tracking dot on locked person (people only)
      if (lockedObject) {
        // Track lock time for charging timer
        if (!lockTimestampsRef.current[lockedObject.id]) {
          lockTimestampsRef.current[lockedObject.id] = Date.now();
        }
        
        // Calculate charging progress (5 seconds to fully charge)
        const elapsed = Date.now() - lockTimestampsRef.current[lockedObject.id];
        const isReady = elapsed >= 5000;
        
        // Use Figma Body Tracker if available
        if (settings.useFigmaBodyTracker && (settings.bodyTrackerChargingProperties || settings.bodyTrackerReadyProperties)) {
          const properties = isReady ? settings.bodyTrackerReadyProperties : settings.bodyTrackerChargingProperties;
          
          if (properties) {
            const fillColor = properties.fillColor || settings.trackingDotColor;
            const strokeColor = properties.strokeColor;
            const strokeWidth = properties.strokeWidth || 0;
            const width = properties.width || settings.trackingDotSize * 2;
            const height = properties.height || settings.trackingDotSize * 2;
            const shape = properties.shape || 'circle';
            
            // Draw based on shape type
            if (shape === 'circle') {
              const radius = Math.max(width, height) / 2;
              
              // Fill
              if (fillColor) {
                ctx.fillStyle = fillColor;
                ctx.beginPath();
                ctx.arc(lockedObject.waistX, lockedObject.waistY, radius, 0, 2 * Math.PI);
                ctx.fill();
              }
              
              // Stroke
              if (strokeColor && strokeWidth > 0) {
                ctx.strokeStyle = strokeColor;
                ctx.lineWidth = strokeWidth;
                ctx.setLineDash([]);
                ctx.beginPath();
                ctx.arc(lockedObject.waistX, lockedObject.waistY, radius, 0, 2 * Math.PI);
                ctx.stroke();
              }
            } else if (shape === 'rectangle' || shape === 'rounded-rectangle') {
              const halfWidth = width / 2;
              const halfHeight = height / 2;
              const x = lockedObject.waistX - halfWidth;
              const y = lockedObject.waistY - halfHeight;
              
              // Fill
              if (fillColor) {
                ctx.fillStyle = fillColor;
                if (shape === 'rounded-rectangle') {
                  const radius = Math.min(width, height) * 0.2;
                  ctx.beginPath();
                  ctx.roundRect(x, y, width, height, radius);
                  ctx.fill();
                } else {
                  ctx.fillRect(x, y, width, height);
                }
              }
              
              // Stroke
              if (strokeColor && strokeWidth > 0) {
                ctx.strokeStyle = strokeColor;
                ctx.lineWidth = strokeWidth;
                ctx.setLineDash([]);
                if (shape === 'rounded-rectangle') {
                  const radius = Math.min(width, height) * 0.2;
                  ctx.beginPath();
                  ctx.roundRect(x, y, width, height, radius);
                  ctx.stroke();
                } else {
                  ctx.strokeRect(x, y, width, height);
                }
              }
            }
          } else {
            // Fallback to default if properties missing
            ctx.fillStyle = settings.trackingDotColor;
            ctx.beginPath();
            ctx.arc(lockedObject.waistX, lockedObject.waistY, settings.trackingDotSize, 0, 2 * Math.PI);
            ctx.fill();
          }
        } else if (settings.trackingDotStyle === 'custom' && settings.customTrackingImage) {
          const img = new Image();
          img.onload = () => {
            const size = settings.trackingDotSize * 2;
            ctx.drawImage(img, lockedObject.waistX - size/2, lockedObject.waistY - size/2, size, size);
          };
          img.onerror = () => {
            console.warn('Failed to load custom tracking dot image, falling back to default');
            // Fall back to default dot
            ctx.fillStyle = settings.trackingDotColor;
            ctx.beginPath();
            ctx.arc(lockedObject.waistX, lockedObject.waistY, settings.trackingDotSize, 0, 2 * Math.PI);
            ctx.fill();
          };
          img.src = settings.customTrackingImage;
        } else if (settings.trackingDotStyle === 'ring') {
          ctx.strokeStyle = settings.trackingDotColor;
          ctx.lineWidth = 2;
          ctx.setLineDash([]);
          ctx.beginPath();
          ctx.arc(lockedObject.waistX, lockedObject.waistY, settings.trackingDotSize, 0, 2 * Math.PI);
          ctx.stroke();
        } else if (settings.trackingDotStyle === 'cross') {
          ctx.strokeStyle = settings.trackingDotColor;
          ctx.lineWidth = 2;
          ctx.setLineDash([]);
          const size = settings.trackingDotSize;
          ctx.beginPath();
          ctx.moveTo(lockedObject.waistX - size, lockedObject.waistY);
          ctx.lineTo(lockedObject.waistX + size, lockedObject.waistY);
          ctx.moveTo(lockedObject.waistX, lockedObject.waistY - size);
          ctx.lineTo(lockedObject.waistX, lockedObject.waistY + size);
          ctx.stroke();
        } else {
          ctx.fillStyle = settings.trackingDotColor;
          ctx.beginPath();
          ctx.arc(lockedObject.waistX, lockedObject.waistY, settings.trackingDotSize, 0, 2 * Math.PI);
          ctx.fill();
          
          ctx.fillStyle = "#ffffff";
          ctx.beginPath();
          ctx.arc(lockedObject.waistX, lockedObject.waistY, settings.trackingDotSize/2, 0, 2 * Math.PI);
          ctx.fill();
          
          ctx.strokeStyle = settings.trackingDotColor;
          ctx.lineWidth = 1;
          ctx.setLineDash([]);
          ctx.beginPath();
          ctx.arc(lockedObject.waistX, lockedObject.waistY, settings.trackingDotSize * 2, 0, 2 * Math.PI);
          ctx.stroke();
        }
      } else {
        // Clear lock timestamps for objects that are no longer locked
        const currentTime = Date.now();
        for (const id in lockTimestampsRef.current) {
          if (currentTime - lockTimestampsRef.current[id] > 10000) {
            delete lockTimestampsRef.current[id];
          }
        }
      }
      
      // Draw dynamic crosshair at center (only if enabled)
      if (settings.enableCrosshair) {
        const centerX = w/2;
        const centerY = h/2;
        const crosshairSize = settings.crosshairSize;
        const halfSize = crosshairSize / 2;
        
        // Check if crosshair is over any object (existing logic)
        const isOverObject = lockedObject || boxes.some(b => {
          const x = b.x * w, y = b.y * h, bw = b.w * w, bh = b.h * h;
          return centerX > x && centerX < x+bw && centerY > y && centerY < y+bh;
        });
        
        // Helper function to draw default canvas crosshair
        const drawDefaultCrosshair = () => {
          ctx.strokeStyle = settings.crosshairColor;
          ctx.lineWidth = settings.crosshairWidth;
          ctx.setLineDash(isOverObject ? [] : [4, 4]);
          
          ctx.beginPath();
          if (settings.crosshairStyle === 'circle') {
            ctx.arc(centerX, centerY, halfSize, 0, 2 * Math.PI);
          } else if (settings.crosshairStyle === 'cross') {
            ctx.moveTo(centerX - halfSize, centerY - halfSize);
            ctx.lineTo(centerX + halfSize, centerY + halfSize);
            ctx.moveTo(centerX - halfSize, centerY + halfSize);
            ctx.lineTo(centerX + halfSize, centerY - halfSize);
          } else {
            ctx.moveTo(centerX - halfSize, centerY);
            ctx.lineTo(centerX + halfSize, centerY);
            ctx.moveTo(centerX, centerY - halfSize);
            ctx.lineTo(centerX, centerY + halfSize);
          }
          ctx.stroke();
          ctx.setLineDash([]);
        };
        
        // Use Figma images if available
        if (settings.useFigmaCrosshair && (crosshairImagesRef.current.defaultLoaded || crosshairImagesRef.current.activeLoaded)) {
          // Select the appropriate cached image and size
          const useActive = isOverObject && crosshairImagesRef.current.activeLoaded;
          const img = useActive ? crosshairImagesRef.current.active : crosshairImagesRef.current.default;
          
          // Use Figma-provided size if available, otherwise fall back to crosshairSize setting
          const figmaSize = useActive 
            ? (settings.crosshairActiveSize || crosshairSize)
            : (settings.crosshairDefaultSize || crosshairSize);
          const halfFigmaSize = figmaSize / 2;
          
          if (img) {
            ctx.drawImage(img, centerX - halfFigmaSize, centerY - halfFigmaSize, figmaSize, figmaSize);
          } else {
            drawDefaultCrosshair();
          }
        } else if (settings.crosshairStyle === 'custom' && settings.customCrosshairImage) {
          // Handle both base64 data URLs and regular URLs for custom images
          const img = new Image();
          img.onload = () => {
            ctx.drawImage(img, centerX - halfSize, centerY - halfSize, crosshairSize, crosshairSize);
          };
          img.onerror = () => {
            console.warn('Failed to load custom crosshair image, falling back to default');
            drawDefaultCrosshair();
          };
          img.src = settings.customCrosshairImage;
        } else {
          // Default canvas drawing
          drawDefaultCrosshair();
        }
      }
      
      // Fixed status square for Hawkeye mode (always bottom right corner)
      if (settings.showStatusSquare && mode === 'hawkeye') {
        const squareSize = 140;
        const margin = 20;
        
        // Always position in bottom right corner
        const squareX = w - squareSize - margin;
        const squareY = h - squareSize - margin;
        
        // Background with distance-based color
        const bgColor = priorityVehicle 
          ? (priorityVehicle.distance <= 5 ? "rgba(0, 255, 0, 0.8)" : "rgba(255, 0, 0, 0.8)")
          : "rgba(0, 0, 0, 0.8)";
        ctx.fillStyle = bgColor;
        ctx.fillRect(squareX, squareY, squareSize, squareSize);
        
        // Border with matching color
        const borderColor = priorityVehicle 
          ? (priorityVehicle.distance <= 5 ? "#00ff00" : "#ff0000")
          : "#007aff";
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = 3;
        ctx.setLineDash([]);
        ctx.strokeRect(squareX, squareY, squareSize, squareSize);
        
        // Status text with tracking state
        ctx.fillStyle = "#ffffff";
        ctx.font = "14px Inter";
        ctx.textAlign = "center";
        
        // Determine tracking state for display
        let trackingState = "SEARCHING";
        if (priorityVehicle && currentPriorityId === priorityVehicle.id) {
          const timeSinceLock = Date.now() - (priorityLockTime || 0);
          if (timeSinceLock < 5000) { // Within 5-second lock period
            trackingState = "LOCKED";
          } else {
            trackingState = "TRACKING";
          }
        }
        
        ctx.fillText("HAWKEYE", squareX + squareSize/2, squareY + 20);
        ctx.fillText(trackingState, squareX + squareSize/2, squareY + 35);
        
        if (priorityVehicle) {
          ctx.font = "12px Inter";
          ctx.fillText(`Vehicle ID: ${priorityVehicle.id}`, squareX + squareSize/2, squareY + 55);
          ctx.fillText(`Distance: ${priorityVehicle.distance}m`, squareX + squareSize/2, squareY + 70);
          ctx.fillText(`Status: ${priorityVehicle.distance <= 5 ? 'CLOSE' : 'PURSUIT'}`, squareX + squareSize/2, squareY + 85);
        } else {
          ctx.font = "12px Inter";
          ctx.fillText("NO TARGET", squareX + squareSize/2, squareY + 60);
          ctx.fillText(`Vehicles: ${validVehicles.length}`, squareX + squareSize/2, squareY + 80);
          ctx.fillText(`People: ${people.length}`, squareX + squareSize/2, squareY + 95);
        }
        
        ctx.textAlign = "left";
      }
      
      requestAnimationFrame(updateTracking);
    }

    resize();
    window.addEventListener("resize", resize);
    
    // Start tracking animation when video plays
    video.addEventListener('play', updateTracking);
    video.addEventListener('seeked', updateTracking);
    
    return ()=>{ 
      window.removeEventListener("resize", resize);
      video.removeEventListener('play', updateTracking);
      video.removeEventListener('seeked', updateTracking);
    }
  },[results, visualSettings, mode]); // Added mode to dependencies

  return (
    <div className="panel" style={{display:"grid", gridTemplateColumns:"1fr", gap:12}}>
      <div style={{position: "relative", display: "inline-block"}}>
        <video 
          ref={videoRef} 
          src={videoUrl}
          controls
          style={{
            display: "block",
            borderRadius: "8px",
            background: "var(--bg-void)"
          }}
        />
        <canvas 
          ref={canvasRef}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            pointerEvents: "none",
            borderRadius: "8px"
          }}
        />
      </div>
      <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
        <small style={{opacity:.7}}>Job: {jobId}</small>
        {results && (
          <small style={{opacity:.7, color: "var(--lcars-gold)"}}>
            {results.meta.frames} frames • {results.meta.fps} fps • {results.tracks.length} detections
            {(() => {
              // Calculate object type counts
              const typeCounts = {};
              results.tracks.forEach(track => {
                const type = track.object_type || 'person';
                typeCounts[type] = (typeCounts[type] || 0) + 1;
              });
              
              const countText = Object.entries(typeCounts)
                .map(([type, count]) => `${count} ${type}${count !== 1 ? 's' : ''}`)
                .join(' • ');
              
              return countText ? ` • ${countText}` : '';
            })()}
          </small>
        )}
      </div>
    </div>
  );
}

